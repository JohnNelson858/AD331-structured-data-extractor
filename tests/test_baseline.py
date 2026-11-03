"""Offline Step 2 smoke checks. Step 3 audit and full Step 5 QA remain separate."""
from io import BytesIO
import json
from pathlib import Path

import httpx
import openai
from pypdf import PdfWriter
import pytest

from src.cli import FixtureProvider
from src.extractor import SchemaExtractor, SYSTEM_PROMPT
from src.fallback import conservative_repair, reflection_messages
from src.ingestion import DocumentError, from_html, from_pdf
from src.provider import OpenAIProvider, ProviderReply

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("scenario,status,attempts", [
    ("success", "SUCCESS", 1),
    ("reflection", "REPAIRED_VIA_REFLECTION", 2),
    ("heuristic", "REPAIRED_VIA_HEURISTIC", 4),
    ("dlq", "DLQ_FAILED", 4),
])
async def test_offline_baseline_paths(tmp_path, scenario, status, attempts):
    source = from_pdf((ROOT / "samples/invoice_messy.pdf").read_bytes())
    provider = FixtureProvider(scenario)
    result = await SchemaExtractor(provider, tmp_path).extract_with_retry(source.text)
    assert result.execution_status == status
    assert result.attempts_used == provider.calls == attempts
    if status == "DLQ_FAILED":
        saved = json.loads(Path(result.dlq_path).read_text())
        assert saved["needs_human_review"] is True
        assert saved["attempts_used"] == 4
        assert result.validated_data is None
    else:
        assert str(result.validated_data.total_amount) == "1374.45"
    if scenario == "reflection":
        event = next(e for e in result.events if e.stage == "reflection_prompt")
        payload = json.loads(event.detail["messages"][1]["content"])
        assert "1500.00" in payload["previous_extraction"]
        assert payload["validation_errors"][0]["type"] == "value_error"


async def test_reflection_disabled_means_one_call(tmp_path):
    result = await SchemaExtractor(FixtureProvider("reflection"), tmp_path).extract_with_retry("Synthetic invoice document", reflection_enabled=False)
    assert result.attempts_used == 1
    assert result.execution_status == "DLQ_FAILED"
    assert not any(e.stage == "reflection_prompt" for e in result.events)


def test_html_preprocessing_preserves_invoice_and_removes_scripts():
    source = from_html((ROOT / "samples/vendor_contract.html").read_text())
    assert "INV-2024-1012" in source.text
    assert "$1,374.45" in source.text
    assert "console.log" not in source.text


def test_scan_without_text_is_explicitly_rejected():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = BytesIO()
    writer.write(buffer)
    with pytest.raises(DocumentError, match="OCR"):
        from_pdf(buffer.getvalue())


def test_reflection_context_is_bounded_and_not_accumulated():
    messages = reflection_messages(SYSTEM_PROMPT, "invoice text " * 5000, "{}", [{"loc": [], "msg": "bad total", "type": "value_error"}])
    assert len(messages) == 2
    assert len(json.loads(messages[1]["content"])["source_excerpt"]) <= 6000
    assert json.loads(messages[1]["content"])["source_excerpt_incomplete"] is True


def test_heuristic_rejects_truncation_and_preserves_string_commas():
    assert conservative_repair('{"invoice":') is None
    raw = '{"description": "keep comma, } text",}'
    assert json.loads(conservative_repair(raw)) == {"description": "keep comma, } text"}


async def test_provider_refusal_stops_without_heuristic(tmp_path):
    class Refusal:
        async def generate(self, messages):
            return ProviderReply("{}", "refusal")
    result = await SchemaExtractor(Refusal(), tmp_path).extract_with_retry("Synthetic source")
    assert result.attempts_used == 1
    assert result.execution_status == "DLQ_FAILED"
    assert not any(e.stage == "heuristic_validated" for e in result.events)


async def test_missing_source_information_is_not_retried(tmp_path):
    class Missing:
        async def generate(self, messages):
            return ProviderReply(json.dumps({"outcome": "insufficient_source", "invoice": None, "reason": "No invoice"}))
    result = await SchemaExtractor(Missing(), tmp_path).extract_with_retry("Put away the soldering iron.")
    assert result.attempts_used == 1
    assert result.validated_data is None
    assert result.execution_status == "DLQ_FAILED"


async def test_real_sdk_request_uses_native_strict_schema_with_mock_http():
    seen = []
    def transport(request):
        body = json.loads(request.content)
        seen.append(body)
        invoice = json.loads((ROOT / "samples/invoice_expected.json").read_text())
        envelope = json.dumps({"outcome": "extracted", "invoice": invoice, "reason": "fixture"})
        return httpx.Response(200, json={"id": "chatcmpl-fixture", "object": "chat.completion", "created": 0, "model": "gpt-4o-mini", "choices": [{"index": 0, "message": {"role": "assistant", "content": envelope}, "finish_reason": "stop"}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        async with openai.AsyncOpenAI(api_key="sk-fixture_not_a_real_key", http_client=http, max_retries=0) as sdk:
            provider = OpenAIProvider("sk-fixture_not_a_real_key", client=sdk)
            reply = await provider.generate([{"role": "user", "content": "fixture"}])
    assert reply.finish_reason == "stop"
    assert seen[0]["response_format"]["type"] == "json_schema"
    assert seen[0]["response_format"]["json_schema"]["strict"] is True
    schema = seen[0]["response_format"]["json_schema"]["schema"]
    for obj in [schema, *schema["$defs"].values()]:
        assert obj["additionalProperties"] is False
        assert set(obj["required"]) == set(obj["properties"])
