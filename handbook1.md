# Handbook 1 — 쉬운문서 도우미(드리미) 개발 복습 노트

> 2026-06-18 세션 정리. 이슈·디버깅·프롬프트 위주. 다음에 비슷한 작업/실수 반복 안 하려고 남김.

---

## 0. 이 세션에서 한 일 (한눈에)
1. **OCR을 Google Vision → Gemini 2.5 Flash 멀티모달로 전환** (키 1개로 통합)
2. 전체 파이프라인 런타임 검증 (`/api/process`, `/api/analyze-text`)
3. **팀원 corpus 통합** (스키마 불일치 → 변환 → 결국 팀원이 우리 스키마 채택)
4. RAG 매칭 규칙(유사도 컷·정렬·가점), **노인 무관 분야 매칭 제외**
5. 프론트 연결, UI 대량 정리 (텍스트입력 제거·카드 헤더·단계 연결선·팁 캐러셀·TTS)
6. **로깅 + PII 마스킹**, 번역 간결화, `watch_out` 주의박스
7. 결과 **공유 단축 URL**, 이모지 → SVG 아이콘 통일

---

## 1. 겪은 이슈 & 해결 (★ 중요)

### ★ `[object Object]` 에러 — 진짜 원인은 프론트 파일 전송 버그
- **증상**: 결과 화면에 빨간 `⚠️ [object Object]`, "결과를 불러오지 못했어요".
- **표면 원인**: `fetch` 실패 시 백엔드가 **422**를 반환, 그 `detail`이 **배열**(`[{...}]`)인데 프론트가 `throw new Error(detail)` 하면서 객체가 문자열화 → `[object Object]`.
- **진짜 원인**: `/api/process`가 422(파일 누락)였음. 함수 진입 로그조차 안 찍힘 = FastAPI 검증 단계에서 막힘 = **`file`이 요청에 없음**.
  ```js
  // 버그: run()이 thunk 실행 "전에" input을 비워버림
  async function run(apiCall){ fileGallery.value=""; ... const data = await apiCall(); }
  fileGallery.onchange = () => run(() => callProcess(fileGallery.files[0])); // 지연평가 → 그땐 files[0]가 undefined
  ```
- **해결**: 파일을 **호출 시점에 캡처**.
  ```js
  fileGallery.onchange = () => { const f = fileGallery.files[0]; if (f) run(() => callProcess(f)); };
  ```
  + 프론트 `formatDetail()`로 배열/객체 detail을 읽을 수 있게, 백엔드 `RequestValidationError` 핸들러로 422 시 content-type 로깅.
- **교훈**: 에러 메시지(`[object Object]`)는 표면. **함수 진입 로그 유무로 "어디서 막혔나"부터 가른다.** 422는 핸들러 안 들어옴.

