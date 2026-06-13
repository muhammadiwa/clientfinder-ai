"""
SQLAlchemy models for ClientFinder
All models imported here for Alembic autogenerate to discover them.
"""
from app.models.activity import Activity
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.lead import Hook, LeadScore
from app.models.outreach import Message, Sequence, SequenceEnrollment, Template
from app.models.prospect import PainPoint, Prospect, Signal, TechStack
from app.models.system import ScrapingJob, Setting
from app.models.user import User

__all__ = [
    "User",
    "Prospect",
    "Signal",
    "TechStack",
    "PainPoint",
    "LeadScore",
    "Hook",
    "Message",
    "Sequence",
    "SequenceEnrollment",
    "Template",
    "Activity",
    "Setting",
    "ScrapingJob",
    "UUIDPrimaryKeyMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
]