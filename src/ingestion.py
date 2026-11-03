"""Bounded local ingestion. Does not fetch URLs, run scripts, or perform OCR."""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import re
from bs4 import BeautifulSoup
from pypdf import PdfReader

MAX_TEXT_CHARS = 24000


class DocumentError(ValueError):
    """Safe document error for display to the user."""


@dataclass(frozen=True)
class SourceDocument:
    text: str
    kind: str
    digest: str


def from_text(text: str, kind: str = "text") -> SourceDocument:
    if not isinstance(text, str):
        raise DocumentError("Input must be text.")
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"[\t ]+", " ", text)
    if not text or "\x00" in text:
        raise DocumentError("Document is empty or contains NUL characters.")
    if len(text) > MAX_TEXT_CHARS:
        raise DocumentError("Document exceeds 24000 characters; split it before extraction.")
    return SourceDocument(text, kind, sha256(text.encode()).hexdigest())


def from_html(html: str) -> SourceDocument:
    if len(html.encode()) > 1000000:
        raise DocumentError("HTML exceeds 1 MB.")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    return from_text(soup.get_text(separator="\n", strip=True), "html")


def from_pdf(data: bytes) -> SourceDocument:
    if not data or len(data) > 5000000:
        raise DocumentError("PDF must contain between 1 byte and 5 MB.")
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise DocumentError("Encrypted PDFs are unsupported.")
        if not 1 <= len(reader.pages) <= 10:
            raise DocumentError("PDF must contain 1-10 pages.")
        pages = []
        for index, page in enumerate(reader.pages, 1):
            contents = page.get_contents()
            if contents is not None and len(contents.get_data()) > 2000000:
                raise DocumentError("PDF page content exceeds the parser limit.")
            text = page.extract_text() or ""
            if len(text.strip()) < 10:
                raise DocumentError(f"Page {index} has no usable text layer. Run OCR before uploading this scan.")
            pages.append(f"[Page {index}]\n{text}")
        return from_text("\n\n".join(pages), "pdf")
    except DocumentError:
        raise
    except Exception:
        raise DocumentError("PDF could not be read; supply a valid text-layer PDF.") from None
