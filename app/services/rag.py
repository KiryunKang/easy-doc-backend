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

        k = get_settings().rag_top_k
        return await asyncio.to_thread(self._query, query, k)

    def _query(self, query: str, k: int) -> list[MatchedPolicy]:
        q_emb = self._model.encode([query], normalize_embeddings=True).tolist()
        res = self._collection.query(
            query_embeddings=q_emb, n_results=min(k, len(self.policies))
        )
        ids = res["ids"][0]
        distances = res["distances"][0]
        metadatas = res["metadatas"][0]

        out: list[MatchedPolicy] = []
        for _id, dist, meta in zip(ids, distances, metadatas):
            idx = int(meta["idx"])
            policy = self.policies[idx]
            # cosine space: distance = 1 - cosine_similarity (정규화 벡터 기준)
            score = 1.0 - float(dist)
            out.append(self._to_policy(policy, score))
        return out

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
