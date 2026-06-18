import asyncio
import os

from google.cloud import vision

from app.config import get_settings

_client: vision.ImageAnnotatorClient | None = None


def _get_client() -> vision.ImageAnnotatorClient:
    global _client
    if _client is None:
        settings = get_settings()
        # 서비스 계정 키 경로를 환경 변수로 노출 (google-cloud-vision 가 자동 인식)
        if settings.google_application_credentials and not os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS"
        ):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
                settings.google_application_credentials
            )
        _client = vision.ImageAnnotatorClient()
    return _client


def _sync_extract(image_bytes: bytes) -> str:
    client = _get_client()
    image = vision.Image(content=image_bytes)
    # 밀집 문서(고지서/공문)에는 document_text_detection 이 더 정확
    response = client.document_text_detection(
        image=image, image_context={"language_hints": ["ko"]}
    )
    if response.error.message:
        raise RuntimeError(response.error.message)
    return response.full_text_annotation.text or ""


async def extract_text(image_bytes: bytes) -> str:
    """이미지 바이트에서 텍스트 추출 (동기 SDK를 스레드로 오프로드)."""
    return await asyncio.to_thread(_sync_extract, image_bytes)
