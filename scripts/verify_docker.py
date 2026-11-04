"""Offline end-to-end Docker check; optionally prove DLQ survives recreation.

Run on the Dell after docker compose up --build -d --wait.
All extraction requests explicitly use offline fixtures. No API key is read.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
OPENER = build_opener(ProxyHandler({}))


def compose(*args):
    result = subprocess.run(['docker', 'compose', '-f', str(ROOT / 'docker-compose.yml'), *args], cwd=ROOT, check=True,
                            capture_output=True, text=True, timeout=120)
    return result.stdout.strip()


def get_json(url):
    with OPENER.open(url, timeout=10) as response:
        return json.load(response)


def extract(base_url, fields, upload=None):
    fields = {'mode': 'offline', **fields}
    if upload is None:
        body = urlencode(fields).encode()
        content_type = 'application/x-www-form-urlencoded'
    else:
        boundary = 'extractor-' + uuid4().hex
        parts = []
        for key, value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        name, mime, data = upload
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n'.encode())
        parts.extend([data, b'\r\n', f'--{boundary}--\r\n'.encode()])
        body = b''.join(parts)
        content_type = 'multipart/form-data; boundary=' + boundary
    request = Request(base_url + '/api/extract', data=body, headers={'Content-Type': content_type})
    with OPENER.open(request, timeout=30) as response:
        frames = [json.loads(line) for line in response.read().decode().splitlines() if line.strip()]
    if not frames or frames[0].get('mode') != 'offline' or frames[-1].get('type') != 'result':
        raise ValueError('Offline extraction did not return a complete result stream.')
    return frames[-1]['result']


def require_result(result, status, attempts):
    if result['execution_status'] != status or result['attempts_used'] != attempts:
        raise ValueError(f"Expected {status}/{attempts} attempts; received {result['execution_status']}/{result['attempts_used']}.")
    accepted = status.startswith('SUCCESS') or status.startswith('REPAIRED_')
    if (result['validated_data'] is not None) != accepted:
        raise ValueError('Accepted-record contract failed.')
    return {'status': status, 'attempts': attempts}


def inspect_record(filename):
    return json.loads(compose('exec', '-T', 'extractor', 'python',
        'scripts/inspect_dlq.py', '--record', filename))


def wait_for_health(base_url):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if get_json(base_url + '/health') == {'status': 'ok'}:
                return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise TimeoutError('Container health did not become ready within 60 seconds.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8001')
    parser.add_argument('--check-persistence', action='store_true', help='Recreate this project service and compare the saved DLQ bytes')
    args = parser.parse_args()
    base_url = args.base_url.rstrip('/')
    url = urlsplit(base_url)
    if url.scheme != 'http' or url.hostname not in {'127.0.0.1', 'localhost', '::1'} or url.username or url.password or url.path or url.query or url.fragment:
        parser.error('Use a local loopback HTTP URL with an optional port.')
    try:
        wait_for_health(base_url)
        if get_json(base_url + '/api/config')['live_available']:
            raise ValueError('Use the default offline Compose configuration for this verification.')
        container_before = compose('ps', '-q', 'extractor')
        if not container_before:
            raise ValueError('The extractor Compose service is not running.')
        print('Checking actual container HTTP routes with offline fixtures…', flush=True)
        text = get_json(base_url + '/api/sample')['text']
        with OPENER.open(base_url + '/samples/invoice_messy.pdf', timeout=10) as response:
            pdf = response.read()
        checks = {}
        result = extract(base_url, {'scenario': 'success', 'reflection': 'true'}, ('invoice_messy.pdf', 'application/pdf', pdf))
        checks['uploaded_pdf'] = require_result(result, 'SUCCESS', 1)
        html = (ROOT / 'samples/vendor_contract.html').read_bytes()
        checks['uploaded_html'] = require_result(extract(base_url, {'scenario': 'success'}, ('vendor_contract.html', 'text/html', html)), 'SUCCESS', 1)
        checks['reflection'] = require_result(extract(base_url, {'text': text, 'scenario': 'reflection', 'reflection': 'true'}), 'REPAIRED_VIA_REFLECTION', 2)
        checks['reflection_disabled'] = require_result(extract(base_url, {'text': text, 'scenario': 'reflection', 'reflection': 'false'}), 'DLQ_FAILED', 1)
        checks['heuristic'] = require_result(extract(base_url, {'text': text, 'scenario': 'heuristic', 'reflection': 'false'}), 'REPAIRED_VIA_HEURISTIC', 1)
        hard_failure = extract(base_url, {'scenario': 'dlq', 'reflection': 'true'})
        checks['hard_failure_dlq'] = require_result(hard_failure, 'DLQ_FAILED', 4)
        filename = PurePosixPath(hard_failure['dlq_path'].replace('\\', '/')).name
        before = inspect_record(filename)
        if before['attempts_used'] != 4 or before['needs_human_review'] is not True:
            raise ValueError('Saved DLQ metadata did not match the HTTP result.')
        checks['dlq_disk_record'] = {'record': filename, 'sha256': before['sha256']}
        if args.check_persistence:
            print('Recreating the extractor container; preserving the named DLQ volume…', flush=True)
            compose('up', '-d', '--force-recreate', '--wait', '--wait-timeout', '90', 'extractor')
            wait_for_health(base_url)
            container_after = compose('ps', '-q', 'extractor')
            after = inspect_record(filename)
            if not container_after or container_after == container_before or after != before:
                raise ValueError('Container recreation or DLQ persistence verification failed.')
            checks['dlq_after_recreation'] = 'PASS: new container, identical saved record bytes'
        else:
            checks['dlq_after_recreation'] = 'NOT RUN: add --check-persistence to verify'
        report = {'verified_at_utc': datetime.now(timezone.utc).isoformat(),
                  'execution': 'OFFLINE FIXTURES ONLY; no provider API calls', 'checks': checks}
        output = ROOT / 'runtime/docker_verification.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
        print('PASS. Saved verification report: runtime/docker_verification.json')
        return 0
    except (OSError, ValueError, KeyError, HTTPError, URLError, subprocess.SubprocessError) as exc:
        print('FAIL: ' + str(exc))
        print('Inspect docker compose ps and docker compose logs --tail 60 extractor; no accepted result is claimed for an incomplete check.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
