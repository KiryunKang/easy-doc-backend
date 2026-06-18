# 쉬운문서 도우미 (백엔드)

노인 대상 — 사진으로 찍은 고지서·안내문·공문을 **OCR → 문서 분석 + 쉬운말 번역(병렬) → 혜택 정책 RAG 매칭**으로 처리하는 FastAPI 백엔드.

## 파이프라인

```
사진 업로드 → Gemini OCR ─┬─ Gemini 문서 분석   (병렬)
                          └─ Gemini 쉬운말 번역 (병렬)
                          → 임베딩 RAG로 혜택 정책 매칭 → 결과 반환
```

## 기술 스택

- **OCR**: Gemini 2.5 Flash (멀티모달, 이미지 → 텍스트)
- **LLM**: Gemini 2.5 Flash (`google-genai`) — OCR · 문서 분석 · 쉬운말 번역
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
│       ├── ocr.py           # Gemini 멀티모달 OCR
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
   - `GEMINI_API_KEY`: Gemini API 키 (OCR·분석·번역 모두 사용)
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
- 응답: `ProcessResponse` (이미지 없이 분석/번역/RAG 개발·테스트 가능)

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
      "id": "health_insurance_reduction", "name": "건강보험료 경감(지역가입자)",
      "category": "의료/공과금", "eligibility": "...",
      "amount": "...", "how_to_apply": "...",
      "phone": "1577-1000", "visit": "국민건강보험공단 지사",
      "source": "국민건강보험공단", "priority": "medium",
      "score": 0.53
    }
  ]
}
```
> `matched_policies` 는 **유사도 0.35 미만 컷 → 유사도 내림차순 → (동점 시) `priority`(high>medium>low)** 순으로 정렬됩니다. 입력 문서종류가 정책의 `related_doc_types` 와 겹치면 가점·강제포함됩니다.

## corpus.json 스키마 (팀원 B→A 계약)

`data/corpus.json` 은 혜택 정책 객체의 **배열**입니다. 각 항목(12필드):

| 필드 | 타입 | 임베딩 | 설명 |
|------|------|:---:|------|
| `id` | string | — | 고유 ID (중복 금지) |
| `name` | string | ✅ | 정책명 |
| `category` | string | ✅ | 분야(연금/의료/공과금/긴급지원…) |
| `eligibility` | string | ✅ | 지원 대상(나이·소득 등) |
| `keywords` | string | ✅ | 검색어 나열(공백 구분) |
| `related_doc_types` | string[] | ✅ | 연관 문서종류 (가점·강제포함 매칭에 사용) |
| `amount` | string | — | 금액(불확실 시 `"확인필요"`) |
| `how_to_apply` | string | — | 신청 방법 |
| `phone` | string | — | 전화 (`tel:` 연결) |
| `visit` | string | — | 찾아가기 (지도 연결) |
| `source` | string | — | 출처(소관기관) |
| `priority` | string | — | `"high"`/`"medium"`/`"low"` (긴급 혜택 상단 정렬) |

임베딩 텍스트 = `name | category | 대상:eligibility | keywords | 관련문서:related_doc_types`.
파일을 교체하면 서버 재시작 시 자동으로 다시 임베딩됩니다.
