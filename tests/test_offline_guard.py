"""HTTP guard contracts, including event-loop creation while the guard is active."""
import asyncio

import httpx
import pytest


def test_default_sync_http_transport_is_blocked_before_network():
    with httpx.Client(trust_env=False) as client:
        with pytest.raises(AssertionError, match='Real HTTP access is disabled'):
            client.get('https://example.invalid/offline-test')


async def test_default_async_http_transport_is_blocked_before_network():
    async with httpx.AsyncClient(trust_env=False) as client:
        with pytest.raises(AssertionError, match='Real HTTP access is disabled'):
            await client.get('https://example.invalid/offline-test')


def test_fresh_event_loop_can_initialize_run_and_close_under_guard():
    # On Windows this constructs the default Proactor loop and its socketpair.
    # Run as a sync test so it does not nest a loop inside pytest's running loop.
    loop = asyncio.new_event_loop()
    try:
        assert loop.run_until_complete(asyncio.sleep(0, result='ready')) == 'ready'
    finally:
        loop.close()
