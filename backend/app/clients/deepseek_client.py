from openai import AsyncOpenAI

from app.core.config import Settings


def build_deepseek_client(settings: Settings) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com",
        max_retries=1,
        timeout=settings.ai_timeout_seconds,
    )
