from datetime import datetime

from app.config import config
from app.platform.base.schemas import BaseSchema
from app.platform.clients.s3 import BaseS3Client
from app.platform.media.models import Media
from app.platform.utils.sqids import Sqid


class MediaSchema(BaseSchema):
    """Bare Media response — no presigned URLs."""

    id: Sqid
    file_name: str
    file_type: str
    file_size: int
    mime_type: str
    state: str
    created_at: datetime
    updated_at: datetime


class MediaResponseSchema(BaseSchema):
    """Media response with presigned view + thumbnail URLs."""

    id: Sqid
    file_name: str
    file_type: str
    file_size: int
    mime_type: str
    state: str
    created_at: datetime
    updated_at: datetime
    view_url: str
    thumbnail_url: str | None


def media_to_response_schema(media: Media, s3_client: BaseS3Client) -> MediaResponseSchema:
    view_url = s3_client.generate_presigned_download_url(
        bucket=config.S3_MEDIA_BUCKET, key=media.file_key, expires_in=3600
    )
    thumbnail_url = (
        s3_client.generate_presigned_download_url(
            bucket=config.S3_MEDIA_BUCKET, key=media.thumbnail_key, expires_in=3600
        )
        if media.thumbnail_key
        else None
    )
    return MediaResponseSchema(
        id=Sqid(media.id),
        file_name=media.file_name,
        file_type=media.file_type,
        file_size=media.file_size,
        mime_type=media.mime_type,
        state=media.state,
        created_at=media.created_at,
        updated_at=media.updated_at,
        view_url=view_url,
        thumbnail_url=thumbnail_url,
    )


class PresignedUploadRequestSchema(BaseSchema):
    file_name: str
    content_type: str
    file_size: int


class PresignedUploadResponseSchema(BaseSchema):
    upload_url: str
    file_key: str


class RegisterMediaSchema(BaseSchema):
    file_key: str
    file_name: str
    file_size: int
    mime_type: str
