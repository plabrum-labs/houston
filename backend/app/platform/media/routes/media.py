import uuid
from collections.abc import Sequence

from litestar import Request, Router, delete, get, post
from litestar.exceptions import NotFoundException, ValidationException
from litestar.types import Guard
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.platform.clients.s3 import BaseS3Client
from app.platform.media.enums import MediaStates, MediaTaskName
from app.platform.media.models import Media
from app.platform.media.schemas import (
    MediaResponseSchema,
    MediaSchema,
    PresignedUploadRequestSchema,
    PresignedUploadResponseSchema,
    RegisterMediaSchema,
    media_to_response_schema,
)
from app.platform.utils.sqids import Sqid


@post("/presigned-upload")
async def request_presigned_upload(
    data: PresignedUploadRequestSchema, s3_client: BaseS3Client
) -> PresignedUploadResponseSchema:
    """Generate a presigned URL for uploading a media file."""
    if data.file_size > config.MAX_UPLOAD_SIZE:
        file_size_mb = data.file_size / (1024 * 1024)
        max_size_mb = config.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise ValidationException(f"File size {file_size_mb:.1f}MB exceeds maximum allowed size of {max_size_mb:.0f}MB")

    file_key = f"media/{uuid.uuid4()}/{data.file_name}"

    upload_url = s3_client.generate_presigned_upload_url(
        bucket=config.S3_MEDIA_BUCKET,
        key=file_key,
        content_type=data.content_type,
        expires_in=300,
    )

    return PresignedUploadResponseSchema(upload_url=upload_url, file_key=file_key)


@post("/register")
async def register_media(
    data: RegisterMediaSchema,
    transaction: AsyncSession,
    request: Request,
) -> MediaSchema:
    """Register an uploaded media file and trigger thumbnail generation."""
    file_type = "image" if data.mime_type.startswith("image/") else "video"

    media = Media(
        organization_id=int(request.user.organization_id),
        file_key=data.file_key,
        file_name=data.file_name,
        file_size=data.file_size,
        mime_type=data.mime_type,
        file_type=file_type,
        state=MediaStates.PENDING,
    )
    transaction.add(media)
    await transaction.flush()

    queue = request.app.state.task_queues.get("default")
    await queue.enqueue(str(MediaTaskName.GENERATE_THUMBNAIL), media_id=int(media.id))

    return MediaSchema(
        id=Sqid(media.id),
        file_name=media.file_name,
        file_type=media.file_type,
        file_size=media.file_size,
        mime_type=media.mime_type,
        state=media.state,
        created_at=media.created_at,
        updated_at=media.updated_at,
    )


@get("/{id:str}")
async def get_media(
    id: Sqid,
    transaction: AsyncSession,
    s3_client: BaseS3Client,
) -> MediaResponseSchema:
    """Get a media item by SQID."""
    media = await transaction.scalar(select(Media).where(Media.id == int(id)))
    if not media:
        raise NotFoundException(f"Media with id {id} not found")
    return media_to_response_schema(media, s3_client)


@delete("/{id:str}", status_code=200)
async def delete_media(id: Sqid, transaction: AsyncSession, s3_client: BaseS3Client) -> dict[str, str]:
    """Delete a media item and its files from S3."""
    media = await transaction.scalar(select(Media).where(Media.id == int(id)))
    if not media:
        raise NotFoundException(f"Media with id {id} not found")

    bucket = config.S3_MEDIA_BUCKET
    await s3_client.delete_file(bucket, media.file_key)
    if media.thumbnail_key:
        await s3_client.delete_file(bucket, media.thumbnail_key)

    await transaction.delete(media)

    return {"status": "deleted"}


def build_media_router(*, path: str = "/media", guards: Sequence[Guard] = ()) -> Router:
    """Build the media router for an app.

    The platform doesn't own the app's auth guards, so the module-level router from
    the source app (which hardcoded `guards=[requires_session]`) becomes a factory
    with `guards` injected — same guard-injection pattern as `build_action_router` / the CRUD
    controller factories / `build_document_router`.
    """
    return Router(
        path=path,
        guards=list(guards),
        route_handlers=[
            request_presigned_upload,
            register_media,
            get_media,
            delete_media,
        ],
        tags=["media"],
    )
