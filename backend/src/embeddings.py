import os
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np
from dotenv import load_dotenv

load_dotenv()


class BaseEmbeddingService(ABC):
    """Abstract Base Class for all EcoRAG embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality of the embedding model."""
        pass

    @property
    @abstractmethod
    def provider(self) -> str:
        """Provider name: 'cloud' or 'local'."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Embed a single string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of strings."""
        pass

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two embedding vectors."""
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


class GeminiEmbeddingService(BaseEmbeddingService):
    """
    Cloud Embedding service utilizing Google Gemini Embedding models via google.genai SDK.
    Supported models:
      - 'gemini-embedding-001' (3072 dimensions)
      - 'gemini-embedding-2'   (3072 dimensions)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-embedding-001",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please add it to your .env file or pass it to GeminiEmbeddingService."
            )
        self.model_name = model_name
        from google import genai
        self.client = genai.Client(api_key=self.api_key)
        self._dim = 3072

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def provider(self) -> str:
        return "cloud-gemini"

    def embed_text(self, text: str) -> List[float]:
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=text,
        )
        return response.embeddings[0].values

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            emb = self.embed_text(text)
            embeddings.append(emb)
        return embeddings


class LocalEmbeddingService(BaseEmbeddingService):
    """
    Local Embedding service using sentence-transformers.
    Supported standard models:
      - 'all-MiniLM-L6-v2' (384 dimensions, ultra-fast CPU)
      - 'BAAI/bge-small-en-v1.5' (384 dimensions, high accuracy)
      - 'BAAI/bge-base-en-v1.5' (768 dimensions)
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.device = device
        self.model = SentenceTransformer(model_name, device=device)
        if hasattr(self.model, "get_embedding_dimension"):
            self._dim = self.model.get_embedding_dimension()
        else:
            self._dim = self.model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def provider(self) -> str:
        return "local-sentence-transformers"

    def embed_text(self, text: str) -> List[float]:
        vec = self.model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        vecs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32)
        return vecs.tolist()
