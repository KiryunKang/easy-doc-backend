"""rag.py 런타임 단독 검증 스크립트.

fastapi/Gemini/Vision 없이 RAG 파이프라인만 점검한다.
실행: hackathon 폴더에서 venv python 으로
    py 기준이 아니라 venv python:
    C:\\Users\\Moel\\rag_test\\.venv\\Scripts\\python.exe tests\\test_rag_runtime.py
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 import 경로에 추가 (app.* 모듈 해석용)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.schemas import DocumentAnalysis  # noqa: E402
from app.services.rag import RAGEngine  # noqa: E402


SAMPLE_CASES = [
    (
        "건강보험 고지서",
        DocumentAnalysis(
            doc_type="건강보험료 고지서",
            sender="국민건강보험공단",
            summary="이번 달 건강보험료 납부 안내 고지서입니다.",
            key_points=["지역가입자 건강보험료", "납부 기한 안내"],
            required_actions=["보험료 납부", "경감 대상 여부 확인"],
        ),
    ),
    (
        "기초연금 안내문",
        DocumentAnalysis(
            doc_type="기초연금 신청 안내",
            sender="보건복지부",
            summary="만 65세 이상 어르신 기초연금 신청 안내입니다.",
            key_points=["65세 이상", "소득 하위 70%"],
            required_actions=["주민센터 방문 신청"],
        ),
    ),
    (
        "난방비 지원 안내",
        DocumentAnalysis(
            doc_type="에너지 지원 안내",
            sender="주민센터",
            summary="겨울철 난방비를 지원하는 바우처 안내입니다.",
            key_points=["난방", "취약계층 에너지 지원"],
            required_actions=["바우처 신청"],
        ),
    ),
]


async def main() -> int:
    # corpus_path 가 'data/corpus.json' 상대경로이므로 루트 기준으로 절대경로 보정
    import os

    os.chdir(ROOT)

    engine = RAGEngine()
    print("[1] 모델 로드 + corpus 임베딩 + Chroma 적재 시작...")
    await engine.load()

    if not engine.ready:
        print("!! engine.ready == False — 로드 실패")
        return 1

    print(f"[2] 적재 완료. 정책 {len(engine.policies)}건. ready={engine.ready}\n")

    all_ok = True
    for label, analysis in SAMPLE_CASES:
        matches = await engine.match(analysis)
        print(f"--- 질의: {label} ---")
        if not matches:
            print("  (매칭 결과 없음)")
            all_ok = False
            continue
        for m in matches:
            print(f"  [{m.score:.4f}] {m.id}  {m.title}  ({m.category})")
        print()

    if all_ok:
        print(">>> RAG 런타임 검증 통과: 모든 질의에서 매칭 결과 반환됨.")
        return 0
    print(">>> 일부 질의에서 매칭 결과 없음 — 확인 필요.")
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
