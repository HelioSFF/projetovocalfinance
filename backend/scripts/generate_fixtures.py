import os
import subprocess
import sys
from pathlib import Path

import httpx

MODEL = "gpt-4o-mini-tts"
VOICE = "marin"
INSTRUCTIONS = "Fale em português do Brasil, tom natural, ritmo normal."

PHRASES = [
    ("groceries_coffee", "comprei três cafés de cinco reais", "m4a"),
    ("slang_drinks", "desci três de dez conto", "webm"),
    ("salary", "recebi meu salário de dois mil reais", "m4a"),
    ("utilities_light", "paguei cento e vinte reais de luz", "webm"),
    ("groceries_market", "gastei quarenta e cinco no mercado", "m4a"),
    ("bakery_bread", "dois e cinquenta de pão", "webm"),
    ("nonsense", "mesa verde canta relógio azul devagar", "m4a"),
    ("greeting", "oi tudo bem", "webm"),
]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    load_dotenv(backend_root / ".env")
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("Missing OPENAI_API_KEY")
        sys.exit(2)
    try:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print("Missing imageio-ffmpeg")
        sys.exit(2)
    out_dir = backend_root / "tests" / "fixtures" / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("probe.*"):
        stale.unlink()
    total_chars = 0
    with httpx.Client(timeout=60.0) as client:
        for slug, text, container in PHRASES:
            total_chars += len(text)
            response = client.post(
                "https://api.openai.com/v1/audio/speech",
                json={"model": MODEL, "voice": VOICE, "input": text, "instructions": INSTRUCTIONS, "response_format": "wav"},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            tmp_wav = out_dir / f"{slug}.tmp.wav"
            tmp_wav.write_bytes(response.content)
            target = out_dir / f"{slug}.{container}"
            if container == "m4a":
                convert = [ffmpeg, "-y", "-i", str(tmp_wav), "-c:a", "aac", str(target)]
            else:
                convert = [ffmpeg, "-y", "-i", str(tmp_wav), "-c:a", "libopus", str(target)]
            subprocess.run(convert, check=True, capture_output=True)
            tmp_wav.unlink()
            print(f"wrote {target.name} ({target.stat().st_size} bytes)")
    print(f"total_chars={total_chars}")


if __name__ == "__main__":
    main()
