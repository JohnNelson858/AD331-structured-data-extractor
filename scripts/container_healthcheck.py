"""Container-local health probe. No provider access or credentials."""
import json
from urllib.request import ProxyHandler, build_opener


def main():
    # Bypass proxy configuration for this loopback-only readiness probe.
    opener = build_opener(ProxyHandler({}))
    with opener.open('http://127.0.0.1:8000/health', timeout=2) as response:
        if response.status != 200 or json.load(response).get('status') != 'ok':
            raise SystemExit(1)


if __name__ == '__main__':
    main()
