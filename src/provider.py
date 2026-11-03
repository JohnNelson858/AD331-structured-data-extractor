"""Native OpenAI strict JSON Schema adapter, without JSON-mode downgrades."""
from dataclasses import dataclass
import re
from typing import Literal, Protocol
import openai
from pydantic import BaseModel, ConfigDict


class WireLine(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str
    quantity: int
    unit_price: str
    line_total: str


class WireInvoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_number: str
    vendor_name: str
    invoice_date: str
    line_items: list[WireLine]
    subtotal: str
    tax_amount: str
    total_amount: str
    currency: Literal["USD", "EUR", "GBP"]
    tax_rate_percent: str | None


class WireEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: Literal["extracted", "insufficient_source"]
    invoice: WireInvoice | None
    reason: str


@dataclass(frozen=True)
class ProviderReply:
    content: str
    finish_reason: str = "stop"


class ProviderFailure(Exception):
    """Public error code only, never raw SDK response details."""
    def __init__(self, code: str, transient: bool = False):
        self.code, self.transient = code, transient
        super().__init__(code)


class StructuredProvider(Protocol):
    async def generate(self, messages: list[dict[str, str]]) -> ProviderReply: ...


class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", client=None):
        if not re.fullmatch(r"sk-[A-Za-z0-9_-]{16,}", api_key.strip()):
            raise ProviderFailure("invalid_api_key_configuration")
        self.model = model
        self._owned = client is None
        self.client = client or openai.AsyncOpenAI(api_key=api_key.strip(), max_retries=0, timeout=30)

    async def generate(self, messages: list[dict[str, str]]) -> ProviderReply:
        error = None
        try:
            response = await self.client.chat.completions.create(
                model=self.model, messages=messages,
                response_format={"type": "json_schema", "json_schema": {
                    "name": "invoice_extraction", "strict": True,
                    "schema": WireEnvelope.model_json_schema(),
                }},
                max_completion_tokens=3000, temperature=0,
            )
            if not response.choices:
                return ProviderReply("", "empty_response")
            choice = response.choices[0]
            if choice.message.refusal:
                return ProviderReply("", "refusal")
            return ProviderReply(choice.message.content or "", choice.finish_reason or "unknown")
        except (openai.APITimeoutError, openai.APIConnectionError, openai.RateLimitError):
            error = ProviderFailure("provider_transient_failure", transient=True)
        except openai.APIStatusError as exc:
            error = ProviderFailure("provider_http_failure", transient=exc.status_code >= 500)
        except openai.OpenAIError:
            error = ProviderFailure("provider_failure")
        raise error

    async def close(self) -> None:
        if self._owned:
            await self.client.close()
