"""Container configuration integration checks, without a Docker daemon or API calls."""
import json
from pathlib import Path

import httpx
import pytest

from src.app import create_app


async def test_environment_dlq_directory_is_used_for_actual_failed_extraction(tmp_path, monkeypatch):
    directory = tmp_path / 'persisted-dlq'
    monkeypatch.setenv('DLQ_DIR', str(directory))
    app = create_app(api_key='')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver') as client:
        response = await client.post('/api/extract', data={'scenario': 'dlq', 'reflection': 'false'})
    frames = [json.loads(line) for line in response.text.splitlines()]
    result = frames[-1]['result']
    assert result['execution_status'] == 'DLQ_FAILED'
    assert Path(result['dlq_path']).parent == directory
    assert json.loads(Path(result['dlq_path']).read_text())['needs_human_review'] is True


async def test_explicit_dlq_argument_overrides_environment(tmp_path, monkeypatch):
    monkeypatch.setenv('DLQ_DIR', str(tmp_path / 'unused'))
    directory = tmp_path / 'explicit'
    app = create_app(api_key='', dlq_dir=directory)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver') as client:
        response = await client.post('/api/extract', data={'scenario': 'dlq', 'reflection': 'false'})
    result = json.loads(response.text.splitlines()[-1])['result']
    assert Path(result['dlq_path']).parent == directory
    assert not (tmp_path / 'unused').exists()


async def test_key_file_is_read_with_windows_bom_but_not_exposed(tmp_path, monkeypatch):
    key = 'sk-synthetic_not_a_real_secret_12345678'
    key_file = tmp_path / 'key.txt'
    key_file.write_text(key + '\n', encoding='utf-8-sig')
    monkeypatch.setenv('OPENAI_API_KEY_FILE', str(key_file))
    monkeypatch.setenv('OPENAI_API_KEY', '')
    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver') as client:
        config = await client.get('/api/config')
    assert config.json()['live_available'] is True
    assert key not in config.text and str(key_file) not in config.text


@pytest.mark.parametrize('kind', ['missing', 'empty', 'invalid_utf8'])
def test_unusable_configured_key_file_fails_without_leaking_path(tmp_path, monkeypatch, kind):
    key_file = tmp_path / 'private-path.txt'
    if kind == 'empty':
        key_file.write_text('   \n')
    elif kind == 'invalid_utf8':
        key_file.write_bytes(b'\xffnot-a-key')
    monkeypatch.setenv('OPENAI_API_KEY_FILE', str(key_file))
    with pytest.raises(RuntimeError) as caught:
        create_app()
    assert str(key_file) not in str(caught.value)
    assert caught.value.__cause__ is None


def test_explicit_offline_key_setting_does_not_read_server_secret_file(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY_FILE', '/nonexistent/private-key')
    app = create_app(api_key='')
    assert app.title == 'SchemaExtractor'
