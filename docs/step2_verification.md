# Step 2 baseline verification

Assistant environment, November 3, 2026: Python 3.11.17, Pydantic 2.14.2,
OpenAI SDK 2.54.0. Initial smoke run: **44 passed in 1.89s**. Final
`uv run pytest -v`: **44 passed in 1.09s**, using no paid API calls.
`uv lock --check` and `git diff --check` also passed.

## Observed offline CLI results

| Command suffix | Status | Actual provider-interface calls |
| --- | --- | --- |
| `--demo success --summary` | SUCCESS | 1 |
| `--demo reflection --summary` | REPAIRED_VIA_REFLECTION | 2 |
| `--demo dlq --summary` | DLQ_FAILED, record written | 4 |
| `--demo heuristic --no-reflection --summary` | REPAIRED_VIA_HEURISTIC | 1 |

All commands begin with `uv run python -m src.cli`. These calls use an offline
fixture provider. They are deterministic simulations, not real OpenAI results.
The PDF loader and business validation execute normally. The SDK request test
uses a real AsyncOpenAI client and httpx.MockTransport, with no internet API call.

The PDF is a synthetic text-layer fixture and was rendered for visual inspection.
HTML preprocessing, OCR-required blank-page handling, bounded feedback, refusal
handling, missing information, conservative repair, and retry limits have initial
smoke coverage. Full audit, fault coverage, UI and Docker checks remain pending.

## Dell verification, November 3, 2026

John's screenshot confirms **44 passed in 9.30s**, reflection success on Attempt
2, and DLQ_FAILED after 4 calls with a saved runtime/dlq record. Both CLI runs
also showed `incorrect startxref pointer(1)` and `parsing for Object Streams`.

The assistant reproduced those exact PDF parser warnings by converting the
checked-in sample's LF bytes to Windows CRLF. The original 1526-byte PDF parses
without the warnings. It contains no NUL bytes, allowing Git's text heuristics
to treat it as text unless attributes explicitly forbid conversion.

Portability correction: `.gitattributes` now declares `*.pdf binary`, disabling
text conversion. Git's Windows checkout filter was checked with core.autocrlf
enabled and must preserve the original PDF bytes. On an existing checkout,
pull the attribute rule then regenerate this synthetic sample using:

```powershell
git pull --ff-only
uv run python scripts/build_samples.py
uv run python -m src.cli --demo reflection --summary
```

Warning-free PDF parsing on the Dell remains pending this refresh. The baseline
commit is preserved; this is a separate portability fix, not a rewritten baseline.

### Original verification commands

In the existing repository folder:

```powershell
git pull --ff-only
uv sync --locked
uv run pytest -v
uv run python -m src.cli --demo reflection --summary
uv run python -m src.cli --demo dlq --summary
```

No `.env`, provider key or Docker required. These offline commands cannot spend
API credits. A DLQ JSON file is expected under `runtime/dlq`; this folder is
ignored by Git. Do not commit private source material or runtime audit records.

## Later opt-in live check (not requested for this milestone)

The CLI has `--live --input samples/invoice_messy.pdf`. This makes separately
billed API calls. Configure an actual OpenAI key only in the ignored `.env` on
the Dell; do not share it. Live verification will be guided separately after
the audit. No live run has been performed or claimed in this milestone.

## Primary references

- Native strict schemas and completion exceptions:
  https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat
- PDF extraction and OCR limits:
  https://pypdf.readthedocs.io/en/stable/user/extract-text.html
- json_repair behavior:
  https://github.com/mangiucugna/json_repair
