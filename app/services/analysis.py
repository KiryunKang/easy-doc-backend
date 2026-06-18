import json

from app.config import get_settings
from app.schemas import DocumentAnalysis
from app.services.gemini_client import get_client

ANALYSIS_PROMPT = """당신은 노인을 돕는 공공문서 분석 도우미입니다.
아래 OCR로 추출한 문서 텍스트를 분석해서 JSON으로만 답하세요.

문서 텍스트:
\"\"\"
{text}
\"\"\"

다음 형식의 JSON만 출력하세요(설명·코드블록 없이 JSON만):
{{
  "doc_type": "문서 종류 (예: 건강보험 고지서, 주민센터 안내문, 세금 고지서)",
  "sender": "보낸 기관",
  "summary": "이 문서가 무엇인지 2~3문장으로 요약",
  "key_points": ["핵심 내용 항목들"],
  "amount": "납부/지급 금액 (없으면 빈 문자열)",
  "deadline": "기한/날짜 (없으면 빈 문자열)",
  "required_actions": ["사용자가 해야 할 일들"]
}}
"""


def _parse_json(raw: str) -> dict:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if "\n" in raw:
            raw = raw.split("\n", 1)[1]  # 언어 태그 줄 제거
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start : end + 1])
        raise


async def analyze(text: str) -> DocumentAnalysis:
    client = get_client()
    settings = get_settings()
    resp = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=ANALYSIS_PROMPT.format(text=text),
        config={"response_mime_type": "application/json", "temperature": 0.2},
    )
    data = _parse_json(resp.text)
    # 알려진 필드만 추려서 검증 오류 방지
    known = {
        k: data[k]
        for k in DocumentAnalysis.model_fields
        if k in data and data[k] is not None
    }
    return DocumentAnalysis(**known)
