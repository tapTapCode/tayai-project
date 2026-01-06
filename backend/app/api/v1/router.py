"""
API v1 Router - Main router for all v1 endpoints
"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, chat, usage, admin, membership

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(membership.router, prefix="/membership", tags=["membership"])
