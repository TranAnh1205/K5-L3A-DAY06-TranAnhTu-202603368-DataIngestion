"""Local semantic embeddings using Qdrant's FastEmbed model registry."""
from typing import Protocol
from fastembed import TextEmbedding


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Real 384-dimensional English embeddings, with no mock fallback."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model_name = model_name
        if model_name != "BAAI/bge-small-en-v1.5":
            raise ValueError("This lab adapter is configured for BAAI/bge-small-en-v1.5 only")
        self.model = TextEmbedding(model_name=model_name)
        self.dimensions = 384

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.model.passage_embed(texts, batch_size=32)]

    def embed_query(self, question: str) -> list[float]:
        return next(iter(self.model.query_embed(question))).tolist()
