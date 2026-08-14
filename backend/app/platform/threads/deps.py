"""Thread DI providers."""

from litestar import Request

from app.platform.threads.services import ThreadViewerStore
from app.platform.utils.deps import dep


@dep("viewer_store", sync_to_thread=False)
def provide_viewer_store(request: Request) -> ThreadViewerStore:
    """Wrap the app's `viewers` store in a `ThreadViewerStore` for handlers."""
    return ThreadViewerStore(store=request.app.stores.get("viewers"))
