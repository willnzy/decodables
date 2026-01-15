"""
Tier Service - Manages tier configuration, display names, and permissions.

@module domains.identity.tier_service
@version 2.0.0

This service handles:
- Tier display names (configurable via system_configs)
- Tier permissions and feature access
- Monthly credits and project limits
- AI queue priorities

All configurations are read from system_configs table, with emergency fallbacks.
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Union

from .constants import (
    TIER_T1,
    TIER_T2,
    TIER_T3,
    TIER_T4,
    VALID_TIERS,
    TIER_LABELS,
    DEFAULT_TIER_DISPLAY_NAMES,
    DEFAULT_TRIAL_DURATION_DAYS,
)
from infrastructure.repositories.config_repository import SupabaseConfigRepository

logger = logging.getLogger(__name__)


class FeatureKey(str, Enum):
    """功能权限 Key - 与 TIER-PERMISSIONS.md 保持一致"""
    # 导出
    PDF_EXPORT = "pdf_export"
    ZIP_EXPORT = "zip_export"

    # 编辑器
    BASIC_EDITOR = "basic_editor"
    VECTOR_TOOLS = "vector_tools"
    FREEHAND_TOOLS = "freehand_tools"
    CLIPBOARD_PASTE = "clipboard_paste"

    # 素材
    PLATFORM_ASSETS = "platform_assets"
    UPLOAD_IMAGE = "upload_image"
    UPLOAD_ADVANCED = "upload_advanced"
    SAVE_ASSETS = "save_assets"
    HISTORY_ASSETS = "history_assets"

    # 市场
    BROWSE_MARKETPLACE = "browse_marketplace"
    PURCHASE_MARKETPLACE = "purchase_marketplace"
    PUBLISH_MARKETPLACE = "publish_marketplace"

    # AI
    AI_FEATURES = "ai_features"

    # t4 专属
    PRIORITY_SUPPORT = "priority_support"
    API_ACCESS = "api_access"


# Emergency fallback - 仅在数据库完全不可用时使用
# 与 TIER-PERMISSIONS.md 保持一致
EMERGENCY_TIER_CONFIGS = {
    TIER_T1: {
        "monthly_credits": 0,  # Aligned with database system_configs
        "max_projects": 1,
        "ai_queue_priority": "low",
        "topup_discount": 1.0,
        "features": {
            "pdf_export": True,
            "zip_export": "trial",
            "basic_editor": "trial",
            "vector_tools": "trial",
            "freehand_tools": "trial",
            "clipboard_paste": "trial",
            "platform_assets": "trial",
            "upload_image": "trial",
            "upload_advanced": "trial",
            "save_assets": "trial",
            "history_assets": "trial",
            "browse_marketplace": "trial",
            "purchase_marketplace": False,
            "publish_marketplace": False,
            "ai_features": "trial",
        }
    },
    TIER_T2: {
        "monthly_credits": 100,  # Aligned with database system_configs
        "max_projects": 10,
        "ai_queue_priority": "normal",
        "topup_discount": 1.0,
        "features": {
            "pdf_export": True,
            "zip_export": False,
            "basic_editor": True,
            "vector_tools": False,
            "freehand_tools": False,
            "clipboard_paste": False,
            "platform_assets": True,
            "upload_image": True,
            "upload_advanced": False,
            "save_assets": False,
            "history_assets": False,
            "browse_marketplace": True,
            "purchase_marketplace": False,
            "publish_marketplace": True,
            "ai_features": True,
        }
    },
    TIER_T3: {
        "monthly_credits": 200,  # Aligned with database system_configs
        "max_projects": 200,
        "ai_queue_priority": "high",
        "topup_discount": 0.9,
        "features": {
            "pdf_export": True,
            "zip_export": True,
            "basic_editor": True,
            "vector_tools": True,
            "freehand_tools": True,
            "clipboard_paste": True,
            "platform_assets": True,
            "upload_image": True,
            "upload_advanced": True,
            "save_assets": True,
            "history_assets": True,
            "browse_marketplace": True,
            "purchase_marketplace": True,
            "publish_marketplace": True,
            "ai_features": True,
        }
    },
    TIER_T4: {
        "monthly_credits": 500,  # Enterprise tier placeholder
        "max_projects": 1000,
        "ai_queue_priority": "high",
        "topup_discount": 0.8,
        "features": {
            "pdf_export": True,
            "zip_export": True,
            "basic_editor": True,
            "vector_tools": True,
            "freehand_tools": True,
            "clipboard_paste": True,
            "platform_assets": True,
            "upload_image": True,
            "upload_advanced": True,
            "save_assets": True,
            "history_assets": True,
            "browse_marketplace": True,
            "purchase_marketplace": True,
            "publish_marketplace": True,
            "ai_features": True,
            "priority_support": True,
            "api_access": True,
        }
    },
}


class TierService:
    """
    Service for managing tier configurations and permissions.

    Responsibilities:
    - Fetch tier display names from system_configs
    - Check feature permissions based on tier
    - Get tier limits (monthly credits, max projects)
    - Get AI queue priorities
    - Provide fallback to emergency values
    - Cache configurations for performance
    """

    def __init__(self, config_repo: SupabaseConfigRepository):
        """
        Initialize TierService with config repository.

        Args:
            config_repo: Configuration repository for accessing system_configs
        """
        self.config_repo = config_repo
        self._cache: Dict[str, Any] = {}
        self._tier_config_cache: Dict[str, Dict[str, Any]] = {}

    async def get_tier_display_name(self, tier: str) -> str:
        """
        Get configurable display name for a tier.

        This fetches the display name from system_configs table.
        Admins can change these names without code changes.

        Args:
            tier: Tier system code ('t1', 't2', or 't3')

        Returns:
            Display name (e.g., 'Free Plan', 'Starter Plan', 'Pro Plan')
            Falls back to default if not found in config.

        Example:
            >>> tier_service = TierService(config_repo)
            >>> await tier_service.get_tier_display_name("t1")
            'Free Plan'
        """
        if tier not in VALID_TIERS:
            logger.warning(f"Invalid tier code: {tier}")
            return tier.upper()

        # Check cache first
        if tier in self._cache:
            return self._cache[tier]

        # Fetch from database
        config_key = f"tier.{tier}.display_name"
        try:
            display_name = await self.config_repo.get_by_key(
                config_key,
                default_value=DEFAULT_TIER_DISPLAY_NAMES.get(tier, tier.upper())
            )

            # Cache the result
            self._cache[tier] = display_name
            return display_name

        except Exception as e:
            logger.error(f"Failed to fetch tier display name for {tier}: {e}")
            # Return default value on error
            return DEFAULT_TIER_DISPLAY_NAMES.get(tier, tier.upper())

    def get_tier_label(self, tier: str) -> str:
        """
        Get fixed descriptive label for a tier.

        These labels are fixed and never change:
        - t1 → "First Tier"
        - t2 → "Second Tier"
        - t3 → "Third Tier"

        Used in documentation, logs, and internal references.

        Args:
            tier: Tier system code ('t1', 't2', or 't3')

        Returns:
            Fixed tier label
        """
        return TIER_LABELS.get(tier, tier.upper())

    async def update_tier_display_name(self, tier: str, display_name: str) -> bool:
        """
        Update tier display name (Admin operation).

        This updates the display name in system_configs and clears the cache.

        Args:
            tier: Tier system code ('t1', 't2', or 't3')
            display_name: New display name to set

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If tier is invalid
        """
        if tier not in VALID_TIERS:
            raise ValueError(f"Invalid tier: {tier}")

        config_key = f"tier.{tier}.display_name"

        try:
            # Update in database
            await self.config_repo.upsert(
                key=config_key,
                value=display_name,
                value_type="text",
                config_group="tier",
                description=f"{self.get_tier_label(tier)} 显示名称 (可配置)",
                is_active=True,
                is_editable=True
            )

            # Clear cache for this tier
            self._cache.pop(tier, None)

            logger.info(f"Updated tier display name: {tier} → '{display_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to update tier display name for {tier}: {e}")
            return False

    async def get_all_tier_configs(self) -> list[dict]:
        """
        Get all tier configurations with display names.

        Returns:
            List of tier configs with system codes, labels, and display names

        Example:
            [
                {
                    "tier": "t1",
                    "tier_label": "First Tier",
                    "display_name": "Free Plan"
                },
                ...
            ]
        """
        configs = []

        for tier in sorted(VALID_TIERS):
            display_name = await self.get_tier_display_name(tier)
            configs.append({
                "tier": tier,
                "tier_label": self.get_tier_label(tier),
                "display_name": display_name,
            })

        return configs

    def clear_cache(self):
        """Clear the tier display name cache."""
        self._cache.clear()
        logger.debug("Tier display name cache cleared")

    async def get_trial_duration_days(self) -> int:
        """
        Get trial period duration in days from system_configs.

        Free tier users get a trial period with full access.
        This value is configurable by admins.

        Returns:
            Number of trial days (default: 30)

        Example:
            >>> tier_service = TierService(config_repo)
            >>> await tier_service.get_trial_duration_days()
            30
        """
        config_key = "trial.duration_days"

        try:
            value = await self.config_repo.get_by_key(
                config_key,
                default_value=str(DEFAULT_TRIAL_DURATION_DAYS)
            )

            # Convert to integer
            return int(value)

        except (ValueError, TypeError) as e:
            logger.error(f"Invalid trial duration value: {e}, using default {DEFAULT_TRIAL_DURATION_DAYS}")
            return DEFAULT_TRIAL_DURATION_DAYS
        except Exception as e:
            logger.error(f"Failed to fetch trial duration: {e}, using default {DEFAULT_TRIAL_DURATION_DAYS}")
            return DEFAULT_TRIAL_DURATION_DAYS

    async def update_trial_duration_days(self, days: int) -> bool:
        """
        Update trial period duration (Admin operation).

        Args:
            days: New trial duration in days (must be > 0)

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If days <= 0
        """
        if days <= 0:
            raise ValueError(f"Trial duration must be positive, got {days}")

        config_key = "trial.duration_days"

        try:
            # Update in database
            await self.config_repo.upsert(
                key=config_key,
                value=str(days),
                value_type="integer",
                config_group="trial",
                description="Free tier 试用期天数 (可配置)",
                is_active=True,
                is_editable=True
            )

            logger.info(f"Updated trial duration: {days} days")
            return True

        except Exception as e:
            logger.error(f"Failed to update trial duration: {e}")
            return False

    # =========================================================================
    # Tier Configuration Methods (权限配置)
    # =========================================================================

    async def get_tier_config(self, tier: str) -> Dict[str, Any]:
        """
        获取 Tier 完整配置 (月度积分、项目限制、功能权限等)

        Args:
            tier: Tier 代码 (t1/t2/t3/t4)

        Returns:
            包含所有配置的字典

        Example:
            {
                "monthly_credits": 100,
                "max_projects": 10,
                "ai_queue_priority": "normal",
                "topup_discount": 1.0,
                "features": {...}
            }
        """
        if tier not in VALID_TIERS:
            logger.warning(f"Invalid tier: {tier}, using t1 config")
            tier = TIER_T1

        # Check cache
        cache_key = f"tier_config_{tier}"
        if cache_key in self._tier_config_cache:
            return self._tier_config_cache[cache_key]

        try:
            # Fetch all tier config values from database
            monthly_credits = await self._get_config_int(f"tier.{tier}.monthly_credits")
            max_projects = await self._get_config_int(f"tier.{tier}.max_projects")
            ai_queue_priority = await self._get_config_str(f"tier.{tier}.ai_queue_priority")
            topup_discount = await self._get_config_float(f"tier.{tier}.topup_discount")
            features = await self._get_config_json(f"tier.{tier}.features")

            config = {
                "monthly_credits": monthly_credits,
                "max_projects": max_projects,
                "ai_queue_priority": ai_queue_priority,
                "topup_discount": topup_discount,
                "features": features,
            }

            # Validate - if features is None, use fallback
            if config["features"] is None:
                logger.warning(f"Missing features config for {tier}, using fallback")
                config = EMERGENCY_TIER_CONFIGS.get(tier, EMERGENCY_TIER_CONFIGS[TIER_T1])
            else:
                # Fill missing values with fallback
                fallback = EMERGENCY_TIER_CONFIGS.get(tier, EMERGENCY_TIER_CONFIGS[TIER_T1])
                for key in ["monthly_credits", "max_projects", "ai_queue_priority", "topup_discount"]:
                    if config[key] is None:
                        config[key] = fallback[key]

            # Cache result
            self._tier_config_cache[cache_key] = config
            return config

        except Exception as e:
            logger.error(
                f"[CRITICAL] Failed to load tier config for {tier}, using fallback",
                extra={"tier": tier, "error": str(e)}
            )
            return EMERGENCY_TIER_CONFIGS.get(tier, EMERGENCY_TIER_CONFIGS[TIER_T1])

    async def can_use_feature(
        self,
        user_tier: str,
        feature: Union[FeatureKey, str],
        is_trial_active: bool = False
    ) -> bool:
        """
        检查用户是否可以使用某功能

        Args:
            user_tier: 用户 Tier (t1/t2/t3/t4)
            feature: 功能 Key (FeatureKey 枚举或字符串)
            is_trial_active: t1 用户是否在试用期内

        Returns:
            True 如果可以使用，False 否则

        Example:
            >>> await tier_service.can_use_feature("t2", FeatureKey.ZIP_EXPORT)
            False
            >>> await tier_service.can_use_feature("t3", FeatureKey.ZIP_EXPORT)
            True
        """
        feature_key = feature.value if isinstance(feature, FeatureKey) else feature

        config = await self.get_tier_config(user_tier)
        features = config.get("features", {})
        feature_value = features.get(feature_key)

        if feature_value is None:
            logger.warning(f"Unknown feature: {feature_key} for tier {user_tier}")
            return False

        # 处理三种权限值: true, false, "trial"
        if feature_value is True:
            return True
        elif feature_value is False:
            return False
        elif feature_value == "trial":
            # 仅在试用期内可用
            return is_trial_active
        else:
            logger.warning(f"Invalid feature value: {feature_value} for {feature_key}")
            return False

    async def get_monthly_credits(self, user_tier: str) -> int:
        """获取月度积分额度"""
        config = await self.get_tier_config(user_tier)
        return config.get("monthly_credits", 0)

    async def get_max_projects(self, user_tier: str) -> int:
        """获取项目数量限制"""
        config = await self.get_tier_config(user_tier)
        return config.get("max_projects", 1)

    async def get_ai_queue_priority(self, user_tier: str) -> str:
        """获取 AI 队列优先级 (low/normal/high)"""
        config = await self.get_tier_config(user_tier)
        return config.get("ai_queue_priority", "low")

    async def get_ai_queue_priority_value(self, user_tier: str) -> int:
        """获取 AI 队列优先级数值 (0=low, 1=normal, 2=high)"""
        priority_str = await self.get_ai_queue_priority(user_tier)
        priority_map = {"low": 0, "normal": 1, "high": 2}
        return priority_map.get(priority_str, 0)

    async def get_topup_discount(self, user_tier: str) -> float:
        """获取充值折扣 (1.0 = 无折扣, 0.9 = 9折)"""
        config = await self.get_tier_config(user_tier)
        return config.get("topup_discount", 1.0)

    async def get_signup_bonus(self) -> int:
        """获取注册赠送积分"""
        try:
            value = await self.config_repo.get_by_key(
                "credits.signup_bonus",
                default_value="100"
            )
            return int(value)
        except Exception as e:
            logger.error(f"Failed to get signup bonus: {e}")
            return 100  # 默认值

    async def get_operation_cost(self, operation: str) -> int:
        """
        获取操作积分成本

        Args:
            operation: 操作名称 (image_generation, page_generation, ocr, smart_scan, text_generation)

        Returns:
            积分成本
        """
        try:
            value = await self.config_repo.get_by_key(
                f"credits.cost.{operation}",
                default_value=None
            )
            if value is not None:
                return int(value)
        except Exception as e:
            logger.error(f"Failed to get operation cost for {operation}: {e}")

        # Fallback costs (aligned with database system_configs)
        fallback_costs = {
            "image_generation": 5,
            "page_generation": 5,
            "ocr": 10,         # Aligned with database: credits.cost.ocr = 10
            "smart_scan": 10,  # Aligned with database: credits.cost.smart_scan = 10
            "text_generation": 0,
        }
        return fallback_costs.get(operation, 5)

    # =========================================================================
    # Trial Status Helper
    # =========================================================================

    def is_trial_active(self, user: Dict[str, Any], trial_days: int = None) -> bool:
        """
        检查 t1 用户是否在试用期内

        Args:
            user: 用户信息字典
            trial_days: 试用期天数 (如果为 None，使用默认值)

        Returns:
            True 如果在试用期内
        """
        if user.get("tier") != TIER_T1:
            return False

        created_at = user.get("created_at")
        if not created_at:
            return False

        # 确保 created_at 是 datetime 对象
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                return False

        # 使用传入的天数或默认值
        if trial_days is None:
            trial_days = DEFAULT_TRIAL_DURATION_DAYS

        trial_end = created_at + timedelta(days=trial_days)
        now = datetime.now(trial_end.tzinfo) if trial_end.tzinfo else datetime.utcnow()
        return now < trial_end

    # =========================================================================
    # Helper Methods (内部方法)
    # =========================================================================

    async def _get_config_int(self, key: str) -> Optional[int]:
        """获取整数配置值"""
        try:
            value = await self.config_repo.get_by_key(key, default_value=None)
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    async def _get_config_float(self, key: str) -> Optional[float]:
        """获取浮点数配置值"""
        try:
            value = await self.config_repo.get_by_key(key, default_value=None)
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    async def _get_config_str(self, key: str) -> Optional[str]:
        """获取字符串配置值"""
        try:
            value = await self.config_repo.get_by_key(key, default_value=None)
            return str(value) if value is not None else None
        except Exception:
            return None

    async def _get_config_json(self, key: str) -> Optional[Dict]:
        """获取 JSON 配置值"""
        try:
            value = await self.config_repo.get_by_key(key, default_value=None)
            if value is None:
                return None
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                return json.loads(value)
            return None
        except (json.JSONDecodeError, TypeError):
            return None

    def clear_tier_config_cache(self):
        """清除 Tier 配置缓存 (配置更新后调用)"""
        self._tier_config_cache.clear()
        logger.debug("Tier config cache cleared")
