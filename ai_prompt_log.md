# AI prompt and human verification log

## Step 1 - environment and schema definition

AI tool: ChatGPT/Codex in the ongoing AD 331 conversation.
Date: November 1, 2026 (student time zone).

### Actual initiating user instructions

> Help me with this assignment the way you did with the Multi-Provider Async LLM Gateway one. This assignment has seven parts with Part 4 having 6 steps. Part 8 is the grading Rubric. Make sure I have completed all of the criteria. I want my repo to be named: https://github.com/JohnNelson858/AD331-structured-data-extractor. I have not created it yet. See if you can create it for me otherwise, I will. Also, I will need a narrative for my video presentation. Ask me any questions you need and let’s take it one step at a time.

The full assignment and sample generation prompt were supplied in the same
conversation. After the assistant proposed commercial invoices, FastAPI,
uv/Python 3.11, OpenAI native structured output, and local Docker, the user
created the repository and replied:

> Ok, here it is: https://github.com/JohnNelson858/AD331-structured-data-extractor

### What the AI generated in this milestone

Project configuration, ignore rules, example environment variables, nested
Pydantic v2 invoice and line-item models, schema fixtures and tests, and a
rubric tracking document. Extractor/fallback/app modules contain only explicit
future-step docstrings. No separate AI service was called to generate the code.

### Design decisions and limitations

- Use Decimal rather than the sample prompt's binary float for monetary checks.
- Use documented date/money pre-parsers and strict quantities, not unrestricted coercion.
- Check line arithmetic, subtotal, total, and optional tax percentage independently.
- Use native strict schema output in Step 2, not `json_object` alone.
- Keep provider wire constraints separate from cross-field business validators.
- pypdf extracts a PDF text layer; image-only scans need an explicit OCR path or clear rejection.
- Do not label heuristic repair as reflection recovery or accept partial objects as success.
- Do not mark deployment, paid integration tests, or human review complete before evidence exists.

### Human review

Assistant verification: 32 schema tests passed. See
`docs/step1_verification.md` for exact commands and measured results.
This is not a substitute for the student's review or Dell verification.

- [ ] John has reviewed the schema and monetary/date policy.
- [x] John cloned this repository on the Dell and ran Step 1 checks: Python
  3.11.17, 32 passed in 1.03s, verified from November 3 screenshots.

## Step 2 - baseline extraction generation

Actual user instruction: **"Proceed with Step 2."** The original assignment and
its sample prompt remain the preceding conversation context. ChatGPT/Codex
generated this baseline directly; there was no separate external AI invocation.
See `docs/step2_generation_prompt.md` for provenance and implementation scope.

Generated modules: native strict provider adapter and wire schema, PDF/HTML/text
ingestion, SchemaExtractor orchestration, reflection/repair/DLQ helpers, result
metadata, CLI, synthetic samples and offline smoke tests. The Step 2 Git commit
preserves the baseline before Step 3. It must not be retroactively rewritten to
manufacture audit evidence.

Assistant verification: initial **44 passed in 1.89s**, final verbose run
**44 passed in 1.09s** (32 existing schema cases plus
12 baseline cases), using fixture responses or SDK MockTransport only. CLI
success, Attempt 2 reflection, bounded DLQ, and conservative heuristic repair
were also exercised. No live provider call or student baseline review is claimed.

No deliberately inserted defects or fabricated failing results are used.
Step 3 will review this actual baseline and record genuine findings with diffs
and regression evidence. The baseline is not labeled production-ready.

## Step 3 - audit and corrections

### Preliminary portability finding during Step 2 Dell verification

The Step 2 sample PDF is valid in its original bytes, but the generated project
omitted a PDF binary rule in Git attributes. On Windows, text-mode checkout can
convert LF to CRLF and invalidate the PDF's byte offsets. John observed the
parser recovering with `incorrect startxref pointer(1)` and
`parsing for Object Streams`, despite all 44 tests passing in 9.30s.

