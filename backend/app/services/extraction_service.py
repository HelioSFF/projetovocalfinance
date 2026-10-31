import json

from openai import AsyncOpenAI

from app.core.errors import ProviderError
from app.schemas.ai import ExtractionResult
from app.schemas.debug import extraction_to_dict, raw_output_text
from app.services.pipeline_trace import NullTrace
from app.services.prompts import EXTRACTION_INSTRUCTIONS

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "item": {"type": "string"},
        "quantity": {"type": "number"},
        "unit_price": {"type": ["number", "null"]},
        "stated_total": {"type": ["number", "null"]},
    },
    "required": ["item", "quantity", "unit_price", "stated_total"],
    "additionalProperties": False,
}


class ExtractionService:
    def __init__(
        self, client: AsyncOpenAI, model: str, service_tier: str, timeout_seconds: int, trace: NullTrace = NullTrace()
    ):
        self.client = client
        self.model = model
        self.service_tier = service_tier
        self.timeout_seconds = timeout_seconds
        self.trace = trace

    async def extract(self, transcript: str, attempt: int = 1) -> ExtractionResult | None:
        options: dict = {
            "model": self.model,
            "instructions": EXTRACTION_INSTRUCTIONS,
            "input": transcript,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "expense_extraction",
                    "strict": True,
                    "schema": EXTRACTION_SCHEMA,
                }
            },
            "timeout": self.timeout_seconds,
        }
        if self.model == "gpt-6-luna":
            options["reasoning"] = {"effort": "none"}
        if self.service_tier:
            options["service_tier"] = self.service_tier
        try:
            response = await self.client.responses.create(**options)
        except Exception as exc:
            raise ProviderError() from exc
        raw_text = raw_output_text(response)
        parsed = self.parse_response(response)
        self.trace.set_extraction(attempt, self.model, self.service_tier or None, response, raw_text, extraction_to_dict(parsed))
        return parsed

    def parse_response(self, response) -> ExtractionResult | None:
        try:
            for item in response.output:
                if getattr(item, "type", None) != "message":
                    continue
                for part in item.content:
                    if getattr(part, "type", None) not in ("output_text", "text"):
                        continue
                    payload = json.loads(part.text)
                    return ExtractionResult(
                        item=payload.get("item", ""),
                        quantity=payload.get("quantity"),
                        unit_price=payload.get("unit_price"),
                        stated_total=payload.get("stated_total"),
                    )
        except (ValueError, AttributeError, TypeError):
            return None
        return None
