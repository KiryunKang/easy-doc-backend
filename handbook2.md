# 핸드북 2 — 프론트엔드(드리미) 작업 기록

> 이 세션에서 진행한 **프론트엔드 + 폰 접속(터널) + 테스트 자료** 작업 정리.
> 백엔드 진행상황은 `handoff.md` 참고. 이 문서는 복습용.

## 한 줄 요약
노인 대상 "쉬운문서 도우미" 앱의 **프론트엔드(앱 이름: 드리미)** 를 빌드 없이 **단일 HTML 파일** + 바닐라 JS로 제작. 사진 촬영 → OCR/분석/번역/혜택 결과를 보여주는 3화면 구조. 폰 접속용 Cloudflare 터널 + QR, OCR 테스트용 생성형 고지서까지 구성.

---

## 1. 핵심 산출물 위치
- **프론트엔드 본체**: `frontend/index.html`  (HTML+CSS+JS 전부 한 파일, 외부 의존성 0)
- **정부 CI 이미지**: `frontend/assets/gov-ci.png` (태극 정부상징)
- **터널/서빙 스크립트**: `tests/serve_tunnel.py` (정적 서빙 + /api 프록시)
- **생성형 고지서 스크립트**: `tests/make_notice.py`
- **테스트 이미지**:
  - `tests/notice_health.png` (건강보험료 납부고지서 — 생성)
  - `tests/notice_electricity.png` (전기요금 청구서 — 생성)
  - `tests/health_insurance_sample.jpg` (웹에서 받은 실물 — 보험료 부과기준 표)
  - `tests/sample_notice.png` (이전 세션 생성, 재산세 고지서)
- **QR 코드**: `tests/tunnel_qr.png` (터널 주소용. 터널 재시작하면 주소 바뀌므로 재생성 필요)

---

## 2. 결정 사항 (스택/방식)
- 빌드 없이 **단일 HTML + 바닐라 JS**. node/npm 불필요. 더블클릭 또는 정적 서버로 실행.
- 입력: **사진 메인**(카메라 `/api/process`) + 보조로 텍스트(현재 홈에서는 사진 전용으로 정리됨).
- 화면 3개 전환 구조: **홈 → 분석 중 → 결과**.
- 대상이 노인이라 **가독성 최우선**: 큰 글씨, 큰 버튼, 고대비.

### 디자인 변천
1. (초기) 글래스모피즘 + 네온 다크 테마 → 가독성 문제로 폐기.
2. (현재) **밝고 깔끔한 테마**: 배경=연회청(`#e9eef6`), 카드=흰색, 글씨=진한 남색(`#14233f`).
   파란 그라데이션은 **홈 상단 배너 하나에만** 포인트로 사용.
- 색 토큰(`:root`): `--accent #1457d6`(파랑), `--urgent #d32f2f`(빨강), `--rec #1e9e57`(초록), `--info #1457d6`(파랑) 등.

---

## 3. 백엔드 API 계약 (프론트가 의존)
- `POST /api/process` (multipart, `file`=이미지) → `ProcessResponse`
- `POST /api/analyze-text` (`{"text":"..."}`) → `ProcessResponse` (OCR 없이 테스트용)
- `ProcessResponse`:
  - `ocr_text`
  - `analysis`: `{doc_type, sender, summary, key_points[], amount, deadline, required_actions[]}`
  - `easy_translation`
  - `matched_policies[]`: `{id, name, category, eligibility, amount, how_to_apply, phone, visit, source, priority, score}`
- **CORS는 `["*"]`** 라 어디서 호출해도 됨.
- ⚠️ **단어 풀이(glossary)는 아직 백엔드에 없음.** 프론트는 `analysis.glossary`(또는 `data.glossary`)가 오면 렌더하도록 만들어둠.
  - 실데이터로 채우려면 백엔드: `schemas.py`의 `DocumentAnalysis`에 `glossary` 필드 + `analysis.py` Gemini 프롬프트에 "어려운 단어/쉬운 뜻 추출" 지시 추가.

