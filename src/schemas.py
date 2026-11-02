"""Pydantic v2 invoice acceptance contract, schema version 1.0.0.

Only explicitly documented normalization is permitted. Validation does not
invent source data or prove that the extracted values match a real document.
Native provider wire schemas will be separate from these business validators.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

SCHEMA_VERSION = "1.0.0"
TOLERANCE = Decimal("0.02")
CENT = Decimal("0.01")
MAX_MONEY = Decimal("1000000000")
MONTHS = {name: i for i, name in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
)}


def parse_decimal(value: object) -> Decimal:
    """Normalize decimal-point notation, grouped thousands, and one leading symbol.

    Reject ambiguous decimal-comma formats rather than silently changing value.
    Currency symbols are checked against the invoice currency in a pre-validator.
    Float inputs from JSON use their decimal string, never Decimal(binary_float).
    """
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("expected a finite decimal number")
    if isinstance(value, str):
        value = value.strip()
        if value[:1] in ("$", "€", "£"):
            value = value[1:].strip()
        if not re.fullmatch(r"-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", value):
            raise ValueError("use decimal-point notation; ambiguous grouping is rejected")
        value = value.replace(",", "")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("expected a finite decimal number") from exc
    if not result.is_finite():
        raise ValueError("number must be finite")
    return result


def parse_invoice_date(value: object) -> date:
    """Accept ISO YYYY-MM-DD or explicit English '12th of Oct, 2024'."""
    if isinstance(value, datetime):
        raise ValueError("invoice_date must be a date without a time")
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("expected an ISO date or an explicit English month name")
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return date.fromisoformat(value)
    match = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?(?: of)? ([A-Za-z]+),? (\d{4})", value, re.I)
    if match:
        day, month, year = match.groups()
        month_names = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        }
        month_number = MONTHS.get(month.lower(), month_names.get(month.lower()))
        if month_number:
            return date(int(year), month_number, int(day))
    raise ValueError("use YYYY-MM-DD or an explicit English date; numeric slash dates are ambiguous")


class StrictRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


PositiveMoney = Annotated[Decimal, Field(gt=0, le=MAX_MONEY, max_digits=12, decimal_places=2)]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, le=MAX_MONEY, max_digits=12, decimal_places=2)]


class LineItem(StrictRecord):
    description: str = Field(min_length=1, max_length=500)
    quantity: StrictInt = Field(gt=0, le=1000000)
    unit_price: PositiveMoney
    line_total: NonNegativeMoney

    @field_validator("unit_price", "line_total", mode="before")
    @classmethod
    def normalize_money(cls, value: object) -> Decimal:
        return parse_decimal(value)

    @model_validator(mode="after")
    def check_line_total(self) -> Self:
        expected = self.unit_price * self.quantity
        if abs(expected - self.line_total) > TOLERANCE:
            raise ValueError(f"line_total {self.line_total} differs from quantity * unit_price {expected}")
        return self


class InvoiceExtraction(StrictRecord):
    invoice_number: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,63}$")
    vendor_name: str = Field(min_length=1, max_length=200)
    invoice_date: date
    line_items: list[LineItem] = Field(min_length=1, max_length=100)
    subtotal: NonNegativeMoney
    tax_amount: NonNegativeMoney
    total_amount: PositiveMoney
    currency: Literal["USD", "EUR", "GBP"]
    tax_rate_percent: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] | None = None

    @model_validator(mode="before")
    @classmethod
    def check_currency_symbols(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        symbols = {"$": "USD", "€": "EUR", "£": "GBP"}
        amounts = [data.get(k) for k in ("subtotal", "tax_amount", "total_amount")]
        items = data.get("line_items")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    amounts.extend(item.get(k) for k in ("unit_price", "line_total"))
        for amount in amounts:
            if isinstance(amount, str) and amount.strip()[:1] in symbols:
                if symbols[amount.strip()[0]] != data.get("currency"):
                    raise ValueError("monetary symbol conflicts with the declared currency")
        return data

    @field_validator("invoice_date", mode="before")
    @classmethod
    def normalize_date(cls, value: object) -> date:
        return parse_invoice_date(value)

    @field_validator("subtotal", "tax_amount", "total_amount", mode="before")
    @classmethod
    def normalize_money(cls, value: object) -> Decimal:
        return parse_decimal(value)

    @field_validator("tax_rate_percent", mode="before")
    @classmethod
    def normalize_tax_rate(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip().removesuffix("%")
        return parse_decimal(value)

    @model_validator(mode="after")
    def reconcile(self) -> Self:
        calculated = sum((item.line_total for item in self.line_items), Decimal("0"))
        checks = [
            ("subtotal vs line items", self.subtotal, calculated),
            ("total vs subtotal + tax", self.total_amount, self.subtotal + self.tax_amount),
            ("total vs line items + tax", self.total_amount, calculated + self.tax_amount),
        ]
        if self.tax_rate_percent is not None:
            expected_tax = (self.subtotal * self.tax_rate_percent / 100).quantize(CENT, rounding=ROUND_HALF_UP)
            checks.append(("tax vs declared percentage", self.tax_amount, expected_tax))
        for rule, found, expected in checks:
            if abs(found - expected) > TOLERANCE:
                raise ValueError(f"{rule}: found {found}, expected {expected}; tolerance is 0.02")
        return self
