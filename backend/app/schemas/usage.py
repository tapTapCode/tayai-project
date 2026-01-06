"""
Usage tracking schemas
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UsageStatus(BaseModel):
    """Usage status schema"""
    user_id: int
    tier: str
    messages_used: int
    messages_limit: int
    tokens_used: int
    api_cost: Optional[float] = None  # API cost in USD
    period_start: datetime
    period_end: datetime
    can_send: bool
    # Trial status (for Basic tier)
    trial_active: Optional[bool] = None
    trial_days_remaining: Optional[int] = None
    trial_end_date: Optional[datetime] = None
