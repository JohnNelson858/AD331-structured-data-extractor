from datetime import date
from decimal import Decimal
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.schemas import InvoiceExtraction


@pytest.fixture
def invoice():
    return json.loads((Path(__file__).parents[1] / "samples/invoice_expected.json").read_text())


def test_valid_invoice_and_decimal_roundtrip(invoice):
    record = InvoiceExtraction.model_validate(invoice)
    assert record.invoice_date == date(2024, 10, 12)
    assert record.total_amount == Decimal("1374.45")
    assert InvoiceExtraction.model_validate_json(record.model_dump_json()) == record


def test_documented_date_currency_and_percent_normalization(invoice):
    invoice.update(invoice_date="12th of Oct, 2024", subtotal="$1,249.50", total_amount="$1,374.45", tax_rate_percent="10%")
    assert InvoiceExtraction.model_validate(invoice).subtotal == Decimal("1249.50")


@pytest.mark.parametrize("quantity", [0, -1, True, "2", 2.0, 1000001])
def test_reject_invalid_or_coerced_quantities(invoice, quantity):
    invoice["line_items"][0]["quantity"] = quantity
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(invoice)


@pytest.mark.parametrize("value", [-1, "NaN", "Infinity", True, "1.249,50", "1,24.50", "1.234", 1000000001])
def test_reject_invalid_monetary_values(invoice, value):
    invoice["total_amount"] = value
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(invoice)


@pytest.mark.parametrize("value", ["12/10/2024", "2024-02-30", "2024-1-2", "12th of Octopus, 2024", "2024-10-12T00:00:00"])
def test_reject_ambiguous_or_invalid_dates(invoice, value):
    invoice["invoice_date"] = value
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(invoice)


@pytest.mark.parametrize("field,value", [("subtotal", "1240.00"), ("total_amount", "1400.00"), ("tax_rate_percent", "15%"), ("currency", "CAD"), ("invoice_number", "../secret path")])
def test_reject_contract_and_reconciliation_failures(invoice, field, value):
    invoice[field] = value
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(invoice)


def test_reject_bad_line_arithmetic(invoice):
    invoice["line_items"][0]["line_total"] = "999.00"
    with pytest.raises(ValidationError, match="quantity"):
        InvoiceExtraction.model_validate(invoice)


def test_reject_unknown_fields(invoice):
    invoice["approved"] = True
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(invoice)


def test_reject_mismatched_currency_symbol(invoice):
    invoice["line_items"][0]["unit_price"] = "€624.75"
    with pytest.raises(ValidationError, match="symbol"):
        InvoiceExtraction.model_validate(invoice)


@pytest.mark.parametrize("delta,accepted", [("0.02", True), ("0.03", False)])
def test_exact_reconciliation_tolerance(invoice, delta, accepted):
    invoice["total_amount"] = str(Decimal(invoice["total_amount"]) + Decimal(delta))
    if accepted:
        InvoiceExtraction.model_validate(invoice)
    else:
        with pytest.raises(ValidationError):
            InvoiceExtraction.model_validate(invoice)


def test_nested_schema_has_closed_objects_and_quantity_bound():
    schema = InvoiceExtraction.model_json_schema()
    assert schema["additionalProperties"] is False
    line = schema["$defs"]["LineItem"]
    assert line["additionalProperties"] is False
    assert line["properties"]["quantity"]["exclusiveMinimum"] == 0
