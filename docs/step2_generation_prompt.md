# Step 2 generation provenance

The actual new user instruction was **"Proceed with Step 2."** It referred to
the complete Resilient Unstructured Data Extraction & Pydantic Validation
Pipelines assignment supplied earlier in the same conversation, including its
sample initial prompt. The code was generated directly by ChatGPT/Codex in that
conversation, not by sending an invented standalone prompt to another service.

## Requirements applied from that assignment

- Python 3.11+, Pydantic v2 nested invoice schema and arithmetic validation.
- Ingest PDF text or HTML and use native schema-constrained generation.
- `extract_with_retry(raw_text, max_retries=3)` with result metadata.
- Capture loc/msg/type for Pydantic failures and send the failed payload,
  relevant source, and precise errors for corrective re-extraction.
- Add finite reflection bounds, backoff, conservative json_repair fallback,
  and explicit DLQ failure reporting.
- Preserve the baseline before the later code audit.

## Explicit adaptations to the sample prompt

The assignment sample mentions `json_object`, which only guarantees JSON syntax.
This implementation uses `json_schema` with `strict: true`, checked by a real SDK
request through an offline HTTP mock. The strict wire schema has closed objects
and all fields required; `tax_rate_percent` and the invoice envelope use explicit
nullability. Monetary strings feed the separate Decimal acceptance model.

An envelope can report `insufficient_source` instead of fabricating an invoice
to satisfy required fields. Unexpected finish reasons such as length/refusal
are failure paths and are not repaired into apparent success.

`max_retries=3` is defined as one initial call plus at most three more calls.
Reflection disabled means one call. SDK retries are disabled in the owned
client. The baseline deadline is 90 seconds, each owned SDK request has a
30-second timeout, and generation allows up to 3000 output tokens per request.

The source character cap is 24000. Correction excerpts are capped at 6000
characters, previous responses at 20000. These are character bounds, not exact
token accounting. No rolling conversation history is appended on each retry.

Heuristic repair is an explicitly labeled third outcome. Only surrounding
fences or trailing commas in otherwise complete objects may be repaired, then
the full schema and business checks run again. No partial extraction or default
all-None object is accepted as success.

The baseline is a candidate for Step 3 review. Smoke tests do not establish
production safety, source faithfulness, OCR capability, live provider support
on the student's account, or completion of the full rubric.