---

## 4. 화면별 구성

### 홈 (`#screen-home`)
- 파란 그라데이션 배너: 큰 아이콘 + 안내문 + 버튼 2개(**사진 찍기**=카메라, **사진 골라오기**=갤러리).
- 아래 기능 소개 카드 4개(돋보기/말풍선/선물/전화) — 정보성.

### 분석 중 (`#screen-loading`)
- **4단계 진행 애니메이션**: 글자 읽기 → 분석 → 쉬운 말 → 혜택 찾기.
- 1~3단계 0.85초 간격 자동 점등, 마지막 단계는 실제 응답 대기 후 완료. 최소 노출 1.4초(`settle`).
- 완료 단계는 초록 체크, 단계 사이 세로 연결선.

### 결과 (`#screen-result`)
- **AI 요약 카드 하나**: 문서종류 배지 + 쉬운 설명 + 금액/기한 강조칩 + 핵심내용/할 일 + **어려운 말 풀이 칩**("미납 = 안 냄" 형태).
- **혜택 카드(3단계 색 구분)**: `priority` → 긴급(high, 빨강)/추천(medium, 초록)/참고(low, 파랑). 금액 크게 색상 강조. 전화(초록)·지도(파랑) 알약 버튼(데이터 없으면 회색 비활성).
- 맨 아래 **카카오톡 공유**(데모: Web Share API → 미지원 시 클립보드 복사. 정식은 Kakao SDK 필요) + 뒤로가기.

---

## 5. 접근성 기능 (헤더 우측 2버튼)
- **읽어주기(TTS)**: 현재 화면 내용을 `speechSynthesis`로 읽음(`ko-KR`). 말하는 중 다시 누르면 멈춤(토글).
- **어르신 글자 크기 = 3단계 순환**: 보통 → 크게(24px) → 더 크게(29px) → 다시 보통. 단계별 버튼 색 변화(`.on`/`.on2`).
- **TTS 속도는 글자 크기 단계에 연동**: 단계 커질수록 천천히(`rate 1.0 / 0.85 / 0.72`). → 별도 "느리게" 버튼 불필요.
- 글자 커질 때 **`word-break: keep-all`** 로 한국어 단어 단위 줄바꿈(단어 중간 안 끊김).
- "드리미" 클릭 / 뒤로가기 → 홈 이동 시 **`confirm()` 한 번**(실수 방지). 이미 홈이면 안 물음.
- 헤더 버튼 클릭 후 `blur()` + `:focus-visible`만 표시 → 터치 잔상 제거, 키보드 접근성 유지.

---

## 6. 아이콘 (이모지 → 인라인 SVG)
- 이모지 전부 제거(사용자 요청). **Lucide 계열 라인 아이콘**을 `<symbol>` 스프라이트로 한 번 정의, `<use href="#i-...">`로 참조.
- 스타일: **단색(currentColor)**, `stroke-width: 2.3`(두껍게). 맥락별 색 자동(헤더=네이비, 강조/타일=파랑, 배너/버튼 위=흰색, 오류=빨강).
- 아이콘 크기: 정사각 배경에 꽉 차게(헤더 32 / 기능타일 40 / 배너 56px).
- 심볼 id: `i-volume, i-person, i-doc, i-camera, i-image, i-search, i-chat, i-gift, i-phone, i-bulb, i-book, i-pin, i-alert`.

---

## 7. 폰 접속 (Cloudflare 터널 + QR)
**문제**: 프론트의 `API_BASE`가 `localhost:8000`인데, 폰에서 터널 접속 시 `localhost`는 폰 자신을 가리켜 백엔드에 못 닿음.

