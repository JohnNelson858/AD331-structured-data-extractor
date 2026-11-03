"""Step 3 regressions reproduced against the preserved generated baseline."""
import json
from pathlib import Path

import pytest

from src.cli import FixtureProvider
from src.extractor import SchemaExtractor, SYSTEM_PROMPT
from src.fallback import MAX_FEEDBACK_CHARS, reflection_messages


def test_root_error_keeps_header_middle_and_tail_evidence():
    source = ("Invoice INV-AUDIT-42; Vendor Cascade Labs\n" + "general terms\n" * 550
              + "Line items: two sensors at 624.75 each\n" + "general terms\n" * 550
              + "Subtotal 1249.50; Tax 124.95; Grand total 1374.45 USD")
    messages = reflection_messages(SYSTEM_PROMPT, source, "{}", [
        {"loc": [], "msg": "line totals do not reconcile", "type": "value_error"}])
    payload = json.loads(messages[1]["content"])
    evidence = payload["source_excerpt"]
    assert "Grand total 1374.45" in evidence
    assert "INV-AUDIT-42" in evidence
    assert "two sensors" in evidence
    assert len(evidence) <= MAX_FEEDBACK_CHARS


def test_field_error_does_not_discard_other_required_facts():
    source = "Invoice INV-AUDIT-43\nVendor Cascade Labs\nCurrency USD\nTotal 1374.45"
    payload = json.loads(reflection_messages(SYSTEM_PROMPT, source, "{}", [
        {"loc": ["currency"], "msg": "bad currency", "type": "literal_error"}])[1]["content"])
    assert source == payload["source_excerpt"]


@pytest.mark.parametrize("scenario,status", [("success", "SUCCESS"), ("dlq", "DLQ_FAILED")])
async def test_observer_failure_does_not_crash_extraction_or_dlq(tmp_path, scenario, status):
    calls = []
    def broken_observer(event):
        calls.append(event.stage)
        raise RuntimeError("private-observer-detail-must-not-leak")
    result = await SchemaExtractor(FixtureProvider(scenario), tmp_path).extract_with_retry(
        "Synthetic invoice source", on_event=broken_observer)
    assert result.execution_status == status
    assert len(calls) == 1  # disable the failed observer; do not recursively notify it
    assert any(event.stage == "audit_sink_failure" for event in result.events)
    assert "private-observer-detail" not in result.model_dump_json()
    if status == "DLQ_FAILED":
        assert Path(result.dlq_path).exists()
        assert result.validated_data is None


async def test_observer_cannot_mutate_retained_audit_events(tmp_path):
    def mutating_observer(event):
        event.stage = "forged"
        event.detail.clear()
    result = await SchemaExtractor(FixtureProvider("success"), tmp_path).extract_with_retry(
        "Synthetic invoice source", on_event=mutating_observer)
    assert result.events[0].stage == "provider_request"
    assert result.events[0].detail["strict_schema"] is True
    assert any(event.stage == "validation_passed" for event in result.events)


async def test_observer_cancellation_still_propagates(tmp_path):
    import asyncio
    def cancelled_observer(event):
        raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await SchemaExtractor(FixtureProvider("success"), tmp_path).extract_with_retry(
            "Synthetic invoice source", on_event=cancelled_observer)


async def test_long_source_reflection_dispatches_needed_evidence(tmp_path):
    class EvidenceCheckingProvider(FixtureProvider):
        async def generate(self, messages):
            if self.calls == 1:
                feedback = json.loads(messages[1]["content"])
                assert "Grand total 1374.45 USD" in feedback["source_excerpt"]
                assert feedback["source_excerpt_incomplete"] is True
                assert feedback["validation_errors"][0]["loc"] == []
                assert len(feedback["source_excerpt"]) <= MAX_FEEDBACK_CHARS
            return await super().generate(messages)
    source = "Invoice INV-2024-1012\n" + "Terms and conditions\n" * 600 + "Grand total 1374.45 USD"
    result = await SchemaExtractor(EvidenceCheckingProvider("reflection"), tmp_path).extract_with_retry(source)
    assert result.execution_status == "REPAIRED_VIA_REFLECTION"
    assert result.attempts_used == 2
