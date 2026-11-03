# Step 5: assignment QA coverage and measured results

John Nelson · AD 331 · November 3, 2026

## Result and scope

`uv run pytest -v`: **108 passed in 10.81s** in the assistant environment.
Full captured output: [step5_test_results.txt](step5_test_results.txt).
`uv lock --check` and `git diff --check` passed; dependencies did not change.
Dell verification of this updated suite remains pending.

This milestone adds 36 cases to the earlier 72. Tests simulate provider responses;
none measures a live model's extraction quality or makes a paid API request.
The golden PDF test runs the actual parser, real AsyncOpenAI SDK and strict-schema
request serialization, httpx.MockTransport, and the full business validation gate.
It does not substitute a mock for PDF parsing or Pydantic validation.

## Required assignment coverage

| Assignment test | Executable evidence | Acceptance asserted |
| --- | --- | --- |
| 1. Golden PDF extraction | tests/test_extraction.py::test_1_golden_pdf_first_attempt_through_real_sdk_mock_transport | Actual sample PDF text enters native json_schema/strict=true request; SUCCESS, 1 call, no errors, Decimal total 1374.45, no DLQ file |
| 2. Schema constraints | test_2_nonpositive_quantity_is_rejected; test_2_negative_money_is_rejected | Zero/negative quantities and negative subtotal/tax/total raise ValidationError at the expected field location |
| 3. Cross-field reconciliation | test_3_grand_total_mismatch_fails_root_validation; test_3_subtotal_mismatch_cannot_hide_behind_consistent_grand_total | Incorrect total fails the root validator; internally consistent subtotal+tax cannot hide a mismatch with line items |
| 4. Reflection success | tests/test_fallbacks.py::test_4_reflection_self_heals_on_attempt_two | Missing currency or ambiguous date is rejected on attempt 1; the actual second request contains previous output, normalized source and exact error locations; a valid response is accepted on attempt 2 |
| 5. Hard-failure DLQ | test_5_irrecoverable_payload_hits_three_retry_limit_and_durable_dlq | max_retries=3 gives exactly 4 calls, 3 corrective prompts, 4 errors, no accepted invoice, and a readable JSON disk record with source hash and human-review flag |

Tests 1-3 are in tests/test_extraction.py; Tests 4-5 are in
tests/test_fallbacks.py, matching the assignment's requested layout.

## Additional resilience coverage

- Both upper/lower retry boundaries and invalid retry settings.
- Validation-reflection backoff and deadline exhaustion before another call.
- Transient provider-error backoff and recovery; permanent failures stop early.
- Zero remaining time and a provider awaiting forever, without timing sleeps in
  the mock provider itself; engine timeout routes failure to DLQ.
- DLQ PermissionError returns DLQ_WRITE_FAILED, never a fake saved path/success.
- Heuristic repair accepts a trailing comma only after full revalidation and
  rejects a fenced object with a missing required currency.
- Incomplete/filtered output is never accepted or repaired into a false success.
- Oversized output stops after one call and saved failed text remains capped.
- Common API-key-shaped strings are redacted from audit events and DLQ.
- Concurrent success/failure requests keep results/events/DLQ records separate.
- Cancellation propagates without manufacturing a validation failure or DLQ.
- Nested multiple-line invoices reconcile every child record.
- Existing schema, Step 3 audit and Step 4 HTTP cases remain in the full suite.

| Module | Passing cases |
| --- | ---: |
| test_schemas.py | 32 |
| test_baseline.py | 12 |
| test_audit_regressions.py | 7 |
| test_web.py | 21 |
| test_extraction.py | 10 |
| test_fallbacks.py | 26 |
| Total | 108 |

## QA-discovered correction: reflection backoff

