from app.config import get_settings
from app.services.gemini_client import get_client

TRANSLATION_PROMPT = """당신은 노인을 위한 '쉬운 말' 번역가입니다.
아래 공공문서 텍스트를 어려운 행정용어 없이, 읽기 쉬운 짧은 문장으로 다시 써 주세요.

규칙:
- 초등학생도 이해할 수준으로
- 한자어/전문용어는 쉬운 우리말로 풀어서
- 무엇을, 언제까지, 어떻게 해야 하는지 명확하게
- 불필요한 인사말·형식 문구는 빼기
- 항목이 여러 개면 줄바꿈으로 정리

문서 텍스트:
\"\"\"
{text}
\"\"\"

쉬운 말로 바꾼 내용만 출력하세요."""


async def to_easy_korean(text: str) -> str:
    client = get_client()
    settings = get_settings()
    resp = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=TRANSLATION_PROMPT.format(text=text),
        config={"temperature": 0.3},
    )
    return (resp.text or "").strip()
