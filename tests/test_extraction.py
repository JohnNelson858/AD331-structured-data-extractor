"""Assignment QA Tests 1-3: golden PDF, strict constraints, reconciliation."""
from decimal import Decimal
import json
from pathlib import Path

import httpx
import openai
from pydantic import ValidationError
import pytest

from src.extractor import SchemaExtractor
from src.ingestion import from_pdf
from src.provider import OpenAIProvider
from src.schemas import InvoiceExtraction

ROOT = Path(__file__).parents[1]


async def test_1_golden_pdf_first_attempt_through_real_sdk_mock_transport(tmp_path, envelope):
    """Actual PDF -> actual SDK strict request -> mocked response -> full validation."""
    source = from_pdf((ROOT / 'samples/invoice_messy.pdf').read_bytes())
    requests = []
    def transport(request):
        body = json.loads(request.content)
        requests.append(body)
        assert 'INV-2024-1012' in body['messages'][1]['content']
        schema = body['response_format']
        assert schema['type'] == 'json_schema'
        assert schema['json_schema']['strict'] is True
        return httpx.Response(200, json={
            'id': 'chatcmpl-offline', 'object': 'chat.completion', 'created': 0,
            'model': 'gpt-4o-mini', 'choices': [{'index': 0, 'message': {
                'role': 'assistant', 'content': envelope()}, 'finish_reason': 'stop'}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        async with openai.AsyncOpenAI(api_key='sk-offline_test_not_a_real_key', http_client=http, max_retries=0) as sdk:
            provider = OpenAIProvider('sk-offline_test_not_a_real_key', client=sdk)
            result = await SchemaExtractor(provider, tmp_path).extract_with_retry(source.text)
    assert result.execution_status == 'SUCCESS'
    assert result.attempts_used == len(requests) == 1
    assert result.error_log == []
    assert result.validated_data.total_amount == Decimal('1374.45')
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('quantity', [0, -1])
def test_2_nonpositive_quantity_is_rejected(invoice_data, quantity):
    invoice_data['line_items'][0]['quantity'] = quantity
    with pytest.raises(ValidationError) as caught:
        InvoiceExtraction.model_validate(invoice_data)
    assert any(e['loc'] == ('line_items', 0, 'quantity') for e in caught.value.errors())


@pytest.mark.parametrize('field', ['subtotal', 'tax_amount', 'total_amount'])
def test_2_negative_money_is_rejected(invoice_data, field):
    invoice_data[field] = '-0.01'
    with pytest.raises(ValidationError) as caught:
        InvoiceExtraction.model_validate(invoice_data)
    assert any(e['loc'] == (field,) for e in caught.value.errors())


def test_3_grand_total_mismatch_fails_root_validation(invoice_data):
    invoice_data['total_amount'] = '1500.00'
    with pytest.raises(ValidationError) as caught:
        InvoiceExtraction.model_validate(invoice_data)
    error = caught.value.errors()[0]
    assert error['loc'] == ()
    assert '1374.45' in error['msg'] and '1500.00' in error['msg']


def test_3_subtotal_mismatch_cannot_hide_behind_consistent_grand_total(invoice_data):
    invoice_data.update(subtotal='1000.00', total_amount='1124.95')
    with pytest.raises(ValidationError, match='subtotal'):
        InvoiceExtraction.model_validate(invoice_data)


def test_multiple_line_items_are_all_reconciled(invoice_data):
    invoice_data['line_items'] = [
        {'description': 'Sensor A', 'quantity': 1, 'unit_price': '624.75', 'line_total': '624.75'},
        {'description': 'Sensor B', 'quantity': 1, 'unit_price': '624.75', 'line_total': '624.75'},
    ]
    record = InvoiceExtraction.model_validate(invoice_data)
    assert sum(item.line_total for item in record.line_items) == record.subtotal
    invoice_data['line_items'][1]['line_total'] = '624.70'
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(invoice_data)


async def test_invalid_business_payload_never_becomes_success(tmp_path, source_text, invoice_data, envelope, sequence_provider, no_wait):
    invoice_data['line_items'][0]['quantity'] = 0
    provider = sequence_provider(envelope(invoice_data))
    result = await SchemaExtractor(provider, tmp_path, sleeper=no_wait[0]).extract_with_retry(source_text)
    assert result.execution_status == 'DLQ_FAILED'
    assert result.validated_data is None
    assert provider.calls == 4
