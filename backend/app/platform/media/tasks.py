"""Background tasks for media processing."""

import subprocess
import tempfile
from pathlib import Path

from PIL import Image
from sqlalchemy import select

from app.config import config
from app.platform.clients.s3 import BaseS3Client
from app.platform.media.enums import MediaStates, MediaTaskName
from app.platform.media.models import Media
from app.platform.queue.registry import task
from app.platform.queue.types import PlatformContext


@task(MediaTaskName.GENERATE_THUMBNAIL)
async def generate_thumbnail(ctx: PlatformContext, *, media_id: int, s3_client: BaseS3Client) -> dict:
    """Generate a thumbnail for an uploaded media file."""
    db_sessionmaker = ctx["db_sessionmaker"]
    bucket = config.S3_MEDIA_BUCKET

    async with db_sessionmaker() as session:
        async with session.begin():
            media = await session.scalar(select(Media).where(Media.id == media_id))
            if not media:
                return {"status": "error", "message": f"Media {media_id} not found"}

            media.state = MediaStates.PROCESSING

            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)

                    original_path = temp_path / media.file_name
                    await s3_client.download(bucket, media.file_key, original_path)

                    thumbnail_filename = f"thumb_{Path(media.file_name).stem}.jpg"
                    thumbnail_path = temp_path / thumbnail_filename

                    if media.file_type == "image":
                        with Image.open(original_path) as img:
                            if img.mode in ("RGBA", "P", "LA"):
                                img = img.convert("RGB")
                            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                            img.save(thumbnail_path, "JPEG", quality=85)
                    elif media.file_type == "video":
                        subprocess.run(
                            [
                                "ffmpeg",
                                "-i",
                                str(original_path),
                                "-ss",
                                "00:00:01.000",
                                "-vframes",
                                "1",
                                "-vf",
                                "scale=300:300:force_original_aspect_ratio=decrease",
                                str(thumbnail_path),
                            ],
                            check=True,
                            capture_output=True,
                        )

                    thumbnail_key = f"media/{media.file_key.split('/')[1]}/thumb_{thumbnail_filename}"
                    await s3_client.upload(bucket, thumbnail_key, thumbnail_path, content_type="image/jpeg")

                    media.thumbnail_key = thumbnail_key
                    media.state = MediaStates.READY

                return {"status": "success", "media_id": media_id, "thumbnail_key": thumbnail_key}

            except Exception as e:
                media.state = MediaStates.FAILED
                return {"status": "error", "media_id": media_id, "message": str(e)}
