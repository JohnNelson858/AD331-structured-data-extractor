# Final repository and submission checklist

John Nelson · AD 331 · finalized November 4, 2026 (Pacific)

The six implementation steps are complete and verified for this educational
invoice domain. The repository is public. The remaining deliverables are the
student's final understanding review and the recorded/uploaded/submitted video.
A planned narration is not proof of video completion.

## Rubric evidence

| Category | Points | Repository / verification evidence | Status |
| --- | ---: | --- | --- |
| Schema architecture | 20 | src/schemas.py; nested LineItem/InvoiceExtraction; v2 field/model validators; regex, enum, strict quantities, Decimal money, date normalization and inclusive 0.02 reconciliation; tests/test_schemas.py | Implemented and tested; student policy review below |
| Extraction and constrained decoding | 20 | src/ingestion.py and src/provider.py; real PDF/HTML parsers; native json_schema + strict=true; live PDF screenshot: Accepted, 1 attempt, total 1374.45 USD | Verified on Dell; one live success, not a general accuracy benchmark |
| Reflection and fallback | 20 | src/extractor.py and src/fallback.py; exact errors, bounded excerpts/retries, deadline-aware backoff, conservative repair, explicit DLQ; Docker verifier confirms each route and persistent record | Verified with labeled offline fault injection and real engine/storage |
| AI audit and human verification | 15 | ai_prompt_log.md; actual prompt context; immutable baseline; two genuine Step 3 findings, source diff and 5 pre-fix failed regressions | Audit evidence complete; student review below |
| Automated QA | 10 | Required named cases in tests/test_extraction.py and tests/test_fallbacks.py; broader schema/web/config/guard coverage; John reports 118 passed in 11.62s on Dell | Verified |
| UI, video and professionalism | 15 | src/static UI; source/JSON, reconciliation, events/errors/prompts, reflection toggle, failure control; Docker healthy and persistent DLQ; prepared timed narration and screen guide | Technical work verified; actual 5–7 minute webcam video pending |

Points describe the assignment's categories, not an awarded or guaranteed score.
Full observed results and limits: [final_verification.md](final_verification.md).

## Six implementation steps

- [x] Step 1: uv/Python project, lockfile and strict nested Pydantic v2 models.
- [x] Step 2: preserved AI-generated provider/ingestion/extraction/recovery baseline.
- [x] Step 3: two real engine defects reproduced, corrected and regression-tested.
- [x] Step 4: main desktop UI flows verified on Dell, including PDF/HTML upload.
- [x] Step 5: required five scenarios and additional failure-path QA; Windows guard corrected.
- [x] Step 6: actual Docker build and healthy service on 127.0.0.1:8001 verified.
- [x] Container verifier: six routes plus saved DLQ record; recreation retains identical bytes.
- [x] Updated suite: John reported 118 passed in 11.62 seconds on Dell.
- [x] Real OpenAI PDF extraction: Accepted, 1 attempt, reconciliation passes; reflection off.

## README and repository requirements

- [x] Original Mermaid architecture/data-flow diagram in README.
- [x] uv setup with Python 3.11+, pyproject.toml and uv.lock.
- [x] Schema field/type/normalization and cross-field policy specification.
- [x] Exact commands for web app, tests and Docker alternative.
- [x] AI audit summary with real provenance, defects, fixes and evidence.
- [x] Synthetic messy PDF, HTML and text samples plus expected record.
- [x] Default offline mode and explicitly acknowledged live requests.
- [x] .env and .secrets excluded from Git/build context; file-based Docker secret option.
- [x] Durable Docker DLQ named volume and verifier/health helpers.
- [x] Timed video_narration.txt, video_walkthrough.md and submission_template.md.
- [x] Final verification documentation distinguishes live results from injected fixtures.

## Student review before recording

These require John's understanding and confirmation; the assistant cannot attest
to an unseen personal review. Use the short understanding check in the walkthrough.

- [ ] I reviewed the supported money/date/currency policy and can explain Decimal,
  explicit normalization, the 0.02 tolerance, unsupported scans and domain limits.
- [ ] I reviewed the actual AI prompt log, both audit findings and before/after
  code, and can explain the fixes in my own words.
- [ ] I checked that any retained local live downloads open correctly under
  runtime/live-verification. Those files remain excluded from the public repo.

## Video execution and submission

- [ ] Rehearsed the prepared narration with screen actions; target about 6:30.
- [ ] Recorded actual duration between 5:00 and 7:00, including all transitions.
- [ ] Webcam and screen visible throughout; code, JSON, errors and tests readable.
- [ ] Showed architecture/schema and at least two actual AI audit corrections.
- [ ] Demonstrated PDF/HTML ingestion and accepted validated record; live run labeled.
- [ ] Demonstrated reflection, bounded hard failure/DLQ and automated pytest execution.
- [ ] Showed Docker healthy status and verified persistent DLQ report.
- [ ] Labeled recovery fixtures as offline; did not imply malformed fixture output
  came from the native strict live provider.
- [ ] Reviewed the complete video for audio, visibility, timing and credentials.
- [ ] Uploaded as Unlisted/Public; verified the URL opens for a viewer.
- [ ] Filled in actual YouTube URL and MM:SS in submission_template.md.
- [ ] Submitted repository URL, Docker-demo note, video link, domain and strategy
  in the correct Canvas assignment.

Actual video URL: pending.
Actual video duration: pending.
Canvas submission: pending.
