"""One-shot structured-output extraction.

Single LLM call against a msgspec schema. Provider chosen by the document's
MIME type (Anthropic for PDFs and images via native document blocks; either
for plain text). Owns its own provider selection, retry, and decode — this
path is deliberately separate from the chat/stream loop in `client.py`.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import anthropic
import msgspec
from anthropic.types import (
    Base64ImageSourceParam,
    Base64PDFSourceParam,
    DocumentBlockParam,
    ImageBlockParam,
    MessageParam,
    TextBlockParam,
    ToolParam,
)
from msgspec import Struct

from app.config import config
from app.platform.extraction.types import Document, ExtractionError

logger = logging.getLogger(__name__)

# Tool name the model is forced to call. Internal; never user-visible.
_EXTRACT_TOOL_NAME = "extract"
_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 8096


def _client() -> anthropic.AsyncAnthropic:
    # Module-level factory so tests can monkey-patch this symbol with a stub.
    return anthropic.AsyncAnthropic(
        api_key=config.ANTHROPIC_API_KEY,
        timeout=anthropic.Timeout(connect=10.0, read=120.0, write=10.0, pool=5.0),
    )


def _schema_to_json_schema(schema: type[Struct]) -> dict[str, Any]:
    """Convert a msgspec Struct into an inline JSON Schema with refs resolved.

    Anthropic's tool `input_schema` expects a self-contained object schema; it
    does not follow `$ref` / `$defs`. We inline every $ref into the tree so the
    top-level object has all its nested types embedded.
    """
    raw_schema, raw_defs = msgspec.json.schema_components([schema], ref_template="#/$defs/{name}")
    defs = raw_defs or {}
    return _inline_refs(raw_schema[0], defs)


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            name = ref.removeprefix("#/$defs/")
            target = defs.get(name)
            if target is None:
                raise ExtractionError(f"Unresolved schema ref: {ref}")
            return _inline_refs(target, defs)
        return {k: _inline_refs(v, defs) for k, v in node.items()}
    if isinstance(node, list):
        return [_inline_refs(item, defs) for item in node]
    return node


def _document_content_block(
    document: Document,
) -> TextBlockParam | DocumentBlockParam | ImageBlockParam:
    """Wrap a Document in the right Anthropic content-block shape for its MIME."""
    mime = document.mime.lower()
    if mime == "text/plain":
        content = document.content
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        return TextBlockParam(type="text", text=content)
    if mime == "application/pdf":
        if not isinstance(document.content, bytes):
            raise ExtractionError("PDF document content must be bytes")
        return DocumentBlockParam(
            type="document",
            source=Base64PDFSourceParam(
                type="base64",
                media_type="application/pdf",
                data=base64.b64encode(document.content).decode("ascii"),
            ),
        )
    if mime in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        if not isinstance(document.content, bytes):
            raise ExtractionError(f"Image document content must be bytes (mime={mime})")
        return ImageBlockParam(
            type="image",
            source=Base64ImageSourceParam(
                type="base64",
                media_type=mime,
                data=base64.b64encode(document.content).decode("ascii"),
            ),
        )
    raise ExtractionError(f"Unsupported document mime: {document.mime}")


async def llm_extract[T: Struct](
    document: Document,
    *,
    schema: type[T],
    prompt: str,
    max_retries: int = 1,
) -> T:
    """Run one structured-output extraction.

    Returns a decoded `schema` instance. Raises `ExtractionError` if the
    model can't be coerced into a valid response after `max_retries` retries
    on decode/schema-validation failures (default: 1 retry → 2 attempts).
    Provider/API errors bubble as-is for the task layer to translate.
    """
    if not config.USE_REAL_LLM:
        raise ExtractionError("LLM extraction disabled (config.USE_REAL_LLM=false)")

    input_schema = _schema_to_json_schema(schema)
    tools: list[ToolParam] = [
        ToolParam(
            name=_EXTRACT_TOOL_NAME,
            description="Return the extracted structured data.",
            input_schema=input_schema,
        )
    ]
    document_block = _document_content_block(document)
    messages: list[MessageParam] = [
        MessageParam(
            role="user",
            content=[document_block, TextBlockParam(type="text", text=prompt)],
        )
    ]

    client = _client()
    last_error: str | None = None

    for attempt in range(max_retries + 1):
        try:
            response = await client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                tools=tools,
                tool_choice={"type": "tool", "name": _EXTRACT_TOOL_NAME},
                messages=messages,
            )
        except anthropic.APIError as exc:
            logger.exception(f"Anthropic API error during extract (attempt {attempt + 1})")
            raise ExtractionError(f"LLM API error: {exc}") from exc

        tool_input = _find_tool_input(response)
        if tool_input is None:
            last_error = f"model did not call {_EXTRACT_TOOL_NAME}"
            logger.warning(f"Extract attempt {attempt + 1} failed: {last_error}")
            continue

        try:
            return msgspec.convert(tool_input, schema)
        except msgspec.ValidationError as exc:
            last_error = f"schema validation failed: {exc}"
            logger.warning(f"Extract attempt {attempt + 1} failed: {last_error}")
            messages.append({"role": "assistant", "content": response.content})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"That response did not match the required schema: {exc}. "
                        "Re-call the tool with corrected input."
                    ),
                }
            )

    raise ExtractionError(f"Could not extract valid {schema.__name__}: {last_error}")


def _find_tool_input(response: Any) -> dict[str, Any] | None:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == _EXTRACT_TOOL_NAME:
            return block.input
    return None
