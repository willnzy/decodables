# 后端 Service 层实现

> **版本**: v1.0
> **日期**: 2026-02-04
> **状态**: 🔴 待实现
> **代码位置**: `decodables/domains/entitlement/`

---

## 相关设计文档

| 设计文档 | 本文档章节 |
|----------|-----------|
| 01-permission-matrix.md | §3.1 |
| 02-tier-config.md | §3.2 |
| 04-feature-flag-engine.md | §3.3 |
| 06-priority-rules.md | §3.4 |
| 07-tier-inheritance.md | §3.2 |
| 08-user-groups.md | §3.5 |
| 09-config-versioning.md | §3.6 |
| 10-workspace-override.md | §3.7 |
| 11-trial-expiration.md | §4.1 |
| 12-tier-downgrade.md | §4.2 |
| 13-subscription-pause.md | §4.3 |
| 14-billing-cycle-switch.md | §4.4 |
| 15-credits-lifecycle.md | §4.5 |
| 16-renewal-reminders.md | §4.6 |
| 17-invoice-management.md | §4.7 |
| 18-refund-processing.md | §4.8 |
| 19-promotions.md | §5.1 |
| 20-referral-rewards.md | §5.2 |
| 21-education-discount.md | §5.3 |
| 22-free-quota.md | §5.4 |
| 23-feature-sunset.md | §5.5 |
| 24-conflict-resolution.md | §5.6 |

---

## 目录

