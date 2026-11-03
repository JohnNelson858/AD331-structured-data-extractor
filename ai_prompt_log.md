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
its sample prompt remain the preceding conversation …1472 tokens truncated…n## Step 4 - interactive web interface

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
