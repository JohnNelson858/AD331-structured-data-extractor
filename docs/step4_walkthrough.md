# Step 4: interactive workbench and Dell verification

## Start the application

From the existing project folder in PowerShell:

```powershell
git pull --ff-only
uv sync --locked
uv run pytest -v
uv run uvicorn src.app:app --host 127.0.0.1 --port 8001
```

Keep that PowerShell window open. Open http://127.0.0.1:8001 in Edge or Chrome.
Port 8001 avoids the earlier LLM gateway's port 8000. If 8001 is occupied, stop
the older instance with Ctrl+C or choose another local port and matching URL.
To stop this application, return to its PowerShell window and press Ctrl+C.

## First visual check

1. Leave Execution mode at **Offline sample demo**.
2. Click **Load sample**. The fictional Cascade Lab Supplies invoice appears.
3. Leave Sample scenario at **Clean extraction** and reflection checked.
4. Click **Run extraction**.
5. Confirm **Accepted**, **1** attempt, and **Within 0.02 tolerance**.
6. Inspect source text and validated JSON side by side. Money is represented as
   decimal strings intentionally. The reconciliation report shows actual Decimal
   differences as well as the tolerance; approximate equality allows 0.02.
7. Expand the audit events. **Download JSON** exports only the accepted invoice;
   **Download audit** exports the complete result and streamed events.

## Recovery controls to verify next

| Action | Expected result with reflection checked |
| --- | --- |
| Choose Incorrect total → reflection repair; Run extraction | Repaired via reflection; 2 attempts; validation_failed and reflection_prompt show the original 1500.00 error and exact correction messages |
| Uncheck reflection and repeat that scenario | DLQ · human review; 1 attempt; no reflection_prompt |
| Check reflection; click Simulate Edge Case Failure | Offline hard failure; DLQ · human review after 4 attempts; saved runtime/dlq path; no accepted JSON |
| Choose JSON fences → heuristic repair; Run extraction | Repaired via heuristic after 4 attempts; full schema validation still required |
| Turn reflection off for JSON fences and run | Heuristic recovery after the single allowed provider-interface call |

The edge-case button always uses the bundled sample and offline hard-failure
fixture. It does not send your uploaded document to a provider. All offline
responses are fixed test fixtures; no model runs and no API credits are spent.

## Uploads and pasted HTML

For a real PDF ingestion demonstration, choose Upload file and select the
repository's samples/invoice_messy.pdf (or use Download sample PDF first).
Only the normalized extracted text is displayed; the PDF itself is not embedded.
Use samples/vendor_contract.html for HTML upload, or paste its source and choose
Raw HTML. Its scripts/styles are removed without executing them.

Offline demos only accept the bundled invoice's normalized text, HTML or PDF.
An arbitrary document is rejected rather than paired with an unrelated fixed
result. Live mode is required to extract your own document. Empty, unreadable,
encrypted, oversized and OCR-required inputs produce visible errors before any
provider request. Supported uploads: PDF, HTML/HTM and UTF-8 TXT.

## Live mode (separate later check)

The application starts offline even when a key exists. Live mode becomes
selectable only when the server has OPENAI_API_KEY configured through the local
ignored .env or environment. No key-entry field exists in the browser. Restart
the server after changing its environment. Never show a key in a recording.

Choosing live mode also requires checking the explicit API-charge acknowledgement
before each run. The server enforces this too. Failure simulations cannot be
combined with live mode. Live quality has not yet been verified; the injected
live-route test is still an offline fixture, not an API request.

## Implementation and verification scope

- FastAPI serves local HTML/CSS/JavaScript; no CDN or browser framework required.
- POST /api/extract streams newline-delimited JSON: source, stage events, then
  final result/report. The browser displays events as chunks arrive, before the
  overall response finishes. No artificial delays or fabricated progress.
- Documents, outputs and prompts enter the DOM using textContent, never innerHTML.
  HTML is not rendered as executable markup. Content Security Policy restricts
  scripts/styles to local assets. No cross-origin API access is enabled.
- Same-origin browser checks and trusted local Host names protect the local
  workbench boundary; no public deployment/authentication is claimed. Start with
  the documented loopback host. Server upload limits apply to actual bytes even
  without Content-Length, and parsing runs before provider calls.
- Per-request providers and engine state keep concurrent extractions separate.
  Generator cleanup cancels unfinished extraction and closes owned OpenAI clients
  when a client disconnects; cancellation does not promise refunds for sent calls.
- Upload bytes stay in the request's temporary spool and are closed after parsing.
  DLQ records persist in ignored runtime/dlq. No arbitrary file-browsing endpoint
  or server filesystem download endpoint is exposed.
- The UI is responsive in CSS: below 800 px, source/results and controls stack.
  Actual browser appearance and mobile layout remain a Dell visual check.

All 51 earlier tests and 21 new HTTP integration cases passed. The exact final
run is in step4_test_results.txt. New coverage includes all three uploaded sample
formats, pasted HTML, streaming event structure, Decimal report, retry toggle,
reflection prompts, hard-failure disk records, malformed inputs, size limits,
origin/host checks, absent-key handling, and explicit live-route wiring via an
injected fixture provider. JavaScript passed node --check; uv lock --check and
git diff --check passed. Dependencies and uv.lock did not change.

Visual browser testing could not complete in the assistant environment: the
headless browser could not start and the separate browser could not connect to
the workspace's local server. No visual screenshot or live provider result is
claimed. The application and API were tested in-process through ASGITransport;
John's actual Dell page verification is the next check. Step 5 expands project
QA and Step 6 provides the separate Docker deployment alternative.

References used for implementation:
- https://fastapi.tiangolo.com/advanced/custom-response/
- https://fastapi.tiangolo.com/tutorial/request-files/
