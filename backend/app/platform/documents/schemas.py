from datetime import datetime

from app.config import config
from app.platform.base.schemas import BaseSchema
from app.platform.clients.s3 import BaseS3Client
from app.platform.documents.models import Document
from app.platform.utils.sqids import Sqid


class DocumentSchema(BaseSchema):
    id: Sqid
    file_name: str
    file_type: str
    file_size: int
    mime_type: str
    state: str
    created_at: datetime
    updated_at: datetime


class DocumentResponseSchema(BaseSchema):
    id: Sqid
    file_name: str
    file_type: str
    file_size: int
    mime_type: str
    state: str
    created_at: datetime
    updated_at: datetime
    view_url: str


def document_to_response_schema(document: Document, s3_client: BaseS3Client) -> DocumentResponseSchema:
    view_url = s3_client.generate_presigned_download_url(
        bucket=config.S3_DOCUMENTS_BUCKET, key=document.file_key, expires_in=3600
    )
    return DocumentResponseSchema(
        id=Sqid(document.id),
        file_name=document.file_name,
        file_type=document.file_type,
        file_size=document.file_size,
        mime_type=document.mime_type,
        state=document.state,
        created_at=document.created_at,
        updated_at=document.updated_at,
        view_url=view_url,
    )


class PresignedUploadRequestSchema(BaseSchema):
    file_name: str
    content_type: str
    file_size: int


class PresignedUploadResponseSchema(BaseSchema):
    upload_url: str
    file_key: str


class RegisterDocumentSchema(BaseSchema):
    file_key: str
    file_name: str
    file_size: int
    mime_type: str
