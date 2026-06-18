from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.logging_utils import logger
from app.routers import document
from app.services.rag import get_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 RAG 코퍼스 로드 (임베딩 사전 계산)
    await get_engine().load()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="쉬운문서 도우미 API",
        description="노인 대상 공공문서 OCR · 분석 · 쉬운말 번역 · 혜택 정책 매칭",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(document.router)

    @app.exception_handler(RequestValidationError)
    async def on_validation_error(request: Request, exc: RequestValidationError):
        # 요청 검증 실패(422) 진단: content-type 과 어떤 필드가 문제인지 로깅
        logger.warning(
            "[422] %s %s | content-type=%s | errors=%s",
            request.method,
            request.url.path,
            request.headers.get("content-type"),
            exc.errors(),
        )
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.get("/health", tags=["meta"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
