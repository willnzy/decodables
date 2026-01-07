# Credit Service 迁移分析

> **Phase**: 7.1
> **日期**: 2026-01-07
> **文件**: services/credit_service.py → domains/billing/ + application/

---

## 1. 现状分析

### 1.1 当前实现

**文件**: `services/credit_service.py` (318 行)

**类**: `CreditService`

**职责混合**:
```python
class CreditService:
    # 🔴 业务规则 (应在 domains/billing/)
    - 积分扣除优先级: 先月度后永久
    - 积分成本计算: get_generation_cost(), get_ocr_cost()

    # 🟢 数据访问 (应在 infrastructure/repositories/)
    - get_balance(): 查询用户积分余额
    - get_total(): 计算总积分
    - has_enough(): 检查积分是否充足

    # 🔵 用例编排 (应在 application/commands/)
    - deduct(): 扣除积分 (调用 RPC)
    - add(): 添加积分 (调用 RPC)
    - reset_monthly(): 重置月度积分
    - deduct_with_details(): 扣除积分并返回详情
```

### 1.2 核心业务规则

根据代码注释和实现:

**积分类型** (PRD v3.2):
```
1. Monthly Credits (月度积分)
   - 每月重置
   - 不滚存

2. Permanent Credits (永久积分)
   - 永不过期
   - 可累积
```

**扣除优先级** (核心业务规则):
```
先扣除 Monthly Credits → 再扣除 Permanent Credits
```

**成本配置** (v3.3 Section 3.3):
```
- AI 图像生成: 5 积分/张 (CREDITS_PER_IMAGE)
- OCR: CREDITS_PER_OCR
```

**原子操作** (v3.22):
```
- 使用 PostgreSQL RPC 函数保证原子性
- 行锁 (SELECT FOR UPDATE) 防止竞态条件
- 幂等性支持 (idempotency_key)
```

### 1.3 依赖关系

**依赖**:
```python
- config.CREDITS_PER_IMAGE, CREDITS_PER_OCR  # 配置
- supabase client                             # 数据库
```

**被依赖** (通过 grep 查找):
```
- tests/test_credit_service.py               # 单元测试
- tests/services/test_credit_service.py      # 集成测试
- services/service_factory.py                # 工厂模式 (待迁移)
```

**API 调用方** (需要进一步查找):
```
- api/routers/credits.py (可能)
- api/routers/generation.py (可能)
- api/routers/marketplace.py (可能)
```

---

## 2. 迁移策略

### 2.1 架构决策

根据 DDD 和 v2 架构规范:

```
┌──────────────────────────────────────────────────────────┐
│ services/credit_service.py (318 行)                      │
│                                                          │
│ CreditService Class                                      │
└──────────────────────┬───────────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
           ▼                       ▼
┌─────────────────────┐  ┌─────────────────────────────────┐
│ domains/billing/    │  │ application/commands/billing/   │
│                     │  │                                 │
│ service.py          │  │ deduct_credits.py               │
│ ├─ 业务规则          │  │ ├─ DeductCreditsCommand         │
│ ├─ 成本计算          │  │ └─ handle()                     │
│ └─ 验证逻辑          │  │                                 │
│                     │  │ add_credits.py                  │
│ cost_calculator.py  │  │ ├─ AddCreditsCommand            │
│ (可选)              │  │ └─ handle()                     │
│                     │  │                                 │
│                     │  │ reset_monthly_credits.py        │
│                     │  │ ├─ ResetMonthlyCreditsCommand   │
│                     │  │ └─ handle()                     │
└─────────────────────┘  └─────────────────────────────────┘
           │                       │
           │                       ▼
           │              ┌──────────────────────────┐
           │              │ infrastructure/          │
           └─────────────>│ repositories/            │
                          │                          │
                          │ credit_repo.py           │
                          │ (已存在)                 │
                          │ ├─ get_balance()         │
                          │ ├─ deduct_atomic()       │
                          │ ├─ add_atomic()          │
                          │ └─ reset_monthly()       │
                          └──────────────────────────┘
```

### 2.2 迁移映射

