"""
Referrals Domain

@module domains.referrals
@version 1.0.0

推荐系统领域层
"""

from .entity import ReferralEntity
from .repository import ReferralRepository
from .service import ReferralService

__all__ = [
    "ReferralEntity",
    "ReferralRepository",
    "ReferralService",
]
