"""API v1 master router module."""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import analyses, auth, health, job_descriptions, resumes

api_router = APIRouter()

# Register endpoint routers
api_router.include_router(health.router, tags=["Health & Status"])
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(resumes.router, tags=["Resumes"])
api_router.include_router(job_descriptions.router, tags=["Job Descriptions"])
api_router.include_router(analyses.router, tags=["Analyses"])