### ★ 서버 재시작이 안 먹힘 (옛 프로세스가 포트 점유)
- bash `pkill -f uvicorn`이 **Windows에선 안 죽음** → 옛 서버가 8000 점유 → 새 서버 바인딩 실패(`Errno 10048`)인데 **옛(구버전) 서버가 계속 응답** → "왜 코드 변경이 반영 안 되지?"
- **해결**: PowerShell로 포트 점유 프로세스 정리.
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 -State Listen | %{ Stop-Process -Id $_.OwningProcess -Force }
  ```
- **교훈**: `--reload` 없이 띄웠으면 코드 변경 = 반드시 재시작. 재시작 실패가 조용히 묻힐 수 있으니 시작 로그(`Application startup complete` / `error while attempting to bind`) 확인.

### ★ 한글 인코딩 깨짐 (cp949)
- uvicorn stdout/콘솔이 cp949 → 한글 로그·출력 `??ï¿½`로 깨짐. **데이터는 정상, 표시만 문제**.
- **해결 모음**:
  - 로깅: `sys.stdout.reconfigure(encoding="utf-8")` (logging_utils import 시 1회)
  - 일회성 출력: `PYTHONIOENCODING=utf-8` 환경변수
  - 멀티라인 로그가 grep에서 잘림 → 로그 문자열의 `\n`을 ` ⏎ `로 치환해 한 줄로
- **교훈**: 깨진 콘솔에 속지 말 것. 검증은 UTF-8로 다시 읽거나 필드값(숫자/스코어)으로 확인.

### Windows / 환경 함정
- PATH의 `python`은 **Microsoft Store 스텁**(`-m` 실행 시 exit 49). venv python 전체경로 사용: `C:\Users\Moel\rag_test\.venv\Scripts\python.exe`. venv는 프로젝트와 분리됨, **이동(move) 금지**(깨짐).
- bash의 `/tmp`는 **Windows python이 못 봄**(`FileNotFoundError`). 임시파일은 Windows 경로(`tests/_*`)로 저장하고 `.gitignore` 처리.
- curl로 **한글 JSON 본문** 보낼 때 인라인은 깨짐 → UTF-8 파일에 쓰고 `--data-binary @file`.

---

## 2. Git 협업 이슈 (팀원과 동시 작업)

- **상황**: 나=백엔드, 팀원=corpus 데이터 담당인데, 팀원이 백엔드(rag.py hybrid)·corpus를 자기 스키마로 따로 발전시켜 **origin에 계속 푸시** → 푸시할 때마다 분기/충돌.
- **스키마 불일치**: 팀원 corpus(`title/benefit/apply/signals/priority(int)`) ≠ 우리(`name/amount/how_to_apply/keywords/priority(str)`). → **변환 스크립트** `scripts/convert_team_corpus.py`로 흡수(idempotent하게: keywords가 list든 str든 처리).
- **머지 전략**:
  - 우리 코드 유지 + 팀원 변경 히스토리만 흡수 → `git merge -s ours origin/main`
  - 팀원이 우리 트리 위에서 작업·코드 안 건드림 → `git merge --ff-only origin/main`
  - 일반 머지(서로 다른 파일) → 자동 머지(`ort`) 충돌 없음
- **교훈**: 푸시 전 항상 `git fetch` 후 `ahead/behind` 확인. 동시 편집 파일(`frontend/index.html`)은 한쪽에서만 저장하도록 역할 분리. 결국 팀원이 우리 스키마/스택을 채택하며 정리됨.
- **`.env` 안전**: `git add -A` 후 매번 `git diff --cached --name-only | grep -x ".env"`로 제외 확인.

---

## 3. 핵심 프롬프트 모음

### OCR (Gemini 2.5 Flash 멀티모달 — `ocr.py`)
```
이 이미지는 한국의 공공문서(고지서·안내문·공문 등)를 촬영한 사진입니다.
이미지에 보이는 모든 글자를 빠짐없이 그대로 추출해 주세요.
규칙:
- 표나 항목은 읽는 순서대로 줄바꿈하여 정리하세요.
- 금액·날짜·기관명·전화번호·숫자를 정확히 옮기세요.
- 설명이나 해석을 덧붙이지 말고, 문서에 실제로 적힌 텍스트만 출력하세요.
- 글자를 전혀 찾을 수 없으면 빈 문자열만 출력하세요.
```
- 호출: `types.Part.from_bytes(data=image_bytes, mime_type=...)` + 프롬프트, `temperature=0.0`.

### 분석 (JSON 출력 — `analysis.py`)
- `response_mime_type: application/json`, `temperature=0.2`. 필드: `doc_type, sender, summary, key_points, amount, deadline, required_actions, watch_out`.
- **watch_out**(이번 추가): `"기한을 놓치거나 신청하지 않으면 생기는 불이익을 한 문장으로 경고(예: 연체료 부과, 지원 자격 상실). 특별한 주의사항이 없으면 빈 문자열"`
- 응답 파싱은 코드블록(```) 제거 + `{ } ` 추출 폴백.

