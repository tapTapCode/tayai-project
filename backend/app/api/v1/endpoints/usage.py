"""
Usage tracking endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.usage import UsageStatus
from app.services.usage_service import UsageService
from app.dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=UsageStatus)
async def get_usage_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get current usage status for user"""
    usage_service = UsageService(db)
    status = await usage_service.get_usage_status(
        user_id=current_user["user_id"],
        tier=current_user["tier"]
    )
    return status
