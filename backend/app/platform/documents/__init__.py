"""Documents module — file uploads (PDFs, etc.) with threadable activity."""

from app.platform.documents.routes import build_document_router

__all__ = ["build_document_router"]
