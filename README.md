# 쉬운문서 도우미 (백엔드)

노인 대상 — 사진으로 찍은 고지서·안내문·공문을 **OCR → 문서 분석 + 쉬운말 번역(병렬) → 혜택 정책 RAG 매칭**으로 처리하는 FastAPI 백엔드.

## 파이프라인

```
사진 업로드 → Google Vision OCR ─┬─ Gemini 문서 분석   (병렬)
                                 └─ Gemini 쉬운말 번역 (병렬)
                                 → 임베딩 RAG로 혜택 정책 매칭 → 결과 반환
```

## 기술 스택

- **OCR**: Google Cloud Vision (`document_text_detection`, 한국어 힌트)
- **LLM**: Gemini 2.5 Flash (`google-genai`) — 문서 분석 · 쉬운말 번역
- **RAG**: 로컬 한국어 임베딩 `jhgan/ko-sroberta-multitask` (sentence-transformers) + ChromaDB(인메모리) 코사인 유사도
- **서버**: FastAPI + uvicorn

## 폴더 구조

```
hackathon/
├── app/
│   ├── main.py              # FastAPI 앱, CORS, lifespan(RAG 로드)
│   ├── config.py            # 환경설정 (.env)
│   ├── schemas.py           # 요청/응답 Pydantic 모델 (프론트 계약)
│   ├── routers/document.py  # /api/process, /api/analyze-text
│   └── services/
│       ├── ocr.py           # Google Vision OCR
│       ├── analysis.py      # Gemini 문서 분석
│       ├── translation.py   # Gemini 쉬운말 번역
│       ├── rag.py           # 혜택 정책 매칭
│       └── gemini_client.py # Gemini 클라이언트 싱글톤
├── data/corpus.json         # 혜택 정책 코퍼스 (팀원 제공 / 샘플 포함)
├── requirements.txt
└── .env.example
```

## 실행 방법

1. 가상환경 만들고 의존성 설치
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. `.env.example` → `.env` 복사 후 키 채우기
   - `GEMINI_API_KEY`: Gemini API 키
   - `GOOGLE_APPLICATION_CREDENTIALS`: Vision 서비스 계정 JSON 경로
3. 서버 실행
   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```
4. 문서: http://localhost:8000/docs

> 참고: 현재 PATH의 `python`은 Microsoft Store 스텁입니다. python.org 정식 3.11 설치를 권장합니다.

## API 계약 (프론트엔드용)

### `POST /api/process`  (multipart/form-data)
- `file`: 이미지 파일
- 응답: `ProcessResponse`

### `POST /api/analyze-text`  (application/json) — OCR 없이 테스트
- 본문: `{ "text": "문서 텍스트" }`
- 응답: `ProcessResponse` (Vision 키 없이 분석/번역/RAG 개발 가능)

### `ProcessResponse`
```jsonc
{
  "ocr_text": "원문 추출 텍스트",
  "analysis": {
    "doc_type": "건강보험 고지서",
    "sender": "국민건강보험공단",
    "summary": "이 문서는 ...",
    "key_points": ["..."],
    "amount": "120,000원",
    "deadline": "2026-07-25",
    "required_actions": ["기한 내 납부하세요"]
  },
  "easy_translation": "쉬운 말로 바꾼 안내문 ...",
  "matched_policies": [
    {
      "id": "policy-004", "title": "건강보험료 경감",
      "summary": "...", "eligibility": "...", "benefit": "...",
      "apply": "...", "category": "...", "source": "...",
      "score": 0.83
    }
  ]
}
```

## corpus.json 스키마 (팀원 작성 가이드)

`data/corpus.json` 은 혜택 정책 객체의 **배열**입니다. 각 항목:

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | string | 고유 ID |
| `title` | string | 정책명 |
| `summary` | string | 한두 문장 설명 |
| `eligibility` | string | 지원 대상/자격 |
| `benefit` | string | 지원 내용/금액 |
| `category` | string | 분류 |
| `keywords` | string[] | 매칭용 키워드 (키워드 폴백에서 사용) |
| `apply` | string | 신청 방법 |
| `source` | string | 출처 기관 |

`title`·`summary`·`eligibility`·`category`·`keywords` 가 임베딩 대상 텍스트로 합쳐집니다. 파일을 교체하면 서버 재시작 시 자동으로 다시 임베딩됩니다.
