"""rag.py 하이브리드 매칭 평가 하네스.

fastapi/Gemini/Vision 없이 RAG 파이프라인만 점검·평가한다.
- PoC 3종(기초연금/본인부담상한제 환급/에너지바우처): top-1 정답 요구
- 신호 강제포함 케이스: 기대 정책이 top-k 안에 있어야 통과
- 엣지(무관 문서): 빈 결과(친절 안내) 기대

실행 (venv python):
    C:\\Users\\Moel\\rag_test\\.venv\\Scripts\\python.exe tests\\test_rag_runtime.py
"""

import asyncio
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# 프로젝트 루트를 import 경로에 추가 (app.* 모듈 해석용)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.schemas import DocumentAnalysis  # noqa: E402
from app.services.rag import RAGEngine  # noqa: E402


@dataclass
class Case:
    label: str
    analysis: DocumentAnalysis
    expect_top1: str = ""            # 이 id 가 1위여야 통과
    expect_in_topk: set = field(default_factory=set)  # 이 id 들이 top-k 안에 있어야 통과
    expect_empty: bool = False       # 결과가 비어 있어야 통과(무관 문서)


CASES: list[Case] = [
    # ── PoC 3종: top-1 정답 요구 ──
    Case(
        "PoC① 기초연금 안내문",
        DocumentAnalysis(
            doc_type="기초연금 신청 안내",
            sender="보건복지부",
            summary="만 65세 이상 어르신 기초연금 신청 안내입니다.",
            key_points=["만 65세 이상", "소득 하위 70%", "매달 연금 지급"],
            required_actions=["주민센터 방문 신청"],
        ),
        expect_top1="policy-001",
    ),
    Case(
        "PoC② 본인부담상한액 초과금 환급 안내",
        DocumentAnalysis(
            doc_type="본인부담상한액 초과금 지급 안내",
            sender="국민건강보험공단",
            summary="작년 한 해 납부한 본인부담 의료비가 상한액을 넘어 초과금을 돌려드립니다.",
            key_points=["본인부담상한제", "의료비 환급", "지급 신청서"],
            required_actions=["지급 신청서 작성·제출"],
        ),
        expect_top1="policy-002",
    ),
    Case(
        "PoC③ 난방비(에너지바우처) 안내",
        DocumentAnalysis(
            doc_type="에너지 지원 안내",
            sender="주민센터",
            summary="겨울철 난방비를 지원하는 에너지바우처 안내입니다.",
            key_points=["난방", "취약계층 에너지 지원", "바우처"],
            required_actions=["바우처 신청"],
        ),
        expect_top1="policy-003",
    ),
    # ── 신호 강제포함 케이스: 기대 정책이 top-k 안에 ──
    Case(
        "건강보험료 고지서",
        DocumentAnalysis(
            doc_type="건강보험료 고지서",
            sender="국민건강보험공단",
            summary="이번 달 지역가입자 건강보험료 납부 안내 고지서입니다.",
            key_points=["지역가입자 건강보험료", "납부 기한"],
            required_actions=["보험료 납부", "경감 대상 여부 확인"],
        ),
        expect_in_topk={"policy-004"},
    ),
    Case(
        "장기요양 인정 안내",
        DocumentAnalysis(
            doc_type="장기요양인정 안내",
            sender="국민건강보험공단",
            summary="어르신 장기요양등급 판정 및 방문요양 이용 안내입니다.",
            key_points=["장기요양등급", "방문요양"],
            required_actions=["장기요양 인정 신청"],
        ),
        expect_in_topk={"policy-005"},
    ),
    Case(
        "치매 치료관리비 안내",
        DocumentAnalysis(
            doc_type="치매 치료관리비 지원 안내",
            sender="보건소 치매안심센터",
            summary="치매로 진단받은 어르신의 약값·진료비를 지원합니다.",
            key_points=["치매", "치료관리비", "약값"],
            required_actions=["치매안심센터 신청"],
        ),
        expect_in_topk={"policy-013"},
    ),
    Case(
        "치과 임플란트·틀니 안내",
        DocumentAnalysis(
            doc_type="어르신 치과 건강보험 안내",
            sender="치과의원",
            summary="만 65세 이상 임플란트·틀니 건강보험 적용 안내입니다.",
            key_points=["임플란트", "틀니", "건강보험 적용"],
            required_actions=["치과에서 건강보험 적용 신청"],
        ),
        expect_in_topk={"policy-016"},
    ),
    Case(
        "전기요금 고지서(복지할인)",
        DocumentAnalysis(
            doc_type="전기요금 청구서",
            sender="한국전력공사",
            summary="이번 달 전기요금 청구 안내입니다. 복지할인 대상 여부를 확인하세요.",
            key_points=["전기요금", "복지할인"],
            required_actions=["전기요금 납부"],
        ),
        expect_in_topk={"policy-018"},
    ),
    # ── 엣지: 무관 문서는 빈 결과(친절 안내) 기대 ──
    Case(
        "무관 문서(택배 배송 안내)",
        DocumentAnalysis(
            doc_type="택배 배송 안내",
            sender="○○택배",
            summary="고객님의 상품이 내일 도착 예정입니다. 부재 시 경비실에 보관됩니다.",
            key_points=["배송 예정", "운송장 번호"],
            required_actions=["수령 확인"],
        ),
        expect_empty=True,
    ),
]


async def main() -> int:
    os.chdir(ROOT)  # corpus_path 상대경로 보정

    engine = RAGEngine()
    print("[1] 모델 로드 + corpus 임베딩 + Chroma 적재 시작...")
    await engine.load()
    if not engine.ready:
        print("!! engine.ready == False — 로드 실패")
        return 1
    print(f"[2] 적재 완료. 정책 {len(engine.policies)}건.\n")

    passed = 0
    for c in CASES:
        matches = await engine.match(c.analysis)
        ids = [m.id for m in matches]
        top1 = ids[0] if ids else None

        if c.expect_empty:
            ok = len(matches) == 0
            want = "빈 결과"
        elif c.expect_top1:
            ok = top1 == c.expect_top1
            want = f"top1={c.expect_top1}"
        else:
            ok = c.expect_in_topk.issubset(set(ids))
            want = f"top-k⊇{sorted(c.expect_in_topk)}"

        passed += ok
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {c.label}  (기대: {want})")
        for m in matches:
            print(f"        [{m.score:.4f}] {m.id}  {m.title}")
        if not matches:
            print("        (매칭 없음 → 프론트: '관련 혜택을 찾지 못했어요' 안내)")
        print()

    total = len(CASES)
    print(f">>> 결과: {passed}/{total} 통과")
    return 0 if passed == total else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
