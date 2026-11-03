# Step 3: audit and regression verification

November 3, 2026. Scope: audit the actual Step 2 generated baseline; no web UI
implementation, paid API calls, or completed deployment is claimed.

## Provenance and reproducibility

Generated baseline: `2d758963f745a3a6648c9c298094dd39f4eb1d6e`.
Immediate pre-audit HEAD: `858874c0dcc333c2fbb795eb36ac211d7e7841f3`
(the separate PDF portability correction). The engine/helper bytes were still
those of the generated baseline. Tests were written and run before editing them.

- `step3_before.txt`: actual initial run of six new regression cases,
  **5 failed, 1 passed in 0.91s**.
- `step3_after.txt`: actual final full-suite run,
  **51 passed in 1.32s**. Includes one additional end-to-end reflection-evidence
  test added after correction, plus the original 44 and six initial regressions.
- `step3_refactor.diff`: source changes against the pre-audit HEAD.
- `tests/test_audit_regressions.py`: executable failure reproductions and guards.

To reproduce the five baseline failures without replacing the current checkout,
use a separate worktree at the pre-audit commit, copy the current regression file
there, and run only its original six cases (exclude
`test_long_source_reflection_dispatches_needed_evidence`). This is optional;
normal Dell verification should use the current main branch.

## Findings and fixes

| Finding | Reproduction / consequence | Correction |
| --- | --- | --- |
| Reflection discards necessary evidence | A root-level reconciliation error has `loc=[]`; the baseline selects only the first 6000 characters, losing late totals. A currency field error selects only the currency line, losing other required fields even for a short document. | Keep short sources intact. For long sources, select header/footer and windows around invoice labels and failing fields; merge overlapping ranges, label original character offsets, and stay within 6000 characters including markers. Explicitly mark incomplete evidence. |
| Optional audit consumer can crash or tamper with extraction | A callback raising RuntimeError aborts the first provider-request event before success or DLQ is possible. A callback mutating the received event also mutates the retained audit evidence. | Pass a deep copy. Catch ordinary callback exceptions, record a safe audit_sink_failure warning, disable that consumer, and continue the same validation/DLQ rules. Preserve cancellation propagation. |

These are genuine baseline defects, not deliberately seeded faults. Simulated
callback failures and malformed model responses are test inputs only.

## Required anti-pattern review

- Pydantic syntax: searched src for v1 validators, root_validator and .dict();
  none found. Existing field_validator/model_validator/model_validate/model_dump
  APIs are v2. No syntax defect was invented for the audit.
- Context stuffing: the baseline already rebuilt two-message prompts and bounded
  source/response sizes. The actual defect was losing relevant evidence while
  truncating. Character limits are not exact token budgets; no token-cost
  guarantee is claimed. Previous output is explicitly not source evidence.
- Schema enforcement: wire-envelope validation is followed by the full business
  model. Reflection and heuristic repairs must pass that same gate. Failure
  statuses have no validated_data. No all-None partial-success path was found.
- Date/type normalization: existing before validators accept explicit English
  dates and documented money syntax, use Decimal, and reject ambiguous dates,
  invalid quantities and unknown fields. Regression coverage already existed.

## Additional checks and limits

`uv lock --check` and `git diff --check` passed. Offline CLI verification:
reflection -> REPAIRED_VIA_REFLECTION, 2 attempts, 1 error, reconciled true;
DLQ -> DLQ_FAILED, 4 attempts, 4 errors, no accepted invoice, JSON record exists.
Tests use fixture responses or the real SDK with MockTransport; they do not
measure live model quality or prove that all source claims are accurate.

Evidence selection is deliberately lossy for long documents. It can still omit
facts or match irrelevant labels. The model must report insufficient_source if
it cannot ground required fields; future chunk-aware retrieval can improve this.
A synchronous event observer must be fast: exception isolation does not prevent
it from blocking the event loop. This is an in-process integrity boundary for
cooperative UI consumers, not a sandbox against malicious Python code.

John's latest screenshot confirms the refreshed PDF now parses without the
previous startxref warning on the Dell. John's next screenshot confirms 51 passed in 2.35s on Dell, Attempt 2 reflection
with one error and reconciled=true, and DLQ after 4 attempts with a saved path.

## Dell verification commands

In the existing repository folder, run in order:

```powershell
git pull --ff-only
uv sync --locked
uv run pytest -v
uv run python -m src.cli --demo reflection --summary
uv run python -m src.cli --demo dlq --summary
```

Expected: 51 passed; reflection succeeds on attempt 2; deliberate hard failure
routes to DLQ after 4 attempts. Timing and DLQ filename vary. These are offline
simulations and do not use or spend API credits. Review ai_prompt_log.md for
the two findings and before/after code; the Step 4 web UI comes next.
