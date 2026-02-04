# 后端 API 端点实现

> **版本**: v1.0
> **日期**: 2026-02-04
> **状态**: 🔴 待实现
> **代码位置**: `decodables/api/routers/entitlement/`

---

## 相关设计文档

| 设计文档 | 本文档章节 |
|----------|-----------|
| 02-tier-config.md | §2.1 |
| 04-feature-flag-engine.md | §2.2 |
| 08-user-groups.md | §2.3 |
| 10-workspace-override.md | §2.4 |
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
- [§2. 核心配置 API](#2-核心配置-api)
  - [§2.1 Tier API](#21-tier-api)
  - [§2.2 Feature Flag API](#22-feature-flag-api)
  - [§2.3 User Group API](#23-user-group-api)
  - [§2.4 Workspace Override API](#24-workspace-override-api)
- [§3. 生命周期 API](#3-生命周期-api)
  - [§3.1 Trial API](#31-trial-api)
  - [§3.2 Tier Downgrade API](#32-tier-downgrade-api)
  - [§3.3 Subscription Pause API](#33-subscription-pause-api)
  - [§3.4 Billing Cycle API](#34-billing-cycle-api)
  - [§3.5 Credits API](#35-credits-api)
  - [§3.6 Invoice API](#36-invoice-api)
  - [§3.7 Refund API](#37-refund-api)
- [§4. 营销扩展 API](#4-营销扩展-api)
  - [§4.1 Promotion API](#41-promotion-api)
  - [§4.2 Referral API](#42-referral-api)
  - [§4.3 Education Discount API](#43-education-discount-api)

---

## §1. 架构概述

### 1.1 目录结构

```
decodables/api/routers/entitlement/
├── __init__.py
├── tier.py              # Tier 相关
├── feature_flags.py     # Feature Flag
├── credits.py           # 积分
├── invoices.py          # 发票
├── refunds.py           # 退款
├── promotions.py        # 促销
├── referrals.py         # 邀请
└── admin/               # 管理员 API
    ├── __init__.py
    ├── tier_admin.py
    ├── flags_admin.py
    └── credits_admin.py
```

### 1.2 路由注册

```python
# api/routers/entitlement/__init__.py
from fastapi import APIRouter
from .tier import router as tier_router
from .feature_flags import router as feature_flags_router
from .credits import router as credits_router
from .invoices import router as invoices_router
from .refunds import router as refunds_router
from .promotions import router as promotions_router
from .referrals import router as referrals_router

entitlement_router = APIRouter(prefix="/entitlement", tags=["Entitlement"])

entitlement_router.include_router(tier_router)
entitlement_router.include_router(feature_flags_router)
entitlement_router.include_router(credits_router)
entitlement_router.include_router(invoices_router)
entitlement_router.include_router(refunds_router)
entitlement_router.include_router(promotions_router)
entitlement_router.include_router(referrals_router)
```

### 1.3 通用响应格式

```python
# api/schemas/common.py
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int
    has_more: bool
```

---

## §2. 核心配置 API

### §2.1 Tier API

> 设计文档: [02-tier-config.md](../02-tier-config.md)

**路由**: `/api/v1/entitlement/tier`

**文件**: `api/routers/entitlement/tier.py`

```python
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user
from api.schemas.entitlement.tier import (
    TierConfigResponse,
    UserTierResponse,
    PermissionCheckRequest,
    PermissionCheckResponse,
)
from application.entitlement.tier_use_case import TierUseCase

router = APIRouter(prefix="/tier", tags=["Tier"])


@router.get("/me", response_model=UserTierResponse)
async def get_my_tier(
    current_user = Depends(get_current_user),
    use_case: TierUseCase = Depends(),
):
    """
    获取当前用户的 Tier 信息

    Returns:
        - tier: str (t1/t2/t3/t4)
        - display_name: str
        - features: dict
        - quotas: dict
    """
    return await use_case.get_user_tier_info(current_user.id)


@router.get("/config", response_model=TierConfigResponse)
async def get_tier_config(
    tier: str,
    use_case: TierUseCase = Depends(),
):
    """
    获取指定 Tier 的配置

    Query Params:
        - tier: t1/t2/t3/t4
    """
    return await use_case.get_tier_config(tier)


@router.post("/check-permission", response_model=PermissionCheckResponse)
async def check_permission(
    request: PermissionCheckRequest,
    current_user = Depends(get_current_user),
    use_case: TierUseCase = Depends(),
):
    """
    检查用户权限

    Body:
        - feature_key: str
        - workspace_id: Optional[str]

    Returns:
        - enabled: bool | "trial"
        - source: str
        - quota: Optional[int]
        - expires_at: Optional[datetime]
    """
    return await use_case.check_permission(
        user_id=current_user.id,
        feature_key=request.feature_key,
        workspace_id=request.workspace_id,
    )


@router.get("/quotas", response_model=dict)
async def get_my_quotas(
    current_user = Depends(get_current_user),
    use_case: TierUseCase = Depends(),
):
    """
    获取当前用户的配额使用情况

    Returns:
        {
            "max_projects": { "used": 5, "limit": 50 },
            "max_pages_per_project": { "used": 12, "limit": 24 },
            "max_custom_assets": { "used": 0, "limit": 0 }
        }
    """
    return await use_case.get_user_quotas(current_user.id)
```

### §2.2 Feature Flag API

> 设计文档: [04-feature-flag-engine.md](../04-feature-flag-engine.md)

**路由**: `/api/v1/entitlement/flags`

**文件**: `api/routers/entitlement/feature_flags.py`

```python
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user
from api.schemas.entitlement.feature_flag import (
    FlagEvaluateRequest,
    FlagEvaluateResponse,
    FlagBatchEvaluateRequest,
    FlagBatchEvaluateResponse,
)
from application.entitlement.feature_flag_use_case import FeatureFlagUseCase

router = APIRouter(prefix="/flags", tags=["Feature Flags"])


@router.post("/evaluate", response_model=FlagEvaluateResponse)
async def evaluate_flag(
    request: FlagEvaluateRequest,
    current_user = Depends(get_current_user),
    use_case: FeatureFlagUseCase = Depends(),
):
    """
    评估单个 Feature Flag

    Body:
        - flag_key: str
        - context: Optional[dict]

    Returns:
        - enabled: bool
        - source: str
        - variant: Optional[str]
    """
    return await use_case.evaluate(
        flag_key=request.flag_key,
        user_id=current_user.id,
        context=request.context,
    )


@router.post("/evaluate-batch", response_model=FlagBatchEvaluateResponse)
async def evaluate_flags_batch(
    request: FlagBatchEvaluateRequest,
    current_user = Depends(get_current_user),
    use_case: FeatureFlagUseCase = Depends(),
):
    """
    批量评估多个 Feature Flag

    Body:
        - flag_keys: list[str]
        - context: Optional[dict]

    Returns:
        - results: dict[str, FlagResult]
    """
    return await use_case.evaluate_batch(
        flag_keys=request.flag_keys,
        user_id=current_user.id,
        context=request.context,
    )
```

### §2.3 User Group API

> 设计文档: [08-user-groups.md](../08-user-groups.md)

**路由**: `/api/v1/entitlement/groups`

**文件**: `api/routers/entitlement/user_groups.py`

```python
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user
from api.schemas.entitlement.user_group import UserGroupResponse
from application.entitlement.user_group_use_case import UserGroupUseCase

router = APIRouter(prefix="/groups", tags=["User Groups"])


@router.get("/me", response_model=list[UserGroupResponse])
async def get_my_groups(
    current_user = Depends(get_current_user),
    use_case: UserGroupUseCase = Depends(),
):
    """获取当前用户所属的用户组"""
    return await use_case.get_user_groups(current_user.id)
```

### §2.4 Workspace Override API

> 设计文档: [10-workspace-override.md](../10-workspace-override.md)

**路由**: `/api/v1/entitlement/workspace-overrides`

**文件**: `api/routers/entitlement/workspace_overrides.py`

```python
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user, get_workspace_member
from api.schemas.entitlement.workspace_override import (
    WorkspaceOverrideResponse,
    SetOverrideRequest,
)
from application.entitlement.workspace_override_use_case import WorkspaceOverrideUseCase

router = APIRouter(prefix="/workspace-overrides", tags=["Workspace Overrides"])


@router.get("/{workspace_id}", response_model=dict[str, WorkspaceOverrideResponse])
async def get_workspace_overrides(
    workspace_id: str,
    current_user = Depends(get_workspace_member),
    use_case: WorkspaceOverrideUseCase = Depends(),
):
    """获取工作区的所有权限覆盖"""
    return await use_case.get_workspace_overrides(workspace_id)


@router.put("/{workspace_id}/{feature_key}")
async def set_workspace_override(
    workspace_id: str,
    feature_key: str,
    request: SetOverrideRequest,
    current_user = Depends(get_workspace_member),  # 需要管理员权限
    use_case: WorkspaceOverrideUseCase = Depends(),
):
    """设置工作区权限覆盖 (需要管理员权限)"""
    return await use_case.set_override(
        workspace_id=workspace_id,
        feature_key=feature_key,
        value=request.value,
        granted_by=current_user.id,
        reason=request.reason,
        expires_at=request.expires_at,
    )
```

---

## §3. 生命周期 API

### §3.1 Trial API

> 设计文档: [11-trial-expiration.md](../11-trial-expiration.md)

**路由**: `/api/v1/entitlement/trial`

**文件**: `api/routers/entitlement/trial.py`

```python
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user
from api.schemas.entitlement.trial import TrialStatusResponse, StartTrialRequest
from application.entitlement.trial_use_case import TrialUseCase

router = APIRouter(prefix="/trial", tags=["Trial"])


@router.get("/status/{feature_key}", response_model=TrialStatusResponse)
async def get_trial_status(
    feature_key: str,
    current_user = Depends(get_current_user),
    use_case: TrialUseCase = Depends(),
):
    """
    获取功能试用状态

    Returns:
        - status: "not_started" | "active" | "expired" | "converted"
        - started_at: Optional[datetime]
        - expires_at: Optional[datetime]
        - remaining_days: Optional[int]
    """
    return await use_case.get_trial_status(current_user.id, feature_key)


@router.post("/start", response_model=TrialStatusResponse)
async def start_trial(
    request: StartTrialRequest,
    current_user = Depends(get_current_user),
    use_case: TrialUseCase = Depends(),
):
    """
    开始功能试用

    Body:
        - feature_key: str
    """
    return await use_case.start_trial(current_user.id, request.feature_key)
```

### §3.2 Tier Downgrade API

> 设计文档: [12-tier-downgrade.md](../12-tier-downgrade.md)

**路由**: `/api/v1/entitlement/downgrade`

**文件**: `api/routers/entitlement/tier_downgrade.py`

```python
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user
from api.schemas.entitlement.tier_downgrade import (
    DowngradePreviewResponse,
    DowngradeLogResponse,
)
from application.entitlement.tier_downgrade_use_case import TierDowngradeUseCase

router = APIRouter(prefix="/downgrade", tags=["Tier Downgrade"])


@router.get("/preview/{to_tier}", response_model=DowngradePreviewResponse)
async def preview_downgrade(
    to_tier: str,
    current_user = Depends(get_current_user),
    use_case: TierDowngradeUseCase = Depends(),
):
    """
    预览降级影响

    Returns:
        - from_tier: str
        - to_tier: str
        - affected_resources: {
            projects_over_limit: int,
            pages_over_limit: int,
            custom_assets_affected: int,
          }
        - features_lost: list[str]
    """
    return await use_case.preview_downgrade(current_user.id, to_tier)


@router.get("/logs", response_model=list[DowngradeLogResponse])
async def get_downgrade_logs(
    current_user = Depends(get_current_user),
    limit: int = 10,
    use_case: TierDowngradeUseCase = Depends(),
):
    """获取降级历史日志"""
    return await use_case.get_user_logs(current_user.id, limit)
```

### §3.3 Subscription Pause API

> 设计文档: [13-subscription-pause.md](../13-subscription-pause.md)

**路由**: `/api/v1/entitlement/subscription/pause`

**文件**: `api/routers/entitlement/subscription_pause.py`

```python
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user
from api.schemas.entitlement.subscription_pause import (
    PauseRequest,
    PauseStatusResponse,
)
from application.entitlement.subscription_pause_use_case import SubscriptionPauseUseCase

router = APIRouter(prefix="/subscription/pause", tags=["Subscription Pause"])


@router.post("/", response_model=PauseStatusResponse)
async def pause_subscription(
    request: PauseRequest,
    current_user = Depends(get_current_user),
    use_case: SubscriptionPauseUseCase = Depends(),
):
    """
    暂停订阅

    Body:
        - pause_days: int (最大 90 天)
        - reason: Optional[str]
    """
    return await use_case.pause_subscription(
        user_id=current_user.id,
        pause_days=request.pause_days,
        reason=request.reason,
    )


@router.post("/resume", response_model=PauseStatusResponse)
async def resume_subscription(
    current_user = Depends(get_current_user),
    use_case: SubscriptionPauseUseCase = Depends(),
):
    """恢复订阅"""
    return await use_case.resume_subscription(current_user.id)


@router.get("/status", response_model=PauseStatusResponse)
async def get_pause_status(
    current_user = Depends(get_current_user),
    use_case: SubscriptionPauseUseCase = Depends(),
):
    """获取暂停状态"""
    return await use_case.get_pause_status(current_user.id)
```

### §3.4 Billing Cycle API

> 设计文档: [14-billing-cycle-switch.md](../14-billing-cycle-switch.md)

**路由**: `/api/v1/entitlement/billing-cycle`

**文件**: `api/routers/entitlement/billing_cycle.py`

```python
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user
from api.schemas.entitlement.billing_cycle import (
    SwitchCycleRequest,
    SwitchCyclePreviewResponse,
    SwitchCycleResponse,
)
from application.entitlement.billing_cycle_use_case import BillingCycleUseCase

router = APIRouter(prefix="/billing-cycle", tags=["Billing Cycle"])


@router.get("/preview/{to_cycle}", response_model=SwitchCyclePreviewResponse)
async def preview_cycle_switch(
    to_cycle: str,  # "monthly" or "yearly"
    current_user = Depends(get_current_user),
    use_case: BillingCycleUseCase = Depends(),
):
    """
    预览周期切换

    Returns:
        - from_cycle: str
        - to_cycle: str
        - effective_at: datetime
        - proration_amount: Decimal
    """
    return await use_case.preview_switch(current_user.id, to_cycle)


@router.post("/switch", response_model=SwitchCycleResponse)
async def switch_billing_cycle(
    request: SwitchCycleRequest,
    current_user = Depends(get_current_user),
    use_case: BillingCycleUseCase = Depends(),
):
    """
    切换账单周期

    Body:
        - to_cycle: "monthly" | "yearly"
    """
    return await use_case.switch_cycle(current_user.id, request.to_cycle)
```

### §3.5 Credits API

> 设计文档: [15-credits-lifecycle.md](../15-credits-lifecycle.md)

**路由**: `/api/v1/entitlement/credits`

**文件**: `api/routers/entitlement/credits.py`

```python
from fastapi import APIRouter, Depends, Query
from api.dependencies import get_current_user
from api.schemas.entitlement.credits import (
    CreditBalanceResponse,
    CreditTransactionResponse,
    ConsumeCreditsRequest,
    ConsumeCreditsResponse,
)
from api.schemas.common import PaginatedResponse
from application.entitlement.credit_use_case import CreditUseCase

router = APIRouter(prefix="/credits", tags=["Credits"])


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    current_user = Depends(get_current_user),
    use_case: CreditUseCase = Depends(),
):
    """
    获取积分余额

    Returns:
        - total: int (总余额)
        - by_source: {
            subscription: int,
            purchase: int,
            bonus_signup: int,
            bonus_referral: int,
            bonus_campaign: int,
            compensation: int,
            earning: int,
          }
        - expiring_soon: int (7 天内过期)
        - expiring_at: Optional[datetime]
    """
    return await use_case.get_balance(current_user.id)


@router.get("/transactions", response_model=PaginatedResponse[CreditTransactionResponse])
async def get_credit_transactions(
    current_user = Depends(get_current_user),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    use_case: CreditUseCase = Depends(),
):
    """
    获取积分交易历史

    Query Params:
        - limit: int (默认 50，最大 100)
        - offset: int
    """
    return await use_case.get_transactions(current_user.id, limit, offset)


@router.post("/consume", response_model=ConsumeCreditsResponse)
async def consume_credits(
    request: ConsumeCreditsRequest,
    current_user = Depends(get_current_user),
    use_case: CreditUseCase = Depends(),
):
    """
    消耗积分 (内部 API，通常由其他服务调用)

    Body:
        - amount: int
        - description: str

    Returns:
        - success: bool
        - consumed: int
        - remaining_balance: int
    """
    return await use_case.consume(
        user_id=current_user.id,
        amount=request.amount,
        description=request.description,
    )


@router.get("/check/{amount}", response_model=dict)
async def check_credits(
    amount: int,
    current_user = Depends(get_current_user),
    use_case: CreditUseCase = Depends(),
):
    """
    检查余额是否足够

    Returns:
        - sufficient: bool
        - balance: int
        - required: int
    """
    balance = await use_case.get_balance_total(current_user.id)
    return {
        "sufficient": balance >= amount,
        "balance": balance,
        "required": amount,
    }
```

### §3.6 Invoice API

> 设计文档: [17-invoice-management.md](../17-invoice-management.md)

**路由**: `/api/v1/entitlement/invoices`

**文件**: `api/routers/entitlement/invoices.py`

```python
from fastapi import APIRouter, Depends, Query
from api.dependencies import get_current_user
from api.schemas.entitlement.invoice import InvoiceResponse
from api.schemas.common import PaginatedResponse
from application.entitlement.invoice_use_case import InvoiceUseCase

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("/", response_model=PaginatedResponse[InvoiceResponse])
async def get_invoices(
    current_user = Depends(get_current_user),
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0, ge=0),
    use_case: InvoiceUseCase = Depends(),
):
    """获取发票列表"""
    return await use_case.get_user_invoices(current_user.id, limit, offset)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user = Depends(get_current_user),
    use_case: InvoiceUseCase = Depends(),
):
    """获取发票详情"""
    return await use_case.get_invoice(invoice_id, current_user.id)


@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: str,
    current_user = Depends(get_current_user),
    use_case: InvoiceUseCase = Depends(),
):
    """获取发票 PDF 下载链接"""
    url = await use_case.get_pdf_url(invoice_id, current_user.id)
    return {"pdf_url": url}
```

### §3.7 Refund API

> 设计文档: [18-refund-processing.md](../18-refund-processing.md)

**路由**: `/api/v1/entitlement/refunds`

**文件**: `api/routers/entitlement/refunds.py`

```python
from fastapi import APIRouter, Depends, Query
from api.dependencies import get_current_user
from api.schemas.entitlement.refund import (
    RefundRequest,
    RefundResponse,
    RefundEligibilityResponse,
)
from api.schemas.common import PaginatedResponse
from application.entitlement.refund_use_case import RefundUseCase

router = APIRouter(prefix="/refunds", tags=["Refunds"])


@router.get("/eligibility/{transaction_id}", response_model=RefundEligibilityResponse)
async def check_refund_eligibility(
    transaction_id: str,
    current_user = Depends(get_current_user),
    use_case: RefundUseCase = Depends(),
):
    """
    检查退款资格

    Returns:
        - eligible: bool
        - reason: Optional[str]
        - max_refund_amount: Decimal
        - credits_to_deduct: int
    """
    return await use_case.check_eligibility(transaction_id, current_user.id)


@router.post("/", response_model=RefundResponse)
async def request_refund(
    request: RefundRequest,
    current_user = Depends(get_current_user),
    use_case: RefundUseCase = Depends(),
):
    """
    申请退款

    Body:
        - transaction_id: str
        - reason: str
        - reason_detail: Optional[str]
    """
    return await use_case.request_refund(
        user_id=current_user.id,
        transaction_id=request.transaction_id,
        reason=request.reason,
        reason_detail=request.reason_detail,
    )


@router.get("/{refund_id}", response_model=RefundResponse)
async def get_refund_status(
    refund_id: str,
    current_user = Depends(get_current_user),
    use_case: RefundUseCase = Depends(),
):
    """获取退款状态"""
    return await use_case.get_refund(refund_id, current_user.id)


@router.get("/", response_model=PaginatedResponse[RefundResponse])
async def get_refunds(
    current_user = Depends(get_current_user),
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0, ge=0),
    use_case: RefundUseCase = Depends(),
):
    """获取退款历史"""
    return await use_case.get_user_refunds(current_user.id, limit, offset)
```

---

## §4. 营销扩展 API

### §4.1 Promotion API

> 设计文档: [19-promotions.md](../19-promotions.md)

**路由**: `/api/v1/entitlement/promotions`

**文件**: `api/routers/entitlement/promotions.py`

```python
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user
from api.schemas.entitlement.promotion import (
    ValidateCodeRequest,
    ValidateCodeResponse,
    ApplyPromotionRequest,
    ApplyPromotionResponse,
)
from application.entitlement.promotion_use_case import PromotionUseCase

router = APIRouter(prefix="/promotions", tags=["Promotions"])


@router.post("/validate", response_model=ValidateCodeResponse)
async def validate_promotion_code(
    request: ValidateCodeRequest,
    current_user = Depends(get_current_user),
    use_case: PromotionUseCase = Depends(),
):
    """
    验证促销码

    Body:
        - code: str
        - plan_type: Optional[str]

    Returns:
        - valid: bool
        - promotion: Optional[PromotionInfo]
        - error: Optional[str]
    """
    return await use_case.validate_code(
        code=request.code,
        user_id=current_user.id,
        plan_type=request.plan_type,
    )


@router.post("/apply", response_model=ApplyPromotionResponse)
async def apply_promotion(
    request: ApplyPromotionRequest,
    current_user = Depends(get_current_user),
    use_case: PromotionUseCase = Depends(),
):
    """
    应用促销码

    Body:
        - code: str
        - subscription_id: Optional[str]
    """
    return await use_case.apply_promotion(
        code=request.code,
        user_id=current_user.id,
        subscription_id=request.subscription_id,
    )
```

### §4.2 Referral API

> 设计文档: [20-referral-rewards.md](../20-referral-rewards.md)

**路由**: `/api/v1/entitlement/referrals`

**文件**: `api/routers/entitlement/referrals.py`

```python
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user
from api.schemas.entitlement.referral import (
    ReferralCodeResponse,
    ReferralStatsResponse,
    UseReferralRequest,
)
from application.entitlement.referral_use_case import ReferralUseCase

router = APIRouter(prefix="/referrals", tags=["Referrals"])


@router.get("/code", response_model=ReferralCodeResponse)
async def get_my_referral_code(
    current_user = Depends(get_current_user),
    use_case: ReferralUseCase = Depends(),
):
    """
    获取我的邀请码

    Returns:
        - code: str
        - share_url: str
        - uses_count: int
    """
    return await use_case.get_or_create_code(current_user.id)


@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    current_user = Depends(get_current_user),
    use_case: ReferralUseCase = Depends(),
):
    """
    获取邀请统计

    Returns:
        - total_referrals: int
        - qualified_referrals: int
        - total_rewards_earned: int
        - pending_rewards: int
    """
    return await use_case.get_stats(current_user.id)


@router.post("/use")
async def use_referral_code(
    request: UseReferralRequest,
    current_user = Depends(get_current_user),
    use_case: ReferralUseCase = Depends(),
):
    """
    使用邀请码 (注册时调用)

    Body:
        - code: str
    """
    return await use_case.use_code(
        referee_id=current_user.id,
        code=request.code,
    )
```

### §4.3 Education Discount API

> 设计文档: [21-education-discount.md](../21-education-discount.md)

**路由**: `/api/v1/entitlement/education`

**文件**: `api/routers/entitlement/education.py`

```python
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user
from api.schemas.entitlement.education import (
    VerificationRequest,
    VerificationResponse,
    VerificationStatusResponse,
)
from application.entitlement.education_discount_use_case import EducationDiscountUseCase

router = APIRouter(prefix="/education", tags=["Education Discount"])


@router.post("/verify", response_model=VerificationResponse)
async def submit_verification(
    request: VerificationRequest,
    current_user = Depends(get_current_user),
    use_case: EducationDiscountUseCase = Depends(),
):
    """
    提交教育验证申请

    Body:
        - institution_name: str
        - institution_type: "k12" | "higher_ed" | "teacher"
        - verification_method: "email" | "document"
        - email_domain: Optional[str]
        - document_url: Optional[str]
    """
    return await use_case.submit_verification(
        user_id=current_user.id,
        **request.dict(),
    )


@router.get("/status", response_model=VerificationStatusResponse)
async def get_verification_status(
    current_user = Depends(get_current_user),
    use_case: EducationDiscountUseCase = Depends(),
):
    """
    获取验证状态

    Returns:
        - status: "none" | "pending" | "approved" | "rejected"
        - discount_percentage: Optional[int]
        - expires_at: Optional[datetime]
    """
    return await use_case.get_status(current_user.id)
```

---

## 附录: API 端点汇总

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| **Tier** | GET | `/tier/me` | 获取当前用户 Tier |
| | GET | `/tier/config` | 获取 Tier 配置 |
| | POST | `/tier/check-permission` | 检查权限 |
| | GET | `/tier/quotas` | 获取配额使用情况 |
| **Feature Flags** | POST | `/flags/evaluate` | 评估单个 Flag |
| | POST | `/flags/evaluate-batch` | 批量评估 |
| **Credits** | GET | `/credits/balance` | 获取余额 |
| | GET | `/credits/transactions` | 交易历史 |
| | POST | `/credits/consume` | 消耗积分 |
| | GET | `/credits/check/{amount}` | 检查余额 |
| **Invoices** | GET | `/invoices` | 发票列表 |
| | GET | `/invoices/{id}` | 发票详情 |
| | GET | `/invoices/{id}/pdf` | 下载 PDF |
| **Refunds** | GET | `/refunds/eligibility/{tx_id}` | 检查退款资格 |
| | POST | `/refunds` | 申请退款 |
| | GET | `/refunds/{id}` | 退款状态 |
| | GET | `/refunds` | 退款历史 |
| **Promotions** | POST | `/promotions/validate` | 验证促销码 |
| | POST | `/promotions/apply` | 应用促销码 |
| **Referrals** | GET | `/referrals/code` | 获取邀请码 |
| | GET | `/referrals/stats` | 邀请统计 |
| | POST | `/referrals/use` | 使用邀请码 |
| **Education** | POST | `/education/verify` | 提交验证 |
| | GET | `/education/status` | 验证状态 |

---

**END OF DOCUMENT**