**해결 구조** (터널 1개로 앱+API 같은 출처):
```
폰 ──https──▶ Cloudflare 터널 ──▶ 프록시(:8080) ──┬─ 정적: frontend/index.html
                                                  └─ /api·/health ─▶ 백엔드(:8000)
```
- `tests/serve_tunnel.py`: 정적 서빙 + `/api`·`/health`를 8000으로 프록시(멀티파트 업로드 포함).
- `index.html`의 `API_BASE`: 로컬(파일/localhost)이면 `http://localhost:8000`, 외부 출처면 `""`(같은 출처) 자동 분기.

**실행 순서**
```powershell
# 1) 백엔드(:8000)는 켜져 있어야 함 (handoff.md 참고)
# 2) 프록시 서버
& "C:\Users\Moel\rag_test\.venv\Scripts\python.exe" "C:\Users\Moel\Desktop\hackathon\tests\serve_tunnel.py" 8080
# 3) 터널 (cloudflared)
& "C:\Users\Moel\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe" tunnel --no-autoupdate --url http://localhost:8080
#    → 출력되는 https://xxxx.trycloudflare.com 주소 확인
# 4) QR 생성
& "C:\Users\Moel\rag_test\.venv\Scripts\python.exe" -c "import qrcode; qrcode.make('https://xxxx.trycloudflare.com').save(r'C:\Users\Moel\Desktop\hackathon\tests\tunnel_qr.png')"
```
- **주의**: trycloudflare 주소는 **임시** → 터널 재시작 시 주소 바뀜 → QR 재생성 필요.
- cloudflared는 winget(`Cloudflare.cloudflared`)으로 설치. `--source winget` 명시해야 설치됨(msstore 충돌).

---

## 8. 생성형 테스트 고지서 (`tests/make_notice.py`)
- Pillow + 맑은고딕(`C:\Windows\Fonts\malgun.ttf`/`malgunbd.ttf`)으로 실제 고지서처럼 그림.
- 포함 필드: 보낸기관, 수신자, 납부번호, 항목별 금액 표, 합계, 납부기한, 연체/할인 안내문구.
- 건강보험료(경감 안내)·전기요금(복지할인 안내)은 RAG 혜택 매칭 단서까지 들어가 end-to-end 검증 가능.
- 실행: `& "C:\Users\Moel\rag_test\.venv\Scripts\python.exe" tests/make_notice.py`
- 금액/기관/문구 바꿔서 변형 생성 가능.

---

## 9. 환경 메모 (중요)
- **venv**: `C:\Users\Moel\rag_test\.venv` (프로젝트와 분리). python 전체경로로 호출.
  - 이번에 추가 설치: `qrcode` (QR 생성용).
- PATH의 `python`은 MS Store 스텁이라 `-m` 안 됨 → venv python 전체경로 사용.
- 포트 8000(백엔드) 정리: PowerShell
  `Get-NetTCPConnection -LocalPort 8000 -State Listen | %{ Stop-Process -Id $_.OwningProcess -Force }`
  (※ 다른 세션 백엔드일 수 있어 강제종료는 주의)
- cloudflared 경로: `C:\Users\Moel\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe`

---

## 10. DEV 전용 (배포 전 삭제)
`index.html` 하단에 화면 전환 바(🏠 홈 / ⏳ 분석중 / ✅ 결과)와 `devShowResult()`(샘플 데이터로 결과 화면 미리보기)가 있음. 주석 `DEV ONLY ~ /DEV ONLY` 블록 2곳(HTML+JS) 통째로 지우면 원복.

---

## 11. 남은 일 / 다음에 볼 것
- [ ] 백엔드에 `glossary` 필드 추가 → 단어 풀이 칩 실데이터 연동.
- [ ] 백엔드 corpus에 `phone`/`visit` 채워지면 전화·지도 버튼 활성화됨.
- [ ] 정식 카카오톡 공유(Kakao JS SDK + 앱키) 필요 시 교체.
- [ ] 배포 전 DEV 바 제거.
- [ ] 상시 고정 주소가 필요하면 cloudflared 네임드 터널(계정 로그인)로 전환.
