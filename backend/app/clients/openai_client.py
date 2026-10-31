from openai import AsyncOpenAI

from app.core.config import Settings


def build_openai_client(settings: Settings) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        max_retries=1,
        timeout=settings.ai_timeout_seconds,
    )
