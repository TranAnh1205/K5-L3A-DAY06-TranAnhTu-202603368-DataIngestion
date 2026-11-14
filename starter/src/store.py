"""Persistent Qdrant local store with exact cosine search and section filtering."""

from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from .models import Chunk


class LocalQdrantStore:
    def __init__(self, path: Path, dimensions: int) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.path = path
        self.dimensions = dimensions
        path.mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=str(path))

    @staticmethod
    def collection_for(strategy: str) -> str:
        if strategy not in {"A", "B", "C"}:
            raise ValueError(f"Unknown strategy: {strategy}")
        # C changes only retrieval filtering and reuses B's identical chunks/vectors.
        return "day06_fixed_a" if strategy == "A" else "day06_sentences_b"

    def replace(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Upsert stable IDs, then remove chunks absent from the current corpus."""
        if strategy not in {"A", "B"}:
            raise ValueError("Only A and B need indexing; C uses B's collection")
        if len(chunks) != len(vectors) or not chunks:
            raise ValueError("Need one vector per nonempty chunk")
        if any(len(vector) != self.dimensions for vector in vectors):
            raise ValueError("Embedding dimension mismatch")
        collection = self.collection_for(strategy)
        if not self.client.collection_exists(collection):
            self.client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(size=self.dimensions, distance=models.Distance.COSINE),
            )
        else:
            config = self.client.get_collection(collection).config.params.vectors
            if config.size != self.dimensions or config.distance != models.Distance.COSINE:
                raise ValueError(f"Existing collection {collection} has incompatible vector settings")
        wanted_ids = {str(uuid5(NAMESPACE_URL, chunk.chunk_id)) for chunk in chunks}
        old_ids = set()
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=collection, offset=offset, limit=100,
                with_payload=False, with_vectors=False,
            )
            old_ids.update(str(point.id) for point in points)
            if offset is None:
                break
        for start in range(0, len(chunks), 100):
            points = []
            for chunk, vector in zip(chunks[start : start + 100], vectors[start : start + 100]):
                payload = {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "source": chunk.source,
                    "page": chunk.page,
                    "text": chunk.text,
                    **chunk.metadata,
                }
                points.append(models.PointStruct(id=str(uuid5(NAMESPACE_URL, chunk.chunk_id)), vector=vector, payload=payload))
            self.client.upsert(collection_name=collection, points=points, wait=True)
        stale = sorted(old_ids - wanted_ids)
        for start in range(0, len(stale), 100):
            self.client.delete(
                collection_name=collection,
                points_selector=models.PointIdsList(points=stale[start : start + 100]),
                wait=True,
            )

    def count(self, strategy: str) -> int:
        return self.client.count(collection_name=self.collection_for(strategy), exact=True).count

    def search(
        self, strategy: str, query_vector: list[float], top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if len(query_vector) != self.dimensions:
            raise ValueError("Query embedding dimension mismatch")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if filters and set(filters) != {"section"}:
            raise ValueError("Only the trusted section metadata filter is supported")
        condition = None
        if filters:
            condition = models.Filter(
                must=[models.FieldCondition(key="section", match=models.MatchValue(value=filters["section"]))]
            )
        result = self.client.query_points(
            collection_name=self.collection_for(strategy),
            query=query_vector,
            query_filter=condition,
            limit=top_k,
            with_payload=True,
        )
        return [
            {"chunk_id": p.payload["chunk_id"], "text": p.payload["text"], "score": p.score,
             "metadata": {k: v for k, v in p.payload.items() if k != "text"}}
            for p in result.points
        ]

    def close(self) -> None:
        self.client.close()
