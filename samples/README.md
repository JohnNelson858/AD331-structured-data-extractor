# Sample documents

`invoice_expected.json` is a synthetic schema fixture, not a live model result.
Step 2 adds matching `invoice_messy.pdf`, `invoice_messy.txt`, and
`vendor_contract.html`. The HTML is an invoice attachment to a fictional vendor
agreement, not a second extraction domain. `irrecoverable.txt` intentionally
contains no invoice facts. All samples are synthetic.
No private invoices or real customer information belong in this public repository.

Image-only PDFs need OCR. `pypdf` alone cannot read scanned pixels. Ingestion
explicitly rejects pages without a text layer with an OCR-required explanation;
OCR itself is not implemented. Mixed image/text documents can require OCR too.

Regenerate the PDF fixture using `uv run python scripts/build_samples.py`.
