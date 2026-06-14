"""
Pydantic schemas for API request/response
"""
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, Token
from app.schemas.prospect import (
    ProspectCreate,
    ProspectListResponse,
    ProspectOut,
    ProspectUpdate,
)
from app.schemas.scraping import (
    ScrapingJobCreate,
    ScrapingJobListResponse,
    ScrapingJobOut,
    ScrapingPresetOut,
)
from app.schemas.outreach import (
    MessageApprovalRequest,
    MessageCreate,
    MessageGenerateRequest,
    MessageListResponse,
    MessageOut,
    MessageUpdate,
    OutreachStatsOut,
)
from app.schemas.templates import (
    TemplateCreate,
    TemplateListResponse,
    TemplateOut,
    TemplateUpdate,
)
from app.schemas.sequences import (
    SequenceCreate,
    SequenceListResponse,
    SequenceOut,
    SequenceUpdate,
)
from app.schemas.analytics import (
    ActivityCount,
    AnalyticsOverview,
    AnalyticsRange,
    ApprovalFunnelStats,
    ConversionRate,
    DailyPipeline,
    GradeDistribution,
    LeadSourceQuality,
    LLMUsageStats,
    OutreachChannelStats,
    PipelineStageCount,
    TimeToEnrichStats,
)
from app.schemas.user import UserCreate, UserInDB, UserOut, UserUpdate

__all__ = [
    "LoginRequest",
    "LogoutRequest",
    "RefreshRequest",
    "Token",
    "UserCreate",
    "UserInDB",
    "UserOut",
    "UserUpdate",
    "ProspectCreate",
    "ProspectListResponse",
    "ProspectOut",
    "ProspectUpdate",
    "ScrapingJobCreate",
    "ScrapingJobListResponse",
    "ScrapingJobOut",
    "ScrapingPresetOut",
    "MessageApprovalRequest",
    "MessageCreate",
    "MessageGenerateRequest",
    "MessageListResponse",
    "MessageOut",
    "MessageUpdate",
    "OutreachStatsOut",
    "TemplateCreate",
    "TemplateListResponse",
    "TemplateOut",
    "TemplateUpdate",
    "SequenceCreate",
    "SequenceListResponse",
    "SequenceOut",
    "SequenceUpdate",
    "ActivityCount",
    "AnalyticsOverview",
    "AnalyticsRange",
    "ApprovalFunnelStats",
    "ConversionRate",
    "DailyPipeline",
    "GradeDistribution",
    "LeadSourceQuality",
    "LLMUsageStats",
    "OutreachChannelStats",
    "PipelineStageCount",
    "TimeToEnrichStats",
]