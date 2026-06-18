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

혜택 정책 코퍼스. **공개 정책정보만 사용**(개인정보·민감정보 없음). 현재 **100건** — 노인 중심에서 장애인·보훈·아동·보육·청년·임산부·한부모·다문화·서민금융·주거·고용·농어업·생활안전(재난·화재·범죄피해·정신건강)까지 전 국민 범위로 확장(기획서 "전 국민 대상 확장" 방향).

**스키마(확장):** 기존 9필드(`id,title,summary,eligibility,benefit,category,keywords,apply,source`) + 하이브리드 검색용 `signals`(강제포함 트리거), `region`/`age_min`(조건필터), `priority`(정렬 가중), `source_url`(출처 URL).

**공개 출처 포털(항목별 `source_url`에 기록):**
| 출처 | URL | 해당 정책 예 |
|---|---|---|
| 복지로 | bokjiro.go.kr | 기초연금·생계/주거급여·돌봄·문화 등 |
| 보조금24(정부24) | gov24.go.kr | 통신요금 감면 등 |
| 국민건강보험공단 | nhis.or.kr | 본인부담상한제·건강보험료 경감·재난적의료비·임플란트·보청기 |
| 노인장기요양보험 | longtermcare.or.kr | 노인장기요양보험 |
| 한국에너지공단(에너지바우처) | energyv.or.kr | 에너지바우처 |
| 한국전력 | kepco.co.kr | 전기요금 복지할인 |
| 문화누리 | mnuri.kr | 통합문화이용권 |
| 한국장애인개발원·활동지원 | koddi.or.kr · ableservice.or.kr | 장애수당·활동지원·발달재활 등 |
| 국가보훈부 | mpva.go.kr | 보훈대상자 의료·수당 |
| 국토교통부·주택기금 | molit.go.kr · nhuf.molit.go.kr | 공공임대·디딤돌·버팀목 |
| 고용노동부 고용센터 | work24.go.kr · ei.go.kr | 국민취업지원·실업급여·내일배움카드 |
| 국세청 홈택스 | hometax.go.kr | 근로·자녀장려금 |
| 여성가족부 | mogef.go.kr | 한부모·다문화·청소년 |
| 서민금융진흥원 | kinfa.or.kr | 햇살론·미소금융 |
| 농림축산식품부·농지연금·농협 | mafra.go.kr · fnp.or.kr · nonghyup | 농어업인 안전보험·농지연금 |
| 국민연금공단 | nps.or.kr | 농어업인 연금보험료 지원 |
| 국민재난안전포털·소방청 | safekorea.go.kr · nfa.go.kr | 재난지원금·풍수해보험·주택 소방시설 |
| 노인의료나눔재단 | ok6595.or.kr | 무릎인공관절 수술 지원 |

> ⚠️ **금액·소득기준 등 수치는 연도별로 변동**한다. 코퍼스의 금액은 2025년 기준 근사값이며, **대회 본선 전 각 포털에서 최신 수치 검증 필요**. (기획서 "검증된 정책 데이터만 참조" 원칙)

## 4. AI 활용 내역 (개발 도구)

| 도구 | 용도 |
|---|---|
| Claude Code | 백엔드 코드 생성·점검, 문서(README/SOURCE_LOG) 작성, git 작업 |
| Codex (예정) | 기획서상 활용 명시 — 사용 시 기록 |

## 5. 더미/합성 데이터

- 시연용 서류 샘플은 **전부 가공 데이터**(가공 인명·임의 번호). 실제 PII 미사용.
- (작성 시 이 절에 샘플 목록 추가)
