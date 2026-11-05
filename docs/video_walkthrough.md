# John Nelson: 5–7 minute video walkthrough

Target: **6:30**. Read [video_narration.txt](video_narration.txt) in a natural
voice while following the screen actions below. The headings and bracketed
time markers are cues, not spoken text. Actual duration must be measured after
recording; the script cannot guarantee runtime.

## Prepare before recording

- Pull the documentation update: `git pull --ff-only`. This update changes docs
  only; your verified application image does not need a rebuild.
- Keep Docker Desktop running and the extractor healthy on http://127.0.0.1:8001.
  The configured live override must be running if you plan the real API demo.
  You already verified it; a documentation pull does not change that container.
- Open the repository in VS Code and prepare tabs/scroll positions for README's
  Mermaid diagram, src/schemas.py (LineItem and InvoiceExtraction),
  ai_prompt_log.md (Step 2 provenance and Step 3 Findings 1/2),
  src/fallback.py (reflection_evidence), src/extractor.py (event callback),
  src/provider.py (response_format), and the final verification report.
- Make source and audit text readable on the recording. Increase browser/editor
  text size if needed. Avoid shrinking the whole desktop to fit every file.
- Use your established Zoom/OBS/Loom recording setup. Both webcam and screen
  must stay visible throughout. Reserve space so the camera does not hide code,
  the LIVE/OFFLINE badge, status cards, reconciliation, errors or final test count.
  Test this with a short recording before the full take.
- Open PowerShell in the project folder. Prepare `uv run pytest -v` without
  executing it yet. Leave source tabs ready so navigation takes only seconds.
- Have runtime/docker_verification.json ready to show the persistence PASS.
  This saved local report is from the actual Docker check you already completed.
- Keep your new API key file, .env, OpenAI account pages and password tools closed.
  Do not open .secrets during recording or show expanded credential values.
- Rehearse with **Offline sample demo**. For the final recording, the live success
  section can make **one separately billed API request**, with reflection off and
  your explicit acknowledgement. The recovery demonstrations use offline fixtures.
- If saved, your prior live results belong under runtime/live-verification:
  validated-invoice.json and extraction-audit.json. We verified the screenshot;
  the downloaded files themselves were not supplied for independent inspection.

## Timeline and screen actions

| Recording time | Screen actions | Main evidence |
| --- | --- | --- |
| 0:00–1:00 | Show repository tree and rendered README flow; switch to prepared schemas.py tab; point to LineItem, InvoiceExtraction, before validators and reconcile | Nested model, regex/enums/bounds, Decimal, normalization, cross-field checks |
| 1:00–2:25 | Show ai_prompt_log.md Step 2/3; show actual old snippets, then prepared reflection_evidence and callback fix; briefly point to docs/step3_before.txt and step3_after.txt | Genuine generation provenance; two real audited defects; preserved baseline and regression proof |
| 2:25–3:50 | Browser: choose Live OpenAI, Upload file, samples/invoice_messy.pdf; reflection OFF; authorize API charges; Run once. During generation briefly show response_format json_schema/strict=true; return to source/JSON, report and audit | Real model extraction, typed acceptance, correct totals/date; no claim of factual perfection |
| 3:50–4:35 | Switch to Offline sample demo; click Load sample (selects Paste); choose Incorrect total → reflection repair; reflection ON; Run; inspect validation failed and reflection prompt, then accepted Attempt 2 | Controlled valid-shape/business-rule failure and targeted recovery |
| 4:35–5:20 | With reflection ON, click Simulate Edge Case Failure; show four attempts, no accepted record, then scroll to dlq written/path/human-review flag | One initial attempt + three retries; explicit failure and persisted DLQ |
| 5:20–5:45 | Choose JSON fences → heuristic repair; reflection OFF; Run; show Repaired via heuristic and 1 attempt | Conservative formatting repair followed by full validation |
| 5:45–6:15 | PowerShell: run uv run pytest -v immediately; narrate coverage while it runs; pause on the final 118 passed line | Required five scenarios plus resilience checks, actual execution |
| 6:15–6:30 | Run docker compose ps; show healthy service; switch to saved runtime/docker_verification.json and point to dlq_after_recreation PASS; close | Actual local deployment and prior verified persistence |

