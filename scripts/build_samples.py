"""Regenerate the synthetic text-layer invoice PDF with existing pypdf dependency."""
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

ROOT = Path(__file__).resolve().parents[1]
writer = PdfWriter()
page = writer.add_blank_page(width=612, height=792)
font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Courier')})
page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
lines = (ROOT / 'samples/invoice_messy.txt').read_text().splitlines()
commands = ['BT', '/F1 10 Tf', '15 TL', '40 740 Td']
for line in lines:
    escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    commands.extend([f'({escaped}) Tj', 'T*'])
commands.append('ET')
stream = DecodedStreamObject()
stream.set_data('\n'.join(commands).encode('ascii'))
page[NameObject('/Contents')] = writer._add_object(stream)
writer.add_metadata({'/Title': 'Synthetic commercial invoice INV-2024-1012', '/Author': 'John Nelson - AD 331'})
writer.write(ROOT / 'samples/invoice_messy.pdf')
print('Generated samples/invoice_messy.pdf (synthetic text-layer fixture).')