The assistant reproduced both exact warnings by newline-converting the original
sample. Added `.gitattributes` with `*.pdf binary`, then verified Git's checkout
filter under core.autocrlf=true preserves the original bytes. John refreshed
the synthetic fixture; his latest screenshot confirms warning-free reflection
on Attempt 2 with one validation error and reconciled=true.
This is a genuine portability defect, preserved as a separate follow-up commit.
It does not complete the required two-finding engine audit by itself.

### Audit request and preserved output

Actual user instruction: **"Proceed with Step 3."** The preceding assignment
requires a rigorous audit, at least two actual corrections and recorded evidence.
Baseline commit: `2d758963f745a3a6648c9c298094dd39f4eb1d6e`.
Pre-audit HEAD: `858874c0dcc333c2fbb795eb36ac211d7e7841f3`.
The baseline modules are available in Git, not replaced with fabricated examples.

### Finding 1: bounded reflection context drops required facts

Actual baseline logic in src/fallback.py:

```python
terms = {str(x) for issue in issues for x in issue.get("loc", []) if isinstance(x, str)}
relevant = [line for line in source.splitlines() if any(term.replace("_", " ").lower() in line.lower() for term in terms)]
evidence = ("\n".join(relevant) if relevant else source)[:MAX_FEEDBACK_CHARS]
```

For a root-level total mismatch, loc=[] leaves no terms. A long invoice's
late totals disappear behind boilerplate. For a currency-only error, selecting
just the currency line removes the rest of a short invoice. Two pre-fix tests
failed with these exact inputs. Merely adding a context cap was insufficient.

Refactor: reflection_evidence preserves complete short sources; long sources
keep header/footer plus label/field windows, merge overlaps, show source offsets,
and fit the original 6000-character cap. Prompt metadata marks incomplete source
and states that previous model output is not evidence. Never invent missing facts.
The seven-case audit module includes a full retry dispatch check for late totals.
The cap remains character-based; long-document evidence completeness is not guaranteed.

### Finding 2: observer exceptions and mutation compromise the engine

Actual baseline logic in src/extractor.py:

```python
events.append(item)
if on_event:
    on_event(item)
```

Three pre-fix cases failed: throwing callbacks abort both the valid and hard-fail
pipelines; a callback changing stage/detail changes the retained event itself.
This would make the future UI an unexpected failure source and weaken auditability.

Refactor: dispatch model_copy(deep=True); catch ordinary Exception, disable the
failed observer, append a sanitized audit_sink_failure warning, and continue
normal validation or DLQ. Exception text is not copied into retained results.
CancelledError still propagates, verified by the pre-existing passing regression.
This protects the callback interface, not arbitrary execution by malicious code.

### Required four-area review and measured evidence

Pydantic v1/v2 search found no v1 decorators or .dict() in src. Existing v2
validators and model_dump are correct. Existing date/money pre-parsers handle
explicit formats and reject ambiguous/coerced values; no artificial fixes claimed.
Strict wire schema and full business validation remain mandatory on every success,
including heuristic repair. No half-empty all-None success bypass was found.
The genuine context-selection problem and observer defects above were corrected.

Before editing engine/helpers: **5 failed, 1 passed in 0.91s** across six new
regression cases. Final full run: **51 passed in 1.32s** (one further end-to-end
case added after correction). Raw captured output: docs/step3_before.txt and
step3_after.txt. Source diff: docs/step3_refactor.diff. Details and limits:
docs/step3_verification.md. No paid API calls were made.

Step 3 code/audit complete. John's screenshot confirms 51 passed in 2.35s on
Dell, successful Attempt 2 reflection and DLQ after 4 attempts with a saved file.
His review of the findings remains pending. Step 4 UI, Step 5
expanded project QA, Step 6 container execution and final video remain pending.

## Step 4 - interactive web interface

Actual user instruction: **"Proceed with Step 4."** The original assignment and
verified Step 3 pipeline were the context; no separate AI service was invoked.
ChatGPT/Codex generated src/app.py, src/static/index.html, app.css, app.js and
21 HTTP integration tests in tests/test_web.py. The existing audited engine
was reused without changing its acceptance or retry rules.

