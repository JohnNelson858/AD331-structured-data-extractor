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


def reflection_messages(system: str, source: str, failed: str, issues: list[dict]) -> list[dict[str, str]]:
    # Rebuild, never append whole documents and history on each iteration.
    terms = {str(x) for issue in issues for x in issue.get("loc", []) if isinstance(x, str)}
    relevant = [line for line in source.splitlines() if any(term.replace("_", " ").lower() in line.lower() for term in terms)]
    evidence = ("\n".join(relevant) if relevant else source)[:MAX_FEEDBACK_CHARS]
    payload = {
        "source_excerpt": evidence,
        "previous_extraction": failed[:MAX_RESPONSE_CHARS],
        "validation_errors": issues,
        "correction_request": "Re-extract from evidence. Correct only supported values. Never invent absent data; return insufficient_source when needed.",
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
