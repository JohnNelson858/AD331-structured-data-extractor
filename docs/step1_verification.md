# Step 1 verification

## Assistant environment

Verified on November 1, 2026 in the assistant's Linux environment:

- Python 3.11.17, Pydantic 2.14.2, uv 0.13.4.
- `uv sync`: successful installation and committed cross-platform dependency lockfile.
- `uv lock --check`: passed.
- `uv run pytest -v`: **32 passed in 0.23s**.
- After explicitly configuring the async fixture scope, `uv run pytest -q`:
  **32 passed in 0.10s**, without the earlier configuration deprecation warning.

Tests cover valid JSON roundtrip, explicit normalization, strict quantity types,
invalid money/date values, nested arithmetic, invoice reconciliation, unknown
fields, symbol/currency mismatch, and exact 0.02 vs 0.03 tolerance boundaries.
These are schema checks, not the full five required extraction/fallback scenarios.
No provider requests, web UI, or Docker tests are part of this step.

## Dell verification

Pending John running these from the new repository folder in PowerShell:

```powershell
uv sync --locked
uv run python --version
uv run pytest -v
```

Expected: Python 3.11.x and the schema tests all passing. No .env or API key is
needed yet. Share the final pytest summary before proceeding to Step 2.
