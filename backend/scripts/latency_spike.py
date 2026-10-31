import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path

import httpx

TRANSCRIPTION_MODEL = "gpt-transcribe"
DECISION_MODEL = "gpt-6-luna"
EXTRACTION_MODELS = ["gpt-6-luna", "gpt-4o-mini"]
REWRITE_MODEL = "deepseek-flash"
ROUNDS = 3
MIME_BY_SUFFIX = {".m4a": "audio/m4a", ".mp4": "audio/mp4", ".webm": "video/webm", ".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".aac": "audio/aac", ".opus": "audio/ogg"}

CATEGORY_CODES = [
    "food", "groceries", "housing", "utilities", "transport", "health", "education",
    "leisure", "shopping", "clothing", "personal_care", "pets", "subscriptions",
    "travel", "taxes_fees", "gifts_donations", "other_expense", "salary",
    "freelance", "sales", "investments", "refunds", "gifts_received", "other_income",
]

DECISION_PREFIX = (
    "Domínio finanças pessoais em português. Regras: frase coerente de fala, "
    "descreve gasto ou ganho com valor. Gírias: conto, pila, real, reais, centavos. "
    "Exemplos: comprei 3 cafés de 5 reais; desci três de dez conto; recebi salário; "
    "paguei luz; oi tudo bem não é financeiro. Responda às perguntas sobre a transcrição."
)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def summarize(name: str, samples: list[float]) -> str:
    median = statistics.median(samples) if samples else 0.0
    peak = max(samples) if samples else 0.0
    ok = len(samples)
    return f"{name}: n={ok} p50={median:.0f}ms max={peak:.0f}ms"


def short_error(exc: Exception) -> str:
    status = ""
    body = ""
    if isinstance(exc, httpx.HTTPStatusError):
        status = str(exc.response.status_code)
        try:
            body = json.dumps(exc.response.json())[:300]
        except ValueError:
            body = exc.response.text[:300]
    return f"{type(exc).__name__} {status} {body}".strip()


KEYWORDS = [
    "Alimentação", "Mercado", "Moradia", "Transporte", "Saúde", "Educação",
    "Lazer", "Compras", "reais", "centavos",
]

TRANSCRIBE_PROMPT = "Transcreva gastos e ganhos em português com valores em reais, centavos, conto e pila."


async def transcribe(client: httpx.AsyncClient, audio_path: Path, api_key: str, timeout: float):
    mime = MIME_BY_SUFFIX.get(audio_path.suffix.lower(), "audio/m4a")
    started = time.perf_counter()
    try:
        with audio_path.open("rb") as stream:
            content = stream.read()
        files = {"file": (audio_path.name, content, mime)}
        data = {"model": TRANSCRIPTION_MODEL, "prompt": TRANSCRIBE_PROMPT, "response_format": "json", "languages[]": ["pt"], "keywords[]": KEYWORDS}
        headers = {"Authorization": f"Bearer {api_key}"}
        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            files=files,
            data=data,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return "", (time.perf_counter() - started) * 1000, short_error(exc), None
    elapsed = (time.perf_counter() - started) * 1000
    text = payload.get("text", "") if isinstance(payload, dict) else ""
    return text, elapsed, "", payload


async def decide(client: httpx.AsyncClient, transcript: str, api_key: str, timeout: float):
    started = time.perf_counter()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body: dict = {
        "model": DECISION_MODEL,
        "input": f"{DECISION_PREFIX}\n{transcript}",
        "prompt_cache_key": "vocal-finance-decisions-v1",
        "questions": [
            {"type": "predicate", "name": "plausible", "instructions": "A frase é uma transcrição coerente de fala em português?"},
            {"type": "predicate", "name": "is_financial", "instructions": "A frase descreve um gasto ou ganho com valor?"},
            {"type": "choice", "name": "type", "instructions": "Tipo de lançamento.", "choices": [{"value": "income"}, {"value": "expense"}]},
            {"type": "choice", "name": "category", "instructions": "Categoria do lançamento.", "choices": [{"value": code} for code in CATEGORY_CODES]},
        ],
    }
    try:
        response = await client.post("https://api.openai.com/v1/decisions", json=body, headers=headers, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return None, (time.perf_counter() - started) * 1000, short_error(exc)
    return payload, (time.perf_counter() - started) * 1000, ""


async def extract(client: httpx.AsyncClient, transcript: str, model: str, api_key: str, service_tier: str, timeout: float):
    started = time.perf_counter()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body: dict = {
        "model": model,
        "instructions": "Extraia item, quantity, unit_price e stated_total de lançamentos financeiros em português.",
        "input": transcript,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "expense_extraction",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "item": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_price": {"type": ["number", "null"]},
                        "stated_total": {"type": ["number", "null"]},
                    },
                    "required": ["item", "quantity", "unit_price", "stated_total"],
                    "additionalProperties": False,
                },
            }
        },
    }
    if model == "gpt-6-luna":
        body["reasoning"] = {"effort": "none"}
    if service_tier:
        body["service_tier"] = service_tier
    try:
        response = await client.post("https://api.openai.com/v1/responses", json=body, headers=headers, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return None, (time.perf_counter() - started) * 1000, short_error(exc)
    return payload, (time.perf_counter() - started) * 1000, ""


async def rewrite(client: httpx.AsyncClient, transcript: str, api_key: str, timeout: float):
    started = time.perf_counter()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": REWRITE_MODEL,
        "thinking": {"type": "disabled"},
        "messages": [
            {"role": "system", "content": "Reescreva a frase do usuário em português padrão, mantendo números, quantidades e valores. Responda só a frase."},
            {"role": "user", "content": transcript},
        ],
        "max_tokens": 120,
        "temperature": 0,
    }
    try:
        response = await client.post("https://api.deepseek.com/chat/completions", json=body, headers=headers, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
    except Exception as exc:
        return "", (time.perf_counter() - started) * 1000, short_error(exc)
    return content, (time.perf_counter() - started) * 1000, ""


def collect_usage(payload) -> dict:
    if not isinstance(payload, dict):
        return {}
    usage = payload.get("usage")
    return usage if isinstance(usage, dict) else {}


async def measure_file(audio_path: Path, openai_key: str, deepseek_key: str, service_tier: str, timeout: float) -> dict:
    timings: dict[str, list[float]] = {"transcribe": [], "decide": [], "rewrite": []}
    for model in EXTRACTION_MODELS:
        timings[f"extract:{model}"] = []
    errors: dict[str, int] = {}
    error_samples: dict[str, str] = {}
    samples: dict = {"transcripts": [], "decisions": [], "extractions": {}, "rewrites": [], "usages": []}
    async with httpx.AsyncClient() as client:
        for _ in range(ROUNDS):
            text, transcribe_elapsed, transcribe_error, transcribe_payload = await transcribe(client, audio_path, openai_key, timeout)
            if transcribe_error:
                errors["transcribe"] = errors.get("transcribe", 0) + 1
                error_samples.setdefault("transcribe", transcribe_error)
            else:
                timings["transcribe"].append(transcribe_elapsed)
                samples["transcripts"].append(text)
                samples["usages"].append(collect_usage(transcribe_payload))
            decide_coro = decide(client, text, openai_key, timeout)
            extract_coros = [extract(client, text, model, openai_key, service_tier, timeout) for model in EXTRACTION_MODELS]
            results = await asyncio.gather(decide_coro, *extract_coros)
            decide_payload, decide_elapsed, decide_error = results[0]
            if decide_error:
                errors["decide"] = errors.get("decide", 0) + 1
                error_samples.setdefault("decide", decide_error)
            else:
                timings["decide"].append(decide_elapsed)
                samples["decisions"].append(json.dumps(decide_payload)[:500])
                samples["usages"].append(collect_usage(decide_payload))
            for model, extract_result in zip(EXTRACTION_MODELS, results[1:]):
                payload, extract_elapsed, extract_error = extract_result
                key = f"extract:{model}"
                if extract_error:
                    errors[key] = errors.get(key, 0) + 1
                    error_samples.setdefault(key, extract_error)
                else:
                    timings[key].append(extract_elapsed)
                    samples["extractions"].setdefault(model, []).append(json.dumps(payload)[:500])
                    samples["usages"].append(collect_usage(payload))
            rewritten, rewrite_elapsed, rewrite_error = await rewrite(client, text, deepseek_key, timeout)
            if rewrite_error:
                errors["rewrite"] = errors.get("rewrite", 0) + 1
                error_samples.setdefault("rewrite", rewrite_error)
            else:
                timings["rewrite"].append(rewrite_elapsed)
                samples["rewrites"].append(rewritten[:200])
    return {"file": audio_path.name, "timings": timings, "errors": errors, "error_samples": error_samples, "samples": samples}


async def main_async(audio_dir: Path, service_tier: str, timeout: float) -> int:
    openai_key = os.getenv("OPENAI_API_KEY", "")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not openai_key or not deepseek_key:
        print("Missing OPENAI_API_KEY or DEEPSEEK_API_KEY in backend/.env")
        return 2
    files = sorted([path for path in audio_dir.glob("*") if path.suffix.lower() in {".m4a", ".webm", ".wav", ".mp3", ".aac", ".opus"}])
    if len(files) < 6:
        print(f"Expected 6 to 10 audio files in {audio_dir}, found {len(files)}")
        return 2
    print(f"service_tier={service_tier or 'default'} timeout={timeout}")
    aggregate: dict[str, list[float]] = {}
    error_total: dict[str, int] = {}
    for audio_path in files:
        result = await measure_file(audio_path, openai_key, deepseek_key, service_tier, timeout)
        print(f"== {result['file']} ==")
        for name, values in result["timings"].items():
            print(f"  {summarize(name, values)}")
            aggregate.setdefault(name, []).extend(values)
        if result["errors"]:
            print(f"  errors={result['errors']}")
            for key, count in result["errors"].items():
                error_total[key] = error_total.get(key, 0) + count
            for key, sample in result.get("error_samples", {}).items():
                print(f"  error_sample[{key}]: {sample[:300]}")
        transcripts = result["samples"]["transcripts"]
        if transcripts:
            print(f"  transcript: {transcripts[0][:160]}")
        for decision in result["samples"]["decisions"][:1]:
            print(f"  decision: {decision[:300]}")
        for model, payloads in result["samples"]["extractions"].items():
            if payloads:
                print(f"  extract[{model}]: {payloads[0][:300]}")
        for rewritten in result["samples"]["rewrites"][:1]:
            print(f"  rewrite: {rewritten[:160]}")
    print("== aggregate ==")
    for name, values in aggregate.items():
        print(f"  {summarize(name, values)}")
    if error_total:
        print(f"errors_total={error_total}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio-dir", default="tests/fixtures/audio")
    parser.add_argument("--service-tier", default=os.getenv("OPENAI_SERVICE_TIER", ""))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("AI_TIMEOUT_SECONDS", "15")))
    args = parser.parse_args()
    backend_root = Path(__file__).resolve().parents[1]
    load_dotenv(backend_root / ".env")
    audio_dir = Path(args.audio_dir)
    if not audio_dir.is_absolute():
        audio_dir = backend_root / audio_dir
    sys.exit(asyncio.run(main_async(audio_dir, args.service_tier, args.timeout)))


if __name__ == "__main__":
    main()
