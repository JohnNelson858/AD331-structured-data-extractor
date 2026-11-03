"""Targeted correction, conservative JSON repair, and atomic local DLQ."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from uuid import uuid4
from json_repair import repair_json
from src.schemas import SCHEMA_VERSION

MAX_RESPONSE_CHARS = 20000
MAX_FEEDBACK_CHARS = 6000


def safe_text(value: str) -> str:
    """Remove common provider-key shapes, not every possible secret or PII."""
    return re.sub(r"sk-[A-Za-z0-9_-]{16,}", "[REDACTED_API_KEY]", value)


def reflection_evidence(source: str, issues: list[dict]) -> str:
    """Bounded, explicitly incomplete evidence with original character offsets.

    Keep short documents intact. For long documents preserve both ends plus
    windows around invoice labels and failing fields; never silently imply that
    a selected excerpt contains every line item or required fact.
    """
    if len(source) <= MAX_FEEDBACK_CHARS:
        return source

    def render(spans):
        merged = []
        for start, end in sorted(spans):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        return "\n\n".join(f"[source chars {start}:{end}]\n" + source[start:end]
                             for start, end in merged)

    spans = [(0, 1200), (len(source) - 1200, len(source))]
    terms = list(dict.fromkeys(str(part).replace("_", " ")
        for issue in issues for part in issue.get("loc", []) if isinstance(part, str)))
    patterns = [re.escape(term) for term in terms] + [
        r"\binvoice\b", r"\bvendor\b", r"\bdate\b", r"\bline[ _-]*items?\b",
        r"\bquantity\b|\bqty\b", r"\bsubtotal\b", r"\btax\b", r"\btotal\b", r"\bcurrency\b",
    ]
    # Consider first and last matches per label. Each proposed window must fit
    # with its offset markers; the budget never grows with document/history size.
    matches = [list(re.finditer(pattern, source, re.IGNORECASE)) for pattern in patterns]
    for side in (0, -1):
        for found in matches:
            if not found:
                continue
            match = found[side]
            candidate = (max(0, match.start() - 160), min(len(source), match.end() + 240))
            proposed = spans + [candidate]
            if len(render(proposed)) <= MAX_FEEDBACK_CHARS:
                spans = proposed
    return render(spans)


def reflection_messages(system: str, source: str, failed: str, issues: list[dict]) -> list[dict[str, str]]:
    # Rebuild, never append whole documents and history on each iteration.
    evidence = reflection_evidence(source, issues)
    truncated = len(source) > MAX_FEEDBACK_CHARS
    payload = {
        "source_excerpt": evidence,
        "source_excerpt_incomplete": truncated,
        "source_characters": len(source),
        "previous_extraction": failed[:MAX_RESPONSE_CHARS],
        "validation_errors": issues,
        "correction_request": "Re-extract from evidence. Correct only supported values. "
            "An incomplete excerpt may omit required facts; previous output is not evidence. "
            "Never invent absent data; return insufficient_source when needed.",
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]


def conservative_repair(raw: str) -> str | None:
    """Only accept fences/trailing commas, with a complete object and unchanged values."""
    if len(raw) > MAX_RESPONSE_CHARS:
        return None
    stripped = raw.strip()
    if stripped.startswith("```json\n") and stripped.endswith("\n```"):
        stripped = stripped[8:-4].strip()
    elif stripped.startswith("```\n") and stripped.endswith("\n```"):
        stripped = stripped[4:-4].strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        return None
    cleaned = []
    in_string = escaped = False
    for index, char in enumerate(stripped):
        if in_string:
            cleaned.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            if char == "," and stripped[index + 1:].lstrip().startswith(("}", "]")):
                continue
            cleaned.append(char)
    try:
        expected = json.loads("".join(cleaned))
        repaired = repair_json(stripped, return_objects=False)
        if json.loads(repaired) != expected:
            return None
        return repaired if raw.strip() != repaired else None
    except (ValueError, TypeError, RecursionError):
        return None


def write_dlq(directory: Path, source: str, payload: str, attempts: int, errors: list[str], model: str) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    stem = uuid4().hex
    temporary, final = directory / (stem + ".tmp"), directory / (stem + ".json")
    record = {
        "record_id": stem, "created_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": SCHEMA_VERSION, "model": model,
        "source_sha256": sha256(source.encode()).hexdigest(),
        "source_excerpt": safe_text(source[:2000]),
        "failed_payload": safe_text(payload[:MAX_RESPONSE_CHARS]),
        "attempts_used": attempts, "errors": errors, "needs_human_review": True,
    }
    try:
        with temporary.open("x", encoding="utf-8") as file:
            os.chmod(temporary, 0o600)
            json.dump(record, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, final)
    finally:
        temporary.unlink(missing_ok=True)
    return str(final)
