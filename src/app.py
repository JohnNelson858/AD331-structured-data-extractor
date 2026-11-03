"""Local FastAPI workbench. Streaming audit events; no browser-side credentials."""
import asyncio
from contextlib import suppress
from decimal import Decimal
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.cli import FixtureProvider
from src.extractor import SchemaExtractor
from src.fallback import safe_text
from src.ingestion import DocumentError, from_html, from_pdf, from_text
from src.provider import OpenAIProvider, ProviderFailure
from src.schemas import TOLERANCE

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).with_name("static")
MAX_BODY_BYTES = 6_000_000


class BodyTooLarge(HTTPException):
    def __init__(self):
        super().__init__(413, "Upload exceeds the 6 MB request limit.")


class BodyLimitMiddleware:
    """Limit actual streamed bytes, including requests without Content-Length."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        total = 0

        async def bounded_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > MAX_BODY_BYTES:
                    raise BodyTooLarge()
            return message

        try:
            await self.app(scope, bounded_receive, send)
        except BodyTooLarge:
            response = JSONResponse({"detail": "Upload exceeds the 6 MB request limit."}, status_code=413)
            await response(scope, receive, send)


def create_app(*, dlq_dir=None, api_key=None, model=None, provider_factory=None):
    """Explicit injection permits offline HTTP tests without loading real keys."""
    if api_key is None:
        load_dotenv(ROOT / ".env", override=False)
        api_key = os.getenv("OPENAI_API_KEY", "")
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    dlq_dir = Path(dlq_dir) if dlq_dir is not None else ROOT / "runtime/dlq"
    app = FastAPI(title="SchemaExtractor", version="0.2.0", docs_url=None, redoc_url=None)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"])

    @app.middleware("http")
    async def local_browser_boundary(request: Request, call_next):
        if request.method == "POST":
            origin = request.headers.get("origin")
            expected = urlsplit(str(request.base_url))
            incoming = urlsplit(origin) if origin else None
            if (request.headers.get("sec-fetch-site") == "cross-site" or
                (incoming and (incoming.scheme, incoming.netloc) != (expected.scheme, expected.netloc))):
                return JSONResponse({"detail": "Use the app in its own local browser tab."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    async def home():
        return FileResponse(STATIC / "index.html")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/config")
    async def config():
        return {"live_available": bool(api_key), "model": model, "max_retries": 3}

    @app.get("/api/sample")
    async def sample():
        return {"text": (ROOT / "samples/invoice_messy.txt").read_text(encoding="utf-8")}

    @app.get("/samples/invoice_messy.pdf")
    async def sample_pdf():
        return FileResponse(ROOT / "samples/invoice_messy.pdf", media_type="application/pdf", filename="invoice_messy.pdf")

    @app.post("/api/extract")
    async def extract(request: Request):
        # Parsing and ingestion finish before streaming headers; bad inputs get a
        # normal non-2xx error and cannot accidentally start paid provider work.
        async with request.form(max_files=1, max_fields=8, max_part_size=1_000_000) as form:
            mode = form.get("mode", "offline")
            scenario = form.get("scenario", "success")
            reflection = form.get("reflection", "true")
            if mode not in {"offline", "live"} or scenario not in {"success", "reflection", "heuristic", "dlq"}:
                raise HTTPException(422, "Unknown execution mode or scenario.")
            if reflection not in {"true", "false"}:
                raise HTTPException(422, "Reflection must be true or false.")
            if mode == "live" and scenario != "success":
                raise HTTPException(422, "Failure simulations are offline only.")
            if mode == "live" and form.get("confirm_live") != "yes":
                raise HTTPException(422, "Confirm separately billed API use before running live extraction.")
            if mode == "live" and not api_key:
                raise HTTPException(503, "No server API key configured. Use the offline sample demonstration.")
            try:
                if scenario == "dlq":
                    document = from_text((ROOT / "samples/invoice_messy.txt").read_text(encoding="utf-8"))
                else:
                    upload = form.get("file")
                    text = form.get("text", "")
                    if upload is not None and not isinstance(upload, UploadFile):
                        raise DocumentError("Choose a PDF, HTML, or text file.")
                    if not isinstance(text, str):
                        raise DocumentError("Paste text into the document field.")
                    if upload is not None and text.strip():
                        raise DocumentError("Choose one input: file upload or pasted text.")
                    if upload is not None:
                        data = await upload.read(5_000_001)
                        if len(data) > 5_000_000:
                            raise DocumentError("File exceeds 5 MB.")
                        suffix = Path(upload.filename or "").suffix.lower()
                        if suffix == ".pdf":
                            document = await asyncio.to_thread(from_pdf, data)
                        elif suffix in {".html", ".htm", ".txt"}:
                            decoded = data.decode("utf-8-sig")
                            document = await asyncio.to_thread(from_html if suffix != ".txt" else from_text, decoded)
                        else:
                            raise DocumentError("Supported files: .pdf, .html, .htm, .txt.")
                    else:
                        kind = form.get("input_kind", "text")
                        if kind not in {"text", "html"}:
                            raise DocumentError("Choose text or HTML format.")
                        document = await asyncio.to_thread(from_html if kind == "html" else from_text, text)
                if mode == "offline":
                    # Fixtures never pretend to extract an arbitrary uploaded invoice.
                    allowed = {
                        from_text((ROOT / "samples/invoice_messy.txt").read_text(encoding="utf-8")).digest,
                        from_html((ROOT / "samples/vendor_contract.html").read_text(encoding="utf-8")).digest,
                        (await asyncio.to_thread(from_pdf, (ROOT / "samples/invoice_messy.pdf").read_bytes())).digest,
                    }
                    if document.digest not in allowed:
                        raise DocumentError("Offline demos use only the bundled sample invoice. Click Load sample, upload a bundled sample, or choose live extraction for your own document.")
            except (DocumentError, UnicodeDecodeError) as exc:
                message = str(exc) if isinstance(exc, DocumentError) else "Text and HTML files must use UTF-8 encoding."
                raise HTTPException(422, message) from None
        try:
            provider = (provider_factory(mode, scenario) if provider_factory else
                        FixtureProvider(scenario) if mode == "offline" else OpenAIProvider(api_key, model))
        except ProviderFailure as exc:
            raise HTTPException(503, exc.code) from None

        async def stream():
            queue = asyncio.Queue()

            def emit_event(event):
                queue.put_nowait({"type": "audit", "event": event.model_dump(mode="json")})

            async def run():
                try:
                    engine = SchemaExtractor(provider, dlq_dir, model=model if mode == "live" else "offline-fixture")
                    result = await engine.extract_with_retry(document.text, reflection_enabled=reflection == "true", on_event=emit_event)
                    invoice = result.validated_data
                    report = None
                    if invoice is not None:
                        line_sum = sum((item.line_total for item in invoice.line_items), Decimal("0"))
                        report = {
                            "line_items_sum": str(line_sum),
                            "subtotal_difference": str(line_sum - invoice.subtotal),
                            "grand_total_difference": str(line_sum + invoice.tax_amount - invoice.total_amount),
                            "tolerance": str(TOLERANCE),
                        }
                    queue.put_nowait({"type": "result", "result": result.model_dump(mode="json"),
                                      "reconciliation_report": report})
                except Exception:
                    # Never expose unexpected exception text, keys or SDK bodies.
                    queue.put_nowait({"type": "error", "message": "Extraction could not finish. No record was accepted; retry or inspect local service health."})
                finally:
                    try:
                        if isinstance(provider, OpenAIProvider):
                            await provider.close()
                    finally:
                        queue.put_nowait(None)

            task = asyncio.create_task(run())
            try:
                def line(value):
                    return safe_text(json.dumps(value, ensure_ascii=False)) + "\n"
                yield line({"type": "source", "text": document.text, "kind": document.kind,
                            "sha256": document.digest, "mode": mode, "scenario": scenario})
                while True:
                    frame = await queue.get()
                    if frame is None:
                        break
                    yield line(frame)
            finally:
                if not task.done():
                    task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

        return StreamingResponse(stream(), media_type="application/x-ndjson",
                                 headers={"X-Accel-Buffering": "no"})

    return app


app = create_app()