| 原方法 | 新位置 | 类型 |
|--------|--------|------|
| `get_generation_cost()` | `domains/billing/cost_calculator.py` | 业务规则 |
| `get_ocr_cost()` | `domains/billing/cost_calculator.py` | 业务规则 |
| `deduct()` | `application/commands/billing/deduct_credits.py` | 用例 |
| `deduct_with_details()` | `application/commands/billing/deduct_credits.py` | 用例 |
| `add()` | `application/commands/billing/add_credits.py` | 用例 |
| `reset_monthly()` | `application/commands/billing/reset_monthly_credits.py` | 用例 |
| `get_balance()` | `infrastructure/repositories/credit_repo.py` | 数据访问 |
| `get_total()` | `infrastructure/repositories/credit_repo.py` | 数据访问 |
| `has_enough()` | `infrastructure/repositories/credit_repo.py` | 数据访问 |

---

## 3. 实施计划

### Step 1: 检查现有 domains/billing/

查看已有的聚合根和仓储接口:

```bash
tree domains/billing/
```

预期:
```
domains/billing/
├── __init__.py
├── aggregates/
│   └── user_credits.py      # UserCredits 聚合根 (已存在)
├── value_objects.py         # Credits, TransactionType (已存在)
├── repository.py            # ICreditRepository (已存在)
├── service.py               # 🆕 需要创建或更新
├── cost_calculator.py       # 🆕 需要创建
└── exceptions.py            # InsufficientCreditsException (已存在)
```

### Step 2: 创建/更新 domains/billing/service.py

**目标**: 将业务规则从 CreditService 提取到领域服务

```python
# domains/billing/service.py

from dataclasses import dataclass
from typing import Tuple
from domains.billing.aggregates.user_credits import UserCredits
from domains.billing.value_objects import Credits, TransactionType
from domains.billing.exceptions import InsufficientCreditsException

@dataclass
class DeductionPlan:
    """积分扣除方案"""
    monthly_deducted: int
    permanent_deducted: int
    total_deducted: int
    bucket: str  # "monthly", "permanent", "mixed"

class BillingService:
    """
    积分领域服务 - 封装业务规则和复杂计算

    职责:
    - 计算积分扣除方案 (月度优先)
    - 验证积分是否充足
    - 业务规则验证
    """

    @staticmethod
    def calculate_deduction_plan(
        monthly: int,
        permanent: int,
        amount: int
    ) -> DeductionPlan:
        """
        计算积分扣除方案 (核心业务规则: 先月度后永久)

        Args:
            monthly: 月度积分余额
            permanent: 永久积分余额
            amount: 需要扣除的积分

        Returns:
            DeductionPlan 扣除方案

        Raises:
            InsufficientCreditsException: 积分不足
        """
        total = monthly + permanent

        if total < amount:
            raise InsufficientCreditsException(
                required=amount,
                available=total,
                monthly=monthly,
                permanent=permanent
            )

        # 业务规则: 先扣月度积分
        if monthly >= amount:
            return DeductionPlan(
                monthly_deducted=amount,
                permanent_deducted=0,
                total_deducted=amount,
                bucket="monthly"
            )
        else:
            # 月度不足,扣除所有月度 + 部分永久
            permanent_needed = amount - monthly
            return DeductionPlan(
                monthly_deducted=monthly,
                permanent_deducted=permanent_needed,
                total_deducted=amount,
                bucket="mixed" if monthly > 0 else "permanent"
            )

    @staticmethod
    def validate_add_amount(amount: int) -> None:
        """验证添加的积分数量"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
```

### Step 3: 创建 domains/billing/cost_calculator.py

**目标**: 将成本计算逻辑提取为独立模块

```python
# domains/billing/cost_calculator.py

from config import CREDITS_PER_IMAGE, CREDITS_PER_OCR

class CostCalculator:
    """
    积分成本计算器

    业务规则 (v3.3 Section 3.3):
    - AI 图像生成: 5 积分/张
    - OCR: CREDITS_PER_OCR
    """

    @staticmethod
    def get_generation_cost() -> int:
        """
        获取 AI 图像生成成本

        Business Rule (v3.3 Section 3.3):
        - AI 图像生成消耗 5 积分/张
        - 无特殊规则（首次免费已移除）

        Returns:
            Cost in credits (always CREDITS_PER_IMAGE)
        """
        return CREDITS_PER_IMAGE

    @staticmethod
    def get_ocr_cost() -> int:
        """获取 OCR 成本"""
        return CREDITS_PER_OCR

    @staticmethod
    def calculate_total_cost(
        images: int = 0,
        ocr_calls: int = 0
    ) -> int:
        """
        计算总成本

        Args:
            images: 图像生成数量
            ocr_calls: OCR 调用次数

        Returns:
            总成本 (积分)
        """
        return (images * CREDITS_PER_IMAGE) + (ocr_calls * CREDITS_PER_OCR)
```

