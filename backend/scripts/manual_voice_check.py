import asyncio
import sys
from pathlib import Path

import httpx

from app.main import app

MIME_BY_SUFFIX = {".m4a": "audio/m4a", ".webm": "audio/webm", ".wav": "audio/wav", ".mp3": "audio/mpeg"}


async def post_audio(path: Path):
    mime = MIME_BY_SUFFIX[path.suffix.lower()]
    content = path.read_bytes()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://backend", timeout=120.0) as client:
        response = await client.post(
            "/api/voice-records",
            files={"file": (path.name, content, mime)},
        )
    return response.status_code, response.text


async def main(paths: list[str]):
    for raw in paths:
        path = Path(raw)
        status, body = await post_audio(path)
        print(f"== {path.name} -> {status}")
        print(body)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
