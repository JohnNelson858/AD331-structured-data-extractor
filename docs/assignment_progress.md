# Assignment and rubric tracking

The assignment has Parts 1-7 plus the Part 8 rubric. Part 4 contains the six
implementation steps. Steps 1-3 code and audit are delivered; Step 3 Dell verification is pending.

| Rubric criterion | Evidence / planned check | Current status |
| --- | --- | --- |
| 1. Nested Pydantic v2 models, regex/bounds/enums, monetary/date handling, reconciliation (20) | src/schemas.py; tests/test_schemas.py | 32 tests verified on Dell; monetary/date policy review pending |
| 2. Native strict decoding and messy PDF/HTML ingestion (20) | Step 2 engine, source samples, real SDK request under MockTransport | Baseline implemented; live provider verification pending |
| 3. Reflection errors, exact bounds/backoff, json_repair and durable DLQ (20) | Step 2 baseline and smoke tests | Step 3 audited; 51 tests pass offline; Step 5 expanded QA pending |
| 4. Actual prompt/baseline and at least two genuine corrected findings (15) | ai_prompt_log.md; preserved baseline; diff + regression evidence | Two genuine engine findings corrected; before/after results and source diff recorded |
| 5. At least five tests covering golden document, rejection, reconciliation, Attempt 2 recovery and three-retry DLQ (10) | tests/test_extraction.py and tests/test_fallbacks.py | 51 schema/baseline/audit tests pass; required Step 5 test organization and expanded QA pending |
| 6. Responsive UI with side-by-side source/JSON, badge, events/prompts and failure button (15, shared with video) | Step 4 UI and browser verification | Pending |
| 6. Webcam + screen, video 5:00-7:00, live success/reflection/DLQ and pytest | Timed narrative after working app, actual saved MP4 | Pending |

## Six implementation steps

- [x] Step 1 code: project scaffolding and acceptance schema.
- [x] Step 1: locked environment verified on Dell, 32 passed in 1.03s.
- [ ] Step 1: student confirms review of the schema's monetary/date policy.
- [x] Step 2: generate and preserve baseline provider engine, ingestion, and recovery.
- [x] Step 2: Dell 44 tests pass; reflection and DLQ verified; PDF warning resolved.
- [x] Step 3: audit two legitimate engine flaws and verify corrections offline.
- [ ] Step 3: student reviews findings and verifies 51 tests on Dell.
- [ ] Step 4: build and verify interactive web UI.
- [ ] Step 5: complete structured QA with all required success/failure paths.
- [ ] Step 6: Docker build and actual end-to-end container demo (local option).

## Requirements to resolve explicitly during implementation

- `max_retries=3` means at most 1 initial provider attempt + 3 corrective
  attempts, unless assignment clarification requires a different convention.
  `attempts_used` reports actual provider calls; tests prove the boundary.
- Reflection disabled means no corrective model requests. The fallback still
  applies full validation before returning any success.
- A native strict provider may reject malformed syntax before returning text.
  Controlled fault injection must be labeled as such; do not claim malformed
  JSON came from a live strict provider when it did not.
- Full JSON, captured validation traces, exact correction prompts and attempts
  must be visible for the demo while avoiding credentials and private documents.
- OCR-required PDFs must be handled explicitly. Never report empty extracted
  text as successful document ingestion.
- Heuristic repair must preserve failure visibility and revalidate all fields.
  No invented missing values or all-None partial-success records.
- Durable DLQ writes must use safe filenames, omit secrets, survive the chosen
  container lifecycle, and handle write failures without false success.
- README must end with a current Mermaid diagram, setup, schema specification,
  app and test commands, audit summary, and honest deployment evidence.

## Submission checklist (later)

- [ ] Public repository contains final code, lockfile, samples, README and audit log.
- [ ] Local Docker execution shown, or cloud URL independently verified.
- [ ] Video demonstrates successful extraction, reflection, durable DLQ and QA.
- [ ] Actual video duration recorded as MM:SS and between 5:00 and 7:00.
- [ ] Webcam visible throughout; YouTube Unlisted/Public.
- [ ] Canvas submission includes John Nelson, repo, deployment note, video,
  commercial invoice domain, and verified validation strategy.

The provided template says "Week 2" although this assignment is Week 4.
Use the actual Canvas assignment title rather than carrying that typo forward.
