"""LLM client dependencies — lazy process singletons, config-driven selection.

The clients are instantiated lazily (on first provide), not at module import, so
importing this module never constructs an Anthropic/OpenAI client (which reads the
API key off `config`) until one is actually selected.

The real provider classes are imported inside the getters, not at module scope,
so importing `llm.deps` (or anything under `app.platform.llm`) never requires
`anthropic`/`openai` installed unless a real client is actually selected.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.platform.llm.client import BaseLLMClient, LocalLLMClient
from app.platform.llm.service import LLMService
from app.platform.utils.deps import dep

_llm_client: BaseLLMClient | None = None
_voice_client: BaseLLMClient | None = None


def _get_llm_client() -> BaseLLMClient:
    global _llm_client
    if _llm_client is None:
        use_anthropic = (not config.IS_DEV) or (config.USE_REAL_LLM and bool(config.ANTHROPIC_API_KEY))
        if use_anthropic:
            from app.platform.llm.anthropic_client import AnthropicLLMClient  # noqa: PLC0415

            _llm_client = AnthropicLLMClient()
        else:
            _llm_client = LocalLLMClient()
    return _llm_client


def _get_voice_client() -> BaseLLMClient:
    global _voice_client
    if _voice_client is None:
        from app.platform.llm.openai_client import OpenAILLMClient  # noqa: PLC0415

        _voice_client = OpenAILLMClient()
    return _voice_client


@dep("llm_client")
def provide_llm_client() -> BaseLLMClient:
    return _get_llm_client()


@dep("voice_llm_client")
def provide_voice_llm_client() -> BaseLLMClient:
    return _get_voice_client()


@dep("llm_service")
def provide_llm_service(transaction: AsyncSession, llm_client: BaseLLMClient) -> LLMService:
    return LLMService(transaction, llm_client)
