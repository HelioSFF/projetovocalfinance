import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.clients.deepseek_client import build_deepseek_client
from app.clients.openai_client import build_openai_client
from app.core.config import settings
from app.core.errors import AppError
from app.routers import financial_records, health, voice_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", force=True)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.openai_client = build_openai_client(settings)
    app.state.deepseek_client = build_deepseek_client(settings)
    if settings.dev_tools_enabled():
        logger.warning("APP_ENV=development: dev tools enabled")
    yield
    await app.state.openai_client.close()
    await app.state.deepseek_client.close()


app = FastAPI(title="Vocal Finance", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    content = {"error": {"code": exc.code, "message": exc.message}}
    if exc.debug is not None:
        content["debug"] = exc.debug
    return JSONResponse(status_code=exc.status, content=content)


app.include_router(health.router)
app.include_router(financial_records.router)
app.include_router(voice_records.router)
