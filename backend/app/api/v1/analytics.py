"""
Analytics router — T7 dashboard endpoints
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser
from app.schemas.analytics import AnalyticsOverview
from app.services.analytics import get_analytics_overview, get_tier_distribution

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def get_analytics_overview_endpoint(
    current_user: CurrentUser,
    days: Annotated[int, Query(ge=1, le=365, description="Lookback period in days")] = 30,
) -> AnalyticsOverview:
    """
    Get the full analytics overview for the dashboard.

    Single round-trip, drives all 4 KPI categories
    (Lead Gen, Outreach, Pipeline, Operational).
    """
    return await get_analytics_overview(days=days)


# --- Sprint 3B carryover: tier distribution widget ---

@router.get("/tier-distribution")
async def get_tier_distribution_endpoint(
    current_user: CurrentUser,
    days: Annotated[int, Query(ge=1, le=365, description="Lookback period in days")] = 30,
) -> dict:
    """Prospect tier distribution for the Dashboard TierDonut.

    Returns counts per tier (smb / mid / enterprise / unknown /
    unclassified) in the lookback period.
    """
    return await get_tier_distribution(days=days)
