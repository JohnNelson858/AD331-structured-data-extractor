"""Auditable extraction results for CLI now and UI in Step 4."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.schemas import InvoiceExtraction, SCHEMA_VERSION

Status = Literal["SUCCESS", "REPAIRED_VIA_REFLECTION", "REPAIRED_VIA_HEURISTIC", "DLQ_FAILED", "DLQ_WRITE_FAILED"]


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: str
    attempt: int = Field(ge=0)
    detail: dict[str, Any]


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    execution_status: Status
    validated_data: InvoiceExtraction | None = None
    attempts_used: int = Field(ge=0)
    error_log: list[str] = Field(default_factory=list)
    events: list[AuditEvent] = Field(default_factory=list)
    dlq_path: str | None = None
    elapsed_ms: float = Field(ge=0)
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def check_outcome(self):
        successful = self.execution_status in {"SUCCESS", "REPAIRED_VIA_REFLECTION", "REPAIRED_VIA_HEURISTIC"}
        if successful != (self.validated_data is not None):
            raise ValueError("success requires a fully validated invoice; failure must not contain one")
        if self.execution_status == "DLQ_FAILED" and not self.dlq_path:
            raise ValueError("DLQ_FAILED requires a recorded DLQ path")
        return self
