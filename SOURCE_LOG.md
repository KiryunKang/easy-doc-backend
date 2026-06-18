# SOURCE_LOG — 외부 코드·데이터·API 사용 내역

> 2026 AI챔피언 해커톤(드리미 팀) 제출용 출처 기록. 운영지침 ⑤(출처 명시)·12(제출 자료) 대응.
> **작업 진행에 맞춰 계속 갱신한다.** 외부 코드/템플릿/라이브러리/모델/데이터/API를 새로 도입할 때마다 그 자리에서 이 표에 추가한다.
> ⚠️ 본 레포는 **모의테스트(연습)** 산출물이다. 실제 대회 제출물은 대회 시작(2026-06-23) 이후 신규 저장소에서 새로 제작한다.
> 역할 분담: 데이터(코퍼스)는 데이터 담당, 백엔드/RAG 로직(`app/services/rag.py` 등)은 백엔드 담당.

최종 갱신: 2026-06-18

---

## 1. 오픈소스 라이브러리 (requirements.txt)

| 라이브러리 | 용도 | 라이선스 | 비고 |
|---|---|---|---|
| FastAPI | 웹 프레임워크(async) | MIT | |
| uvicorn[standard] | ASGI 서버 | BSD-3-Clause | |
| python-multipart | 파일 업로드 파싱 | Apache-2.0 | |
| pydantic / pydantic-settings | 요청·응답 스키마, 환경설정 | MIT | |
| google-genai | Gemini API 클라이언트 | Apache-2.0 | OCR·분석·번역 모두 사용 |
| sentence-transformers | 임베딩 생성 | Apache-2.0 | |
| chromadb | 벡터 DB(인메모리) | Apache-2.0 | |

> 라이선스는 통상 알려진 값 기준. 제출 전 각 패키지 배포 페이지에서 최종 확인 예정.

## 2. AI 모델 / 외부 API

| 항목 | 제공처 | 용도 | 비고 |
|---|---|---|---|
| Gemini 2.5 Flash | Google AI Studio (`google-genai`) | **OCR(멀티모달)** · 문서 분석 · 쉬운말 번역 | API 키 필요(.env), 호출 비용 발생 |
| `jhgan/ko-sroberta-multitask` | HuggingFace (sentence-transformers) | 한국어 임베딩(RAG) | 로컬 실행·무료·오프라인. 라이선스 HF 페이지 확인 필요 |

> OCR 스택 변경 이력: 초기 Google Cloud Vision → **Gemini 2.5 Flash 멀티모달로 통일**(키 1개로 OCR·분석·번역 일원화, 기획서 원안과 일치). `google-cloud-vision` 의존성 제거됨.

## 3. 데이터 출처 (`data/corpus.json`)

혜택 정책 코퍼스. **공개 정책정보만 사용**(개인정보·민감정보 없음). 현재 **100건** — 노인 중심에서 장애인·보훈·아동·보육·청년·임산부·한부모·다문화·서민금융·주거·고용·농어업·생활안전(재난·화재·범죄피해·정신건강)까지 전 국민 범위로 확장(기획서 "전 국민 대상 확장" 방향).

**스키마 (팀원 B→A 계약, 12필드):** `id, name, category, eligibility, keywords, related_doc_types, amount, how_to_apply, phone, visit, source, priority`.
- 임베딩 대상: `name | category | 대상:eligibility | keywords | 관련문서:related_doc_types`
- `related_doc_types`: 입력 문서종류와 겹치면 RAG에서 가점·강제포함 (데이터로 매칭 정확도 견인)
- `phone`(tel: 버튼)·`visit`(지도 검색) : 어르신 행동유도용. 전 100건 채움(공개된 기관 대표번호·방문처).
- `source`: 정책 소관기관(아래 출처 포털과 대응).

**공개 출처 포털 (데이터 출처 = provenance):**
| 출처 | URL | 해당 정책 예 |
|---|---|---|
| 복지로 | bokjiro.go.kr | 기초연금·생계/주거급여·돌봄·문화 등 |
| 보조금24(정부24) | gov.kr | 각종 보조금·증명 안내 |
| 국민건강보험공단 | nhis.or.kr | 본인부담상한제·건강보험료 경감·재난적의료비·임플란트·보청기 |
| 노인장기요양보험 | longtermcare.or.kr | 노인장기요양보험 |
| 한국에너지공단(에너지바우처) | energyv.or.kr | 에너지바우처 |
| 한국전력 | kepco.co.kr | 전기요금 복지할인 |
| 문화누리 | mnuri.kr | 통합문화이용권 |
| 한국장애인개발원·활동지원 | koddi.or.kr · ableservice.or.kr | 장애수당·활동지원·발달재활 등 |
| 국가보훈부 | mpva.go.kr | 보훈대상자 의료·수당 |
| 국토교통부·주택기금·LH | molit.go.kr · nhuf.molit.go.kr · lh.or.kr | 공공임대·디딤돌·버팀목 |
| 고용노동부 고용센터 | work24.go.kr · ei.go.kr | 국민취업지원·실업급여·내일배움카드 |
| 국세청 홈택스 | hometax.go.kr | 근로·자녀장려금 |
| 여성가족부 | mogef.go.kr | 한부모·다문화·청소년 |
| 서민금융진흥원 | kinfa.or.kr | 햇살론·미소금융 |
| 농림축산식품부·농지연금·농협 | mafra.go.kr · 농어촌공사 · nonghyup | 농어업인 안전보험·농지연금 |
| 국민연금공단 | nps.or.kr | 기초연금 상담·농어업인 연금보험료 지원 |
| 국민재난안전포털·소방청 | safekorea.go.kr · nfa.go.kr | 재난지원금·풍수해보험·주택 소방시설 |

> ⚠️ **금액·소득기준 등 수치는 변동**한다. 코퍼스 수치는 2025년 기준 근사값이며, **대회 본선 전 각 포털에서 최신값 검증 필요**(기획서 "검증된 정책 데이터만 참조" 원칙). `phone` 번호도 제출 전 실통화 확인 권장.

## 4. AI 활용 내역 (개발 도구)

| 도구 | 용도 |
|---|---|
| Claude Code | 데이터(코퍼스) 생성·검증·필드 보강, 문서(SOURCE_LOG) 작성, git 작업 |

## 5. 더미/합성 데이터

- 시연용 서류 샘플은 **전부 가공 데이터**(가공 인명·임의 번호). 실제 PII 미사용.
- (작성 시 이 절에 샘플 목록 추가)
