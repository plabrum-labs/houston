"""Embedding client dependency — app-injected singleton.

The concrete client (provider selection) is wired by the app at startup via
`set_embedding_client()` — mirrors `events.set_queue_resolver` in this
same module. The platform ships no concrete provider; the app builds a
`BaseEmbeddingClient` (e.g. an `LLMEmbeddingClient` over its LLM client, deferred
with the `llm` port) and injects it.
"""

from __future__ import annotations

from app.platform.embeddings.client import BaseEmbeddingClient
from app.platform.utils.deps import dep

# Client set by the app at startup via set_embedding_client().
_embedding_client: BaseEmbeddingClient | None = None


def set_embedding_client(client: BaseEmbeddingClient | None) -> None:
    global _embedding_client
    _embedding_client = client


@dep("embedding_client")
def provide_embedding_client() -> BaseEmbeddingClient:
    return get_embedding_client()


def get_embedding_client() -> BaseEmbeddingClient:
    """For tasks that don't go through Litestar DI."""
    if _embedding_client is None:
        raise RuntimeError(
            "embeddings is not configured — call app.platform.embeddings.deps.set_embedding_client(client) at startup",
        )
    return _embedding_client
