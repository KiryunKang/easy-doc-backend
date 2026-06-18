# 핸드오프 — 쉬운문서 도우미 백엔드

> 다음 세션에서 이 파일을 먼저 읽고 이어서 진행하세요.
> **프로젝트 폴더: `C:\Users\Moel\Desktop\hackathon`**

## 한 줄 요약
노인 대상 앱. 폰으로 고지서/안내문/공문을 **사진 촬영 → OCR → (문서 분석 ∥ 쉬운말 번역, 병렬) → RAG로 혜택 정책 매칭** 하는 FastAPI 백엔드. 내가(사용자) 백엔드 담당, 팀원이 `corpus.json` + 프론트엔드 담당, 내가 합침.

## ✅ 현재 상태 (2026-06-18 갱신)
**전체 파이프라인 런타임 검증 완료.** 서버 구동 → `/api/analyze-text`(텍스트) → `/api/process`(이미지 업로드) 모두 HTTP 200 정상 응답 확인. OCR·분석·번역·RAG 4단계 전부 동작.
- OCR을 **Google Cloud Vision → Gemini 2.5 Flash 멀티모달로 전환** (Vision 서비스계정 키 불필요해짐). 이제 키는 `GEMINI_API_KEY` 하나만 필요.
- `.env`에 `GEMINI_API_KEY` 채워짐 (Google AI Studio 발급).
- **corpus 스키마를 팀원 계약(B→A, `E:\0618\ocr_rehearsal\CORPUS_SCHEMA.md`)으로 정렬.** 12필드: `id, name, category, eligibility, keywords(공백구분 string), related_doc_types[], amount, how_to_apply, phone, visit, source, priority`. `schemas.py`의 `MatchedPolicy`, `rag.py`, `data/corpus.json`(샘플 4건) 모두 이 스키마로 교체. README도 갱신.
- **RAG 매칭 규칙**: 임베딩텍스트=`name | category | 대상:eligibility | keywords | 관련문서:related_doc_types`. 유사도 0.35 미만 컷(`rag_score_threshold`) → **정렬은 유사도 내림차순 → 동점 시 priority**(사용자 결정. 팀원 스펙은 priority 우선이었으나 뒤집음). 입력 `doc_type`이 `related_doc_types`와 겹치면 +0.15 가점·강제포함.
- ⚠️ **표현 정합성 주의**: Gemini 분석 `doc_type`이 "전기요금 **청구서**"로 나오면 corpus의 "전기요금 **고지서**"와 substring이 안 겹쳐 가점이 안 걸림. 팀원 실 corpus의 `related_doc_types`에 표현 변형(청구서/고지서/안내문)을 넉넉히 넣어야 가점이 잘 작동함.
- 테스트 이미지 `tests/sample_notice.png`(노원구 재산세 고지서), 생성 스크립트 `/tmp/make_img.py`(malgun 폰트). 임시 응답파일은 `tests/_*`로 만들고 `.gitignore` 처리.

## 확정된 기술 스택
| 영역 | 선택 | 비고 |
|------|------|------|
| 웹서버 | FastAPI + uvicorn | |
| OCR | **Gemini 2.5 Flash** (멀티모달) | `app/services/ocr.py` — 이미지 bytes+mime_type → 텍스트. Vision 폐기 |
| LLM | **Gemini 2.5 Flash** (`google-genai`) | OCR + 문서 분석 + 쉬운말 번역 (Claude/OpenAI 아님) |
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
- **백엔드 구동 필수 패키지 설치 완료**: fastapi, uvicorn, python-multipart, google-genai, sentence-transformers, chromadb, torch, pydantic(-settings), Pillow(테스트 이미지 생성용). `google-cloud-vision`은 OCR을 Gemini로 바꾸면서 requirements에서 제거.
- **PATH의 `python`은 Microsoft Store 스텁 → `-m` 실행 불가(exit 49)**. CLI에서 직접 쓸 땐 **`py -3`** 또는 venv python 전체경로 `C:\Users\Moel\rag_test\.venv\Scripts\python.exe` 사용.
- **서버 재시작 주의**: bash `pkill`은 Windows uvicorn 프로세스를 못 죽임. 포트 8000 점유 프로세스는 PowerShell로 정리: `Get-NetTCPConnection -LocalPort 8000 -State Listen | %% { Stop-Process -Id $_.OwningProcess -Force }`. (안 죽이면 옛 프로세스가 포트 물고 있어 새 서버가 바인딩 실패 → 구버전이 응답함)
- `pip`/`git`/`uv` 는 시스템 PATH에 없음. git은 PATH에 있음(2.54).

## API 계약 (프론트엔드용 — README에도 있음)
- `POST /api/process` (multipart, `file`=이미지) → `ProcessResponse`
- `POST /api/analyze-text` (`{"text": "..."}`) → `ProcessResponse`  *(OCR/Vision 키 없이 분석·번역·RAG 개발 가능 — 프론트 먼저 붙일 때 유용)*
- `ProcessResponse` = `{ ocr_text, analysis{doc_type,sender,summary,key_points,amount,deadline,required_actions}, easy_translation, matched_policies[{id,title,summary,eligibility,benefit,apply,category,source,score}] }`

