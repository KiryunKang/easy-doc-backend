from google.genai import types

from app.config import get_settings
from app.services.gemini_client import get_client

OCR_PROMPT = """이 이미지는 한국의 공공문서(고지서·안내문·공문 등)를 촬영한 사진입니다.
이미지에 보이는 모든 글자를 빠짐없이 그대로 추출해 주세요.

규칙:
- 표나 항목은 읽는 순서대로 줄바꿈하여 정리하세요.
- 금액·날짜·기관명·전화번호·숫자를 정확히 옮기세요.
- 설명이나 해석을 덧붙이지 말고, 문서에 실제로 적힌 텍스트만 출력하세요.
- 글자를 전혀 찾을 수 없으면 빈 문자열만 출력하세요."""


async def extract_text(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """이미지 바이트에서 Gemini 2.5 Flash 로 텍스트(OCR) 추출."""
    client = get_client()
    settings = get_settings()
    resp = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            OCR_PROMPT,
        ],
        config={"temperature": 0.0},
    )
    return (resp.text or "").strip()
