# Sample documents

`invoice_expected.json` is a synthetic schema fixture, not a live model result.
Step 2 will add matching messy PDF and HTML samples plus ingestion code.
No private invoices or real customer information belong in this public repository.

Image-only PDFs need OCR. `pypdf` alone cannot read scanned pixels. The ingestion
step will explicitly distinguish extractable text from OCR-required documents.
