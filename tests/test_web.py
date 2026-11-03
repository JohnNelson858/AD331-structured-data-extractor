"""Step 4 HTTP integration checks; no live provider calls or real credentials."""
import json
from pathlib import Path

import httpx
import pytest

from src.app import MAX_BODY_BYTES, create_app
from src.cli import FixtureProvider

ROOT = Path(__file__).parents[1]
SAMPLE = (ROOT / "samples/invoice_messy.txt").read_text()


@pytest.fixture
async def client(tmp_path):
    app = create_app(dlq_dir=tmp_path, api_key="")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


def frames(response):
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/x-ndjson")
    return [json.loads(line) for line in response.text.splitlines()]


async def test_home_config_assets_and_no_secret_exposure(client):
    home = await client.get("/")
    assert home.status_code == 200
    assert 'Simulate Edge Case Failure' in home.text
    assert "script-src 'self'" in home.headers['content-security-policy']
    assert home.headers['cache-control'] == 'no-store'
    assert (await client.get('/static/app.js')).status_code == 200
    assert (await client.get('/static/app.css')).status_code == 200
    assert (await client.get('/health')).json() == {'status': 'ok'}
    assert (await client.get('/api/config')).json()['live_available'] is False
    assert (await client.get('/api/sample')).json()['text'] == SAMPLE
    pdf = await client.get('/samples/invoice_messy.pdf')
    assert pdf.content.startswith(b'%PDF')


@pytest.mark.parametrize('scenario,status,attempts', [
    ('success', 'SUCCESS', 1),
    ('reflection', 'REPAIRED_VIA_REFLECTION', 2),
    ('heuristic', 'REPAIRED_VIA_HEURISTIC', 4),
    ('dlq', 'DLQ_FAILED', 4),
])
async def test_streamed_scenarios_have_source_events_and_final_result(client, scenario, status, attempts):
    records = frames(await client.post('/api/extract', data={'text': SAMPLE, 'scenario': scenario}))
    assert records[0]['type'] == 'source'
    assert records[0]['mode'] == 'offline'
    assert any(item['type'] == 'audit' for item in records)
    result = records[-1]['result']
    assert result['execution_status'] == status
    assert result['attempts_used'] == attempts
    if result['validated_data']:
        assert records[-1]['reconciliation_report']['grand_total_difference'] == '0.00'
        assert records[-1]['reconciliation_report']['tolerance'] == '0.02'
    else:
        assert records[-1]['reconciliation_report'] is None
    if scenario == 'reflection':
        event = next(item['event'] for item in records if item.get('event', {}).get('stage') == 'reflection_prompt')
        prompt = json.loads(event['detail']['messages'][1]['content'])
        assert prompt['validation_errors'][0]['loc'] == []
        assert '1500.00' in prompt['previous_extraction']
        assert '1,374.45' in prompt['source_excerpt']
    if scenario == 'dlq':
        assert result['validated_data'] is None
        saved = json.loads(Path(result['dlq_path']).read_text())
        assert saved['needs_human_review'] is True
        assert saved['model'] == 'offline-fixture'


async def test_reflection_toggle_changes_actual_http_attempt_limit(client):
    records = frames(await client.post('/api/extract', data={'text': SAMPLE, 'scenario': 'reflection', 'reflection': 'false'}))
    result = records[-1]['result']
    assert result['execution_status'] == 'DLQ_FAILED'
    assert result['attempts_used'] == 1
    assert not any(e['stage'] == 'reflection_prompt' for e in result['events'])


@pytest.mark.parametrize('name,mime', [('invoice_messy.pdf', 'application/pdf'), ('vendor_contract.html', 'text/html'), ('invoice_messy.txt', 'text/plain')])
async def test_actual_uploaded_sample_files(client, name, mime):
    response = await client.post('/api/extract', files={'file': (name, (ROOT / 'samples' / name).read_bytes(), mime)})
    result = frames(response)[-1]['result']
    assert result['execution_status'] == 'SUCCESS'
    assert result['validated_data']['total_amount'] == '1374.45'


