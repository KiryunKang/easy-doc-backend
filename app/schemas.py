from pydantic import BaseModel, Field


class DocumentAnalysis(BaseModel):
    """문서 분석 결과."""

    doc_type: str = Field("", description="문서 종류 (예: 건강보험 고지서)")
    sender: str = Field("", description="보낸 기관")
    summary: str = Field("", description="문서 요약")
    key_points: list[str] = Field(default_factory=list, description="핵심 내용")
    amount: str = Field("", description="금액 (있을 경우)")
    deadline: str = Field("", description="기한/날짜 (있을 경우)")
    required_actions: list[str] = Field(
        default_factory=list, description="사용자가 해야 할 일"
    )
    watch_out: str = Field(
        "", description="놓치면 불이익이 생기는 주의사항(연체료·자격 상실 등). 없으면 빈 문자열"
    )


class MatchedPolicy(BaseModel):
    """RAG로 매칭된 혜택 정책 (corpus.json 스키마 계약 B→A 기준)."""

    id: str = ""
    name: str = ""
    category: str = ""
    eligibility: str = ""
    amount: str = ""
    how_to_apply: str = ""
    phone: str = ""
    visit: str = ""
    source: str = ""
    priority: str = "medium"
    score: float = 0.0


class ProcessResponse(BaseModel):
    """/api/process 응답 (프론트엔드 계약)."""

    ocr_text: str
    analysis: DocumentAnalysis
    easy_translation: str
    matched_policies: list[MatchedPolicy]


class AnalyzeTextRequest(BaseModel):
    """OCR 없이 텍스트만으로 테스트할 때 사용."""

    text: str