### Step 4: 更新 infrastructure/repositories/credit_repo.py

**目标**: 确保仓储实现了所有需要的查询方法

```python
# infrastructure/repositories/credit_repo.py (部分)

class SupabaseCreditRepository(ICreditRepository):
    """Supabase 积分仓储实现"""

    async def get_balance(self, user_id: str) -> Tuple[int, int]:
        """
        获取用户积分余额

        Returns:
            Tuple of (monthly_credits, permanent_credits)
        """
        result = await self.client.table("profiles").select(
            "credits_monthly, credits_permanent"
        ).eq("id", user_id).single().execute()

        if result.data:
            return (
                result.data.get("credits_monthly", 0),
                result.data.get("credits_permanent", 0)
            )
        return (0, 0)

    async def deduct_atomic(
        self,
        user_id: str,
        amount: int,
        tx_type: str,
        description: Optional[str] = None,
        timezone: str = "UTC",
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        原子扣除积分 (调用 PostgreSQL RPC)

        Returns:
            Dict with success, balance_monthly, balance_permanent, etc.
        """
        result = await self.client.rpc("deduct_credits_atomic", {
            "p_user_id": user_id,
            "p_amount": amount,
            "p_tx_type": tx_type,
            "p_description": description,
            "p_timezone": timezone,
            "p_idempotency_key": idempotency_key
        }).execute()

        return result.data or {}

    async def add_atomic(
        self,
        user_id: str,
        amount: int,
        bucket: Literal["monthly", "permanent"],
        tx_type: str,
        description: Optional[str] = None,
        timezone: str = "UTC",
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """原子添加积分 (调用 PostgreSQL RPC)"""
        result = await self.client.rpc("add_credits_atomic", {
            "p_user_id": user_id,
            "p_amount": amount,
            "p_bucket": bucket,
            "p_tx_type": tx_type,
            "p_description": description,
            "p_timezone": timezone,
            "p_idempotency_key": idempotency_key
        }).execute()

        return result.data or {}

    async def reset_monthly(
        self,
        user_id: str,
        amount: int,
        timezone: str = "UTC"
    ) -> Tuple[bool, str]:
        """重置月度积分"""
        # ... (从 CreditService.reset_monthly 迁移)
```

### Step 5: 创建 application/commands/billing/deduct_credits.py

**目标**: 用例编排,调用领域服务和仓储

```python
# application/commands/billing/deduct_credits.py

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
import logging

from domains.billing.repository import ICreditRepository
from domains.billing.service import BillingService
from domains.billing.cost_calculator import CostCalculator
from core.exceptions import ValidationException

logger = logging.getLogger(__name__)

@dataclass
class DeductCreditsCommand:
    """扣除积分命令"""
    user_id: str
    amount: int
    tx_type: str
    description: Optional[str] = None
    timezone: str = "UTC"
    idempotency_key: Optional[str] = None
    return_details: bool = False  # 是否返回详细信息

async def handle(
    cmd: DeductCreditsCommand,
    repo: ICreditRepository
) -> Tuple[bool, str] | Dict[str, Any]:
    """
    处理扣除积分命令

    用例编排:
    1. 验证参数
    2. 调用仓储原子扣除
    3. 返回结果

    Args:
        cmd: 扣除积分命令
        repo: 积分仓储

    Returns:
        如果 return_details=False: Tuple[bool, str]
        如果 return_details=True: Dict with balance details
    """
    # 1. 验证
    if cmd.amount <= 0:
        if cmd.return_details:
            monthly, permanent = await repo.get_balance(cmd.user_id)
            return {
                "success": True,
                "message": "No credits needed",
                "balance_monthly": monthly,
                "balance_permanent": permanent
            }
        return (True, "No credits needed")

    # 2. 调用仓储原子扣除
    try:
        result = await repo.deduct_atomic(
            user_id=cmd.user_id,
            amount=cmd.amount,
            tx_type=cmd.tx_type,
            description=cmd.description,
            timezone=cmd.timezone,
            idempotency_key=cmd.idempotency_key
        )

        # 3. 处理结果
        if not result:
            logger.error(f"[DeductCredits] RPC returned no data for user {cmd.user_id}")
            if cmd.return_details:
                return {"success": False, "error": "Database error: no response"}
            return (False, "Database error: no response")

        success = result.get("success", False)

        if cmd.return_details:
            return {
                "success": success,
                "balance_monthly": result.get("balance_monthly", 0),
                "balance_permanent": result.get("balance_permanent", 0),
                "deducted": result.get("deducted", 0),
                "bucket": result.get("bucket", ""),
                "error": result.get("error"),
                "error_code": result.get("error_code"),
                "idempotent": result.get("idempotent", False)
            }
        else:
            if success:
                if result.get("idempotent"):
                    logger.info(f"[DeductCredits] Idempotent for {cmd.user_id}: {cmd.idempotency_key}")
                return (True, f"Deducted {cmd.amount} credits")
            else:
                error = result.get("error", "Unknown error")
                logger.warning(f"[DeductCredits] Failed for {cmd.user_id}: {error}")
                return (False, error)

    except Exception as e:
        logger.error(f"[DeductCredits] Exception for {cmd.user_id}: {e}")
        if cmd.return_details:
            return {"success": False, "error": str(e), "error_code": "EXCEPTION"}
        return (False, str(e))
```

