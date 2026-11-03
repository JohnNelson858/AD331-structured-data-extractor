"""Assignment QA Tests 4-5 and production failure-path contracts, all offline."""
import asyncio
from hashlib import sha256
import json
from pathlib import Path

import pytest

from src.extractor import SchemaExtractor
from src.fallback import MAX_RESPONSE_CHARS
from src.ingestion import from_text
from src.provider import ProviderFailure, ProviderReply


@pytest.mark.parametrize('defect,location', [('missing_currency', ['invoice', 'currency']), ('ambiguous_date', ['invoice_date'])])
async def test_4_reflection_self_heals_on_attempt_two(tmp_path, source_text, invoice_data, envelope, sequence_provider, no_wait, defect, location):
    malformed = dict(invoice_data)
    if defect == 'missing_currency':
        malformed.pop('currency')
    else:
        malformed['invoice_date'] = '12/10/2024'
    provider = sequence_provider(envelope(malformed), envelope())
    result = await SchemaExtractor(provider, tmp_path, sleeper=no_wait[0]).extract_with_retry(source_text)
    assert result.execution_status == 'REPAIRED_VIA_REFLECTION'
    assert result.attempts_used == provider.calls == 2
    assert len(result.error_log) == 1
    feedback = json.loads(provider.messages[1][1]['content'])
    assert feedback['validation_errors'][0]['loc'] == location
    assert json.loads(feedback['previous_extraction'])['invoice'] == malformed
    assert feedback['source_excerpt'] == from_text(source_text).text
    assert len(provider.messages[1]) == 2
    assert result.validated_data.currency == 'USD'
    assert result.validated_data.invoice_date.isoformat() == '2024-10-12'


async def test_5_irrecoverable_payload_hits_three_retry_limit_and_durable_dlq(tmp_path, source_text, sequence_provider, no_wait):
    provider = sequence_provider('total nonsense text')
    result = await SchemaExtractor(provider, tmp_path, sleeper=no_wait[0]).extract_with_retry(source_text, max_retries=3)
    assert result.execution_status == 'DLQ_FAILED'
    assert result.validated_data is None
    assert result.attempts_used == provider.calls == 4
    assert len(result.error_log) == 4
    assert sum(event.stage == 'reflection_prompt' for event in result.events) == 3
    saved = json.loads(Path(result.dlq_path).read_text())
    assert saved['failed_payload'] == 'total nonsense text'
    assert saved['source_sha256'] == sha256(from_text(source_text).text.encode()).hexdigest()
    assert saved['attempts_used'] == 4 and saved['needs_human_review'] is True
    assert len(saved['errors']) == 4
    assert not list(tmp_path.glob('*.tmp'))


async def test_reflection_retries_use_bounded_backoff(tmp_path, source_text, sequence_provider, no_wait):
    provider = sequence_provider('not valid JSON')
    sleep, delays = no_wait
    result = await SchemaExtractor(provider, tmp_path, sleeper=sleep).extract_with_retry(source_text)
    assert result.attempts_used == 4
    assert delays == [0.25, 0.5, 1.0]
    assert sum(event.stage == 'backoff' for event in result.events) == 3


async def test_reflection_backoff_respects_remaining_deadline(tmp_path, source_text, envelope, invoice_data, sequence_provider, no_wait):
    invoice_data['total_amount'] = '1500.00'
    provider = sequence_provider(envelope(invoice_data))
    result = await SchemaExtractor(provider, tmp_path, sleeper=no_wait[0], deadline_seconds=0.1).extract_with_retry(source_text)
    assert provider.calls == 1
    assert no_wait[1] == []
    assert 'execution_deadline_exceeded' in result.error_log
    assert result.execution_status == 'DLQ_FAILED'


@pytest.mark.parametrize('retries', [0, 1, 2, 3])
async def test_retry_boundary_counts_actual_calls(tmp_path, source_text, sequence_provider, no_wait, retries):
    provider = sequence_provider('not JSON')
    result = await SchemaExtractor(provider, tmp_path, sleeper=no_wait[0]).extract_with_retry(source_text, max_retries=retries)
    assert result.attempts_used == provider.calls == retries + 1
    assert result.validated_data is None


@pytest.mark.parametrize('retries', [-1, 4, True, 1.0])
async def test_invalid_retry_configuration_makes_no_provider_calls(tmp_path, source_text, sequence_provider, retries):
    provider = sequence_provider('not JSON')
    with pytest.raises(ValueError):
        await SchemaExtractor(provider, tmp_path).extract_with_retry(source_text, max_retries=retries)
    assert provider.calls == 0


async def test_transient_provider_failure_uses_backoff_then_succeeds(tmp_path, source_text, envelope, sequence_provider, no_wait):
    provider = sequence_provider(ProviderFailure('provider_transient_failure', transient=True), envelope())
    result = await SchemaExtractor(provider, tmp_path, sleeper=no_wait[0]).extract_with_retry(source_text)
    assert result.execution_status == 'SUCCESS'  # transport recovery is not validation reflection
    assert provider.calls == 2 and 1 <= no_wait[1][0] <= 1.25
    assert any(event.stage == 'backoff' for event in result.events)


async def test_permanent_provider_failure_is_not_retried(tmp_path, source_text, sequence_provider, no_wait):
    provider = sequence_provider(ProviderFailure('provider_http_failure'))
    result = await SchemaExtractor(provider, tmp_path, sleeper=no_wait[0]).extract_with_retry(source_text)
    assert result.execution_status == 'DLQ_FAILED'
    assert provider.calls == 1 and no_wait[1] == []


