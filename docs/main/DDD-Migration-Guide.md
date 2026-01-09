# DDD 迁移指南 (v2.x → v3.1)

> **文档版本**: 1.1.0
> **更新日期**: 2026-01-08
> **目标读者**: 后端开发工程师
> **状态**: ✅ 迁移已完成

---

## 目录

1. [迁移概述](#1-迁移概述)
2. [核心概念](#2-核心概念)
3. [旧代码 → 新代码映射](#3-旧代码--新代码映射)
4. [迁移检查清单](#4-迁移检查清单)
5. [常见问题 FAQ](#5-常见问题-faq)
6. [示例对比](#6-示例对比)

---

## 1. 迁移概述

### 1.1 为什么迁移到 DDD?

| 痛点 | v2.x 问题 | v3.0 DDD 解决方案 |
|------|-----------|------------------|
| **代码混乱** | services/ 中业务逻辑、数据访问、外部调用混在一起 | 清晰分层：domain (业务) / infrastructure (技术) |
| **测试困难** | Service 直接依赖 Supabase，无法 mock | Repository 接口 + 依赖注入，易于测试 |
| **功能散乱** | 积分扣费逻辑散落在多个 service 文件 | 统一在 `billing domain` 中管理 |
| **可维护性差** | 修改积分规则需改动多处 | 单一职责，只需修改 `BillingService` |

### 1.2 迁移范围

**Phase 1-2 (已完成)**:
- ✅ 创建 `core/` 框架层
- ✅ 创建 `domains/` 领域层 (5个 domain)
- ✅ 创建 `application/` 应用层 (commands + queries)
- ✅ 创建 `infrastructure/` 基础设施层

**Phase 3 (已完成)**:
- ✅ 清理废弃代码 (`repositories/`, `exceptions/` 目录)
- ✅ 向后兼容层 (`exceptions.py`)
- ✅ 完整测试覆盖 (startup + integration + domain)

**Phase 4 (已完成)**:
- ✅ 系统性清理旧代码 (`services/`, `routers/` 已删除)
- ✅ 规范化目录结构
- ✅ 文档更新

**Phase 5 (已完成)**:
- ✅ `schemas/` 迁移至 `api/schemas/`
- ✅ `scheduled_tasks/` 迁移至 `application/services/`
- ✅ 临时文档清理 (docs/tmp/)

---

## 2. 核心概念

### 2.1 DDD 三层架构

```
┌─────────────────────────────────────────┐
│  API 层 (api/*)                         │  ← HTTP 请求入口
│  调用 → Application 层                   │
├─────────────────────────────────────────┤
│  Application 层 (application/*)         │  ← 用例编排
│  调用 → Domain Service                   │
│  调用 → Repository Interface             │
├─────────────────────────────────────────┤
│  Domain 层 (domains/*)                  │  ← 业务规则核心
│  定义 → Aggregate, Value Object         │
│  定义 → Repository Interface (抽象)      │
│  定义 → Domain Exception                │
├─────────────────────────────────────────┤
│  Infrastructure 层 (infrastructure/*)   │  ← 技术实现
│  实现 → Repository (Supabase)           │
│  实现 → External Service (Stripe, Clerk)│
└─────────────────────────────────────────┘
```

### 2.2 关键组件说明

#### Aggregate (聚合根)
- **定义**: 领域对象的集合，有明确的边界和一致性规则
- **示例**: `UserCredits` 聚合包含月度积分、永久积分、交易记录
- **规则**: 所有对积分的操作必须通过 `UserCredits` 进行

#### Value Object (值对象)
- **定义**: 不可变对象，由属性值定义，无唯一标识
- **示例**: `Credits(monthly=100, permanent=50)`
- **规则**: 一旦创建不可修改，需要新值时创建新对象

#### Domain Service (领域服务)
- **定义**: 不属于任何聚合的业务逻辑
- **示例**: `BillingService.deduct_for_operation()` - 跨交易的积分扣费
- **规则**: 无状态，只依赖 repository 接口

#### Repository Interface (仓储接口)
- **定义**: 定义数据访问抽象，在 domain 层定义接口
- **示例**: `ICreditRepository.get_user_credits(user_id)`
- **规则**: Domain 只依赖接口，不依赖实现

#### Repository Implementation (仓储实现)
- **定义**: 在 infrastructure 层实现 repository 接口
- **示例**: `SupabaseCreditRepository` 实现 `ICreditRepository`
- **规则**: 可以访问 Supabase、Redis 等技术细节

---

## 3. 旧代码 → 新代码映射

### 3.1 积分系统 (Billing)

#### ❌ 旧代码 (v2.x)
```python
# services/credit_service.py
from services.db.core import get_supabase_client

class CreditService:
    def deduct_credits(self, user_id: str, amount: int):
        supabase = get_supabase_client()
        # 直接写 SQL 逻辑
        result = supabase.rpc("deduct_credits", {
            "p_user_id": user_id,
            "p_amount": amount
        }).execute()
        return result.data
```

#### ✅ 新代码 (v3.0)
```python
# domains/billing/service.py
from domains.billing.repository import ICreditRepository

class BillingService:
    def __init__(self, repository: ICreditRepository):
        self._repo = repository  # 依赖注入

    async def deduct_for_operation(
        self,
        user_id: str,
        operation: str,
        description: str = None,
    ):
        # 1. 获取用户积分 (通过 repository)
        user_credits = await self._repo.get_user_credits(user_id)

        # 2. 业务规则：计算扣费金额
        cost = self.get_operation_cost(operation)

        # 3. 领域逻辑：扣费
        user_credits.deduct(cost, description)

        # 4. 持久化
        await self._repo.save(user_credits)
        return user_credits
```

**迁移要点**:
- ❌ 不再直接调用 `get_supabase_client()`
- ✅ 通过 `repository.get_user_credits()` 获取聚合
- ✅ 在聚合上执行业务操作 `user_credits.deduct()`
- ✅ 通过 `repository.save()` 持久化

### 3.2 用户系统 (Identity)

#### ❌ 旧代码
```python
# services/user_service.py
def get_user(user_id: str):
    supabase = get_supabase_client()
    result = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    return result.data[0] if result.data else None
```

#### ✅ 新代码
```python
# domains/identity/service.py
class IdentityService:
    def __init__(self, repository: IUserRepository):
        self._repo = repository

    async def get_user(self, user_id: str) -> UserProfile:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id=user_id)
        return user
```

### 3.3 API 层调用方式

#### ❌ 旧代码 (routers/)
```python
# routers/users.py
from services.user_service import UserService

@router.get("/users/me")
async def get_current_user(user: dict = Depends(get_current_user)):
    service = UserService()  # 直接实例化
    user_data = service.get_user(user["id"])
    return user_data
```

#### ✅ 新代码 (api/)
```python
# api/user_api.py
from container import Container

@router.get("/users/me")
async def get_current_user(
    user: dict = Depends(get_current_user),
    container: Container = Depends(get_container),
):
    # 通过容器获取服务 (依赖注入)
    identity_service = container.identity_service()

    # 调用 application 层
    query = GetUserQuery(user_id=user["id"])
    user_profile = await identity_service.get_user(query.user_id)

    return UserResponse.from_domain(user_profile)
```

**迁移要点**:
- ❌ 不再 `service = UserService()` 直接实例化
- ✅ 通过 `container.identity_service()` 获取服务
- ✅ 使用 DTO (UserResponse) 转换 domain 对象

---

## 4. 迁移检查清单

### 4.1 新功能开发 (强制使用 DDD)

- [ ] 确定功能属于哪个 domain (billing/identity/creation/marketplace/platform)
- [ ] 在 `domains/{domain}/` 中定义聚合根和值对象
- [ ] 在 `domains/{domain}/service.py` 中实现业务逻辑
- [ ] 在 `infrastructure/repositories/` 中实现数据访问
- [ ] 在 `application/commands/` 或 `application/queries/` 中编排用例
- [ ] 在 `api/` 中创建 HTTP 端点
- [ ] 在 `container.py` 中注册依赖

### 4.2 旧代码迁移 (逐步进行)

- [ ] 识别 `services/` 中的旧代码功能
- [ ] 映射到对应的 domain
- [ ] 重写为 DDD 结构
- [ ] 更新 API 调用方
- [ ] 添加测试
- [ ] 删除旧代码
- [ ] 更新文档

---

## 5. 常见问题 FAQ

### Q1: 为什么 domain 不能直接访问数据库?

**A**: 这是**依赖倒置原则** (Dependency Inversion Principle)。

- ❌ 错误: `domains/billing/service.py` 直接 `import supabase`
- ✅ 正确: Domain 定义 `ICreditRepository` 接口，Infrastructure 实现它

**好处**:
- Domain 层可以独立测试 (mock repository)
- 未来可以轻松切换数据库 (PostgreSQL → MongoDB)
- 业务逻辑不受技术实现影响

### Q2: Aggregate 和 Entity 的区别?

| Aggregate (聚合根) | Entity (实体) |
|-------------------|--------------|
| 整个聚合的入口点 | 聚合内部的对象 |
| 有全局唯一 ID | 可能只有聚合内唯一 ID |
| 示例: `UserCredits` | 示例: `CreditTransaction` |

### Q3: 什么时候用 Domain Service vs Application Service?

| Domain Service | Application Service |
|----------------|---------------------|
| 纯业务逻辑 | 用例编排 |
| 不跨 domain | 可以协调多个 domain |
| 示例: 计算积分扣费优先级 | 示例: 创建订单 + 扣积分 + 发通知 |

### Q4: 旧代码 `services/` 何时完全删除?

**迁移路线图**:
1. **Phase 3 (当前)**: 标记 `services/` 为 deprecated
2. **Phase 4**: 将核心业务逻辑迁移到 domains
3. **Phase 5**: 删除未使用的 services 文件
4. **Phase 6**: 完全移除 `services/` 目录

**原则**: 先迁移再删除，确保 100% 功能覆盖

### Q5: 如何处理跨 domain 依赖?

**错误做法**:
```python
# ❌ domains/billing/service.py
from domains.identity.service import IdentityService  # 不能这样!

class BillingService:
    def deduct(self, user_id):
        identity = IdentityService()  # 跨 domain 依赖
        user = identity.get_user(user_id)
```

**正确做法**:
```python
# ✅ application/commands/billing.py
class DeductCreditsCommand:
    def __init__(
        self,
        billing_service: BillingService,
        identity_service: IdentityService,
    ):
        self._billing = billing_service
        self._identity = identity_service

    async def execute(self, user_id, amount):
        # Application 层协调多个 domain
        user = await self._identity.get_user(user_id)
        await self._billing.deduct(user_id, amount)
```

---

## 6. 示例对比

### 6.1 完整功能：积分扣费

#### ❌ v2.x 旧代码

```python
# services/credit_service.py
class CreditService:
    def deduct_for_generation(self, user_id: str):
        supabase = get_supabase_client()

        # 获取用户积分
        user = supabase.table("profiles").select("credits_monthly, credits_permanent").eq("user_id", user_id).single().execute()

        # 计算扣费
        cost = 5  # 硬编码
        monthly = user.data["credits_monthly"]
        permanent = user.data["credits_permanent"]

        # 扣费逻辑
        if monthly >= cost:
            new_monthly = monthly - cost
            new_permanent = permanent
        else:
            remaining = cost - monthly
            new_monthly = 0
            new_permanent = permanent - remaining

        # 检查余额
        if new_permanent < 0:
            raise Exception("Insufficient credits")

        # 更新数据库
        supabase.table("profiles").update({
            "credits_monthly": new_monthly,
            "credits_permanent": new_permanent,
        }).eq("user_id", user_id).execute()

        # 记录交易
        supabase.table("credit_transactions").insert({
            "user_id": user_id,
            "amount": -cost,
            "type": "generation",
        }).execute()
```

**问题**:
- 🔴 业务逻辑 + 数据访问混在一起
- 🔴 扣费规则散落各处，难以维护
- 🔴 无法单元测试 (依赖真实数据库)
- 🔴 Magic number `cost = 5` 硬编码

#### ✅ v3.0 新代码

```python
# domains/billing/aggregates/user_credits.py
@dataclass
class UserCredits:
    user_id: str
    balance: Credits

    def deduct(self, amount: int, description: str = None):
        """扣费：月度优先，永久次之"""
        if not self.can_afford(amount):
            raise InsufficientCreditsException(
                user_id=self.user_id,
                required=amount,
                available=self.balance.total
            )

        # 业务规则：月度积分优先扣除
        if self.balance.monthly >= amount:
            new_balance = Credits(
                monthly=self.balance.monthly - amount,
                permanent=self.balance.permanent
            )
        else:
            remaining = amount - self.balance.monthly
            new_balance = Credits(
                monthly=0,
                permanent=self.balance.permanent - remaining
            )

        # 更新余额
        object.__setattr__(self, 'balance', new_balance)

        # 记录交易 (用于持久化)
        self.pending_transactions.append(
            CreditTransaction(
                amount=-amount,
                bucket=CreditBucket.MONTHLY,
                tx_type=TransactionType.GENERATION,
                description=description,
                balance_after=new_balance,
            )
        )

# domains/billing/service.py
class BillingService:
    def __init__(self, repository: ICreditRepository, config_service=None):
        self._repo = repository
        self._config = config_service

    async def deduct_for_operation(self, user_id: str, operation: str):
        # 1. 获取聚合
        user_credits = await self._repo.get_user_credits(user_id)

        # 2. 获取动态配置的成本
        cost = self.get_operation_cost(operation)

        # 3. 执行业务逻辑
        user_credits.deduct(cost, description=f"{operation} operation")

        # 4. 持久化 (通过 RPC 原子操作)
        await self._repo.save(user_credits)
        return user_credits

    def get_operation_cost(self, operation: str) -> int:
        """从配置中获取操作成本"""
        if self._config:
            return self._config.get_config(
                f"credits.cost.{operation}",
                use_cache=True
            ).get("amount", 5)
        return 5  # Emergency fallback

# infrastructure/repositories/credit_repository.py
class SupabaseCreditRepository(ICreditRepository):
    async def save(self, user_credits: UserCredits):
        """通过 RPC 原子保存"""
        for tx in user_credits.pending_transactions:
            await self._client.rpc("deduct_credits_atomic", {
                "p_user_id": user_credits.user_id,
                "p_amount": abs(tx.amount),
                "p_bucket": tx.bucket.value,
                "p_tx_type": tx.tx_type.value,
                "p_description": tx.description,
            }).execute()

# api/generation_api.py
@router.post("/generate")
async def generate_image(
    request: GenerationRequest,
    user: dict = Depends(get_current_user),
    container: Container = Depends(get_container),
):
    # 1. 扣费
    billing_service = container.billing_service()
    await billing_service.deduct_for_operation(
        user_id=user["id"],
        operation="image_generation",
    )

    # 2. 调用 AI
    ai_service = container.ai_service()
    result = await ai_service.generate_image(request.prompt)

    return GenerationResponse(image_url=result.url)
```

**优势**:
- ✅ 扣费规则集中在 `UserCredits.deduct()`
- ✅ 动态配置成本 (从数据库读取)
- ✅ 可以完全 mock repository 进行单元测试
- ✅ 原子操作保证一致性 (RPC)
- ✅ 清晰的职责分离

---

## 7. 快速参考

### 7.1 代码位置速查

| 功能 | 旧位置 (v2.x) | 新位置 (v3.0) |
|------|---------------|---------------|
| 积分扣费 | `services/credit_service.py` | `domains/billing/service.py` |
| 用户信息 | `services/user_service.py` | `domains/identity/service.py` |
| 项目管理 | `services/project_service.py` | `domains/creation/service.py` |
| 市场交易 | `services/marketplace_service.py` | `domains/marketplace/service.py` |
| 数据库访问 | `services/db/*.py` | `infrastructure/repositories/*.py` |
| 异常定义 | `exceptions/*.py` | `core/exceptions/*.py` + `domains/*/exceptions.py` |

### 7.2 import 路径速查

```python
# ❌ 旧 import
from services.user_service import UserService
from services.credit_service import CreditService
from exceptions.billing import InsufficientCreditsException

# ✅ 新 import
from domains.identity import IdentityService, UserProfile, UserTier
from domains.billing import BillingService, UserCredits, Credits
from domains.billing.exceptions import InsufficientCreditsException
from infrastructure.repositories import SupabaseUserRepository
from container import Container
```

---

## 8. 下一步

### 8.1 学习资源

- 📖 `docs/后台业务逻辑说明.md` - 完整架构文档
- 🧪 `tests/domains/` - Domain 层测试示例
- 🧪 `tests/integration/` - 集成测试示例
- 📋 `docs/shared/[重构后]System-Refactoring-Proposal-v2.md` - DDD 设计方案

### 8.2 待办事项

- [ ] 阅读 5 个 domain 的代码结构
- [ ] 运行测试套件 `pytest tests/domains/ -v`
- [ ] 尝试添加新的 Value Object
- [ ] 参与旧代码迁移

---

**版本记录**:
- v1.1.0 (2026-01-08): 更新迁移状态为全部完成 (Phase 1-5)
- v1.0.0 (2026-01-07): 初始版本，DDD 迁移指南
