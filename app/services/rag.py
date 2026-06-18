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
        # 스키마 계약(B→A) 임베딩 공식:
        # name | category | 대상:eligibility | keywords | 관련문서:related_doc_types
        related = ", ".join(p.get("related_doc_types", []) or [])
        return (
            f"{p.get('name', '')} | {p.get('category', '')} "
            f"| 대상:{p.get('eligibility', '')} | {p.get('keywords', '')} "
            f"| 관련문서:{related}"
        )

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

    async def match(self, analysis: DocumentAnalysis) -> list[MatchedPolicy]:
        if not self.ready or not self.policies:
            return []

        query = " ".join(
            [
                analysis.doc_type,
                analysis.summary,
                " ".join(analysis.key_points),
                " ".join(analysis.required_actions),
            ]
        ).strip()
        if not query:
            return []

        return await asyncio.to_thread(self._query, query, analysis.doc_type)

    # priority 정렬용 가중치 (high 가 상단)
    _PRIORITY_RANK = {"high": 2, "medium": 1, "low": 0}
    _DOC_TYPE_BOOST = 0.15  # 입력 고지서 종류가 related_doc_types 와 겹칠 때 가점

    def _query(self, query: str, doc_type: str) -> list[MatchedPolicy]:
        settings = get_settings()
        threshold = settings.rag_score_threshold
        k = settings.rag_top_k

        q_emb = self._model.encode([query], normalize_embeddings=True).tolist()
        # 전체에서 검색 후 컷·가점·정렬 (corpus 가 작아 비용 무시 가능)
        res = self._collection.query(
            query_embeddings=q_emb, n_results=len(self.policies)
        )
        distances = res["distances"][0]
        metadatas = res["metadatas"][0]

        scored: list[tuple[dict, float]] = []
        for dist, meta in zip(distances, metadatas):
            policy = self.policies[int(meta["idx"])]
            # cosine space: distance = 1 - cosine_similarity (정규화 벡터 기준)
            score = 1.0 - float(dist)

            # 입력 문서종류가 related_doc_types 와 겹치면 가점 + 강제포함
            forced = self._doc_type_overlap(doc_type, policy)
            if forced:
                score += self._DOC_TYPE_BOOST

            # 유사도 컷 (단, 문서종류 매칭건은 강제포함)
            if score < threshold and not forced:
                continue
            scored.append((policy, score))

        # 정렬: 유사도 → (동점 시) priority(high>medium>low)
        scored.sort(
            key=lambda ps: (
                ps[1],
                self._PRIORITY_RANK.get(ps[0].get("priority", "medium"), 1),
            ),
            reverse=True,
        )
        return [self._to_policy(p, s) for p, s in scored[:k]]

    @staticmethod
    def _doc_type_overlap(doc_type: str, policy: dict) -> bool:
        doc_type = (doc_type or "").strip()
        if not doc_type:
            return False
        for rdt in policy.get("related_doc_types", []) or []:
            rdt = (rdt or "").strip()
            if rdt and (rdt in doc_type or doc_type in rdt):
                return True
        return False

    @staticmethod
    def _to_policy(p: dict, score: float) -> MatchedPolicy:
        return MatchedPolicy(
            id=str(p.get("id", "")),
            name=p.get("name", ""),
            category=p.get("category", ""),
            eligibility=p.get("eligibility", ""),
            amount=p.get("amount", ""),
            how_to_apply=p.get("how_to_apply", ""),
            phone=p.get("phone", ""),
            visit=p.get("visit", ""),
            source=p.get("source", ""),
            priority=p.get("priority", "medium"),
            score=round(min(score, 1.0), 4),
        )


@lru_cache
def get_engine() -> RAGEngine:
    return RAGEngine()
