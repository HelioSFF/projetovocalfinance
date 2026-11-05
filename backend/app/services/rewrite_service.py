from openai import AsyncOpenAI

from app.core.errors import ProviderError
from app.services.pipeline_trace import NullTrace
from app.services.prompts import REWRITE_SYSTEM


class RewriteService:
    def __init__(self, client: AsyncOpenAI, timeout_seconds: int, trace: NullTrace = NullTrace()):
        self.client = client
        self.timeout_seconds = timeout_seconds
        self.trace = trace

    async def rewrite(self, transcript: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model="deepseek-flash",
                messages=[
                    {"role": "system", "content": REWRITE_SYSTEM},
                    {"role": "user", "content": transcript},
                ],
                max_tokens=120,
                temperature=0,
                timeout=self.timeout_seconds,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except Exception as exc:
            raise ProviderError() from exc
        content = response.choices[0].message.content
        if not isinstance(content, str):
            content = ""
        else:
            content = content.strip()
        self.trace.set_fallback("deepseek-flash", transcript, response, content)
        return content