- [§1. 架构概述](#1-架构概述)
- [§2. 目录结构](#2-目录结构)
- [§3. 核心配置服务](#3-核心配置服务)
  - [§3.1 PermissionService](#31-permissionservice)
  - [§3.2 TierService](#32-tierservice)
  - [§3.3 FeatureFlagService](#33-featureflagservice)
  - [§3.4 PriorityEvaluator](#34-priorityevaluator)
  - [§3.5 UserGroupService](#35-usergroupservice)
  - [§3.6 ConfigVersionService](#36-configversionservice)
  - [§3.7 WorkspaceOverrideService](#37-workspaceoverrideservice)
- [§4. 生命周期服务](#4-生命周期服务)
  - [§4.1 TrialService](#41-trialservice)
  - [§4.2 TierDowngradeService](#42-tierdowngradeservice)
  - [§4.3 SubscriptionPauseService](#43-subscriptionpauseservice)
  - [§4.4 BillingCycleService](#44-billingcycleservice)
  - [§4.5 CreditService](#45-creditservice)
  - [§4.6 RenewalReminderService](#46-renewalreminderservice)
  - [§4.7 InvoiceService](#47-invoiceservice)
  - [§4.8 RefundService](#48-refundservice)
- [§5. 营销扩展服务](#5-营销扩展服务)
  - [§5.1 PromotionService](#51-promotionservice)
  - [§5.2 ReferralService](#52-referralservice)
  - [§5.3 EducationDiscountService](#53-educationdiscountservice)
  - [§5.4 FreeQuotaService](#54-freequotaservice)
  - [§5.5 FeatureSunsetService](#55-featuresunsetservice)
  - [§5.6 ConflictResolutionService](#56-conflictresolutionservice)

---

## §1. 架构概述

### 1.1 DDD 分层

```
api/routers/entitlement/    → API 端点 (调用 Application)
application/entitlement/    → 用例编排 (调用 Domain Service)
domains/entitlement/        → 领域服务 (本文档)
infrastructure/entitlement/ → Repository 实现
```

### 1.2 Service 设计原则

1. **单一职责**: 每个 Service 负责一个领域概念
2. **依赖注入**: 通过构造函数注入 Repository
3. **接口隔离**: Service 定义 Interface，Repository 实现
4. **事务边界**: 复杂操作在 Application 层协调事务

---

## §2. 目录结构

```
decodables/domains/entitlement/
├── __init__.py
├── entities/                    # 领域实体
│   ├── permission.py
│   ├── tier.py
│   ├── feature_flag.py
│   ├── credit_pool.py
│   └── ...
├── services/                    # 领域服务
│   ├── permission_service.py
│   ├── tier_service.py
│   ├── feature_flag_service.py
│   ├── credit_service.py
│   └── ...
├── repositories/                # Repository 接口
│   ├── permission_repository.py
│   ├── tier_repository.py
│   ├── credit_repository.py
│   └── ...
├── value_objects/               # 值对象
│   ├── feature_key.py
│   ├── tier_type.py
│   ├── source_type.py
│   └── ...
└── exceptions.py                # 领域异常
```

---

## §3. 核心配置服务

### §3.1 PermissionService

> 设计文档: [01-permission-matrix.md](../01-permission-matrix.md)

**文件**: `domains/entitlement/services/permission_service.py`

**职责**: 权限检查的统一入口，整合 7 层优先级

**实现状态**: 🔴 待实现

```python
from typing import Optional
from domains.entitlement.entities.permission import PermissionResult
from domains.entitlement.services.priority_evaluator import PriorityEvaluator

class PermissionService:
    """权限服务 - 统一权限检查入口"""

    def __init__(
        self,
        priority_evaluator: PriorityEvaluator,
        tier_service: "TierService",
        feature_flag_service: "FeatureFlagService",
    ):
        self.priority_evaluator = priority_evaluator
        self.tier_service = tier_service
        self.feature_flag_service = feature_flag_service

    async def check_permission(
        self,
        user_id: str,
        feature_key: str,
        workspace_id: Optional[str] = None,
    ) -> PermissionResult:
        """
        检查用户对某功能的权限

        Returns:
            PermissionResult:
                - enabled: bool | "trial"
                - source: str (权限来源)
                - quota: Optional[int] (如有配额限制)
                - expires_at: Optional[datetime] (如有过期时间)
        """
        return await self.priority_evaluator.evaluate(
            user_id=user_id,
            feature_key=feature_key,
            workspace_id=workspace_id,
        )

    async def check_quota(
        self,
        user_id: str,
        quota_key: str,
        workspace_id: Optional[str] = None,
    ) -> tuple[int, int]:
        """
        检查用户配额

        Returns:
            (used, limit): 已使用数量和限制
            limit = -1 表示无限
        """
        tier = await self.tier_service.get_user_tier(user_id)
        limit = await self.tier_service.get_tier_quota(tier, quota_key)
        used = await self._get_quota_usage(user_id, quota_key, workspace_id)
        return used, limit

    async def can_perform(
        self,
        user_id: str,
        feature_key: str,
        workspace_id: Optional[str] = None,
    ) -> bool:
        """简化的权限检查，返回 bool"""
        result = await self.check_permission(user_id, feature_key, workspace_id)
        return result.enabled is True  # "trial" 也返回 True
```

### §3.2 TierService

> 设计文档: [02-tier-config.md](../02-tier-config.md), [07-tier-inheritance.md](../07-tier-inheritance.md)

**文件**: `domains/entitlement/services/tier_service.py`

**职责**: Tier 配置管理，继承链计算

**实现状态**: 🔴 待实现

```python
from typing import Dict, Any, Optional
from domains.entitlement.entities.tier import TierConfig
from domains.entitlement.repositories.tier_repository import TierRepository

# Tier 继承链
TIER_INHERITANCE = {
    "t1": [],
    "t2": ["t1"],
    "t3": ["t2"],
    "t4": ["t3"],
}

class TierService:
    """Tier 服务 - 管理 Tier 配置和继承"""

    def __init__(self, tier_repository: TierRepository):
        self.repository = tier_repository
        self._config_cache: Optional[Dict[str, TierConfig]] = None

    async def get_user_tier(self, user_id: str) -> str:
        """获取用户当前 Tier"""
        return await self.repository.get_user_tier(user_id)

    async def get_tier_config(self, tier: str) -> TierConfig:
        """获取 Tier 完整配置 (含继承)"""
        if self._config_cache is None:
            await self._load_config()

        return self._config_cache.get(tier, self._config_cache["t1"])

    async def get_tier_feature(
        self,
        tier: str,
        feature_key: str,
    ) -> bool | str:
        """获取 Tier 的某个功能权限"""
        config = await self.get_tier_config(tier)
        return config.features.get(feature_key, False)

    async def get_tier_quota(
        self,
        tier: str,
        quota_key: str,
    ) -> int:
        """获取 Tier 的某个配额限制，-1 表示无限"""
        config = await self.get_tier_config(tier)
        return config.quotas.get(quota_key, 0)

    async def get_tier_display_name(self, tier: str) -> str:
        """获取 Tier 显示名称 (可配置)"""
        config = await self.get_tier_config(tier)
        return config.display_name

    def get_tier_with_inheritance(self, tier: str) -> Dict[str, Any]:
        """计算包含继承的完整 Tier 配置"""
        result = {}
        parents = TIER_INHERITANCE.get(tier, [])

        # 递归获取父级配置
        for parent in parents:
            parent_config = self.get_tier_with_inheritance(parent)
            result.update(parent_config)

        # 覆盖当前层级配置
        # ... 从数据库获取 delta 配置
        return result

    async def _load_config(self):
        """加载 Tier 配置到缓存"""
        self._config_cache = await self.repository.get_all_tier_configs()
```

### §3.3 FeatureFlagService

> 设计文档: [04-feature-flag-engine.md](../04-feature-flag-engine.md)

**文件**: `domains/entitlement/services/feature_flag_service.py`

**职责**: Feature Flag 评估引擎

**实现状态**: 🔴 待实现

```python
import hashlib
from typing import Optional, Any
from domains.entitlement.entities.feature_flag import FeatureFlag, FlagResult
from domains.entitlement.repositories.feature_flag_repository import FeatureFlagRepository

class FeatureFlagService:
    """Feature Flag 服务 - 9 步评估引擎"""

    def __init__(self, repository: FeatureFlagRepository):
        self.repository = repository

    async def evaluate(
        self,
        flag_key: str,
        user_id: str,
        context: Optional[dict] = None,
    ) -> FlagResult:
        """
        评估 Feature Flag (9 步流程)

        1. 获取 Flag 配置
        2. 检查 Flag 是否存在
        3. 检查 Flag 是否启用
        4. 检查用户白名单
        5. 检查用户黑名单
        6. 检查定向规则
        7. 计算灰度百分比
        8. 获取变体 (A/B 测试)
        9. 返回默认值
        """
        # Step 1: 获取 Flag
        flag = await self.repository.get_flag(flag_key)

        # Step 2: 不存在返回默认
        if flag is None:
            return FlagResult(enabled=False, source="not_found")

        # Step 3: 未启用返回默认
        if not flag.enabled:
            return FlagResult(enabled=False, source="disabled")

        # Step 4: 白名单检查
        if user_id in flag.whitelist:
            return FlagResult(enabled=True, source="whitelist")

        # Step 5: 黑名单检查
        if user_id in flag.blacklist:
            return FlagResult(enabled=False, source="blacklist")

        # Step 6: 定向规则检查
        if flag.targeting_rules:
            rule_result = self._evaluate_targeting_rules(
                flag.targeting_rules, user_id, context
            )
            if rule_result is not None:
                return rule_result

        # Step 7: 灰度百分比
        if flag.rollout_percentage > 0:
            in_rollout = self._is_in_rollout(user_id, flag_key, flag.rollout_percentage)
            if not in_rollout:
                return FlagResult(enabled=False, source="rollout_excluded")

        # Step 8: A/B 测试变体
        if flag.variants:
            variant = self._select_variant(user_id, flag_key, flag.variants)
            return FlagResult(enabled=True, source="variant", variant=variant)

        # Step 9: 默认启用
        return FlagResult(enabled=True, source="enabled")

    def _is_in_rollout(
        self,
        user_id: str,
        flag_key: str,
        percentage: int,
    ) -> bool:
        """基于哈希的确定性灰度分配"""
        hash_input = f"{user_id}:{flag_key}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = hash_value % 100
        return bucket < percentage

    def _select_variant(
        self,
        user_id: str,
        flag_key: str,
        variants: list,
    ) -> str:
        """确定性变体选择"""
        hash_input = f"{user_id}:{flag_key}:variant"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)

        total_weight = sum(v.get("weight", 1) for v in variants)
        bucket = hash_value % total_weight

        cumulative = 0
        for variant in variants:
            cumulative += variant.get("weight", 1)
            if bucket < cumulative:
                return variant["name"]

        return variants[0]["name"]

    def _evaluate_targeting_rules(
        self,
        rules: list,
        user_id: str,
        context: Optional[dict],
    ) -> Optional[FlagResult]:
        """评估定向规则"""
        for rule in rules:
            if self._match_rule(rule, user_id, context):
                return FlagResult(
                    enabled=rule.get("enabled", True),
                    source="targeting_rule",
                )
        return None
```

### §3.4 PriorityEvaluator

> 设计文档: [06-priority-rules.md](../06-priority-rules.md)

**文件**: `domains/entitlement/services/priority_evaluator.py`

**职责**: 7 层优先级权限计算

**实现状态**: 🔴 待实现

```python
from typing import Optional
from domains.entitlement.entities.permission import PermissionResult

class PriorityEvaluator:
    """
    7 层优先级评估器

    优先级 (高 → 低):
    1. Kill Switch (系统级禁用)
    2. Feature Flag (灰度/实验)
    3. User Override (用户级覆盖)
    4. Group Override (用户组覆盖)
    5. Workspace Override (工作区覆盖)
    6. Tier Config (Tier 配置)
    7. Fallback (兜底配置)
    """

    def __init__(
        self,
        config_service: "ConfigService",
        feature_flag_service: "FeatureFlagService",
        override_repository: "OverrideRepository",
        tier_service: "TierService",
    ):
        self.config_service = config_service
        self.feature_flag_service = feature_flag_service
        self.override_repository = override_repository
        self.tier_service = tier_service

    async def evaluate(
        self,
        user_id: str,
        feature_key: str,
        workspace_id: Optional[str] = None,
    ) -> PermissionResult:
        """执行 7 层优先级评估"""

        # Layer 1: Kill Switch
        kill_switch = await self.config_service.get_kill_switch(feature_key)
        if kill_switch is False:
            return PermissionResult(enabled=False, source="kill_switch")

        # Layer 2: Feature Flag
        flag_result = await self.feature_flag_service.evaluate(feature_key, user_id)
        if flag_result.source not in ("not_found", "disabled"):
            return PermissionResult(
                enabled=flag_result.enabled,
                source=f"feature_flag:{flag_result.source}",
            )

        # Layer 3: User Override
        user_override = await self.override_repository.get_user_override(
            user_id, feature_key
        )
        if user_override is not None:
            return PermissionResult(
                enabled=user_override.value,
                source="user_override",
                expires_at=user_override.expires_at,
            )

        # Layer 4: Group Override
        group_override = await self._get_effective_group_override(user_id, feature_key)
        if group_override is not None:
            return PermissionResult(
                enabled=group_override.value,
                source=f"group_override:{group_override.group_id}",
            )

        # Layer 5: Workspace Override
        if workspace_id:
            ws_override = await self.override_repository.get_workspace_override(
                workspace_id, feature_key
            )
            if ws_override is not None:
                return PermissionResult(
                    enabled=ws_override.value,
                    source="workspace_override",
                )

        # Layer 6: Tier Config
        tier = await self.tier_service.get_user_tier(user_id)
        tier_value = await self.tier_service.get_tier_feature(tier, feature_key)
        if tier_value is not None:
            return PermissionResult(
                enabled=tier_value,
                source=f"tier_config:{tier}",
            )

        # Layer 7: Fallback
        fallback = await self.config_service.get_fallback(feature_key)
        return PermissionResult(enabled=fallback, source="fallback")

    async def _get_effective_group_override(
        self,
        user_id: str,
        feature_key: str,
    ) -> Optional[Any]:
        """
        获取有效的用户组覆盖

        冲突解决策略 (参考 24-conflict-resolution.md):
        - 同时属于多个组时，取优先级最高的组
        """
        groups = await self.override_repository.get_user_groups(user_id)
        groups_sorted = sorted(groups, key=lambda g: g.priority, reverse=True)

        for group in groups_sorted:
            override = await self.override_repository.get_group_override(
                group.id, feature_key
            )
            if override is not None:
                return override

        return None
```

### §3.5 UserGroupService

> 设计文档: [08-user-groups.md](../08-user-groups.md)

**文件**: `domains/entitlement/services/user_group_service.py`

**实现状态**: 🔴 待实现

```python
class UserGroupService:
    """用户组服务"""

    async def create_group(self, name: str, group_type: str, **kwargs) -> UserGroup:
        """创建用户组"""

    async def add_member(self, group_id: str, user_id: str, added_by: str) -> None:
        """添加组成员"""

    async def remove_member(self, group_id: str, user_id: str) -> None:
        """移除组成员"""

    async def get_user_groups(self, user_id: str) -> list[UserGroup]:
        """获取用户所属的所有组"""

    async def set_group_override(
        self, group_id: str, feature_key: str, value: Any
    ) -> None:
        """设置组级别权限覆盖"""
```

### §3.6 ConfigVersionService

> 设计文档: [09-config-versioning.md](../09-config-versioning.md)

**文件**: `domains/entitlement/services/config_version_service.py`

**实现状态**: 🔴 待实现

```python
class ConfigVersionService:
    """配置版本服务"""

    async def save_version(
        self,
        config_key: str,
        value: dict,
        changed_by: str,
        reason: str,
    ) -> int:
        """保存配置新版本，返回版本号"""

    async def get_version(self, config_key: str, version: int) -> dict:
        """获取指定版本的配置"""

    async def get_history(
        self, config_key: str, limit: int = 10
    ) -> list[ConfigVersion]:
        """获取配置历史"""

    async def rollback(self, config_key: str, version: int, by: str) -> None:
        """回滚到指定版本"""
```

### §3.7 WorkspaceOverrideService

> 设计文档: [10-workspace-override.md](../10-workspace-override.md)

**文件**: `domains/entitlement/services/workspace_override_service.py`

**实现状态**: 🔴 待实现

```python
class WorkspaceOverrideService:
    """工作区覆盖服务"""

    async def set_override(
        self,
        workspace_id: str,
        feature_key: str,
        value: Any,
        granted_by: str,
        reason: str,
        expires_at: Optional[datetime] = None,
    ) -> None:
        """设置工作区级别权限覆盖"""

    async def remove_override(
        self, workspace_id: str, feature_key: str
    ) -> None:
        """移除工作区覆盖"""

    async def get_workspace_overrides(
        self, workspace_id: str
    ) -> dict[str, Any]:
        """获取工作区所有覆盖"""
```

---

## §4. 生命周期服务

### §4.1 TrialService

> 设计文档: [11-trial-expiration.md](../11-trial-expiration.md)

**文件**: `domains/entitlement/services/trial_service.py`

**实现状态**: 🔴 待实现

```python
from datetime import datetime, timedelta

TRIAL_DURATION_DAYS = 7

class TrialService:
    """试用期服务"""

    def __init__(self, repository: TrialRepository):
        self.repository = repository

    async def start_trial(self, user_id: str, feature_key: str) -> TrialRecord:
        """开始试用"""
        now = datetime.utcnow()
        expires_at = now + timedelta(days=TRIAL_DURATION_DAYS)

        return await self.repository.create_trial(
            user_id=user_id,
            feature_key=feature_key,
            started_at=now,
            expires_at=expires_at,
        )

    async def get_trial_status(
        self, user_id: str, feature_key: str
    ) -> Optional[TrialRecord]:
        """获取试用状态"""
        return await self.repository.get_trial(user_id, feature_key)

    async def is_trial_active(self, user_id: str, feature_key: str) -> bool:
        """检查试用是否有效"""
        trial = await self.get_trial_status(user_id, feature_key)
        if trial is None:
            return False
        return trial.status == "active" and trial.expires_at > datetime.utcnow()

    async def get_trial_remaining_days(
        self, user_id: str, feature_key: str
    ) -> Optional[int]:
        """获取剩余试用天数"""
        trial = await self.get_trial_status(user_id, feature_key)
        if trial is None or trial.status != "active":
            return None

        remaining = trial.expires_at - datetime.utcnow()
        return max(0, remaining.days)

    async def convert_trial(self, user_id: str, feature_key: str) -> None:
        """试用转正式 (用户订阅后调用)"""
        await self.repository.update_trial_status(
            user_id=user_id,
            feature_key=feature_key,
            status="converted",
            converted_at=datetime.utcnow(),
        )

    async def expire_trials(self) -> int:
        """批量过期试用 (定时任务调用)"""
        return await self.repository.expire_trials()
```

### §4.2 TierDowngradeService

> 设计文档: [12-tier-downgrade.md](../12-tier-downgrade.md)

**文件**: `domains/entitlement/services/tier_downgrade_service.py`

**实现状态**: 🔴 待实现

```python
class TierDowngradeService:
    """Tier 降级服务 - Graceful Degradation"""

    async def process_downgrade(
        self,
        user_id: str,
        from_tier: str,
        to_tier: str,
        reason: str,
    ) -> DowngradeResult:
        """
        处理 Tier 降级

        步骤:
        1. 计算受影响资源
        2. 应用 Graceful Degradation (只读而非删除)
        3. 记录降级日志
        4. 发送通知
        """

    async def get_affected_resources(
        self,
        user_id: str,
        from_tier: str,
        to_tier: str,
    ) -> AffectedResources:
        """计算降级影响的资源"""
        # 项目数超限
        # 页面数超限
        # 自定义素材超限

    async def apply_graceful_degradation(
        self,
        user_id: str,
        affected: AffectedResources,
    ) -> None:
        """应用优雅降级 - 资源变为只读"""
```

### §4.3 SubscriptionPauseService

> 设计文档: [13-subscription-pause.md](../13-subscription-pause.md)

**文件**: `domains/entitlement/services/subscription_pause_service.py`

**实现状态**: 🔴 待实现

```python
MAX_PAUSE_DAYS = 90

class SubscriptionPauseService:
    """订阅暂停服务"""

    async def pause_subscription(
        self,
        user_id: str,
        subscription_id: str,
        pause_days: int,
        reason: Optional[str] = None,
    ) -> PauseRecord:
        """暂停订阅"""
        if pause_days > MAX_PAUSE_DAYS:
            raise ValueError(f"Max pause duration is {MAX_PAUSE_DAYS} days")

        # 1. 调用 Stripe API 暂停
        # 2. 创建暂停记录
        # 3. 触发 Graceful Degradation

    async def resume_subscription(
        self, user_id: str, subscription_id: str
    ) -> None:
        """恢复订阅"""
        # 1. 调用 Stripe API 恢复
        # 2. 更新暂停记录
        # 3. 恢复用户权限

    async def get_pause_status(
        self, user_id: str, subscription_id: str
    ) -> Optional[PauseRecord]:
        """获取暂停状态"""

    async def auto_resume_expired(self) -> int:
        """自动恢复到期的暂停 (定时任务)"""
```

### §4.4 BillingCycleService

> 设计文档: [14-billing-cycle-switch.md](../14-billing-cycle-switch.md)

**文件**: `domains/entitlement/services/billing_cycle_service.py`

**实现状态**: 🔴 待实现

```python
class BillingCycleService:
    """账单周期切换服务"""

    async def switch_cycle(
        self,
        user_id: str,
        subscription_id: str,
        to_cycle: str,  # "monthly" or "yearly"
    ) -> CycleChangeResult:
        """
        切换账单周期

        月转年: 立即生效，按比例退款/补差价
        年转月: 周期结束后生效
        """

    async def calculate_proration(
        self,
        subscription_id: str,
        from_cycle: str,
        to_cycle: str,
    ) -> Decimal:
        """计算差价"""
```

### §4.5 CreditService

> 设计文档: [15-credits-lifecycle.md](../15-credits-lifecycle.md)

**文件**: `domains/entitlement/services/credit_service.py`

**实现状态**: 🔴 待实现

```python
from decimal import Decimal
from typing import Optional
from domains.entitlement.entities.credit import CreditPool, CreditTransaction

# 7 种积分来源
SOURCE_TYPES = [
    "subscription",     # 订阅月度积分
    "purchase",         # 购买积分
    "bonus_signup",     # 注册赠送
    "bonus_referral",   # 邀请奖励
    "bonus_campaign",   # 营销活动
    "compensation",     # 客服补偿
    "earning",          # 销售收入
]

# 扣费优先级 (FEFO)
DEDUCTION_PRIORITY = [
    "subscription",      # 先扣订阅 (有过期时间)
    "bonus_signup",
    "bonus_referral",
    "bonus_campaign",
    "purchase",
    "earning",
    "compensation",      # 最后扣补偿
]

class CreditService:
    """积分服务 - 二维模型 (source_type + expires_at)"""

    def __init__(self, repository: CreditRepository):
        self.repository = repository

    async def get_balance(self, user_id: str) -> int:
        """获取用户总积分余额"""
        pools = await self.repository.get_user_pools(user_id)
        return sum(p.balance for p in pools if p.balance > 0)

    async def get_balance_by_source(self, user_id: str) -> dict[str, int]:
        """按来源分类获取余额"""
        pools = await self.repository.get_user_pools(user_id)
        result = {source: 0 for source in SOURCE_TYPES}
        for pool in pools:
            if pool.balance > 0:
                result[pool.source_type] += pool.balance
        return result

    async def grant_credits(
        self,
        user_id: str,
        amount: int,
        source_type: str,
        source_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> CreditPool:
        """
        发放积分

        Args:
            source_type: 7 种来源之一
            source_id: 关联的来源记录 ID
            expires_at: 过期时间，None 表示永久
        """
        if source_type not in SOURCE_TYPES:
            raise ValueError(f"Invalid source_type: {source_type}")

        return await self.repository.create_pool(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            initial_amount=amount,
            balance=amount,
            expires_at=expires_at,
        )

    async def consume_credits(
        self,
        user_id: str,
        amount: int,
        description: str,
    ) -> tuple[bool, int]:
        """
        消耗积分 (FEFO 策略)

        Returns:
            (success, consumed): 是否成功，实际消耗数量
        """
        # 使用 RPC 函数保证原子性
        result = await self.repository.consume_fefo(
            user_id=user_id,
            amount=amount,
            description=description,
        )
        return result.success, result.consumed

    async def has_enough_credits(self, user_id: str, amount: int) -> bool:
        """检查余额是否足够"""
        balance = await self.get_balance(user_id)
        return balance >= amount

    async def get_transactions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CreditTransaction]:
        """获取交易历史"""
        return await self.repository.get_transactions(user_id, limit, offset)

    async def expire_credits(self) -> int:
        """过期积分处理 (定时任务)"""
        return await self.repository.expire_pools()

    async def deduct_for_refund(
        self,
        user_id: str,
        amount: int,
    ) -> tuple[int, int]:
        """
        退款积分扣回 (FEFO 逆序)

        Returns:
            (deducted, debt): 实际扣回数量，欠款数量
        """
        return await self.repository.deduct_for_refund(user_id, amount)
```

### §4.6 RenewalReminderService

> 设计文档: [16-renewal-reminders.md](../16-renewal-reminders.md)

**文件**: `domains/entitlement/services/renewal_reminder_service.py`

**实现状态**: 🔴 待实现

```python
REMINDER_DAYS = [7, 3, 1]  # 提前 N 天提醒

class RenewalReminderService:
    """续费提醒服务"""

    async def send_reminder(
        self,
        user_id: str,
        subscription_id: str,
        days_before: int,
    ) -> None:
        """发送续费提醒"""

    async def process_reminders(self) -> int:
        """处理待发送的提醒 (定时任务)"""
        # 查找 N 天后到期的订阅
        # 发送提醒邮件
        # 记录日志
```

### §4.7 InvoiceService

> 设计文档: [17-invoice-management.md](../17-invoice-management.md)

**文件**: `domains/entitlement/services/invoice_service.py`

**实现状态**: 🔴 待实现

```python
class InvoiceService:
    """发票服务"""

    async def create_invoice(
        self,
        user_id: str,
        invoice_type: str,
        line_items: list,
        amount: Decimal,
    ) -> Invoice:
        """创建发票"""

    async def get_invoices(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Invoice]:
        """获取发票列表"""

    async def download_pdf(self, invoice_id: str) -> str:
        """获取 PDF 下载链接"""

    async def sync_from_stripe(self, stripe_invoice_id: str) -> Invoice:
        """从 Stripe 同步发票"""
```

### §4.8 RefundService

> 设计文档: [18-refund-processing.md](../18-refund-processing.md)

**文件**: `domains/entitlement/services/refund_service.py`

**实现状态**: 🔴 待实现

```python
class RefundService:
    """退款服务"""

    def __init__(
        self,
        repository: RefundRepository,
        credit_service: CreditService,
        stripe_service: StripeService,
    ):
        self.repository = repository
        self.credit_service = credit_service
        self.stripe_service = stripe_service

    async def request_refund(
        self,
        user_id: str,
        transaction_id: str,
        reason: str,
        reason_detail: Optional[str] = None,
    ) -> Refund:
        """申请退款"""
        # 1. 验证退款条件
        # 2. 创建退款记录
        # 3. 自动审批或人工审核

    async def process_refund(self, refund_id: str) -> RefundResult:
        """
        处理退款

        步骤:
        1. 调用 Stripe 退款 API
        2. 扣回已发放积分 (FEFO 逆序)
        3. 更新订阅/Tier 状态
        4. 发送通知
        """
        refund = await self.repository.get(refund_id)

        # Stripe 退款
        await self.stripe_service.create_refund(
            payment_intent=refund.payment_intent_id,
            amount=refund.amount,
        )

        # 积分扣回
        deducted, debt = await self.credit_service.deduct_for_refund(
            user_id=refund.user_id,
            amount=refund.credits_to_deduct,
        )

        # 更新记录
        await self.repository.update(
            refund_id,
            status="completed",
            credits_deducted=deducted,
            credits_debt=debt,
        )

    async def get_refund_status(self, refund_id: str) -> Refund:
        """获取退款状态"""

    async def get_user_refunds(
        self, user_id: str, limit: int = 20
    ) -> list[Refund]:
        """获取用户退款历史"""
```

---

## §5. 营销扩展服务

### §5.1 PromotionService

> 设计文档: [19-promotions.md](../19-promotions.md)

**文件**: `domains/entitlement/services/promotion_service.py`

**实现状态**: 🔴 待实现

```python
class PromotionService:
    """促销服务"""

    async def validate_code(
        self,
        code: str,
        user_id: str,
        plan_type: Optional[str] = None,
    ) -> ValidationResult:
        """验证促销码"""

    async def apply_promotion(
        self,
        code: str,
        user_id: str,
        subscription_id: Optional[str] = None,
    ) -> ApplyResult:
        """应用促销"""

    async def create_promotion(self, **kwargs) -> Promotion:
        """创建促销活动 (管理员)"""

    async def deactivate_promotion(self, promotion_id: str) -> None:
        """停用促销活动"""
```

### §5.2 ReferralService

> 设计文档: [20-referral-rewards.md](../20-referral-rewards.md)

**文件**: `domains/entitlement/services/referral_service.py`

**实现状态**: 🔴 待实现

```python
REFERRER_REWARD = 50   # 邀请人奖励积分
REFEREE_REWARD = 50    # 被邀请人奖励积分

class ReferralService:
    """邀请奖励服务"""

    async def generate_code(self, user_id: str) -> str:
        """生成邀请码"""

    async def use_referral_code(
        self,
        referee_id: str,
        code: str,
    ) -> ReferralReward:
        """使用邀请码 (注册时)"""

    async def grant_rewards(
        self,
        referral_id: str,
        event: str,  # "signup", "first_purchase", "subscription"
    ) -> None:
        """发放奖励 (触发事件后)"""

    async def get_referral_stats(self, user_id: str) -> ReferralStats:
        """获取邀请统计"""
```

### §5.3 EducationDiscountService

> 设计文档: [21-education-discount.md](../21-education-discount.md)

**文件**: `domains/entitlement/services/education_discount_service.py`

**实现状态**: 🔴 待实现

```python
EDUCATION_DISCOUNT = 50  # 50% 折扣

class EducationDiscountService:
    """教育优惠服务"""

    async def submit_verification(
        self,
        user_id: str,
        institution_name: str,
        institution_type: str,
        verification_method: str,
        document_url: Optional[str] = None,
    ) -> EducationVerification:
        """提交验证申请"""

    async def approve_verification(
        self,
        verification_id: str,
        approved_by: str,
    ) -> None:
        """审批通过"""

    async def reject_verification(
        self,
        verification_id: str,
        rejected_by: str,
        reason: str,
    ) -> None:
        """审批拒绝"""

    async def is_eligible(self, user_id: str) -> bool:
        """检查是否有教育优惠资格"""

    async def get_discount(self, user_id: str) -> Optional[int]:
        """获取折扣比例"""
```

### §5.4 FreeQuotaService

> 设计文档: [22-free-quota.md](../22-free-quota.md)

**文件**: `domains/entitlement/services/free_quota_service.py`

**实现状态**: 🔴 待实现

```python
class FreeQuotaService:
    """免费配额服务"""

    async def check_quota(
        self,
        user_id: str,
        feature_key: str,
    ) -> tuple[int, int]:
        """
        检查免费配额

        Returns:
            (used, limit): 已使用, 限制
        """

    async def consume_quota(
        self,
        user_id: str,
        feature_key: str,
        amount: int = 1,
    ) -> bool:
        """消耗配额"""

    async def reset_quotas(self, period_type: str) -> int:
        """重置配额 (定时任务)"""
```

### §5.5 FeatureSunsetService

> 设计文档: [23-feature-sunset.md](../23-feature-sunset.md)

**文件**: `domains/entitlement/services/feature_sunset_service.py`

**实现状态**: 🔴 待实现

```python
class FeatureSunsetService:
    """功能下线服务"""

    async def schedule_sunset(
        self,
        feature_key: str,
        sunset_date: datetime,
        migration_guide: str,
    ) -> SunsetSchedule:
        """计划下线"""

    async def notify_affected_users(
        self,
        feature_key: str,
        days_before: int,
    ) -> int:
        """通知受影响用户"""

    async def execute_sunset(self, feature_key: str) -> None:
        """执行下线"""
```

### §5.6 ConflictResolutionService

> 设计文档: [24-conflict-resolution.md](../24-conflict-resolution.md)

**文件**: `domains/entitlement/services/conflict_resolution_service.py`

**实现状态**: 🔴 待实现

```python
class ConflictResolutionService:
    """权限冲突解决服务"""

    async def resolve_group_conflict(
        self,
        user_id: str,
        feature_key: str,
        groups: list[UserGroup],
    ) -> Any:
        """
        解决用户组冲突

        策略:
        1. 优先级最高的组生效
        2. 优先级相同时，最严格的值生效
        """

    async def resolve_workspace_conflict(
        self,
        user_id: str,
        feature_key: str,
        workspaces: list[str],
    ) -> Any:
        """解决工作区冲突"""
```

---

## 附录: 服务依赖图

```
PermissionService
├── PriorityEvaluator
│   ├── ConfigService
│   ├── FeatureFlagService
│   ├── OverrideRepository
│   └── TierService
├── TierService
│   └── TierRepository
└── FeatureFlagService
    └── FeatureFlagRepository

CreditService
└── CreditRepository

RefundService
├── RefundRepository
├── CreditService
└── StripeService
```

---

**END OF DOCUMENT**
