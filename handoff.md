# 핸드오프 — 쉬운문서 도우미 백엔드

> 다음 세션에서 이 파일을 먼저 읽고 이어서 진행하세요.
> **프로젝트 폴더: `C:\Users\Moel\Desktop\hackathon`**

## 한 줄 요약
노인 대상 앱. 폰으로 고지서/안내문/공문을 **사진 촬영 → OCR → (문서 분석 ∥ 쉬운말 번역, 병렬) → RAG로 혜택 정책 매칭** 하는 FastAPI 백엔드. 내가(사용자) 백엔드 담당, 팀원이 `corpus.json` + 프론트엔드 담당, 내가 합침.

## 확정된 기술 스택
| 영역 | 선택 | 비고 |
|------|------|------|
| 웹서버 | FastAPI + uvicorn | |
| OCR | Google Cloud Vision | `document_text_detection`, 한국어 힌트. 서비스계정 JSON 키 필요 |
| LLM | **Gemini 2.5 Flash** (`google-genai`) | 문서 분석 + 쉬운말 번역 (Claude/OpenAI 아님) |
| RAG 임베딩 | **로컬 `jhgan/ko-sroberta-multitask`** (sentence-transformers) | 한국어 특화, 비용 0, 오프라인. HF 캐시에 다운로드 완료 |
| 벡터DB | **ChromaDB** (인메모리, 시작 시 corpus 적재) | |

## 폴더 구조 (모두 작성 완료)
```
Desktop\hackathon\
├── app\
│   ├── main.py              # FastAPI 앱, CORS, lifespan에서 RAG 로드
│   ├── config.py            # .env 설정 (Gemini 키, Vision 키 경로, 임베딩 모델명 등)
│   ├── schemas.py           # 요청/응답 Pydantic 모델 = 프론트 계약
│   ├── routers\document.py  # POST /api/process, POST /api/analyze-text
│   └── services\
│       ├── ocr.py           # Google Vision OCR (asyncio.to_thread)
│       ├── analysis.py      # Gemini 문서 분석 (JSON 응답)
│       ├── translation.py   # Gemini 쉬운말 번역
│       ├── rag.py           # ko-sroberta + ChromaDB 매칭  ← 이번에 로컬 스택으로 재작성됨
│       └── gemini_client.py # Gemini 클라이언트 싱글톤
├── data\corpus.json         # 혜택 정책 샘플 4건 (팀원 파일로 교체 예정)
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md                # API 계약 + corpus.json 스키마 표 (팀원 공유용)
└── handoff.md               # 이 파일
```
모든 .py 파일 **문법 검증 통과**. 단, **런타임 실제 구동 테스트는 아직 안 함** (아래 "다음 할 일" 참고).

## 환경 상태 (중요)
- **venv 위치**: `C:\Users\Moel\rag_test\.venv` (프로젝트 폴더와 분리되어 있음).
  - "Desktop\hackathon으로 통합" 결정함 → venv를 재생성하거나 이 venv를 그대로 쓰기로. **단 venv 폴더 이동(move)은 Windows에서 깨지므로 금지.** torch 재다운로드 피하려면 이 venv를 그대로 쓰고 hackathon 코드를 그 python으로 실행하는 게 빠름.
- **이미 설치됨** (rag_test\.venv): `chromadb`, `sentence-transformers`, `torch`, `pydantic`, `pydantic-settings`, `uvicorn`, `numpy` + HF 모델 `jhgan/ko-sroberta-multitask` 캐시 완료.
- **아직 설치 안 됨 (백엔드 구동 필수 4종)**:
  ```powershell
  C:\Users\Moel\rag_test\.venv\Scripts\Activate.ps1
  pip install fastapi "uvicorn[standard]" python-multipart google-genai google-cloud-vision
  ```
- **PATH의 `python`은 Microsoft Store 스텁 → `-m` 실행 불가(exit 49)**. CLI에서 직접 쓸 땐 **`py -3`** 사용. (venv 활성화 후엔 venv의 python 사용)
- `pip`/`git`/`uv` 는 시스템 PATH에 없음.

## API 계약 (프론트엔드용 — README에도 있음)
- `POST /api/process` (multipart, `file`=이미지) → `ProcessResponse`
- `POST /api/analyze-text` (`{"text": "..."}`) → `ProcessResponse`  *(OCR/Vision 키 없이 분석·번역·RAG 개발 가능 — 프론트 먼저 붙일 때 유용)*
- `ProcessResponse` = `{ ocr_text, analysis{doc_type,sender,summary,key_points,amount,deadline,required_actions}, easy_translation, matched_policies[{id,title,summary,eligibility,benefit,apply,category,source,score}] }`

## 키 발급 필요
1. **GEMINI_API_KEY** — Google AI Studio
2. **Google Cloud Vision 서비스계정 JSON** — GCP 콘솔, 경로를 `GOOGLE_APPLICATION_CREDENTIALS`에 지정
→ `.env.example`을 `.env`로 복사 후 채우기

## 다음 할 일 (우선순위 순)
1. [ ] 누락 패키지 4종 설치 (위 명령)
2. [ ] `.env` 만들고 GEMINI_API_KEY / Vision 키 경로 채우기
3. [ ] **rag.py 런타임 검증**: ko-sroberta 모델 로드 → corpus 임베딩 → Chroma 적재 → `match()` 가 실제로 동작하는지 확인 (이 부분은 설치된 패키지로 fastapi 없이도 단독 테스트 가능)
4. [ ] 서버 구동: `uvicorn app.main:app --reload --port 8000` → http://localhost:8000/docs
5. [ ] `/api/analyze-text` 로 분석·번역·RAG 파이프라인 먼저 점검 (이미지 없이)
6. [ ] Vision 키 준비되면 `/api/process` 로 실제 사진 업로드 테스트
7. [ ] 팀원의 실제 `corpus.json` 으로 교체 (스키마는 README 참고)
8. [ ] 프론트엔드 CORS 주소를 `.env`의 `CORS_ORIGINS`에 추가

## 다음 세션 시작 멘트(붙여넣기용)
"Desktop\hackathon 프로젝트 이어서 하자. handoff.md 읽고, 다음 할 일 3번(rag.py 런타임 검증)부터 진행해줘. venv는 C:\Users\Moel\rag_test\.venv."
