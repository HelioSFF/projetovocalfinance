from openai import AsyncOpenAI

from app.core.errors import ProviderError
from app.schemas.ai import DecisionResult
from app.services.categories import CATEGORIES
from app.services.pipeline_trace import NullTrace
from app.services.prompts import DECISION_CACHE_KEY, DECISION_PREFIX


class DecisionService:
    def __init__(self, client: AsyncOpenAI, timeout_seconds: int, trace: NullTrace = NullTrace()):
        self.client = client
        self.timeout_seconds = timeout_seconds
        self.trace = trace

    def build_questions(self) -> list[dict]:
        category_choices = [{"value": entry["code"], "description": entry["label"]} for entry in CATEGORIES]
        return [
            {
                "type": "predicate",
                "name": "plausible",
                "instructions": "A frase é uma transcrição coerente de fala em português (não corrompida/sem sentido)?",
            },
            {
                "type": "predicate",
                "name": "is_financial",
                "instructions": "A frase descreve um gasto ou um ganho de dinheiro com valor?",
            },
            {
                "type": "choice",
                "name": "type",
                "instructions": "Tipo de lançamento.",
                "choices": [{"value": "income"}, {"value": "expense"}],
            },
            {
                "type": "choice",
                "name": "category",
                "instructions": "Categoria do lançamento.",
                "choices": category_choices,
            },
        ]

    async def decide(self, transcript: str, attempt: int = 1) -> DecisionResult:
        try:
            response = await self.client.decisions.create(
                model="gpt-6-luna",
                input=f"{DECISION_PREFIX}\n{transcript}",
                prompt_cache_key=DECISION_CACHE_KEY,
                questions=self.build_questions(),
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            raise ProviderError() from exc
        self.trace.set_decision(attempt, "gpt-6-luna", response)
        return self.parse_answers(response.answers)

    def parse_answers(self, answers) -> DecisionResult:
        result = DecisionResult()
        for answer in answers:
            name = getattr(answer, "name", None)
            kind = getattr(answer, "type", None)
            if kind == "refusal":
                continue
            if name == "plausible":
                result.plausible = getattr(answer, "probability", None)
            elif name == "is_financial":
                result.is_financial = getattr(answer, "probability", None)
            elif name == "type":
                result.record_type = getattr(answer, "choice", None)
            elif name == "category":
                result.category = getattr(answer, "choice", None)
        return result
