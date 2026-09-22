"""Strict authorization and resource ownership verification."""

from backend.app.core.errors import ForbiddenError


def verify_ownership(resource_owner_id: str, current_user_id: str, resource_name: str = "Resource") -> None:
    """Enforces that a resource can only be viewed, updated, or deleted by its verified owner."""
    if resource_owner_id != current_user_id:
        raise ForbiddenError(f"Access denied. You do not have permission to access this {resource_name.lower()}.")
