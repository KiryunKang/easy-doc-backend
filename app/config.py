from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경 변수 / .env 에서 읽어오는 설정값."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Gemini (문서 분석 / 쉬운말 번역)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # RAG 임베딩 (로컬 한국어 모델, sentence-transformers)
    embedding_model: str = "jhgan/ko-sroberta-multitask"

    # Google Cloud Vision (OCR) - 서비스 계정 키 경로
    google_application_credentials: str = ""

    # RAG
    corpus_path: str = "data/corpus.json"
    rag_top_k: int = 3
    rag_min_score: float = 0.35  # 코사인 유사도 임계값(미달은 신호/키워드 폴백으로만 포함)

    # CORS
    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
