"""Media module — image/video uploads with thumbnail post-processing."""

from app.platform.media.routes import build_local_files_router, build_media_router

__all__ = ["build_local_files_router", "build_media_router"]