async def test_pasted_raw_html_goes_through_ingestion(client):
    html = (ROOT / 'samples/vendor_contract.html').read_text()
    records = frames(await client.post('/api/extract', data={'text': html, 'input_kind': 'html'}))
    assert records[0]['kind'] == 'html'
    assert 'console.log' not in records[0]['text']
    assert records[-1]['result']['execution_status'] == 'SUCCESS'


@pytest.mark.parametrize('data,expected', [
    ({'text': ''}, 'empty'),
    ({'text': 'An arbitrary invoice 999'}, 'bundled sample'),
    ({'text': SAMPLE, 'mode': 'unknown'}, 'Unknown'),
    ({'text': SAMPLE, 'reflection': 'perhaps'}, 'Reflection must'),
    ({'text': SAMPLE, 'mode': 'live'}, 'Confirm'),
    ({'text': SAMPLE, 'mode': 'live', 'scenario': 'dlq'}, 'offline only'),
])
async def test_invalid_inputs_reject_before_provider_work(client, data, expected):
    response = await client.post('/api/extract', data=data)
    assert response.status_code == 422
    assert expected in response.json()['detail']


async def test_missing_key_and_cross_site_requests_are_rejected(client):
    response = await client.post('/api/extract', data={'mode': 'live', 'confirm_live': 'yes', 'text': SAMPLE})
    assert response.status_code == 503
    for headers in ({'Origin': 'https://other.example'}, {'Sec-Fetch-Site': 'cross-site'}):
        response = await client.post('/api/extract', data={'text': SAMPLE}, headers=headers)
        assert response.status_code == 403
    assert (await client.get('/', headers={'Host': 'other.example'})).status_code == 400


async def test_live_wiring_with_injected_provider_is_explicit_and_offline(tmp_path):
    seen = []
    def provider_factory(mode, scenario):
        seen.append((mode, scenario))
        return FixtureProvider('success')
    app = create_app(dlq_dir=tmp_path, api_key='sk-fixture_not_a_real_key', provider_factory=provider_factory)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver') as client:
        config = (await client.get('/api/config')).json()
        assert config['live_available'] is True
        assert 'sk-' not in json.dumps(config)
        response = await client.post('/api/extract', data={'mode': 'live', 'confirm_live': 'yes', 'text': SAMPLE})
        records = frames(response)
        assert records[0]['mode'] == 'live'
        assert records[-1]['result']['execution_status'] == 'SUCCESS'
        assert seen == [('live', 'success')]


async def test_bad_file_and_ambiguous_input_return_safe_errors(client):
    response = await client.post('/api/extract', files={'file': ('bad.pdf', b'not PDF', 'application/pdf')})
    assert response.status_code == 422
    response = await client.post('/api/extract', files={'file': ('sample.exe', b'not executable', 'application/octet-stream')})
    assert response.status_code == 422
    response = await client.post('/api/extract', data={'text': SAMPLE}, files={'file': ('invoice.txt', SAMPLE.encode(), 'text/plain')})
    assert response.status_code == 422
    assert 'one input' in response.json()['detail']


async def test_streamed_request_body_limit_without_content_length(client):
    async def chunks():
        yield b'--audit-boundary\r\nContent-Disposition: form-data; name="file"; filename="large.pdf"\r\nContent-Type: application/pdf\r\n\r\n'
        for _ in range(7):
            yield b'a' * 1_000_000
        yield b'\r\n--audit-boundary--\r\n'
    response = await client.post('/api/extract', content=chunks(), headers={'Content-Type': 'multipart/form-data; boundary=audit-boundary'})
    assert response.status_code == 413


async def test_oversized_file_rejected_before_extraction(client):
    response = await client.post('/api/extract', files={'file': ('large.pdf', b'x' * 5_000_001, 'application/pdf')})
    assert response.status_code == 422
    assert '5 MB' in response.json()['detail']
