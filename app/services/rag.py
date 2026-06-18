import asyncio
import json
from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.schemas import DocumentAnalysis, MatchedPolicy


class RAGEngine:
    """corpus.json 의 혜택 정책을 로컬 한국어 임베딩(ko-sroberta) + ChromaDB 로 매칭.

    시작 시 corpus 를 임베딩해 인메모리 Chroma 컬렉션에 적재하고,
    요청마다 질의 임베딩으로 코사인 유사도 상위 K건을 반환한다.
    """

    def __init__(self) -> None:
        self.policies: list[dict] = []
        self._model = None  # SentenceTransformer (지연 로드)
        self._collection = None  # chromadb collection
        self.ready: bool = False

    @staticmethod
    def _policy_text(p: dict) -> str:
        parts = [
            p.get("title", ""),
            p.get("summary", ""),
            p.get("eligibility", ""),
            p.get("category", ""),
            " ".join(p.get("keywords", []) or []),
        ]
        return " ".join(x for x in parts if x)

    async def load(self) -> None:
        settings = get_settings()
        path = Path(settings.corpus_path)
        if not path.exists():
            print(f"[RAG] corpus 파일 없음: {path} — 정책 매칭은 코퍼스 제공 후 활성화됩니다.")
            self.policies = []
            return

        self.policies = json.loads(path.read_text(encoding="utf-8"))
        if not self.policies:
            print("[RAG] corpus 가 비어 있습니다.")
            return

        # 무거운 의존성은 여기서 지연 로드
        import chromadb
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(settings.embedding_model)

        client = chromadb.EphemeralClient()
        self._collection = client.get_or_create_collection(
            name="policies", metadata={"hnsw:space": "cosine"}
        )

        texts = [self._policy_text(p) for p in self.policies]
        embeddings = self._model.encode(
            texts, normalize_embeddings=True
        ).tolist()
        # id 는 인덱스 기반으로 고유성 보장, 실제 정책은 metadata.idx 로 역참조
        self._collection.add(
            ids=[f"doc-{i}" for i in range(len(self.policies))],
            embeddings=embeddings,
            documents=texts,
            metadatas=[{"idx": i} for i in range(len(self.policies))],
        )
        self.ready = True
        print(
            f"[RAG] 정책 {len(self.policies)}건 → "
            f"{settings.embedding_model} 임베딩 → Chroma 적재 완료."
        )

    @staticmethod
    def _norm(s: str) -> str:
        """부분문자열 매칭용 정규화: 소문자화 + 공백 제거."""
        return "".join(str(s).lower().split())

    async def match(self, analysis: DocumentAnalysis) -> list[MatchedPolicy]:
        if not self.ready or not self.policies:
            return []

        query = " ".join(
            [
                analysis.doc_type,
                analysis.sender,
                analysis.summary,
                " ".join(analysis.key_points),
                " ".join(analysis.required_actions),
            ]
        ).strip()
        if not query:
            return []

        settings = get_settings()
        return await asyncio.to_thread(
            self._query, query, settings.rag_top_k, settings.rag_min_score
        )

    def _query(self, query: str, k: int, min_score: float) -> list[MatchedPolicy]:
        """하이브리드 매칭: 벡터(임계값) + 신호 강제포함 + 키워드 폴백 + 부적합 제외,
        정렬은 우선순위(priority) → 유사도(score)."""
        # 1) 모든 정책에 대한 코사인 유사도 확보 (25건 수준이라 전수 조회 부담 없음)
        q_emb = self._model.encode([query], normalize_embeddings=True).tolist()
        res = self._collection.query(
            query_embeddings=q_emb, n_results=len(self.policies)
        )
        # idx -> similarity (cosine space: distance = 1 - cos_sim, 정규화 벡터 기준)
        sims: dict[int, float] = {}
        for dist, meta in zip(res["distances"][0], res["metadatas"][0]):
            sims[int(meta["idx"])] = 1.0 - float(dist)

        q_norm = self._norm(query)

        # 2) 후보 분류: 임계값 통과 / 신호 강제포함 / 부적합 제외
        # 항목: (idx, score, signal_hit)
        threshold_or_signal: list[tuple[int, float, bool]] = []
        keyword_fallback: list[tuple[int, float, bool]] = []
        for idx, policy in enumerate(self.policies):
            score = sims.get(idx, 0.0)

            # 부적합 강제제외: exclude_if 토큰이 질의에 있으면 컷
            if any(self._norm(x) in q_norm for x in policy.get("exclude_if", []) or []):
                continue

            signal_hit = any(
                self._norm(s) in q_norm for s in policy.get("signals", []) or []
            )
            if score >= min_score or signal_hit:
                threshold_or_signal.append((idx, score, signal_hit))
                continue

            # 임계값·신호 미달이지만 키워드가 질의에 있으면 폴백 후보로 보관
            if any(self._norm(kw) in q_norm for kw in policy.get("keywords", []) or []):
                keyword_fallback.append((idx, score, False))

        # 3) 1차(임계값/신호)가 비면 키워드 폴백 사용, 그래도 없으면 빈 결과
        selected = threshold_or_signal or keyword_fallback
        if not selected:
            return []

        # 4) 랭킹: 유사도 중심 + 신호 가산점(강) + priority 가산점(약 tiebreak).
        #    관련도(score)가 주이고, 신호/우선순위는 동급 후보 사이를 가르는 보정.
        def rank(item: tuple[int, float, bool]) -> float:
            idx, score, signal_hit = item
            priority = int(self.policies[idx].get("priority", 5))
            return score + (0.20 if signal_hit else 0.0) + (5 - min(priority, 5)) * 0.02

        selected.sort(key=rank, reverse=True)

        # 표시 score 는 보정 전 원본 유사도 유지
        return [self._to_policy(self.policies[idx], score) for idx, score, _ in selected[:k]]

    @staticmethod
    def _to_policy(p: dict, score: float) -> MatchedPolicy:
        return MatchedPolicy(
            id=str(p.get("id", "")),
            title=p.get("title", ""),
            summary=p.get("summary", ""),
            eligibility=p.get("eligibility", ""),
            benefit=p.get("benefit", ""),
            apply=p.get("apply", ""),
            category=p.get("category", ""),
            source=p.get("source", ""),
            score=round(score, 4),
        )


@lru_cache
def get_engine() -> RAGEngine:
    return RAGEngine()
