# Windows QA guard correction

John Nelson reported the Step 5 Dell run as **46 passed, 16 warnings, 62 errors**.
The screenshot shows the offline-network AssertionError followed by an incomplete
ProactorEventLoop cleanup (`_ssock` missing). The application was not restarted.

## Cause and correction

The initial autouse test fixture patched socket.socket.connect/connect_ex for
all tests. That was too broad: Windows' Proactor event loop uses a local
socketpair for its self-pipe. Blocking initialization leaves a partially created
loop, causing many repeated setup errors and secondary cleanup warnings. The
Linux run passed because its socketpair initialization differs. This is a test
fixture portability defect, not evidence of 62 independent extraction defects.

Removed the global socket patches. The guard now intercepts the sync and async
default HTTPX transport methods, before real HTTP requests reach DNS or TCP.
MockTransport and ASGITransport remain usable; no actual API requests are needed.
The scope is this application's HTTPX/OpenAI requests, not every networking
library or arbitrary subprocess. Runtime application behavior is unchanged.

Added tests/test_offline_guard.py:

- Default synchronous HTTP requests are rejected by the guard.
- Default asynchronous HTTP requests are rejected by the guard.
- A fresh default event loop can initialize, run a coroutine, and close while
  the guard is active. On Windows this exercises Proactor initialization.

Measured verification on the assistant's Linux environment:
**111 passed in 10.72s**, captured in step5_windows_guard_fix_results.txt.
Lockfile and whitespace checks passed. Actual Windows verification is still
pending; no native Windows execution in this workspace is claimed.

## Dell commands

Keep the application stopped. In the existing project folder:

```powershell
git pull --ff-only
uv run pytest -v --maxfail=1
```

Expected: 111 passed, timing varies. maxfail=1 prevents another long cascade if
an unrelated issue remains. If anything fails, share the first traceback, not
just the final summary. No package reinstall, PowerShell upgrade, event-loop
policy switch or Windows configuration change is required for this correction.

After tests pass, restart the application:

```powershell
uv run uvicorn src.app:app --host 127.0.0.1 --port 8001
```

Primary Python references:
- https://docs.python.org/3.11/library/socket.html#socket.socketpair
- https://github.com/python/cpython/blob/3.11/Lib/asyncio/proactor_events.py
