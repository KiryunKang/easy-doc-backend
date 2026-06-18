from app.config import get_settings
from app.services.gemini_client import get_client

TRANSLATION_PROMPT = """당신은 노인을 위한 '쉬운 말' 도우미입니다.
아래 공공문서를 어르신이 한눈에 이해하도록 아주 간단하게 설명해 주세요.

규칙:
- 가장 중요한 것만! 전체 3~4문장 이내로 짧게.
- 이 문서가 무엇인지, (돈이 있으면) 금액이 얼마인지, 언제까지 무엇을 하면 되는지만 알려주세요.
- 복잡한 신청 절차, 은행/전화 버튼 코드, 일련번호, 표의 세부 숫자는 절대 적지 마세요.
  신청 방법은 "자세한 방법은 가족이나 가까운 주민센터에 물어보세요." 정도로만 안내하세요.
- 어려운 한자어·행정용어 금지, 초등학생도 아는 말로.
- 별표(*)나 굵게(**) 같은 기호를 쓰지 말고 자연스러운 문장으로.
- 인사말·형식 문구는 빼기.

문서 텍스트:
\"\"\"
{text}
\"\"\"

쉬운 말 설명만 출력하세요."""


async def to_easy_korean(text: str) -> str:
    client = get_client()
    settings = get_settings()
    resp = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=TRANSLATION_PROMPT.format(text=text),
        config={"temperature": 0.3},
    )
    return (resp.text or "").strip()
