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
- [ ] John has cloned this repository on the Dell and run the Step 1 checks.

## Step 2 - baseline extraction generation

Pending. Preserve the actual generated baseline in Git before auditing.
Do not fabricate a separate prompt, intentionally insert bugs, or manufacture
before/after test failures for the video.

## Step 3 - audit and corrections

Pending. At least two genuine code defects, security gaps, or anti-patterns
must be identified and refactored with specific evidence and regression checks.
Inspect v2 API usage, bounded source context, deterministic acceptance and DLQ,
and explicit date/type normalization. Step 1 design choices are not substitutes
for auditing the Step 2 generated engine.
