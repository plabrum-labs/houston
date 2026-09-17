"""Embedding clients — one per provider, swappable behind BaseEmbeddingClient."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.platform.llm.client import BaseLLMClient

logger = logging.getLogger(__name__)


class BaseEmbeddingClient(ABC):
    model: str
    dim: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbeddingClient(BaseEmbeddingClient):
    """Dev/test stub — returns deterministic zero vectors."""

    model = "local-dev"
    dim = 1536

    async def embed(self, texts: list[str]) -> list[list[float]]:
        logger.info(f"[dev] embed called for {len(texts)} input(s) — returning zero vectors")
        return [[0.0] * self.dim for _ in texts]


class LLMEmbeddingClient(BaseEmbeddingClient):
    """Delegates to a BaseLLMClient's embed capability.

    Keeps the embeddings module's surface narrow (model/dim/embed) while letting
    provider selection live entirely in llm/deps.py — swap the underlying LLM
    client and embeddings follow.
    """

    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm = llm_client
        self.model = llm_client.embedding_model
        self.dim = llm_client.embedding_dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self._llm.embed(texts)
