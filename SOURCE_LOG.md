# SOURCE_LOG — 외부 코드·데이터·API 사용 내역

> 2026 AI챔피언 해커톤(드리미 팀) 제출용 출처 기록. 운영지침 ⑤(출처 명시)·12(제출 자료) 대응.
> **작업 진행에 맞춰 계속 갱신한다.** 외부 코드/템플릿/라이브러리/모델/데이터/API를 새로 도입할 때마다 그 자리에서 이 표에 추가한다.
> ⚠️ 본 레포는 **모의테스트(연습)** 산출물이다. 실제 대회 제출물은 대회 시작(2026-06-23) 이후 신규 저장소에서 새로 제작한다.

최종 갱신: 2026-06-18

---

## 1. 오픈소스 라이브러리 (requirements.txt)

| 라이브러리 | 용도 | 라이선스 | 비고 |
|---|---|---|---|
| FastAPI | 웹 프레임워크(async) | MIT | |
| uvicorn[standard] | ASGI 서버 | BSD-3-Clause | |
| python-multipart | 파일 업로드 파싱 | Apache-2.0 | |
| pydantic / pydantic-settings | 요청·응답 스키마, 환경설정 | MIT | |
| google-genai | Gemini API 클라이언트 | Apache-2.0 | |
| google-cloud-vision | Google Cloud Vision OCR 클라이언트 | Apache-2.0 | |
| sentence-transformers | 임베딩 생성 | Apache-2.0 | |
| chromadb | 벡터 DB(인메모리) | Apache-2.0 | |

> 라이선스는 통상 알려진 값 기준. 제출 전 각 패키지 배포 페이지에서 최종 확인 예정.

## 2. AI 모델 / 외부 API

| 항목 | 제공처 | 용도 | 비고 |
|---|---|---|---|
| Gemini 2.5 Flash | Google AI Studio (`google-genai`) | 문서 분석 · 쉬운말 번역 | API 키 필요(.env), 호출 비용 발생 |
| Google Cloud Vision | Google Cloud (`document_text_detection`) | OCR(사진→텍스트), 한국어 힌트 | 서비스계정 JSON 키 필요 |
| `jhgan/ko-sroberta-multitask` | HuggingFace (sentence-transformers) | 한국어 임베딩(RAG) | 로컬 실행·무료·오프라인. 라이선스 HF 페이지 확인 필요 |

> 기획서 원안은 OCR도 Gemini 멀티모달 사용이었으나, 현재 백엔드 구현은 OCR을 **Google Cloud Vision**으로 분리함. (구현 시점 결정 — 추후 통일 여부 검토)

## 3. 데이터 출처 (`data/corpus.json`)

혜택 정책 코퍼스. **공개 정책정보만 사용**(개인정보·민감정보 없음). 현재 샘플 4건:

| id | 정책 | 출처 기관 | 공개 출처 |
|---|---|---|---|
| policy-001 | 기초연금 | 보건복지부 | 복지로 bokjiro.go.kr |
| policy-002 | 노인장기요양보험 | 국민건강보험공단 | 복지로 / 건보공단 |
| policy-003 | 에너지바우처 | 산업통상자원부 | 복지로 |
| policy-004 | 건강보험료 경감(지역가입자) | 국민건강보험공단 | 건보공단 |

> 정식 코퍼스는 복지로·보조금24(gov24) 공개 정책정보를 큐레이션하여 확장 예정. 항목별 원문 URL을 이 표에 추가한다.

## 4. AI 활용 내역 (개발 도구)

| 도구 | 용도 |
|---|---|
| Claude Code | 백엔드 코드 생성·점검, 문서(README/SOURCE_LOG) 작성, git 작업 |
| Codex (예정) | 기획서상 활용 명시 — 사용 시 기록 |

## 5. 더미/합성 데이터

- 시연용 서류 샘플은 **전부 가공 데이터**(가공 인명·임의 번호). 실제 PII 미사용.
- (작성 시 이 절에 샘플 목록 추가)