### Step 6: 创建 application/commands/billing/add_credits.py

类似 deduct_credits.py 的结构

### Step 7: 创建 application/commands/billing/reset_monthly_credits.py

类似 deduct_credits.py 的结构

---

## 4. 更新调用方

### 4.1 查找所有调用方

```bash
# 查找直接导入
grep -r "from services.credit_service import" --include="*.py"
grep -r "CreditService" --include="*.py" | grep -v test | grep -v __pycache__

# 查找可能的使用位置
grep -r "credit_service" api/routers/ --include="*.py"
```

### 4.2 更新导入路径

**之前**:
```python
from services.credit_service import CreditService

credit_service = CreditService(supabase)
result = credit_service.deduct(user_id, amount, "generation")
```

**之后**:
```python
from application.commands.billing.deduct_credits import DeductCreditsCommand, handle as deduct_credits

repo = get_credit_repo()  # 依赖注入
cmd = DeductCreditsCommand(
    user_id=user_id,
    amount=amount,
    tx_type="generation"
)
success, message = await deduct_credits(cmd, repo)
```

---

## 5. 测试策略

### 5.1 单元测试

**新增测试**:
```
tests/domains/billing/
├── test_billing_service.py       # 测试 BillingService
└── test_cost_calculator.py       # 测试 CostCalculator

tests/application/commands/billing/
├── test_deduct_credits.py        # 测试 DeductCreditsCommand
├── test_add_credits.py
└── test_reset_monthly_credits.py
```

### 5.2 集成测试

**保留并更新**:
```
tests/integration/billing/
└── test_credit_operations.py     # 端到端测试积分操作
```

### 5.3 迁移现有测试

```
tests/test_credit_service.py      → tests/domains/billing/test_billing_service.py
tests/services/test_credit_service.py → tests/application/commands/billing/
```

---

## 6. 验收标准

### 6.1 功能验证

- [ ] 积分扣除功能正常 (先月度后永久)
- [ ] 积分添加功能正常
- [ ] 月度积分重置功能正常
- [ ] 幂等性正常工作
- [ ] 成本计算正确
- [ ] 原子操作不出现竞态条件

### 6.2 架构验证

- [ ] 业务规则在 domains/billing/ 里
- [ ] 用例编排在 application/commands/billing/ 里
- [ ] 数据访问在 infrastructure/repositories/ 里
- [ ] 依赖方向正确
- [ ] 测试覆盖率 ≥ 60%

### 6.3 性能验证

- [ ] 积分操作响应时间无明显增加
- [ ] 数据库查询次数无增加
- [ ] 无额外的 N+1 查询

---

## 7. 风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **RPC 调用逻辑复杂** | 高 | 保持 RPC 调用在仓储层,不改变调用方式 |
| **幂等性实现** | 高 | 完全保留现有幂等性逻辑 |
| **原子性破坏** | 高 | 使用相同的 PostgreSQL RPC,不改变事务边界 |
| **调用方过多** | 中 | 分批更新,逐个验证 |
| **测试覆盖不足** | 中 | 迁移前补充测试 |

---

## 8. 下一步行动

### 立即执行 (Phase 7.1.2)

1. **检查现有 domains/billing/ 结构**
2. **创建 domains/billing/service.py**
3. **创建 domains/billing/cost_calculator.py**
4. **更新 infrastructure/repositories/credit_repo.py**
5. **创建 application/commands/billing/deduct_credits.py**
6. **创建 application/commands/billing/add_credits.py**
7. **创建 application/commands/billing/reset_monthly_credits.py**

---

**文档版本**: v1.0
**最后更新**: 2026-01-07
**状态**: 分析完成,准备实施
