from openai import AsyncOpenAI

from app.core.errors import ProviderError
from app.services.pipeline_trace import NullTrace
from app.services.prompts import TRANSCRIPTION_KEYWORDS, TRANSCRIPTION_PROMPT


class TranscriptionService:
    def __init__(self, client: AsyncOpenAI, timeout_seconds: int, trace: NullTrace = NullTrace()):
        self.client = client
        self.timeout_seconds = timeout_seconds
        self.trace = trace

    async def transcribe(self, audio: bytes, filename: str, mime: str) -> str:
        try:
            result = await self.client.audio.transcriptions.create(
                model="gpt-transcribe",
                file=(filename, audio, mime),
                prompt=TRANSCRIPTION_PROMPT,
                response_format="json",
                timeout=self.timeout_seconds,
                extra_body={"languages": ["pt"], "keywords": TRANSCRIPTION_KEYWORDS},
            )
        except Exception as exc:
            raise ProviderError() from exc
        text = result.text if isinstance(result.text, str) else ""
        text = text.strip()
        self.trace.set_transcription("gpt-transcribe", text, result)
        return text
