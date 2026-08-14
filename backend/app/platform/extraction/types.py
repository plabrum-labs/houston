"""`Document` and `ExtractionError` — the leaf types shared between the
extractor framework and the LLM call. Lives in its own module to break the
import cycle between `extraction.base` and `llm.extract`.
"""

from __future__ import annotations

from dataclasses import dataclass


class ExtractionError(Exception):
    """Raised when the LLM cannot return a valid response for the requested schema.

    Bubbles from `llm_extract` after structured-output retries are exhausted, or
    when an extractor's domain code rejects the parsed payload. Callers catch
    this at the task boundary to send a user-facing failure reply; everything
    inside the extraction tree should let it propagate.
    """


@dataclass(frozen=True)
class Document:
    content: bytes | str
    mime: str

    @classmethod
    def from_text(cls, text: str) -> Document:
        return cls(content=text, mime="text/plain")

    @classmethod
    def from_pdf(cls, data: bytes) -> Document:
        return cls(content=data, mime="application/pdf")

    @classmethod
    def from_image(cls, data: bytes, *, mime: str = "image/png") -> Document:
        return cls(content=data, mime=mime)
