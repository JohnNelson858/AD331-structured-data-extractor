"""Inspect a named local DLQ record without printing source text or credentials."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', required=True, help='UUID filename, not a path')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{32}\.json', args.record):
        parser.error('record must be a generated UUID JSON filename')
    directory = Path(os.getenv('DLQ_DIR', '/app/runtime/dlq'))
    content = (directory / args.record).read_bytes()
    record = json.loads(content)
    print(json.dumps({'record': args.record, 'sha256': sha256(content).hexdigest(),
        'attempts_used': record['attempts_used'],
        'needs_human_review': record['needs_human_review']}))


if __name__ == '__main__':
    main()
