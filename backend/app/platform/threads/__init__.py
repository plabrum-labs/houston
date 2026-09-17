"""Threads module for real-time messaging on threadable objects."""

from app.platform.threads.routes import build_thread_router
from app.platform.threads.websocket import build_thread_handler

__all__ = ["build_thread_handler", "build_thread_router"]
