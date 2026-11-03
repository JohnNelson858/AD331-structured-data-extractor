"""Shared synthetic fixtures and an offline-only test network boundary."""
import copy
import json
from pathlib import Path
import socket

import pytest

from src.provider import ProviderReply

ROOT = Path(__file__).parents[1]


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    """Mocks/ASGI are allowed; accidental real TCP API calls fail immediately."""
    def blocked(*args, **kwargs):
        raise AssertionError("Real network access is disabled in the offline QA suite")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)


@pytest.fixture
def invoice_data():
    return json.loads((ROOT / 'samples/invoice_expected.json').read_text())


@pytest.fixture
def source_text():
    return (ROOT / 'samples/invoice_messy.txt').read_text()


@pytest.fixture
def envelope(invoice_data):
    def build(invoice=None):
        return json.dumps({'outcome': 'extracted', 'invoice': invoice_data if invoice is None else invoice, 'reason': 'Offline QA fixture'})
    return build


class SequenceProvider:
    """Captures actual messages; repeats last reply to expose retry boundaries."""
    def __init__(self, *responses):
        self.responses = responses
        self.messages = []

    @property
    def calls(self):
        return len(self.messages)

    async def generate(self, messages):
        self.messages.append(copy.deepcopy(messages))
        response = self.responses[min(self.calls - 1, len(self.responses) - 1)]
        if isinstance(response, Exception):
            raise response
        return response if isinstance(response, ProviderReply) else ProviderReply(response)


@pytest.fixture
def sequence_provider():
    return SequenceProvider


@pytest.fixture
def no_wait():
    """Virtual backoff for targeted retry tests; record requested delays."""
    delays = []
    async def sleep(seconds):
        delays.append(seconds)
    return sleep, delays
