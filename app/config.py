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

    # RAG
    corpus_path: str = "data/corpus.json"
    rag_top_k: int = 3
    rag_score_threshold: float = 0.35  # 코사인 유사도 컷 (미만 제외)
    # 노인 대상 앱 — 노인과 무관한 분야는 매칭 제외(category 의 '/' 앞 접두사 기준)
    exclude_categories: list[str] = [
        "청년", "아동", "보육", "임산부", "청소년", "구직자", "실업자",
    ]

    # CORS
    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