## 키 (완료)
- **GEMINI_API_KEY** — Google AI Studio(https://aistudio.google.com/apikey)에서 발급, `.env`에 채움. OCR·분석·번역 전부 이 키로 동작.
- Vision 서비스계정 키는 **더 이상 불필요** (OCR을 Gemini로 전환).

## Git / GitHub (셋업 완료)
- **원격 레포(Public)**: https://github.com/KiryunKang/easy-doc-backend
- 로컬 레포 `C:\Users\Moel\Desktop\hackathon` 초기화 완료, `main` → `origin/main` 추적.
- **gh CLI 설치됨**: `C:\Program Files\GitHub CLI\gh.exe` (v2.94). 시스템 PATH 반영됐을 수 있으나, 새 셸에서 못 찾으면 전체경로 사용. **bash(`!`)에서는** `/c/Program Files/GitHub CLI/gh.exe` 형식.
- gh 로그인 계정: **KiryunKang**. git user: 강기륜 / ptlkiki@korea.kr.
- git은 이제 시스템 PATH에 있음(`git 2.54`). pip/uv는 여전히 PATH에 없음.
- `.gitignore` 검증됨: `.env`, vision 서비스계정 키 제외 / `data/corpus.json`은 추적.

## 다음 할 일 (우선순위 순)
1. [x] 패키지 설치 완료 (google-cloud-vision은 제거, Pillow 추가)
2. [x] `.env`에 GEMINI_API_KEY 채움 (Vision 키 불필요)
3. [x] **rag.py 런타임 검증 완료** — `tests/test_rag_runtime.py`로 ko-sroberta 로드→corpus 임베딩→Chroma 적재→`match()` 동작 확인.
4. [x] 서버 구동 확인 (http://localhost:8000/docs → 200)
5. [x] `/api/analyze-text` 검증 — 건강보험 고지서 텍스트 → 분석/번역/RAG 모두 정상, policy-004 1위 매칭.
6. [x] `/api/process` 검증 — 한글 재산세 고지서 테스트 이미지(`tests/sample_notice.png`, `tests/`의 생성 스크립트는 /tmp/make_img.py 참고) 업로드 → **Gemini OCR 정확 추출**(기관·금액·기한·전화·납부번호) → 분석/번역/RAG 정상.
7. [x] **팀원 corpus 100건 적용 완료.** 팀원이 origin/main에 올린 corpus(title/benefit/signals/region/age_min 등 다른 스키마 + hybrid rag.py)를 데이터만 가져와 **우리 12필드 스키마로 변환**(title→name, benefit→amount, apply→how_to_apply, keywords+signals→공백string, priority int 1~2/3/4~5→high/medium/low). 변환은 재사용 스크립트 `scripts/convert_team_corpus.py`로 수행(검증됨). 단 **팀원이 우리 12필드 스키마를 그대로 채택**(2026-06-18, e9ddcf4/547372d)해서 이제 변환 불필요 — 팀원이 우리 merge커밋(8c71a7e) 위에서 phone/visit/related_doc_types를 100/100 채워 푸시했고 백엔드 코드는 안 건드림 → `git merge --ff-only origin/main`로 그냥 반영됨. 변환기는 팀원이 옛 스키마(title/benefit/signals)로 회귀할 경우 대비 보험으로 보관. 백엔드 코드(ocr=Gemini, rag, schemas)는 **우리 것 유지**(팀원 hybrid rag는 미채택, 사용자 결정). phone/visit는 corpus에 데이터 없어 빈값(프론트 전화/지도 버튼 비활성). related_doc_types도 빈배열이라 doc_type 가점은 현재 무효, 임베딩 매칭만 작동. 100건 매칭 검증 완료(세금/건강보험/돌봄 등). **phone/visit/related_doc_types 100% 채워짐**(팀원이 채워 푸시 → ff로 반영). doc_type↔related_doc_types 가점도 이제 실제 작동. SOURCE_LOG.md는 팀원이 현재 스키마/스택에 맞춰 복원함.
   - **검증 시 OCR 재호출 금지**: `tests/sample_notice.ocr.txt`에 캐싱된 OCR 텍스트를 `/api/analyze-text`로 넣어 검증(Gemini OCR 호출 0). 이미지 OCR 자체를 새로 테스트할 때만 `/api/process` 사용.
8. [ ] 프론트엔드 CORS 주소를 `.env`의 `CORS_ORIGINS`에 추가
9. [ ] (선택) 번역 출력이 마크다운(**/*) 섞여 나옴 — 노인 대상이면 프롬프트에서 순수 텍스트로 다듬을지 검토
10. [ ] (선택) git 커밋/푸시 — 이번 변경(OCR=Gemini, corpus 스키마 정렬) 아직 커밋 안 됨

## 다음 세션 시작 멘트(붙여넣기용)
"Desktop\hackathon 프로젝트 이어서 하자. handoff.md 읽고, 다음 할 일 3번(rag.py 런타임 검증)부터 진행해줘. venv는 C:\Users\Moel\rag_test\.venv."
