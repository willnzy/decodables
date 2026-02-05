# 后端 Repository 层实现

> **版本**: v1.0
> **日期**: 2026-02-04
> **状态**: 🔴 待实现
> **代码位置**: `decodables/infrastructure/entitlement/`

---

## 相关设计文档

| 设计文档 | 本文档章节 |
|----------|-----------|
| 02-tier-config.md | §2.1 |
| 04-feature-flag-engine.md | §2.2 |
| 08-user-groups.md | §2.3 |
| 09-config-versioning.md | §2.4 |
| 10-workspace-override.md | §2.5 |
| 11-trial-expiration.md | §3.1 |
| 12-tier-downgrade.md | §3.2 |
| 13-subscription-pause.md | §3.3 |
| 14-billing-cycle-switch.md | §3.4 |
| 15-credits-lifecycle.md | §3.5 |
| 17-invoice-management.md | §3.6 |
| 18-refund-processing.md | §3.7 |
| 19-promotions.md | §4.1 |
| 20-referral-rewards.md | §4.2 |
| 21-education-discount.md | §4.3 |

---

## 目录

- [§1. 架构概述](#1-架构概述)
- [§2. 核心配置 Repository](#2-核心配置-repository)
  - [§2.1 TierRepository](#21-tierrepository)
  - [§2.2 FeatureFlagRepository](#22-featureflagrepository)
  - [§2.3 UserGroupRepository](#23-usergrouprepository)
  - [§2.4 ConfigVersionRepository](#24-configversionrepository)
  - [§2.5 OverrideRepository](#25-overriderepository)
- [§3. 生命周期 Repository](#3-生命周期-repository)
  - [§3.1 TrialRepository](#31-trialrepository)
  - [§3.2 TierDowngradeRepository](#32-tierdowngraderepository)
  - [§3.3 SubscriptionPauseRepository](#33-subscriptionpauserepository)
  - [§3.4 BillingCycleRepository](#34-billingcyclerepository)
  - [§3.5 CreditRepository](#35-creditrepository)
  - [§3.6 InvoiceRepository](#36-invoicerepository)
  - [§3.7 RefundRepository](#37-refundrepository)
- [§4. 营销扩展 Repository](#4-营销扩展-repository)
  - [§4.1 PromotionRepository](#41-promotionrepository)
  - [§4.2 ReferralRepository](#42-referralrepository)
  - [§4.3 EducationVerificationRepository](#43-educationverificationrepository)

---

## §1. 架构概述

### 1.1 Repository 模式

```
domains/entitlement/repositories/   → 接口定义 (Abstract)
infrastructure/entitlement/         → 具体实现 (Supabase)
```

### 1.2 目录结构

```
decodables/
├── domains/entitlement/repositories/     # 接口
│   ├── __init__.py
│   ├── tier_repository.py
│   ├── feature_flag_repository.py
│   ├── credit_repository.py
│   └── ...
└── infrastructure/entitlement/           # 实现
    ├── __init__.py
    ├── tier_repository_impl.py
    ├── feature_flag_repository_impl.py
    ├── credit_repository_impl.py
    └── ...
```

### 1.3 基类定义

```python
# domains/entitlement/repositories/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List

T = TypeVar("T")

class BaseRepository(ABC, Generic[T]):
    """Repository 基类"""

    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        """根据 ID 获取"""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """创建"""
        pass

    @abstractmethod
    async def update(self, id: str, **kwargs) -> T:
        """更新"""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """删除"""
        pass
```

### 1.4 Supabase Client 注入

```python
# infrastructure/entitlement/base.py
from supabase import AsyncClient

class SupabaseRepository:
    """Supabase Repository 基类"""

    def __init__(self, client: AsyncClient):
        self.client = client

    async def _execute_rpc(self, function_name: str, params: dict):
        """执行 RPC 函数"""
        return await self.client.rpc(function_name, params).execute()
```

---

## §2. 核心配置 Repository

### §2.1 TierRepository

> 设计文档: [02-tier-config.md](../02-tier-config.md)

**接口定义**: `domains/entitlement/repositories/tier_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict
from domains.entitlement.entities.tier import TierConfig

class TierRepository(ABC):
    """Tier 配置 Repository 接口"""

    @abstractmethod
    async def get_user_tier(self, user_id: str) -> str:
        """获取用户当前 Tier"""
        pass

    @abstractmethod
    async def get_all_tier_configs(self) -> Dict[str, TierConfig]:
        """获取所有 Tier 配置"""
        pass

    @abstractmethod
    async def get_tier_config(self, tier: str) -> Optional[TierConfig]:
        """获取单个 Tier 配置"""
        pass

    @abstractmethod
    async def update_tier_config(self, tier: str, config: dict) -> TierConfig:
        """更新 Tier 配置"""
        pass
```

**Supabase 实现**: `infrastructure/entitlement/tier_repository_impl.py`

```python
from infrastructure.entitlement.base import SupabaseRepository
from domains.entitlement.repositories.tier_repository import TierRepository
from domains.entitlement.entities.tier import TierConfig

class TierRepositoryImpl(SupabaseRepository, TierRepository):
    """Tier Repository Supabase 实现"""

    async def get_user_tier(self, user_id: str) -> str:
        result = await self.client.table("profiles") \
            .select("tier") \
            .eq("id", user_id) \
            .single() \
            .execute()
        return result.data.get("tier", "t1")

    async def get_all_tier_configs(self) -> Dict[str, TierConfig]:
        # 从 system_configs 获取 TIER_FEATURES 和 TIER_QUOTAS
        features_result = await self.client.table("system_configs") \
            .select("value") \
            .eq("key", "TIER_FEATURES") \
            .single() \
            .execute()

        quotas_result = await self.client.table("system_configs") \
            .select("value") \
            .eq("key", "TIER_QUOTAS") \
            .single() \
            .execute()

        features = features_result.data.get("value", {})
        quotas = quotas_result.data.get("value", {})

        return {
            tier: TierConfig(
                tier=tier,
                features=features.get(tier, {}),
                quotas=quotas.get(tier, {}),
            )
            for tier in ["t1", "t2", "t3", "t4"]
        }

    async def get_tier_config(self, tier: str) -> Optional[TierConfig]:
        configs = await self.get_all_tier_configs()
        return configs.get(tier)

    async def update_tier_config(self, tier: str, config: dict) -> TierConfig:
        # 更新 TIER_FEATURES
        await self.client.rpc("update_tier_config", {
            "p_tier": tier,
            "p_config": config
        }).execute()
        return await self.get_tier_config(tier)
```

### §2.2 FeatureFlagRepository

> 设计文档: [04-feature-flag-engine.md](../04-feature-flag-engine.md)

**接口定义**: `domains/entitlement/repositories/feature_flag_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from domains.entitlement.entities.feature_flag import FeatureFlag

class FeatureFlagRepository(ABC):
    """Feature Flag Repository 接口"""

    @abstractmethod
    async def get_flag(self, key: str) -> Optional[FeatureFlag]:
        """获取 Flag"""
        pass

    @abstractmethod
    async def get_all_flags(self) -> List[FeatureFlag]:
        """获取所有 Flag"""
        pass

    @abstractmethod
    async def create_flag(self, flag: FeatureFlag) -> FeatureFlag:
        """创建 Flag"""
        pass

    @abstractmethod
    async def update_flag(self, key: str, **kwargs) -> FeatureFlag:
        """更新 Flag"""
        pass

    @abstractmethod
    async def delete_flag(self, key: str) -> bool:
        """删除 Flag"""
        pass
```

**Supabase 实现**: `infrastructure/entitlement/feature_flag_repository_impl.py`

```python
class FeatureFlagRepositoryImpl(SupabaseRepository, FeatureFlagRepository):
    """Feature Flag Repository Supabase 实现"""

    async def get_flag(self, key: str) -> Optional[FeatureFlag]:
        result = await self.client.table("feature_flags") \
            .select("*") \
            .eq("key", key) \
            .maybeSingle() \
            .execute()

        if not result.data:
            return None

        return FeatureFlag(**result.data)

    async def get_all_flags(self) -> List[FeatureFlag]:
        result = await self.client.table("feature_flags") \
            .select("*") \
            .execute()

        return [FeatureFlag(**row) for row in result.data]

    async def create_flag(self, flag: FeatureFlag) -> FeatureFlag:
        result = await self.client.table("feature_flags") \
            .insert(flag.dict()) \
            .execute()

        return FeatureFlag(**result.data[0])

    async def update_flag(self, key: str, **kwargs) -> FeatureFlag:
        result = await self.client.table("feature_flags") \
            .update(kwargs) \
            .eq("key", key) \
            .execute()

        return FeatureFlag(**result.data[0])

    async def delete_flag(self, key: str) -> bool:
        await self.client.table("feature_flags") \
            .delete() \
            .eq("key", key) \
            .execute()
        return True
```

### §2.3 UserGroupRepository

> 设计文档: [08-user-groups.md](../08-user-groups.md)

**接口定义**: `domains/entitlement/repositories/user_group_repository.py`

```python
from abc import ABC, abstractmethod
from typing import List
from domains.entitlement.entities.user_group import UserGroup

class UserGroupRepository(ABC):
    """用户组 Repository 接口"""

    @abstractmethod
    async def get_group(self, group_id: str) -> Optional[UserGroup]:
        """获取用户组"""
        pass

    @abstractmethod
    async def get_user_groups(self, user_id: str) -> List[UserGroup]:
        """获取用户所属的所有组"""
        pass

    @abstractmethod
    async def add_member(self, group_id: str, user_id: str, added_by: str) -> None:
        """添加组成员"""
        pass

    @abstractmethod
    async def remove_member(self, group_id: str, user_id: str) -> None:
        """移除组成员"""
        pass

    @abstractmethod
    async def get_group_members(self, group_id: str) -> List[str]:
        """获取组成员列表"""
        pass
```

**Supabase 实现**:

```python
class UserGroupRepositoryImpl(SupabaseRepository, UserGroupRepository):

    async def get_user_groups(self, user_id: str) -> List[UserGroup]:
        result = await self.client.table("user_group_members") \
            .select("group_id, user_groups(*)") \
            .eq("user_id", user_id) \
            .execute()

        return [UserGroup(**row["user_groups"]) for row in result.data]

    async def add_member(self, group_id: str, user_id: str, added_by: str) -> None:
        await self.client.table("user_group_members") \
            .insert({
                "group_id": group_id,
                "user_id": user_id,
                "added_by": added_by,
            }) \
            .execute()

    async def remove_member(self, group_id: str, user_id: str) -> None:
        await self.client.table("user_group_members") \
            .delete() \
            .eq("group_id", group_id) \
            .eq("user_id", user_id) \
            .execute()
```

### §2.4 ConfigVersionRepository

> 设计文档: [09-config-versioning.md](../09-config-versioning.md)

**接口定义**: `domains/entitlement/repositories/config_version_repository.py`

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from domains.entitlement.entities.config_version import ConfigVersion

class ConfigVersionRepository(ABC):
    """配置版本 Repository 接口"""

    @abstractmethod
    async def save_version(
        self,
        config_key: str,
        value: dict,
        changed_by: str,
        reason: str,
    ) -> ConfigVersion:
        """保存新版本"""
        pass

    @abstractmethod
    async def get_version(self, config_key: str, version: int) -> Optional[ConfigVersion]:
        """获取指定版本"""
        pass

    @abstractmethod
    async def get_latest_version(self, config_key: str) -> Optional[ConfigVersion]:
        """获取最新版本"""
        pass

    @abstractmethod
    async def get_history(self, config_key: str, limit: int = 10) -> List[ConfigVersion]:
        """获取版本历史"""
        pass
```

### §2.5 OverrideRepository

> 设计文档: [02-tier-config.md](../02-tier-config.md), [10-workspace-override.md](../10-workspace-override.md)

**接口定义**: `domains/entitlement/repositories/override_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, Any
from domains.entitlement.entities.override import UserOverride, GroupOverride, WorkspaceOverride

class OverrideRepository(ABC):
    """权限覆盖 Repository 接口"""

    # User Override
    @abstractmethod
    async def get_user_override(
        self, user_id: str, feature_key: str
    ) -> Optional[UserOverride]:
        """获取用户级覆盖"""
        pass

    @abstractmethod
    async def set_user_override(
        self,
        user_id: str,
        feature_key: str,
        value: Any,
        **kwargs
    ) -> UserOverride:
        """设置用户级覆盖"""
        pass

    @abstractmethod
    async def remove_user_override(self, user_id: str, feature_key: str) -> None:
        """移除用户级覆盖"""
        pass

    # Group Override
    @abstractmethod
    async def get_group_override(
        self, group_id: str, feature_key: str
    ) -> Optional[GroupOverride]:
        """获取组级覆盖"""
        pass

    @abstractmethod
    async def get_user_groups(self, user_id: str) -> List[UserGroup]:
        """获取用户所属组"""
        pass

    # Workspace Override
    @abstractmethod
    async def get_workspace_override(
        self, workspace_id: str, feature_key: str
    ) -> Optional[WorkspaceOverride]:
        """获取工作区级覆盖"""
        pass
```

**Supabase 实现**:

```python
class OverrideRepositoryImpl(SupabaseRepository, OverrideRepository):

    async def get_user_override(
        self, user_id: str, feature_key: str
    ) -> Optional[UserOverride]:
        result = await self.client.table("user_feature_overrides") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("feature_key", feature_key) \
            .maybeSingle() \
            .execute()

        if not result.data:
            return None

        # 检查是否过期
        if result.data.get("expires_at"):
            expires_at = datetime.fromisoformat(result.data["expires_at"])
            if expires_at < datetime.utcnow():
                return None

        return UserOverride(**result.data)

    async def set_user_override(
        self,
        user_id: str,
        feature_key: str,
        value: Any,
        **kwargs
    ) -> UserOverride:
        data = {
            "user_id": user_id,
            "feature_key": feature_key,
            "override_value": {"enabled": value},
            **kwargs,
        }

        result = await self.client.table("user_feature_overrides") \
            .upsert(data, on_conflict="user_id,feature_key") \
            .execute()

        return UserOverride(**result.data[0])
```

---

## §3. 生命周期 Repository

### §3.1 TrialRepository

> 设计文档: [11-trial-expiration.md](../11-trial-expiration.md)

**接口定义**:

```python
class TrialRepository(ABC):
    """试用期 Repository 接口"""

    @abstractmethod
    async def create_trial(
        self,
        user_id: str,
        feature_key: str,
        started_at: datetime,
        expires_at: datetime,
    ) -> TrialRecord:
        pass

    @abstractmethod
    async def get_trial(self, user_id: str, feature_key: str) -> Optional[TrialRecord]:
        pass

    @abstractmethod
    async def update_trial_status(
        self,
        user_id: str,
        feature_key: str,
        status: str,
        **kwargs
    ) -> None:
        pass

    @abstractmethod
    async def expire_trials(self) -> int:
        """批量过期试用，返回受影响数量"""
        pass
```

### §3.2 TierDowngradeRepository

> 设计文档: [12-tier-downgrade.md](../12-tier-downgrade.md)

**接口定义**:

```python
class TierDowngradeRepository(ABC):
    """Tier 降级日志 Repository 接口"""

    @abstractmethod
    async def create_log(
        self,
        user_id: str,
        from_tier: str,
        to_tier: str,
        reason: str,
        affected_resources: dict,
    ) -> TierDowngradeLog:
        pass

    @abstractmethod
    async def get_user_logs(
        self, user_id: str, limit: int = 10
    ) -> List[TierDowngradeLog]:
        pass
```

### §3.3 SubscriptionPauseRepository

> 设计文档: [13-subscription-pause.md](../13-subscription-pause.md)

**接口定义**:

```python
class SubscriptionPauseRepository(ABC):
    """订阅暂停 Repository 接口"""

    @abstractmethod
    async def create_pause(
        self,
        user_id: str,
        subscription_id: str,
        resume_at: datetime,
        reason: Optional[str] = None,
    ) -> PauseRecord:
        pass

    @abstractmethod
    async def get_pause(
        self, user_id: str, subscription_id: str
    ) -> Optional[PauseRecord]:
        pass

    @abstractmethod
    async def update_pause(self, pause_id: str, **kwargs) -> PauseRecord:
        pass

    @abstractmethod
    async def get_expired_pauses(self) -> List[PauseRecord]:
        """获取需要自动恢复的暂停"""
        pass
```

### §3.4 BillingCycleRepository

> 设计文档: [14-billing-cycle-switch.md](../14-billing-cycle-switch.md)

**接口定义**:

```python
class BillingCycleRepository(ABC):
    """账单周期 Repository 接口"""

    @abstractmethod
    async def create_change(
        self,
        user_id: str,
        subscription_id: str,
        from_cycle: str,
        to_cycle: str,
        effective_at: datetime,
        proration_amount: Optional[Decimal] = None,
    ) -> BillingCycleChange:
        pass

    @abstractmethod
    async def get_changes(
        self, user_id: str, limit: int = 10
    ) -> List[BillingCycleChange]:
        pass
```

### §3.5 CreditRepository

> 设计文档: [15-credits-lifecycle.md](../15-credits-lifecycle.md)

**接口定义**: `domains/entitlement/repositories/credit_repository.py`

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
from domains.entitlement.entities.credit import CreditPool, CreditTransaction

@dataclass
class ConsumeResult:
    success: bool
    consumed: int
    remaining_balance: int
    pools_affected: List[dict]

@dataclass
class DeductResult:
    deducted: int
    debt: int

class CreditRepository(ABC):
    """积分 Repository 接口"""

    @abstractmethod
    async def get_user_pools(self, user_id: str) -> List[CreditPool]:
        """获取用户所有积分池"""
        pass

    @abstractmethod
    async def create_pool(
        self,
        user_id: str,
        source_type: str,
        initial_amount: int,
        balance: int,
        source_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> CreditPool:
        """创建积分池"""
        pass

    @abstractmethod
    async def consume_fefo(
        self,
        user_id: str,
        amount: int,
        description: str,
    ) -> ConsumeResult:
        """FEFO 方式消耗积分"""
        pass

    @abstractmethod
    async def deduct_for_refund(
        self,
        user_id: str,
        amount: int,
    ) -> DeductResult:
        """退款积分扣回 (FEFO 逆序)"""
        pass

    @abstractmethod
    async def get_transactions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CreditTransaction]:
        """获取交易历史"""
        pass

    @abstractmethod
    async def expire_pools(self) -> int:
        """过期积分处理"""
        pass
```

**Supabase 实现**: `infrastructure/entitlement/credit_repository_impl.py`

```python
class CreditRepositoryImpl(SupabaseRepository, CreditRepository):

    async def get_user_pools(self, user_id: str) -> List[CreditPool]:
        result = await self.client.table("credit_pools") \
            .select("*") \
            .eq("user_id", user_id) \
            .gt("balance", 0) \
            .execute()

        return [CreditPool(**row) for row in result.data]

    async def create_pool(
        self,
        user_id: str,
        source_type: str,
        initial_amount: int,
        balance: int,
        source_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> CreditPool:
        data = {
            "user_id": user_id,
            "source_type": source_type,
            "source_id": source_id,
            "initial_amount": initial_amount,
            "balance": balance,
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

        result = await self.client.table("credit_pools") \
            .insert(data) \
            .execute()

        return CreditPool(**result.data[0])

    async def consume_fefo(
        self,
        user_id: str,
        amount: int,
        description: str,
    ) -> ConsumeResult:
        """调用 RPC 函数执行 FEFO 扣费"""
        result = await self.client.rpc("consume_credits_fefo", {
            "p_user_id": user_id,
            "p_amount": amount,
            "p_description": description,
        }).execute()

        data = result.data[0]
        return ConsumeResult(
            success=data["success"],
            consumed=data["consumed"],
            remaining_balance=data["remaining_balance"],
            pools_affected=data["pools_affected"],
        )

    async def deduct_for_refund(
        self,
        user_id: str,
        amount: int,
    ) -> DeductResult:
        """调用 RPC 函数执行退款扣回"""
        result = await self.client.rpc("deduct_credits_for_refund", {
            "p_user_id": user_id,
            "p_amount": amount,
        }).execute()

        data = result.data[0]
        return DeductResult(
            deducted=data["deducted"],
            debt=data["remaining_debt"],
        )

    async def get_transactions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CreditTransaction]:
        result = await self.client.table("credit_transactions") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        return [CreditTransaction(**row) for row in result.data]

    async def expire_pools(self) -> int:
        """过期积分处理"""
        result = await self.client.rpc("expire_credit_pools").execute()
        return result.data.get("expired_count", 0)
```

### §3.6 InvoiceRepository

> 设计文档: [17-invoice-management.md](../17-invoice-management.md)

**接口定义**:

```python
class InvoiceRepository(ABC):
    """发票 Repository 接口"""

    @abstractmethod
    async def create(self, invoice: Invoice) -> Invoice:
        pass

    @abstractmethod
    async def get(self, invoice_id: str) -> Optional[Invoice]:
        pass

    @abstractmethod
    async def get_by_stripe_id(self, stripe_invoice_id: str) -> Optional[Invoice]:
        pass

    @abstractmethod
    async def get_user_invoices(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> List[Invoice]:
        pass

    @abstractmethod
    async def update(self, invoice_id: str, **kwargs) -> Invoice:
        pass
```

### §3.7 RefundRepository

> 设计文档: [18-refund-processing.md](../18-refund-processing.md)

**接口定义**:

```python
class RefundRepository(ABC):
    """退款 Repository 接口"""

    @abstractmethod
    async def create(self, refund: Refund) -> Refund:
        pass

    @abstractmethod
    async def get(self, refund_id: str) -> Optional[Refund]:
        pass

    @abstractmethod
    async def get_user_refunds(
        self, user_id: str, limit: int = 20
    ) -> List[Refund]:
        pass

    @abstractmethod
    async def update(self, refund_id: str, **kwargs) -> Refund:
        pass

    @abstractmethod
    async def get_pending_refunds(self) -> List[Refund]:
        """获取待处理的退款"""
        pass
```

---

## §4. 营销扩展 Repository

### §4.1 PromotionRepository

> 设计文档: [19-promotions.md](../19-promotions.md)

**接口定义**:

```python
class PromotionRepository(ABC):
    """促销 Repository 接口"""

    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[Promotion]:
        pass

    @abstractmethod
    async def create(self, promotion: Promotion) -> Promotion:
        pass

    @abstractmethod
    async def increment_uses(self, promotion_id: str) -> None:
        pass

    @abstractmethod
    async def create_user_promotion(
        self,
        user_id: str,
        promotion_id: str,
        **kwargs
    ) -> UserPromotion:
        pass

    @abstractmethod
    async def get_user_promotions(self, user_id: str) -> List[UserPromotion]:
        pass
```

### §4.2 ReferralRepository

> 设计文档: [20-referral-rewards.md](../20-referral-rewards.md)

**接口定义**:

```python
class ReferralRepository(ABC):
    """邀请 Repository 接口"""

    @abstractmethod
    async def create_code(self, user_id: str, code: str) -> ReferralCode:
        pass

    @abstractmethod
    async def get_code_by_value(self, code: str) -> Optional[ReferralCode]:
        pass

    @abstractmethod
    async def get_user_code(self, user_id: str) -> Optional[ReferralCode]:
        pass

    @abstractmethod
    async def create_reward(
        self,
        referrer_id: str,
        referee_id: str,
        referral_code_id: str,
        **kwargs
    ) -> ReferralReward:
        pass

    @abstractmethod
    async def get_referrer_rewards(self, user_id: str) -> List[ReferralReward]:
        pass

    @abstractmethod
    async def update_reward(self, reward_id: str, **kwargs) -> ReferralReward:
        pass
```

### §4.3 EducationVerificationRepository

> 设计文档: [21-education-discount.md](../21-education-discount.md)

**接口定义**:

```python
class EducationVerificationRepository(ABC):
    """教育验证 Repository 接口"""

    @abstractmethod
    async def create(self, verification: EducationVerification) -> EducationVerification:
        pass

    @abstractmethod
    async def get(self, verification_id: str) -> Optional[EducationVerification]:
        pass

    @abstractmethod
    async def get_user_verification(self, user_id: str) -> Optional[EducationVerification]:
        pass

    @abstractmethod
    async def update(self, verification_id: str, **kwargs) -> EducationVerification:
        pass

    @abstractmethod
    async def get_pending_verifications(self) -> List[EducationVerification]:
        """获取待审核的验证"""
        pass
```

---

## 附录: 依赖注入配置

```python
# infrastructure/entitlement/container.py
from dependency_injector import containers, providers
from infrastructure.entitlement.tier_repository_impl import TierRepositoryImpl
from infrastructure.entitlement.feature_flag_repository_impl import FeatureFlagRepositoryImpl
from infrastructure.entitlement.credit_repository_impl import CreditRepositoryImpl
# ... 其他导入

class EntitlementContainer(containers.DeclarativeContainer):
    """Entitlement 模块依赖注入容器"""

    supabase_client = providers.Dependency()

    # Repositories
    tier_repository = providers.Singleton(
        TierRepositoryImpl,
        client=supabase_client,
    )

    feature_flag_repository = providers.Singleton(
        FeatureFlagRepositoryImpl,
        client=supabase_client,
    )

    credit_repository = providers.Singleton(
        CreditRepositoryImpl,
        client=supabase_client,
    )

    # ... 其他 Repository
```

---

**END OF DOCUMENT**
