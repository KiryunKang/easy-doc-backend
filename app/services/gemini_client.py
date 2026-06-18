from functools import lru_cache

from google import genai

from app.config import get_settings


@lru_cache
def get_client() -> genai.Client:
    """Gemini API 클라이언트 (싱글톤)."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY 가 설정되지 않았습니다. .env 를 확인하세요."
        )
    return genai.Client(api_key=settings.gemini_api_key)
