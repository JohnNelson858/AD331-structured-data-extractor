"""Labeled offline demos and opt-in live extraction. No web UI yet."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from src.extractor import SchemaExtractor
from src.ingestion import DocumentError, from_html, from_pdf, from_text
from src.provider import OpenAIProvider, ProviderFailure, ProviderReply

ROOT = Path(__file__).resolve().parents[1]


class FixtureProvider:
    """Fault injection for offline checks, never presented as actual model output."""
    def __init__(self, scenario):
        self.scenario, self.calls = scenario, 0

    async def generate(self, messages):
        self.calls += 1
        invoice = json.loads((ROOT / "samples/invoice_expected.json").read_text())
        if self.scenario == "dlq":
            return ProviderReply("not valid JSON")
        if self.scenario == "reflection" and self.calls == 1:
            invoice["total_amount"] = "1500.00"
        text = json.dumps({"outcome": "extracted", "invoice": invoice, "reason": "Synthetic test fixture"})
        if self.scenario == "heuristic":
            text = "```json\n" + text + "\n```"
        return ProviderReply(text)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", choices=["success", "reflection", "heuristic", "dlq"])
    parser.add_argument("--live", action="store_true", help="Make separately billed OpenAI calls")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--no-reflection", action="store_true")
    parser.add_argument("--summary", action="store_true", help="Print a compact result instead of full audit events")
    args = parser.parse_args()
    if bool(args.demo) == args.live:
        parser.error("choose exactly one of --demo or --live")
    filename = args.input or ROOT / "samples/invoice_messy.pdf"
    try:
        if filename.suffix.lower() == ".pdf":
            document = from_pdf(filename.read_bytes())
        elif filename.suffix.lower() in {".html", ".htm"}:
            document = from_html(filename.read_text(encoding="utf-8"))
        else:
            document = from_text(filename.read_text(encoding="utf-8"))
    except (OSError, DocumentError) as exc:
        print(json.dumps({"status": "SOURCE_REJECTED", "message": str(exc)}))
        return
    provider = None
    try:
        if args.live:
            load_dotenv(ROOT / ".env", override=False)
            provider = OpenAIProvider(os.getenv("OPENAI_API_KEY", ""), os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        else:
            print("OFFLINE SIMULATION: fixture responses, no provider calls or API charges.")
            provider = FixtureProvider(args.demo)
        extractor = SchemaExtractor(provider, ROOT / "runtime/dlq")
        result = await extractor.extract_with_retry(document.text, reflection_enabled=not args.no_reflection)
        if args.summary:
            print(json.dumps({"execution_status": result.execution_status,
                "attempts_used": result.attempts_used, "error_count": len(result.error_log),
                "reconciled": result.validated_data is not None, "dlq_path": result.dlq_path}, indent=2))
        else:
            print(result.model_dump_json(indent=2))
    except ProviderFailure as exc:
        print(json.dumps({"status": "PROVIDER_CONFIGURATION_FAILED", "message": exc.code}))
    finally:
        if isinstance(provider, OpenAIProvider):
            await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