### 쉬운말 번역 (노인 대상 — `translation.py`) ★ 간결화가 핵심
```
당신은 노인을 위한 '쉬운 말' 도우미입니다.
아래 공공문서를 어르신이 한눈에 이해하도록 아주 간단하게 설명해 주세요.
규칙:
- 가장 중요한 것만! 전체 3~4문장 이내로 짧게.
- 이 문서가 무엇인지, (돈이 있으면) 금액이 얼마인지, 언제까지 무엇을 하면 되는지만.
- 복잡한 신청 절차, 은행/전화 버튼 코드, 일련번호, 표의 세부 숫자는 절대 적지 마세요.
  신청 방법은 "자세한 방법은 가족이나 가까운 주민센터에 물어보세요." 정도로만.
- 어려운 한자어·행정용어 금지, 초등학생도 아는 말로.
- 별표(*)·굵게(**)·이모지·그림문자 쓰지 말고 자연스러운 문장으로.
- 인사말·형식 문구는 빼기.
```
- **왜**: 처음엔 원문을 다 풀어써서 783자(ARS 번호·주민번호 7자리·계좌입력 절차까지). 노인 대상엔 과함 → "핵심만, 절차/코드 생략"으로 **783자→115자**.
- **교훈**: "무엇을·언제까지·**어떻게**" 다 시키면 길어진다. 절차는 사람(가족·주민센터)에게 넘기는 안내로 대체.

---

## 4. PII 마스킹 규칙 (`logging_utils.py`)
로그에만 적용(원본 데이터 불변). 입력→출력 전 과정 로깅하되 가림.
- 주민등록번호 `901231-1234567` → `901231-*******`
- 전화 `010-1234-5678` → `010-****-5678`
- 계좌/납부번호 `1234-5678-9012` → `********9012` (뒤 4자리만)
- 이름 `김복순 귀하/님` → `김** 귀하`
- **함정**: 이름 정규식 `([가-힣]{2,4})\s*(님)`이 **"선생님·어머님·사장님"을 이름으로 오인** → 호칭 화이트리스트(`_TITLE_WORDS`)로 제외.
- **교훈**: 한국어 이름 마스킹은 일반 호칭과 충돌. 예외 목록 필수.

---

## 5. RAG 매칭 규칙 (`rag.py`)
- 임베딩 텍스트 = `name | category | 대상:eligibility | keywords | 관련문서:related_doc_types`
- **유사도 0.35 미만 컷** → 정렬: **유사도 내림차순 → 동점 시 priority**(사용자가 "유사도 우선"으로 결정, 팀원 스펙은 priority 우선이었음)
- `doc_type`이 `related_doc_types`와 겹치면 **+0.15 가점·강제포함**. 단 표현 불일치 주의("전기요금 청구서" vs corpus "전기요금 고지서"면 substring 안 겹쳐 가점 안 걸림).
- **노인 대상 앱** → `config.exclude_categories`(청년·아동·보육·임산부·청소년·구직자·실업자)를 `load()`에서 category '/' 앞 접두사로 필터(100→75건).

---

## 6. 작업 방식 메모
- **검증 시 OCR 재호출 금지**: `tests/sample_notice.ocr.txt`(캐싱된 OCR 텍스트)를 `/api/analyze-text`로 넣어 분석/번역/RAG 검증 → Gemini OCR 호출 0(비용·rate limit 절약). 이미지 OCR 경로 자체를 테스트할 때만 `/api/process`.
- 결과 공유: `POST /api/share`(인메모리 저장→6자 코드) + `?s=코드`로 열면 결과 표시. **단축 URL 주소는 프론트가 떠있는 주소** → localhost면 같은 PC만, 외부 공유는 배포/터널 필요.
- UI 이모지는 line 스타일 SVG 심볼(`viewBox 0 0 24 24, stroke 2.3`)로 통일. 없는 건 같은 스타일로 신규 추가(i-won/i-health/i-fire).
