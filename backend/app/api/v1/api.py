"""API v1 master router module."""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import auth, health

api_router = APIRouter()

# Register endpoint routers
api_router.include_router(health.router, tags=["Health & Status"])
api_router.include_router(auth.router, tags=["Authentication"])