async def test_deadline_before_first_call_stops_without_provider_work(tmp_path, source_text, sequence_provider):
    provider = sequence_provider('not JSON')
    result = await SchemaExtractor(provider, tmp_path, deadline_seconds=0).extract_with_retry(source_text)
    assert result.attempts_used == provider.calls == 0
    assert result.error_log == ['execution_deadline_exceeded']
    assert result.execution_status == 'DLQ_FAILED'


async def test_hung_provider_timeout_routes_to_dlq(tmp_path, source_text):
    class HungProvider:
        async def generate(self, messages):
            await asyncio.Event().wait()
    result = await SchemaExtractor(HungProvider(), tmp_path, deadline_seconds=0.02).extract_with_retry(source_text)
    assert result.execution_status == 'DLQ_FAILED'
    assert result.attempts_used == 1
    assert 'execution_deadline_exceeded' in result.error_log


async def test_unwritable_dlq_does_not_claim_saved_record(tmp_path, source_text, sequence_provider, monkeypatch):
    def denied(*args):
        raise PermissionError('private filesystem detail')
    monkeypatch.setattr('src.extractor.write_dlq', denied)
    result = await SchemaExtractor(sequence_provider('not JSON'), tmp_path).extract_with_retry(source_text, max_retries=0)
    assert result.execution_status == 'DLQ_WRITE_FAILED'
    assert result.dlq_path is None and result.validated_data is None
    assert 'dlq_storage_failure' in result.error_log
    assert 'private filesystem' not in result.model_dump_json()


async def test_heuristic_cannot_invent_missing_currency(tmp_path, source_text, invoice_data, envelope, sequence_provider):
    invoice_data.pop('currency')
    provider = sequence_provider('```json\n' + envelope(invoice_data) + '\n```')
    result = await SchemaExtractor(provider, tmp_path).extract_with_retry(source_text, max_retries=0)
    assert result.execution_status == 'DLQ_FAILED'
    assert result.validated_data is None
    assert any(event.stage == 'heuristic_rejected' for event in result.events)


async def test_heuristic_repairs_trailing_comma_but_still_reconciles(tmp_path, source_text, envelope, sequence_provider):
    provider = sequence_provider(envelope()[:-1] + ',}')
    result = await SchemaExtractor(provider, tmp_path).extract_with_retry(source_text, max_retries=0)
    assert result.execution_status == 'REPAIRED_VIA_HEURISTIC'
    assert result.attempts_used == 1 and result.error_log


@pytest.mark.parametrize('finish', ['length', 'content_filter'])
async def test_incomplete_or_filtered_output_stops_without_repair(tmp_path, source_text, envelope, sequence_provider, finish):
    result = await SchemaExtractor(sequence_provider(ProviderReply(envelope(), finish)), tmp_path).extract_with_retry(source_text)
    assert result.execution_status == 'DLQ_FAILED'
    assert result.attempts_used == 1
    assert not any(e.stage == 'heuristic_validated' for e in result.events)


async def test_oversized_response_stops_and_caps_saved_payload(tmp_path, source_text, sequence_provider):
    result = await SchemaExtractor(sequence_provider('x' * (MAX_RESPONSE_CHARS + 1)), tmp_path).extract_with_retry(source_text)
    assert result.execution_status == 'DLQ_FAILED' and result.attempts_used == 1
    saved = json.loads(Path(result.dlq_path).read_text())
    assert len(saved['failed_payload']) == MAX_RESPONSE_CHARS


async def test_redacts_key_shaped_strings_from_audit_and_dlq(tmp_path, sequence_provider):
    key = 'sk-synthetic_secret_string_for_test_123456'
    result = await SchemaExtractor(sequence_provider(key), tmp_path).extract_with_retry('Synthetic source ' + key, max_retries=0)
    assert key not in result.model_dump_json()
    saved = Path(result.dlq_path).read_text()
    assert key not in saved and '[REDACTED_API_KEY]' in saved


async def test_concurrent_requests_keep_attempts_events_and_dlq_separate(tmp_path, source_text, sequence_provider, envelope, no_wait):
    class InterleavedProvider:
        async def generate(self, messages):
            await asyncio.sleep(0)
            return ProviderReply('not JSON' if 'force-failure' in messages[1]['content'] else envelope())
    engine = SchemaExtractor(InterleavedProvider(), tmp_path, sleeper=no_wait[0])
    accepted, rejected = await asyncio.gather(engine.extract_with_retry(source_text), engine.extract_with_retry('force-failure', max_retries=0))
    assert accepted.execution_status == 'SUCCESS' and accepted.error_log == []
    assert rejected.execution_status == 'DLQ_FAILED' and rejected.validated_data is None
    assert accepted.dlq_path is None and rejected.dlq_path is not None
    assert len(list(tmp_path.glob('*.json'))) == 1
    assert 'force-failure' not in accepted.model_dump_json()


async def test_cancelled_extraction_does_not_write_false_dlq(tmp_path, source_text):
    started = asyncio.Event()
    class CancellableProvider:
        async def generate(self, messages):
            started.set()
            await asyncio.Event().wait()
    task = asyncio.create_task(SchemaExtractor(CancellableProvider(), tmp_path).extract_with_retry(source_text))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not list(tmp_path.iterdir())