Pre-Step-5 HEAD: 27b1aefb8ec49c0ebf3d800fe9978d4925cea8dd.
The engine had jittered backoff for transient provider errors, but not for
validation reflection. The assignment requires backoff for the corrective loop.
After correcting test expectations to use the ingestion-normalized source,
the pre-fix targeted run produced **2 failed, 34 passed in 0.63s**. The two real
failures were absent reflection sleeps and continuing to call the provider when
the remaining budget could not accommodate the next required pause.
Raw result: [step5_before.txt](step5_before.txt).
Source change: [step5_refactor.diff](step5_refactor.diff).

Correction: validation retries pause 0.25, 0.50 and 1.00 seconds (maximum total
1.75 seconds at three retries). Each pause emits a backoff event with reason
validation_reflection. A shared deadline-aware helper also handles transport
backoff and a sleeper exceeding the remaining time. An exhausted budget stops
additional model calls and preserves fallback/DLQ behavior. Existing schema,
wire contract and retry counting are unchanged. Reflection_prompt means the
corrective message was assembled; the next provider_request records dispatch.

The Step 3 genuine findings remain separately preserved; this is a further
implementation gap found during Step 5, not a retroactive baseline audit claim.

## Offline execution safeguards

The autouse fixture in tests/conftest.py blocks socket connect/connect_ex for
all tests. HTTP tests use in-process ASGITransport and SDK tests use
MockTransport; no real API key is needed. Targeted retry tests inject a virtual
sleeper and assert the requested delays; existing end-to-end smoke/HTTP cases
exercise real short validation pauses. The fixture is a guard against accidental
network use by this suite, not a security sandbox for arbitrary external code.
No tests are marked live and no paid integration is silently skipped or claimed.

## Dell visual evidence carried forward from Step 4

John's supplied screenshots verify the actual browser interface on the Dell:

| Scenario | Observed result |
| --- | --- |
| Clean pasted sample | Accepted, 1 attempt, zero logged issues, zero reconciliation differences; source/JSON side by side and three audit stages |
| Incorrect total with reflection | Repaired via reflection, 2 attempts; error found 1500.00 versus expected 1374.45; corrective prompt displayed |
| Same incorrect total, reflection disabled | DLQ human review, 1 attempt, no accepted record |
| Simulate Edge Case Failure, reflection enabled | DLQ human review after 4 attempts; final validation error plus dlq_written path and needs_human_review=true visible |
| JSON fences, reflection disabled | Repaired via heuristic, 1 attempt, reconciliation passes |
| Uploaded invoice_messy.pdf | PDF extracted text, Accepted, 1 attempt, reconciliation passes |
| Uploaded vendor_contract.html | HTML extracted text, Accepted, 1 attempt, reconciliation passes |

These were offline fixture demonstrations, not live model extraction. Desktop
visual checks are verified; mobile layout, download actions and pasted raw HTML
have HTTP/CSS implementation coverage but no separate Dell browser screenshot.
No screenshot of the Dell's earlier 72-test terminal run was supplied, so it is
not claimed here. The prior 51-test Dell run was confirmed separately.

## Commands on the Dell

The application is already running in the current PowerShell window. Press
Ctrl+C there to stop it before pulling, then run in order:

```powershell
git pull --ff-only
uv sync --locked
uv run pytest -v
uv run uvicorn src.app:app --host 127.0.0.1 --port 8001
```

Expected: 108 tests pass (timing varies). The final command restarts the web app
with the updated backoff behavior. Open http://127.0.0.1:8001 and refresh the tab.
Leave the server terminal running. For a focused instructor check, the new
required cases can also be run with:

```powershell
uv run pytest tests/test_extraction.py tests/test_fallbacks.py -v
```

That focused command has 36 cases; the full 108-case run is the normal check.
All verification above is offline and uses no API credits.

## Remaining assignment work

Step 6: create and prove the Docker deployment alternative, including persistent
DLQ storage. Verify actual provider extraction separately before calling the
application a tested live LLM extractor. Complete the student's policy/audit
review, then prepare and record the 5-7 minute webcam/screen narrative, verify
video duration/visibility, upload and submit the actual links. This milestone
does not claim the whole assignment, deployment or video is complete.