The narration groups 3:50–5:45 as one section; its three paragraphs/actions follow
the three recovery rows. Advance at the target times rather than rushing text.
The roughly 700 spoken words allow short navigation pauses at about 125–135
words/minute. Test/response wait time can overlap the relevant explanation.

## Important execution details

1. **The live key is already configured.** Do not reopen it or create a new key
   for every rehearsal. The new key's expiry must cover the actual recording day.
2. The real API success must be labeled LIVE OPENAI. Reflection remains unchecked
   to limit that run to one provider call. A schema-valid result is expected,
   but a new model invocation can differ. If it fails, stop the take and inspect
   its audit before another paid request; do not repeatedly click Run.
3. After the live section, choosing Offline reveals the Sample scenario dropdown.
   **Load sample** switches to Paste and fills the bundled text. This avoids
   leaving an old upload or unrelated source active during fixture demonstrations.
4. The failure button overrides the selected scenario and runs the hard-failure
   fixture. Re-enable reflection first so its limit is four total attempts.
5. The malformed JSON and JSON fences are deliberately injected offline. Never
   imply those were generated by the live strict-schema provider.
6. Reflection_prompt records the assembled corrective messages. The following
   provider_request records dispatch. Show both if explaining the sequence.
7. Expand/collapse audit disclosures to keep the relevant trace visible. The
   reflection pane has its own scroll bar; expose its USER payload containing
   source_excerpt, previous_extraction and validation_errors.
8. Running pytest on the Dell uses its Python environment, while the UI remains
   served by Docker. The production image omits dev dependencies intentionally.
9. For the saved persistence report, the exact PASS text is:
   `PASS: new container, identical saved record bytes`. Show the existing report;
   rerunning container recreation inside a 6:30 presentation is unnecessary.
10. Switching the browser to Offline prevents further requests from that page
    unless Live is deliberately selected again. It does not unmount the key.
    For a complete offline deployment later, use the base Compose file; see
    docs/step6_docker.md. No additional deployment change is needed for rehearsal.

## Timing and recovery plan

- Target finish 6:30, leaving 30 seconds below the strict 7:00 maximum.
- At 3:50 be starting offline reflection. At 5:45 start pytest.
- If navigation is slow, shorten explanatory repetition; preserve schema,
  two audit defects, success, reflection, DLQ, tests and webcam evidence.
- Heuristic repair is valuable; its one-call demonstration is budgeted for 25
  seconds. Keep the explanation short enough to reach pytest on time.
- If live generation stalls, continue its structural-validation explanation
  while waiting. If that prevents a complete 5–7 minute take, resolve the issue
  and record a new take. Never present a fixture as the successful live call.
- Avoid ending below 5:00. Use genuine evidence/explanation rather than filler.
- Review the saved video from beginning to end. Confirm readable screens, audible
  voice, webcam visibility, actual duration and absence of credentials. Do not
  check these items as complete based only on this planned timeline.

## Your understanding check before recording

Mark the human-review items in assignment_progress.md after you can explain:

- Why Decimal and a two-cent tolerance are used, and why valid JSON alone does
  not establish monetary consistency.
- Why a root reconciliation error has an empty field location, and how truncating
  to a document's beginning could hide the evidence needed to correct it.
- Why passing a mutable retained audit event to a callback was a defect, and
  how deep-copy/error isolation fixes that interface.
- Why three retries means four total calls, and why a failure must never become
  an all-None or invented success record.

The script is AI-assisted presentation support. Read the corresponding code and
logs before presenting these points as your understanding. The repository log
already discloses AI assistance; it does not attest to an unseen student review.

## Submission after recording

Use [submission_template.md](submission_template.md). Replace the YouTube URL and
actual MM:SS duration. Set the video to Unlisted or Public and verify that a
viewer can open it without your account. The Docker option is a local-demo
alternative; 127.0.0.1 is not a public deployment link for the instructor.
