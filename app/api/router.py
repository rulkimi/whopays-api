from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Sequence

from fastapi import APIRouter, Depends


# Shared default error responses for all routers for consistency
DEFAULT_ERROR_RESPONSES: Dict[int, Dict[str, Any]] = {
    400: {"description": "Bad Request"},
    401: {"description": "Unauthorized"},
    403: {"description": "Forbidden"},
    404: {"description": "Not Found"},
    500: {"description": "Internal Server Error"},
}


def create_router(
    *,
    name: Optional[str] = None,
    dependencies: Optional[Sequence[Depends]] = None,
    default_responses: Optional[Dict[int, Dict[str, Any]]] = None,
) -> APIRouter:
    """Create a pre-configured APIRouter with standardized defaults.

    Args:
        name: Optional logical name for the router; useful for debugging/metrics.
        dependencies: Optional dependencies applied to all routes in the router.
        default_responses: Optional map to override default error responses.

    Returns:
        Configured APIRouter instance.
    """
    router = APIRouter(
        dependencies=list(dependencies) if dependencies else None,
        responses=(default_responses or DEFAULT_ERROR_RESPONSES),
    )
    # Attach metadata for introspection or future tooling (non-functional)
    if name:
        setattr(router, "name", name)
    return router


