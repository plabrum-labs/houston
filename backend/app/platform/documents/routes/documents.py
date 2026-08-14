import uuid
from collections.abc import Sequence

from litestar import Router, delete, get, post
from litestar.exceptions import NotFoundException, ValidationException
from litestar.types import Guard
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.platform.clients.s3 import BaseS3Client
from app.platform.documents.enums import DocumentStates
from app.platform.documents.models import Document
from app.platform.documents.schemas import (
    DocumentResponseSchema,
    DocumentSchema,
    PresignedUploadRequestSchema,
    PresignedUploadResponseSchema,
    RegisterDocumentSchema,
    document_to_response_schema,
)
from app.platform.utils.sqids import Sqid


@post("/presigned-upload")
async def request_presigned_upload(
    data: PresignedUploadRequestSchema, s3_client: BaseS3Client
) -> PresignedUploadResponseSchema:
    """Generate a presigned URL for uploading a document."""
    if data.file_size > config.MAX_DOCUMENT_SIZE:
        file_size_mb = data.file_size / (1024 * 1024)
        max_size_mb = config.MAX_DOCUMENT_SIZE / (1024 * 1024)
        raise ValidationException(f"File size {file_size_mb:.1f}MB exceeds maximum allowed size of {max_size_mb:.0f}MB")

    file_key = f"documents/{uuid.uuid4()}/{data.file_name}"

    upload_url = s3_client.generate_presigned_upload_url(
        bucket=config.S3_DOCUMENTS_BUCKET,
        key=file_key,
        content_type=data.content_type,
        expires_in=300,
    )

    return PresignedUploadResponseSchema(upload_url=upload_url, file_key=file_key)


@post("/register")
async def register_document(
    data: RegisterDocumentSchema,
    transaction: AsyncSession,
) -> DocumentSchema:
    """Register an uploaded document."""
    file_type = _determine_file_type(data.mime_type, data.file_name)

    # TODO: scope by the source app org/owner once domain is decided.
    document = Document(
        file_key=data.file_key,
        file_name=data.file_name,
        file_size=data.file_size,
        mime_type=data.mime_type,
        file_type=file_type,
        state=DocumentStates.READY,  # No async post-processing for documents.
    )
    transaction.add(document)
    await transaction.flush()

    return DocumentSchema(
        id=Sqid(document.id),
        file_name=document.file_name,
        file_type=document.file_type,
        file_size=document.file_size,
        mime_type=document.mime_type,
        state=document.state,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@get("/{id:str}")
async def get_document(
    id: Sqid,
    transaction: AsyncSession,
    s3_client: BaseS3Client,
) -> DocumentResponseSchema:
    document = await transaction.scalar(select(Document).where(Document.id == int(id)))
    if not document:
        raise NotFoundException(f"Document with id {id} not found")
    return document_to_response_schema(document, s3_client)


@delete("/{id:str}", status_code=200)
async def delete_document(id: Sqid, transaction: AsyncSession, s3_client: BaseS3Client) -> dict[str, str]:
    document = await transaction.scalar(select(Document).where(Document.id == int(id)))
    if not document:
        raise NotFoundException(f"Document with id {id} not found")

    await s3_client.delete_file(config.S3_DOCUMENTS_BUCKET, document.file_key)
    if document.thumbnail_key:
        await s3_client.delete_file(config.S3_DOCUMENTS_BUCKET, document.thumbnail_key)

    await transaction.delete(document)
    return {"status": "deleted"}


@get("/")
async def list_documents(
    transaction: AsyncSession,
    s3_client: BaseS3Client,
) -> list[DocumentResponseSchema]:
    """List all documents (RLS scope filters once added)."""
    query = select(Document).order_by(Document.created_at.desc())
    result = await transaction.execute(query)
    documents = result.scalars().all()
    return [document_to_response_schema(d, s3_client) for d in documents]


def _determine_file_type(mime_type: str, file_name: str) -> str:
    mime_type_map = {
        "application/pdf": "pdf",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.ms-excel": "xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "text/plain": "txt",
        "text/markdown": "md",
        "text/csv": "csv",
    }
    if mime_type in mime_type_map:
        return mime_type_map[mime_type]
    if "." in file_name:
        return file_name.rsplit(".", 1)[-1].lower()
    return "file"


def build_document_router(*, path: str = "/documents", guards: Sequence[Guard] = ()) -> Router:
    """Build the documents router for an app.

    The platform doesn't own the app's auth guards, so the module-level router from
    the source app (which hardcoded `guards=[requires_session]`) becomes a factory
    with `guards` injected — same guard-injection pattern as `build_action_router` / the CRUD
    controller factories.
    """
    return Router(
        path=path,
        guards=list(guards),
        route_handlers=[
            request_presigned_upload,
            register_document,
            get_document,
            delete_document,
            list_documents,
        ],
        tags=["documents"],
    )