Implemented upload PDF/HTML/text or pasted HTML/text; reflection toggle;
source/validated JSON side by side; streamed audit events including field errors
and exact corrective prompts; reconciliation status and Decimal differences;
offline reflection, heuristic and DLQ simulations; accepted JSON/audit downloads.
The failure button is always an explicit offline simulation against the sample.

Design choices: default offline mode; fixed fixtures restricted to bundled
source content so they cannot misrepresent arbitrary-document extraction; live
mode requires a server key and explicit charge acknowledgement; no browser keys.
Bound actual upload bytes, reject bad source before calling a provider, render
untrusted text using textContent, enforce same-origin browser requests and local
hostnames, and close per-request providers on completion/cancellation.

During implementation an upload-limit test initially received 400, not the
expected 413: a single oversized form field hit the parser's 1 MB field limit
before the whole-request limit. The final test streams a multipart file across
the 6 MB request boundary and verifies the actual body-limit path. BodyTooLarge
uses HTTPException so request parsing preserves the intended 413 status. This
is Step 4 development evidence, not an invented Step 3 baseline finding.

Measured final results are in docs/step4_test_results.txt: 72 total passing
cases (51 earlier + 21 HTTP cases). node --check passed for browser JavaScript;
lockfile and whitespace checks passed. No actual live API calls were made.
The live-route wiring test injects a fixture provider and is labeled offline.

Visual browser verification could not finish in the assistant environment;
no screenshot, confirmed responsive layout or successful live extraction is
claimed. Dell visual verification is pending. See docs/step4_walkthrough.md
for commands, exact expected outcomes and remaining scope. Step 5 expanded QA,
Step 6 Docker and the final timed video are still pending.

## Step 5 - structured project QA

Actual user instruction: **"Proceed with Step 5."** Preceding context included
the original assignment and John's screenshots verifying Step 4's main browser
flows: clean sample, reflection, reflection disabled, bounded DLQ, heuristic,
PDF upload and HTML upload. No additional AI service was invoked.

ChatGPT/Codex populated the existing Step 5 test placeholders with 10 cases in
tests/test_extraction.py and 26 in tests/test_fallbacks.py. tests/conftest.py
supplies synthetic fixtures, captured provider sequences, a virtual sleeper and
an autouse real-socket connection guard. The golden test uses actual pypdf,
AsyncOpenAI/strict JSON Schema serialization and Pydantic, with MockTransport
returning the model response. No live model or paid API call is claimed.

The required five tests are explicitly named/mapped, with additional failure
coverage for transport recovery, retry limits/deadlines, storage failure,
conservative repair, oversize/incomplete responses, key-shape redaction,
concurrency and cancellation. Source/data comparisons use the normalized text
that ingestion actually sends, not the original unnormalized spacing.

QA found a real gap: only transient-provider retries had backoff. Validation
reflection retried immediately. After correcting normalization expectations in
the new tests, the targeted pre-fix run showed **2 failed, 34 passed in 0.63s**.
Saved output: docs/step5_before.txt. Fixed by sharing a deadline-aware pause
helper and adding 0.25/0.50/1.00-second validation retry pauses. Both retry kinds
now report a safe deadline exhaustion rather than scheduling an out-of-budget
wait. Source diff: docs/step5_refactor.diff. This is a new Step 5 finding; the
separate Step 3 baseline findings and original Git history remain intact.

Final full suite: **108 passed in 10.81s**; raw output in
docs/step5_test_results.txt. Lock and whitespace checks passed. Engine tests
inject a virtual sleeper where exact delays matter; existing smoke/HTTP paths
also exercise real short reflection pauses. No dependency change was required.

See docs/step5_verification.md for the five-case rubric map and complete scope.
Step 5 Dell verification remains pending. Step 6 Docker, actual live provider
verification, student policy/audit review and final recording/submission remain
pending. The future narration will describe offline fault injection honestly.
