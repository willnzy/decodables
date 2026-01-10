# 数据库-代码同步最优方案 (基于架构规范深度分析)

**创建时间**: 2026-01-10
**基于审查**: Agent a7062f1 (基础问题发现) + Agent aab95b3 (架构规范分析)
**架构评分**: ⭐⭐⭐⭐+ (4.75/5) - 生产级别高质量架构
**项目状态**: 未上线,无需向后兼容

---

## 🎯 执行摘要

### 核心发现

经过对项目架构文档 (BACKEND_ARCHITECTURE_GUIDE.md, DDD-Migration-Guide.md) 和数据库 Schema (refactored_schema_v2.sql 3,158 行, 47 张表) 的深度分析，得出以下结论：

**✅ 代码架构优秀** (DDD 合规度 98%):
- 三层架构 + 轻量级 DDD 融合
- 清晰的分层职责 (API → Application → Domains ← Infrastructure)
- 完美的依赖倒置 (接口在 domains,实现在 infrastructure)
- 7 个独立领域 (identity/billing/creation/marketplace/platform/tasks/tools)

**✅ 数据库设计成熟** (47 张表完整建模):
- 统一的 snake_case 命名规范
- 标准审计字段 (created_at, updated_at, is_deleted, deleted_at)
- Append-Only 表 (credit_transactions) 防篡改
- CHECK 约束 + 触发器强制业务规则
- 完整的索引设计 + RPC 函数优化

**⚠️ 同步问题可控** (预计 1-2 周修复):
- 🔴 P0 问题: 3 个 (表名映射错误,枚举值大小写,业务约束验证) - 8-16 小时
- 🟡 P1 问题: 5 个 (字段映射文档化,soft delete,审计字段) - 24-36 小时
- 🟢 P2 问题: 2 个 (文档同步,性能优化) - 16-24 小时

---

## 一、战略选择: 双向调整策略 (推荐)

### 1.1 为什么不是"纯代码适配 Schema"

虽然之前的初步方案建议"代码适配 Schema",但深度分析后发现:

**Schema 也有需要调整的地方**:
1. 缺失 13 个业务必需的表 (user_events, error_logs, support_tickets, etc.)
2. 缺失 6 个业务字段 (profiles.first_name/last_name/preferences, etc.)
3. 枚举值定义与 Python 惯例不一致 (小写 vs UPPER_CASE)

**代码也有需要调整的地方**:
1. 表名引用错误 (users vs profiles)
2. 字段名映射不一致 (project_id vs id, buyer_id vs user_id)
3. 枚举值大小写转换代码冗余

### 1.2 最优策略: 双向调整 (70% 代码, 30% Schema)

```
┌──────────────────────────────────────────────────┐
│           双向调整策略 (Bidirectional Sync)         │
├──────────────────────────────────────────────────┤
│                                                  │
│  代码调整 (70%):                                │
│  ✅ 修复错误的表名引用 (users → profiles)        │
│  ✅ 修复错误的字段名 (project_id → id)          │
│  ✅ 统一枚举值为小写 (符合 PostgreSQL 规范)     │
│  ✅ 创建字段映射表 (field_mappings.py)          │
│  ✅ 在聚合根中添加业务约束验证                  │
│                                                  │
│  Schema 调整 (30%):                             │
│  ✅ 创建 13 个缺失的表 (P0: 5 tables)           │
│  ✅ 添加 6 个缺失字段到 profiles/projects       │
│  ✅ 补充索引 (条件索引 WHERE is_deleted=FALSE) │
│  ✅ 完善注释 (COMMENT ON 所有表和字段)          │
│  ✅ 创建审计追踪视图 (VIEW user_audit_trail)   │
│                                                  │
│  优势:                                          │
│  ✅ 代码和 Schema 都达到生产标准                │
│  ✅ 保持架构一致性 (遵循 DDD 原则)              │
│  ✅ 最小化变更量 (只改必要的)                   │
│  ✅ 长期可维护 (符合业界最佳实践)               │
└──────────────────────────────────────────────────┘
```

---

## 二、分阶段执行计划

### Phase 1: P0 关键问题修复 (Day 1-2, 估计 8-16 小时)

#### 1.1 修复代码中的表名映射错误 (4 小时)

**问题**: `credit_repository.py` 等多处引用不存在的 `users` 表

**解决方案**:
```python
# infrastructure/repositories/credit_repository.py
# ❌ 错误:
result = self.client.table("users").select("user_id, credits_monthly, ...").execute()

# ✅ 正确:
result = self.client.table("profiles").select("id as user_id, credits_monthly, ...").execute()
```

**执行步骤**:
```bash
# 1. 搜索所有错误的表名引用
cd /Users/zhangyi/Code_all/AI-WEB/decodables
grep -rn 'table("users")' infrastructure/repositories/

# 2. 逐个文件修复
#    - credit_repository.py: 5 处修改
#    - user_repository.py: 已正确使用 "profiles"
#    - admin_repository.py: 需确认是否引用

# 3. 验证修复
python -m pytest tests/infrastructure/repositories/test_credit_repository.py -v
```

**修改文件清单**:
- `infrastructure/repositories/credit_repository.py` (5 处)
- `infrastructure/repositories/admin_repository.py` (需确认)

**预计时间**: 4 小时

---

#### 1.2 统一枚举值的大小写 (4 小时)

**问题**: 代码中使用 `MONTHLY`/`PERMANENT`,数据库中是 `monthly`/`permanent`

**解决方案**: 统一为小写 snake_case (符合 PostgreSQL 规范)

```python
# domains/billing/value_objects.py

# ❌ 旧代码:
class CreditBucket(str, Enum):
    MONTHLY = "MONTHLY"           # 需要运行时转换为 "monthly"
    PERMANENT = "PERMANENT"       # 需要运行时转换为 "permanent"

# ✅ 新代码:
class CreditBucket(str, Enum):
    MONTHLY = "monthly"           # 直接匹配数据库值
    PERMANENT = "permanent"

class TransactionType(str, Enum):
    SUBSCRIPTION_GRANT = "subscription_grant"
    PURCHASE = "purchase"
    AI_GENERATION = "ai_generation"
    SMART_SCAN = "smart_scan"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    SIGNUP_BONUS = "signup_bonus"
    REFERRAL_BONUS = "referral_bonus"
    CAMPAIGN_REWARD = "campaign_reward"
    EXPIRATION = "expiration"
    MARKETPLACE_PURCHASE = "marketplace_purchase"
    MARKETPLACE_SALE = "marketplace_sale"
    TRIAL_GRANT = "trial_grant"
```

**影响范围**:
- `domains/billing/value_objects.py` - 枚举定义
- `infrastructure/repositories/credit_repository.py` - 移除 `.lower()` 转换
- `application/commands/billing.py` - 使用枚举时不需要转换
- `api/billing/*.py` - 返回值直接使用枚举值

**预计时间**: 4 小时 (包括测试)

---

#### 1.3 创建字段映射表 (4 小时)

**目标**: 创建单一真实来源 (Single Source of Truth),文档化所有表 ↔ 聚合根的映射

**实现**:

```python
# infrastructure/repositories/field_mappings.py
"""
数据库字段 ↔ 领域对象字段映射
这是代码和数据库同步的单一真实来源 (SSOT)

使用方式:
1. 新增表时,先在此文件定义映射关系
2. Repository 实现时,使用 map_db_to_domain() 和 map_domain_to_db()
3. 运行测试验证映射正确性
"""

from typing import Dict, Any
from dataclasses import asdict

# ============================================================
# profiles 表 → UserProfile 聚合根
# ============================================================
PROFILES_DB_TO_DOMAIN: Dict[str, str] = {
    # 数据库字段 → 聚合根属性路径
    'id': 'user_id',                          # TEXT (Clerk ID)
    'email': 'email',                         # TEXT
    'tier': 'tier',                           # TEXT (t1/t2/t3) → UserTier enum
    'tier_changed_at': 'tier_changed_at',     # TIMESTAMPTZ
    'credits_monthly': 'balance.monthly',     # INTEGER
    'credits_permanent': 'balance.permanent', # INTEGER
    'stripe_customer_id': 'stripe_customer_id', # TEXT
    'stripe_subscription_id': 'stripe_subscription_id', # TEXT
    'trial_start_date': 'trial_start_date',   # DATE
    'trial_end_date': 'trial_end_date',       # DATE
    'is_deleted': 'is_deleted',               # BOOLEAN
    'deleted_at': 'deleted_at',               # TIMESTAMPTZ
    'created_at': 'created_at',               # TIMESTAMPTZ
    'updated_at': 'updated_at',               # TIMESTAMPTZ
}

# ============================================================
# credit_transactions 表 → CreditTransaction 值对象
# ============================================================
CREDIT_TX_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'transaction_id',                   # UUID
    'user_id': 'user_id',                     # TEXT
    'transaction_type': 'tx_type',            # TEXT → TransactionType enum
    'bucket': 'bucket',                       # TEXT → CreditBucket enum
    'amount': 'amount',                       # INTEGER
    'balance_monthly_after': 'balance.monthly',   # INTEGER
    'balance_permanent_after': 'balance.permanent', # INTEGER
    'description': 'description',             # TEXT
    'idempotency_key': 'idempotency_key',     # TEXT
    'metadata': 'metadata',                   # JSONB → dict
    'created_at': 'created_at',               # TIMESTAMPTZ
}

# ============================================================
# projects 表 → Project 聚合根
# ============================================================
PROJECTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'project_id',                       # UUID (注意: 代码中使用 project_id)
    'user_id': 'owner_id',                    # TEXT (注意: 代码中使用 owner_id)
    'title': 'title',                         # TEXT
    'description': 'description',             # TEXT
    'paper_size': 'paper_size',               # TEXT → PaperSize enum
    'orientation': 'orientation',             # TEXT → Orientation enum
    'num_pages': 'num_pages',                 # INTEGER
    'is_public': 'is_public',                 # BOOLEAN
    'marketplace_listing_id': 'listing_id',   # UUID (可空)
    'source_listing_id': 'source_listing_id', # UUID (可空) - 购买来源
    'is_purchased': 'is_purchased',           # BOOLEAN
    'origin_owner_id': 'origin_owner_id',     # TEXT (可空) - 原作者
    'contains_locked_elements': 'contains_locked_elements', # BOOLEAN
    'is_deleted': 'is_deleted',               # BOOLEAN
    'deleted_at': 'deleted_at',               # TIMESTAMPTZ
    'created_at': 'created_at',               # TIMESTAMPTZ
    'updated_at': 'updated_at',               # TIMESTAMPTZ
}

# ============================================================
# marketplace_listings 表 → Listing 聚合根
# ============================================================
LISTINGS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'listing_id',                       # UUID
    'project_id': 'project_id',               # UUID
    'seller_id': 'seller_id',                 # TEXT
    'title': 'title',                         # TEXT
    'description': 'description',             # TEXT
    'price_usd': 'price_usd',                 # NUMERIC
    'price_credits': 'price_credits',         # INTEGER
    'preview_image_url': 'preview_image_url', # TEXT
    'tags': 'tags',                           # TEXT[]
    'category': 'category',                   # TEXT → AssetCategory enum
    'total_purchases': 'total_purchases',     # INTEGER
    'total_favorites': 'total_favorites',     # INTEGER
    'avg_rating': 'avg_rating',               # NUMERIC
    'moderation_status': 'moderation_status', # TEXT → ModerationStatus enum
    'is_featured': 'is_featured',             # BOOLEAN
    'is_visible': 'is_visible',               # BOOLEAN
    'is_deleted': 'is_deleted',               # BOOLEAN
    'deleted_at': 'deleted_at',               # TIMESTAMPTZ
    'created_at': 'created_at',               # TIMESTAMPTZ
    'updated_at': 'updated_at',               # TIMESTAMPTZ
}

# ============================================================
# 映射工具函数
# ============================================================

def map_db_to_domain(db_record: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    将数据库记录映射为领域对象属性

    Example:
        db_record = {"id": "user_123", "credits_monthly": 100}
        mapping = PROFILES_DB_TO_DOMAIN
        result = map_db_to_domain(db_record, mapping)
        # => {"user_id": "user_123", "balance": {"monthly": 100}}
    """
    result = {}
    for db_field, domain_path in mapping.items():
        if db_field not in db_record:
            continue

        db_value = db_record[db_field]

        # 处理嵌套路径 (如 "balance.monthly")
        if "." in domain_path:
            parts = domain_path.split(".")
            current = result
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = db_value
        else:
            result[domain_path] = db_value

    return result

def map_domain_to_db(domain_obj: Any, mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    将领域对象映射为数据库记录

    Example:
        user = UserProfile(user_id="user_123", balance=Credits(monthly=100, permanent=50))
        mapping = PROFILES_DB_TO_DOMAIN
        result = map_domain_to_db(user, mapping)
        # => {"id": "user_123", "credits_monthly": 100, "credits_permanent": 50}
    """
    domain_dict = asdict(domain_obj) if hasattr(domain_obj, '__dataclass_fields__') else vars(domain_obj)

    result = {}
    for db_field, domain_path in mapping.items():
        # 处理嵌套路径
        if "." in domain_path:
            parts = domain_path.split(".")
            current = domain_dict
            for part in parts:
                if part in current:
                    current = current[part]
                else:
                    current = None
                    break
            if current is not None:
                result[db_field] = current
        else:
            if domain_path in domain_dict:
                result[db_field] = domain_dict[domain_path]

    return result

# ============================================================
# 验证工具
# ============================================================

def validate_mapping(table_name: str, mapping: Dict[str, str], db_schema: Dict[str, str]):
    """
    验证映射表的正确性

    Args:
        table_name: 表名
        mapping: 字段映射字典
        db_schema: 数据库 Schema (字段名 → 数据类型)

    Raises:
        ValueError: 如果映射中的字段不存在于 Schema
    """
    for db_field in mapping.keys():
        if db_field not in db_schema:
            raise ValueError(
                f"映射错误: 表 {table_name} 中不存在字段 {db_field}\n"
                f"Schema 中的字段: {list(db_schema.keys())}"
            )

    print(f"✅ 表 {table_name} 的映射验证通过 ({len(mapping)} 个字段)")
```

**使用示例**:

```python
# infrastructure/repositories/user_repository.py
from infrastructure.repositories.field_mappings import (
    PROFILES_DB_TO_DOMAIN,
    map_db_to_domain,
    map_domain_to_db
)

class SupabaseUserRepository(IUserRepository):
    async def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        result = self.client.table("profiles").select("*").eq("id", user_id).execute()

        if not result.data:
            return None

        # 使用映射表转换
        domain_data = map_db_to_domain(result.data[0], PROFILES_DB_TO_DOMAIN)

        # 构造聚合根
        return UserProfile(
            user_id=domain_data['user_id'],
            email=domain_data['email'],
            tier=UserTier(domain_data['tier']),
            balance=Credits(
                monthly=domain_data['balance']['monthly'],
                permanent=domain_data['balance']['permanent']
            ),
            # ...
        )
```

**预计时间**: 4 小时

---

#### 1.4 在聚合根中添加业务约束验证 (4 小时)

**目标**: 确保业务规则在代码层和数据库层都有验证 (双重防守)

**实现**:

```python
# domains/billing/aggregates/user_credits.py
from dataclasses import dataclass, field
from domains.billing.value_objects import Credits, CreditBucket, TransactionType
from domains.billing.exceptions import (
    InsufficientCreditsException,
    InvalidAmountException,
    CreditLimitExceededException
)

@dataclass
class UserCredits:
    """
    用户积分聚合根

    业务约束 (与数据库 CHECK 约束同步):
    - 月度积分: 0 <= credits_monthly <= 1,000,000
    - 永久积分: 0 <= credits_permanent <= 10,000,000
    - 扣费规则: 优先扣月度,再扣永久
    - 原子性: 通过 pending_transactions 确保
    """

    user_id: str
    balance: Credits
    pending_transactions: list = field(default_factory=list)

    # 常量定义 (与数据库 CHECK 约束同步)
    MAX_MONTHLY_CREDITS = 1_000_000
    MAX_PERMANENT_CREDITS = 10_000_000
    MIN_CREDITS = 0

    def __post_init__(self):
        """验证约束 (与数据库 CHECK 同步)"""
        self._validate_constraints()

    def _validate_constraints(self):
        """验证业务约束"""
        if self.balance.monthly < self.MIN_CREDITS:
            raise ValueError(f"月度积分不能为负: {self.balance.monthly}")

        if self.balance.monthly > self.MAX_MONTHLY_CREDITS:
            raise CreditLimitExceededException(
                f"月度积分超过限制: {self.balance.monthly} > {self.MAX_MONTHLY_CREDITS}"
            )

        if self.balance.permanent < self.MIN_CREDITS:
            raise ValueError(f"永久积分不能为负: {self.balance.permanent}")

        if self.balance.permanent > self.MAX_PERMANENT_CREDITS:
            raise CreditLimitExceededException(
                f"永久积分超过限制: {self.balance.permanent} > {self.MAX_PERMANENT_CREDITS}"
            )

    def deduct(self, amount: int, tx_type: TransactionType, description: str = None) -> Credits:
        """
        扣费业务规则 (优先扣月度积分)

        业务规则:
        1. amount 必须 > 0
        2. 总积分必须 >= amount
        3. 优先扣月度积分,不足时扣永久积分
        4. 扣费后立即验证约束

        Args:
            amount: 扣费金额 (必须 > 0)
            tx_type: 交易类型
            description: 交易描述

        Returns:
            扣费后的积分余额

        Raises:
            InvalidAmountException: 金额无效
            InsufficientCreditsException: 积分不足
            CreditLimitExceededException: 扣费后违反约束
        """
        # 前置验证
        if amount <= 0:
            raise InvalidAmountException(f"扣费金额必须大于 0: {amount}")

        total_credits = self.balance.total
        if total_credits < amount:
            raise InsufficientCreditsException(
                f"积分不足: 需要 {amount},当前 {total_credits} "
                f"(月度: {self.balance.monthly}, 永久: {self.balance.permanent})"
            )

        # 执行扣费 (优先月度)
        remaining = amount
        monthly_deducted = 0
        permanent_deducted = 0

        if self.balance.monthly > 0:
            monthly_deducted = min(self.balance.monthly, remaining)
            remaining -= monthly_deducted

        if remaining > 0:
            permanent_deducted = remaining

        # 更新余额
        new_balance = Credits(
            monthly=self.balance.monthly - monthly_deducted,
            permanent=self.balance.permanent - permanent_deducted
        )

        # 记录待提交的交易
        self.pending_transactions.append({
            'tx_type': tx_type,
            'bucket': CreditBucket.MONTHLY if monthly_deducted > 0 else CreditBucket.PERMANENT,
            'amount': -amount,  # 负数表示扣费
            'balance_after': new_balance,
            'description': description,
            'monthly_deducted': monthly_deducted,
            'permanent_deducted': permanent_deducted,
        })

        # 更新内部状态
        self.balance = new_balance

        # 后置验证 (确保不违反约束)
        self._validate_constraints()

        return self.balance

    def add(self, amount: int, bucket: CreditBucket, tx_type: TransactionType, description: str = None) -> Credits:
        """
        增加积分业务规则

        Args:
            amount: 增加金额 (必须 > 0)
            bucket: 积分桶 (月度 or 永久)
            tx_type: 交易类型
            description: 交易描述

        Returns:
            增加后的积分余额

        Raises:
            InvalidAmountException: 金额无效
            CreditLimitExceededException: 增加后超过限制
        """
        if amount <= 0:
            raise InvalidAmountException(f"增加金额必须大于 0: {amount}")

        # 计算新余额
        if bucket == CreditBucket.MONTHLY:
            new_monthly = self.balance.monthly + amount
            if new_monthly > self.MAX_MONTHLY_CREDITS:
                raise CreditLimitExceededException(
                    f"增加后月度积分超过限制: {new_monthly} > {self.MAX_MONTHLY_CREDITS}"
                )
            new_balance = Credits(monthly=new_monthly, permanent=self.balance.permanent)
        else:
            new_permanent = self.balance.permanent + amount
            if new_permanent > self.MAX_PERMANENT_CREDITS:
                raise CreditLimitExceededException(
                    f"增加后永久积分超过限制: {new_permanent} > {self.MAX_PERMANENT_CREDITS}"
                )
            new_balance = Credits(monthly=self.balance.monthly, permanent=new_permanent)

        # 记录待提交的交易
        self.pending_transactions.append({
            'tx_type': tx_type,
            'bucket': bucket,
            'amount': amount,
            'balance_after': new_balance,
            'description': description,
        })

        # 更新内部状态
        self.balance = new_balance

        # 后置验证
        self._validate_constraints()

        return self.balance

    @property
    def total_credits(self) -> int:
        """总积分 (月度 + 永久)"""
        return self.balance.total

    def can_afford(self, amount: int) -> bool:
        """检查是否有足够积分"""
        return self.total_credits >= amount
```

**预计时间**: 4 小时

---

**Phase 1 总计**: 16 小时 (2 个工作日)

---

### Phase 2: P1 高优先级优化 (Day 3-5, 估计 24-36 小时)

#### 2.1 创建 13 个缺失的数据库表 (12 小时)

**优先级分类**:

| 优先级 | 表名 | 用途 | 预计时间 |
|--------|------|------|---------|
| P0 (立即) | user_events | 用户行为追踪 | 1h |
| P0 | aggregated_stats | 统计聚合 | 1h |
| P0 | error_logs | 错误日志 | 1h |
| P0 | support_tickets | 支持工单 | 1.5h |
| P0 | support_replies | 工单回复 | 0.5h |
| P1 (本周) | admin_operations | 管理员操作日志 | 1h |
| P1 | listing_usages | 资产使用追踪 | 1h |
| P1 | marketplace_reports | 市场报告 | 1h |
| P1 | daily_metrics | 每日指标 | 1h |
| P1 | monthly_metrics | 月度指标 | 1h |
| P2 (下周) | generation_tasks | AI 生成任务 | 1h |
| P2 | page_prompt_templates | 页面模板 | 0.5h |
| P2 | payment_records | 支付记录 | 1h |

**执行方式**: 创建单独的迁移文件

```sql
-- migrations/v2/patches/001_create_missing_tables_p0.sql

-- ============================================================
-- user_events 表 - 用户行为追踪
-- ============================================================
CREATE TABLE user_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    session_id TEXT,
    ip_address INET,
    user_agent TEXT,
    referer TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_event_type CHECK (
        event_type IN (
            'page_view', 'button_click', 'form_submit',
            'feature_used', 'error_occurred', 'api_call',
            'project_created', 'project_updated', 'project_deleted',
            'asset_uploaded', 'asset_purchased', 'payment_completed'
        )
    )
);

CREATE INDEX idx_user_events_user_id ON user_events(user_id);
CREATE INDEX idx_user_events_event_type ON user_events(event_type);
CREATE INDEX idx_user_events_created_at ON user_events(created_at DESC);
CREATE INDEX idx_user_events_session ON user_events(session_id) WHERE session_id IS NOT NULL;

COMMENT ON TABLE user_events IS '用户行为事件追踪表,记录所有用户交互行为';
COMMENT ON COLUMN user_events.event_type IS '事件类型,枚举值见 CHECK 约束';
COMMENT ON COLUMN user_events.event_data IS '事件详情 (JSON 格式),结构取决于 event_type';

-- ============================================================
-- aggregated_stats 表 - 统计聚合
-- ============================================================
CREATE TABLE aggregated_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_type TEXT NOT NULL,
    stat_key TEXT NOT NULL,
    stat_value NUMERIC DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_stat_type CHECK (
        stat_type IN ('daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'custom')
    ),
    CONSTRAINT unique_aggregated_stat UNIQUE (stat_type, stat_key, period_start)
);

CREATE INDEX idx_aggregated_stats_period ON aggregated_stats(period_start DESC, period_end DESC);
CREATE INDEX idx_aggregated_stats_type_key ON aggregated_stats(stat_type, stat_key);

COMMENT ON TABLE aggregated_stats IS '聚合统计表,存储各时间维度的指标汇总';
COMMENT ON COLUMN aggregated_stats.stat_key IS '指标键 (如 "total_users", "active_users", "revenue")';
COMMENT ON COLUMN aggregated_stats.metadata IS '附加元数据 (如 breakdown by tier)';

-- ============================================================
-- error_logs 表 - 错误日志
-- ============================================================
CREATE TABLE error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT REFERENCES profiles(id) ON DELETE SET NULL,
    error_type TEXT NOT NULL,
    error_message TEXT,
    stack_trace TEXT,
    request_path TEXT,
    request_method TEXT,
    request_body JSONB,
    response_status_code INTEGER,
    severity TEXT DEFAULT 'error',
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_severity CHECK (
        severity IN ('debug', 'info', 'warning', 'error', 'critical', 'fatal')
    ),
    CONSTRAINT check_status_code CHECK (
        response_status_code IS NULL OR (response_status_code >= 100 AND response_status_code < 600)
    )
);

CREATE INDEX idx_error_logs_user_id ON error_logs(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_error_logs_created_at ON error_logs(created_at DESC);
CREATE INDEX idx_error_logs_resolved ON error_logs(resolved, created_at DESC) WHERE NOT resolved;
CREATE INDEX idx_error_logs_severity ON error_logs(severity, created_at DESC);
CREATE INDEX idx_error_logs_error_type ON error_logs(error_type);

COMMENT ON TABLE error_logs IS '系统错误日志表,记录所有后端异常';
COMMENT ON COLUMN error_logs.severity IS '错误严重程度,影响告警策略';
COMMENT ON COLUMN error_logs.resolved IS '是否已解决 (用于工程师追踪)';

-- ============================================================
-- support_tickets 表 - 支持工单
-- ============================================================
CREATE TABLE support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT,
    priority TEXT DEFAULT 'normal',
    status TEXT DEFAULT 'open',
    assigned_to TEXT,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,

    CONSTRAINT check_priority CHECK (
        priority IN ('low', 'normal', 'high', 'urgent', 'critical')
    ),
    CONSTRAINT check_status CHECK (
        status IN ('open', 'pending', 'in_progress', 'waiting_user', 'resolved', 'closed', 'wont_fix')
    ),
    CONSTRAINT check_category CHECK (
        category IS NULL OR category IN (
            'bug', 'feature_request', 'account', 'billing', 'technical', 'feedback', 'other'
        )
    ),
    CONSTRAINT check_subject_length CHECK (length(subject) >= 5 AND length(subject) <= 200),
    CONSTRAINT check_description_length CHECK (length(description) >= 10)
);

CREATE INDEX idx_support_tickets_user_id ON support_tickets(user_id);
CREATE INDEX idx_support_tickets_status ON support_tickets(status, created_at DESC);
CREATE INDEX idx_support_tickets_assigned ON support_tickets(assigned_to) WHERE assigned_to IS NOT NULL;
CREATE INDEX idx_support_tickets_priority ON support_tickets(priority, created_at DESC);
CREATE INDEX idx_support_tickets_category ON support_tickets(category) WHERE category IS NOT NULL;

-- 自动更新 updated_at
CREATE TRIGGER update_support_tickets_updated_at
    BEFORE UPDATE ON support_tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE support_tickets IS '客户支持工单表';
COMMENT ON COLUMN support_tickets.assigned_to IS '分配给的工程师 ID (TEXT, 可扩展为员工系统)';

-- ============================================================
-- support_replies 表 - 工单回复
-- ============================================================
CREATE TABLE support_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES profiles(id) ON DELETE SET NULL,
    is_staff BOOLEAN DEFAULT false,
    message TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_message_length CHECK (length(message) > 0)
);

CREATE INDEX idx_support_replies_ticket_id ON support_replies(ticket_id, created_at);
CREATE INDEX idx_support_replies_user_id ON support_replies(user_id) WHERE user_id IS NOT NULL;

COMMENT ON TABLE support_replies IS '工单回复表 (支持用户和工程师回复)';
COMMENT ON COLUMN support_replies.is_staff IS 'true: 工程师回复, false: 用户回复';
COMMENT ON COLUMN support_replies.attachments IS 'JSON 数组,存储附件 URL 列表';
```

**同步更新 refactored_schema_v2.sql**:
```bash
# 将新表定义追加到 refactored_schema_v2.sql
cat migrations/v2/patches/001_create_missing_tables_p0.sql >> migrations/v2/refactored_schema_v2.sql
```

**预计时间**: 12 小时 (包括 P0/P1/P2 所有表)

---

#### 2.2 添加缺失字段到现有表 (4 小时)

**profiles 表缺失字段**:

```sql
-- migrations/v2/patches/002_add_missing_fields_profiles.sql

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS first_name TEXT,
ADD COLUMN IF NOT EXISTS last_name TEXT,
ADD COLUMN IF NOT EXISTS onboarding_step TEXT DEFAULT 'not_started',
ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS credits_reset_at TIMESTAMPTZ;

-- 添加约束
ALTER TABLE profiles
ADD CONSTRAINT check_onboarding_step CHECK (
    onboarding_step IN (
        'not_started', 'profile_setup', 'tutorial_completed', 'first_project_created', 'completed'
    )
);

-- 添加注释
COMMENT ON COLUMN profiles.first_name IS '用户名字 (可选)';
COMMENT ON COLUMN profiles.last_name IS '用户姓氏 (可选)';
COMMENT ON COLUMN profiles.onboarding_step IS '新手引导步骤';
COMMENT ON COLUMN profiles.preferences IS '用户偏好设置 (JSON 格式)';
COMMENT ON COLUMN profiles.credits_reset_at IS '月度积分重置时间 (用于跟踪下次重置)';
```

**projects 表缺失字段**:

```sql
-- migrations/v2/patches/003_add_missing_fields_projects.sql

ALTER TABLE projects
ADD COLUMN IF NOT EXISTS is_permanently_deleted BOOLEAN DEFAULT false;

-- 添加注释
COMMENT ON COLUMN projects.is_permanently_deleted IS '是否永久删除 (true: 硬删除, false: 软删除)';

-- 创建条件索引 (只索引未永久删除的项目)
CREATE INDEX idx_projects_not_permanently_deleted
ON projects(user_id, created_at DESC)
WHERE is_deleted = FALSE AND is_permanently_deleted = FALSE;
```

**预计时间**: 4 小时

---

#### 2.3 实现 soft delete + hard delete API (8 小时)

**目标**: 所有 Repository 支持逻辑删除和物理删除,并在查询时自动过滤已删除记录

**实现策略**:

```python
# infrastructure/repositories/base_repository.py (新文件)
"""
基础 Repository,提供通用的软删除和查询过滤
"""

from abc import ABC
from typing import Optional, List, Dict, Any
from core.database import IDatabase

class BaseRepository(ABC):
    """
    基础 Repository,提供通用功能:
    1. 软删除 (is_deleted = TRUE)
    2. 硬删除 (永久删除记录)
    3. 自动过滤已删除记录
    """

    def __init__(self, client: IDatabase, table_name: str):
        self.client = client
        self.table_name = table_name

    async def _query_active_only(self, query):
        """
        自动过滤已删除记录

        使用方式:
            query = self.client.table("projects").select("*")
            query = self._query_active_only(query)  # 添加 WHERE is_deleted=FALSE
            result = await query.execute()
        """
        return query.eq("is_deleted", False)

    async def soft_delete(self, record_id: str, id_column: str = "id") -> bool:
        """
        软删除 (逻辑删除)

        Args:
            record_id: 记录 ID
            id_column: 主键列名 (默认 "id")

        Returns:
            是否成功删除
        """
        from datetime import datetime, timezone

        result = self.client.table(self.table_name).update({
            "is_deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        }).eq(id_column, record_id).execute()

        return bool(result.data)

    async def hard_delete(self, record_id: str, id_column: str = "id") -> bool:
        """
        硬删除 (物理删除,不可恢复)

        ⚠️ 警告: 此操作不可逆!

        Args:
            record_id: 记录 ID
            id_column: 主键列名 (默认 "id")

        Returns:
            是否成功删除
        """
        result = self.client.table(self.table_name).delete().eq(id_column, record_id).execute()
        return bool(result.data)

    async def restore(self, record_id: str, id_column: str = "id") -> bool:
        """
        恢复已软删除的记录

        Args:
            record_id: 记录 ID
            id_column: 主键列名 (默认 "id")

        Returns:
            是否成功恢复
        """
        result = self.client.table(self.table_name).update({
            "is_deleted": False,
            "deleted_at": None,
        }).eq(id_column, record_id).eq("is_deleted", True).execute()

        return bool(result.data)
```

**使用示例**:

```python
# infrastructure/repositories/project_repository.py
from infrastructure.repositories.base_repository import BaseRepository
from domains.creation.repository import IProjectRepository

class SupabaseProjectRepository(BaseRepository, IProjectRepository):
    def __init__(self, client: IDatabase):
        super().__init__(client, "projects")

    async def get_user_projects(self, user_id: str, include_deleted: bool = False) -> List[Project]:
        """
        获取用户的项目列表

        Args:
            user_id: 用户 ID
            include_deleted: 是否包含已删除项目 (默认 False)

        Returns:
            项目列表
        """
        query = self.client.table(self.table_name).select("*").eq("user_id", user_id)

        # 自动过滤已删除项目 (除非明确要求包含)
        if not include_deleted:
            query = self._query_active_only(query)

        result = await query.order("created_at", desc=True).execute()

        return [self._map_to_project(row) for row in result.data]

    async def delete_project(self, project_id: str, permanent: bool = False) -> bool:
        """
        删除项目

        Args:
            project_id: 项目 ID
            permanent: 是否永久删除 (True: 硬删除, False: 软删除)

        Returns:
            是否成功删除
        """
        if permanent:
            return await self.hard_delete(project_id)
        else:
            return await self.soft_delete(project_id)
```

**API 层使用**:

```python
# api/user/projects.py
@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    permanent: bool = Query(False, description="是否永久删除 (不可恢复)"),
    user: dict = Depends(get_current_user)
):
    """
    删除项目

    - permanent=false: 软删除 (可恢复)
    - permanent=true: 硬删除 (不可恢复,需要二次确认)
    """
    container = get_container()
    repo = container.project_repository

    # 验证项目所有权
    project = await repo.get_by_id(project_id)
    if not project or project.owner_id != user["id"]:
        raise HTTPException(404, "项目不存在")

    # 如果是硬删除,需要额外验证
    if permanent:
        # 可以添加二次确认逻辑 (如要求传入项目标题)
        pass

    success = await repo.delete_project(project_id, permanent=permanent)

    return {
        "success": success,
        "deleted_permanently": permanent,
        "message": "项目已永久删除" if permanent else "项目已删除 (可恢复)"
    }
```

**预计时间**: 8 小时

---

**Phase 2 总计**: 24 小时 (3 个工作日)

---

### Phase 3: P2 文档与优化 (Day 6-7, 估计 16-24 小时)

#### 3.1 完善 Schema 注释 (8 小时)

**目标**: 为所有表和字段添加 COMMENT,便于数据库可视化工具展示

```sql
-- migrations/v2/patches/010_add_schema_comments.sql

-- ============================================================
-- profiles 表注释
-- ============================================================
COMMENT ON TABLE profiles IS '用户档案表,存储 Clerk 认证用户的基础信息和业务数据';

COMMENT ON COLUMN profiles.id IS '用户 ID (来自 Clerk,格式: user_xxxxx)';
COMMENT ON COLUMN profiles.email IS '用户邮箱';
COMMENT ON COLUMN profiles.tier IS '用户等级 (t1:免费版, t2:基础版, t3:专业版)';
COMMENT ON COLUMN profiles.tier_changed_at IS '等级变更时间 (用于追踪升级/降级历史)';
COMMENT ON COLUMN profiles.credits_monthly IS '月度积分余额 (每月重置)';
COMMENT ON COLUMN profiles.credits_permanent IS '永久积分余额 (不重置)';
COMMENT ON COLUMN profiles.stripe_customer_id IS 'Stripe 客户 ID (格式: cus_xxxxx)';
COMMENT ON COLUMN profiles.stripe_subscription_id IS 'Stripe 订阅 ID (格式: sub_xxxxx)';
COMMENT ON COLUMN profiles.trial_start_date IS '试用开始日期';
COMMENT ON COLUMN profiles.trial_end_date IS '试用结束日期';
COMMENT ON COLUMN profiles.is_deleted IS '是否已删除 (软删除标记)';
COMMENT ON COLUMN profiles.deleted_at IS '删除时间 (软删除时设置)';
COMMENT ON COLUMN profiles.created_at IS '创建时间 (UTC)';
COMMENT ON COLUMN profiles.updated_at IS '更新时间 (UTC,通过触发器自动更新)';

-- ============================================================
-- credit_transactions 表注释
-- ============================================================
COMMENT ON TABLE credit_transactions IS 'Append-Only 积分交易表,记录所有积分变动 (通过触发器防止修改/删除)';

COMMENT ON COLUMN credit_transactions.id IS '交易 ID (UUID)';
COMMENT ON COLUMN credit_transactions.user_id IS '用户 ID (外键: profiles.id)';
COMMENT ON COLUMN credit_transactions.transaction_type IS '交易类型 (subscription_grant, purchase, ai_generation, refund, etc.)';
COMMENT ON COLUMN credit_transactions.bucket IS '积分桶 (monthly: 月度, permanent: 永久)';
COMMENT ON COLUMN credit_transactions.amount IS '交易金额 (正数: 增加, 负数: 扣减)';
COMMENT ON COLUMN credit_transactions.balance_monthly_after IS '交易后月度积分余额 (快照)';
COMMENT ON COLUMN credit_transactions.balance_permanent_after IS '交易后永久积分余额 (快照)';
COMMENT ON COLUMN credit_transactions.description IS '交易描述 (人类可读)';
COMMENT ON COLUMN credit_transactions.idempotency_key IS '幂等键 (防止重复交易,唯一索引)';
COMMENT ON COLUMN credit_transactions.metadata IS '扩展元数据 (JSON 格式)';
COMMENT ON COLUMN credit_transactions.created_at IS '交易时间 (UTC,不可修改)';

-- ============================================================
-- projects 表注释
-- ============================================================
COMMENT ON TABLE projects IS '用户项目表,存储所有创作项目';

COMMENT ON COLUMN projects.id IS '项目 ID (UUID)';
COMMENT ON COLUMN projects.user_id IS '项目所有者 ID (外键: profiles.id)';
COMMENT ON COLUMN projects.title IS '项目标题';
COMMENT ON COLUMN projects.description IS '项目描述';
COMMENT ON COLUMN projects.paper_size IS '纸张尺寸 (A4, Letter, etc.)';
COMMENT ON COLUMN projects.orientation IS '方向 (portrait: 纵向, landscape: 横向)';
COMMENT ON COLUMN projects.num_pages IS '页数';
COMMENT ON COLUMN projects.is_public IS '是否公开';
COMMENT ON COLUMN projects.marketplace_listing_id IS '关联的市场商品 ID (如果已上架)';
COMMENT ON COLUMN projects.source_listing_id IS '购买来源商品 ID (如果是购买的)';
COMMENT ON COLUMN projects.is_purchased IS '是否为购买的项目';
COMMENT ON COLUMN projects.origin_owner_id IS '原作者 ID (购买时记录)';
COMMENT ON COLUMN projects.contains_locked_elements IS '是否包含锁定元素 (需 Pro 解锁)';
COMMENT ON COLUMN projects.is_deleted IS '是否已删除 (软删除)';
COMMENT ON COLUMN projects.is_permanently_deleted IS '是否永久删除 (硬删除标记)';
COMMENT ON COLUMN projects.deleted_at IS '删除时间';
COMMENT ON COLUMN projects.created_at IS '创建时间';
COMMENT ON COLUMN projects.updated_at IS '更新时间 (自动更新)';

-- (继续为所有表添加注释...)
```

**预计时间**: 8 小时

---

#### 3.2 创建数据库设计文档 (8 小时)

**创建 `docs/main/DATABASE-SCHEMA-DESIGN.md`**:

```markdown
# Make Decodables 数据库设计文档

> **版本**: v4.0
> **Schema 文件**: migrations/v2/refactored_schema_v2.sql (3,158 行)
> **总表数**: 47
> **设计理念**: PostgreSQL 最佳实践 + Append-Only + 审计追踪

---

## 1. 设计原则

### 1.1 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 表名 | snake_case, 复数形式 | profiles, credit_transactions, marketplace_listings |
| 字段名 | snake_case | user_id, created_at, stripe_customer_id |
| 主键 | id (UUID) 或 id (TEXT) | profiles.id (TEXT), projects.id (UUID) |
| 外键 | {table}_id | user_id, project_id, listing_id |
| 布尔字段 | is_{state} | is_deleted, is_public, is_visible |
| 时间戳 | {action}_at | created_at, updated_at, deleted_at |
| 枚举字段 | {noun}_{adjective} | transaction_type, moderation_status |

### 1.2 审计字段标准

所有业务表都包含以下标准审计字段:

```sql
created_at TIMESTAMPTZ DEFAULT NOW()     -- 创建时间 (UTC)
updated_at TIMESTAMPTZ DEFAULT NOW()     -- 更新时间 (自动触发器)
is_deleted BOOLEAN DEFAULT false         -- 软删除标记
deleted_at TIMESTAMPTZ                   -- 删除时间
```

### 1.3 Append-Only 模式

关键业务表 (如 credit_transactions) 使用 Append-Only 模式:

```sql
-- 创建触发器,防止修改和删除
CREATE OR REPLACE FUNCTION prevent_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Table % is append-only. Updates and deletes are not allowed.', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_credit_tx_modification
    BEFORE UPDATE OR DELETE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_modification();
```

**优势**:
- ✅ 防止数据篡改 (合规要求)
- ✅ 完整审计追踪
- ✅ 便于数据恢复

---

## 2. 核心表设计

### 2.1 profiles 表 - 用户档案

**设计目标**: 存储 Clerk 认证用户的业务信息

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | TEXT | PRIMARY KEY | Clerk User ID (user_xxxxx) |
| email | TEXT | UNIQUE, NOT NULL | 邮箱 |
| tier | TEXT | CHECK (t1/t2/t3) | 用户等级 |
| tier_changed_at | TIMESTAMPTZ | | 等级变更时间 |
| credits_monthly | INTEGER | CHECK (0-1000000) | 月度积分 |
| credits_permanent | INTEGER | CHECK (0-10000000) | 永久积分 |

**索引设计**:
```sql
CREATE UNIQUE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_tier ON profiles(tier);
CREATE INDEX idx_profiles_created_at ON profiles(created_at DESC);
```

**业务约束**:
- ✅ 月度积分上限 100 万
- ✅ 永久积分上限 1000 万
- ✅ tier 只能是 t1/t2/t3

---

### 2.2 credit_transactions 表 - 积分交易 (Append-Only)

**设计目标**: 不可变的积分交易记录

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PRIMARY KEY | 交易 ID |
| user_id | TEXT | FOREIGN KEY | 用户 ID |
| transaction_type | TEXT | CHECK (13 种枚举) | 交易类型 |
| bucket | TEXT | CHECK (monthly/permanent) | 积分桶 |
| amount | INTEGER | NOT NULL | 金额 (正/负) |
| balance_monthly_after | INTEGER | NOT NULL | 交易后月度余额 (快照) |
| balance_permanent_after | INTEGER | NOT NULL | 交易后永久余额 (快照) |
| idempotency_key | TEXT | UNIQUE | 幂等键 |

**索引设计**:
```sql
CREATE INDEX idx_credit_tx_user_id ON credit_transactions(user_id, created_at DESC);
CREATE UNIQUE INDEX idx_credit_tx_idempotency ON credit_transactions(idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE INDEX idx_credit_tx_type ON credit_transactions(transaction_type);
```

**触发器**:
- ✅ prevent_modification() - 禁止 UPDATE/DELETE
- ✅ Append-Only 保证

---

(继续为所有 47 张表编写详细设计文档...)

---

## 3. 索引策略

### 3.1 复合索引

```sql
-- 用户项目列表查询 (user_id + 时间排序)
CREATE INDEX idx_projects_user_created ON projects(user_id, created_at DESC);

-- 积分交易历史查询
CREATE INDEX idx_credit_tx_user_created ON credit_transactions(user_id, created_at DESC);
```

### 3.2 条件索引 (Partial Index)

```sql
-- 只索引未删除的记录 (提升查询性能)
CREATE INDEX idx_projects_active ON projects(user_id, created_at DESC)
WHERE is_deleted = FALSE;

-- 只索引已上架的商品
CREATE INDEX idx_listings_visible ON marketplace_listings(category, created_at DESC)
WHERE is_visible = TRUE AND is_deleted = FALSE;
```

---

## 4. RPC 函数

### 4.1 原子扣费函数

```sql
CREATE OR REPLACE FUNCTION deduct_credits_atomic(
    p_user_id TEXT,
    p_amount INTEGER,
    p_transaction_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_idempotency_key TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_monthly_balance INTEGER;
    v_permanent_balance INTEGER;
    v_monthly_deducted INTEGER := 0;
    v_permanent_deducted INTEGER := 0;
    v_remaining INTEGER;
BEGIN
    -- 获取当前余额 (FOR UPDATE 锁定行)
    SELECT credits_monthly, credits_permanent
    INTO v_monthly_balance, v_permanent_balance
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    -- 检查幂等性
    IF p_idempotency_key IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM credit_transactions
            WHERE idempotency_key = p_idempotency_key
        ) THEN
            RAISE EXCEPTION 'Duplicate transaction: %', p_idempotency_key;
        END IF;
    END IF;

    -- 检查余额
    IF (v_monthly_balance + v_permanent_balance) < p_amount THEN
        RAISE EXCEPTION 'Insufficient credits: required %, available %',
            p_amount, (v_monthly_balance + v_permanent_balance);
    END IF;

    -- 执行扣费 (优先月度)
    v_remaining := p_amount;
    IF v_monthly_balance > 0 THEN
        v_monthly_deducted := LEAST(v_monthly_balance, v_remaining);
        v_remaining := v_remaining - v_monthly_deducted;
    END IF;

    IF v_remaining > 0 THEN
        v_permanent_deducted := v_remaining;
    END IF;

    -- 更新余额
    UPDATE profiles
    SET credits_monthly = credits_monthly - v_monthly_deducted,
        credits_permanent = credits_permanent - v_permanent_deducted,
        updated_at = NOW()
    WHERE id = p_user_id;

    -- 记录交易 (月度)
    IF v_monthly_deducted > 0 THEN
        INSERT INTO credit_transactions (
            user_id, transaction_type, bucket, amount,
            balance_monthly_after, balance_permanent_after,
            description, idempotency_key
        ) VALUES (
            p_user_id, p_transaction_type, 'monthly', -v_monthly_deducted,
            v_monthly_balance - v_monthly_deducted,
            v_permanent_balance,
            p_description, p_idempotency_key
        );
    END IF;

    -- 记录交易 (永久)
    IF v_permanent_deducted > 0 THEN
        INSERT INTO credit_transactions (
            user_id, transaction_type, bucket, amount,
            balance_monthly_after, balance_permanent_after,
            description, idempotency_key
        ) VALUES (
            p_user_id, p_transaction_type, 'permanent', -v_permanent_deducted,
            v_monthly_balance - v_monthly_deducted,
            v_permanent_balance - v_permanent_deducted,
            p_description, NULL  -- 幂等键只用于第一笔交易
        );
    END IF;

    -- 返回结果
    RETURN jsonb_build_object(
        'success', TRUE,
        'monthly_deducted', v_monthly_deducted,
        'permanent_deducted', v_permanent_deducted,
        'balance_monthly_after', v_monthly_balance - v_monthly_deducted,
        'balance_permanent_after', v_permanent_balance - v_permanent_deducted
    );
END;
$$ LANGUAGE plpgsql;
```

---

## 5. 迁移管理

### 5.1 迁移文件命名规范

```
migrations/v2/
├── refactored_schema_v2.sql          # 完整 Schema (3,158 行)
└── patches/
    ├── 001_create_missing_tables_p0.sql
    ├── 002_add_missing_fields_profiles.sql
    ├── 003_add_missing_fields_projects.sql
    ├── 010_add_schema_comments.sql
    └── ...
```

### 5.2 Schema 同步流程

```bash
# 1. 在 patches/ 中创建新迁移文件
vim migrations/v2/patches/XXX_description.sql

# 2. 在开发数据库执行迁移
psql -h localhost -U postgres -d decodables_dev < migrations/v2/patches/XXX_description.sql

# 3. 验证迁移成功
psql -h localhost -U postgres -d decodables_dev -c "\d+ table_name"

# 4. 同步到 refactored_schema_v2.sql
cat migrations/v2/patches/XXX_description.sql >> migrations/v2/refactored_schema_v2.sql

# 5. 提交代码
git add migrations/
git commit -m "chore(db): add XXX migration"
git push
```

---

## 6. 性能优化

### 6.1 查询性能

| 优化技术 | 使用场景 | 示例 |
|---------|---------|------|
| 复合索引 | 多字段排序/过滤 | (user_id, created_at DESC) |
| 条件索引 | 只索引部分数据 | WHERE is_deleted=FALSE |
| JSONB 索引 | JSONB 字段查询 | CREATE INDEX ON ... USING GIN(metadata) |
| RPC 函数 | 复杂事务逻辑 | deduct_credits_atomic() |

### 6.2 写入性能

| 优化技术 | 使用场景 | 说明 |
|---------|---------|------|
| 批量 INSERT | 插入多条记录 | INSERT INTO ... VALUES (), (), () |
| COPY 命令 | 大量数据导入 | COPY table FROM stdin |
| 延迟触发器 | 批量操作 | SET CONSTRAINTS ... DEFERRED |

---

## 7. 安全性

### 7.1 Row Level Security (RLS)

```sql
-- 启用 RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- 用户只能查看自己的档案
CREATE POLICY profiles_select_policy ON profiles
    FOR SELECT
    USING (id = current_setting('app.current_user_id', TRUE)::TEXT);

-- 用户只能更新自己的档案
CREATE POLICY profiles_update_policy ON profiles
    FOR UPDATE
    USING (id = current_setting('app.current_user_id', TRUE)::TEXT);
```

### 7.2 数据脱敏

```sql
-- 创建视图,脱敏敏感信息
CREATE VIEW profiles_public AS
SELECT
    id,
    SUBSTRING(email FROM 1 FOR 3) || '***@' || SUBSTRING(email FROM POSITION('@' IN email) + 1) AS email_masked,
    tier,
    created_at
FROM profiles
WHERE is_deleted = FALSE;
```

---

**文档版本**: v1.0
**最后更新**: 2026-01-10
**维护者**: 后端团队
```

**预计时间**: 8 小时

---

#### 3.3 更新架构指南文档 (4 小时)

**更新 `docs/main/BACKEND_ARCHITECTURE_GUIDE.md`**:

在文档中添加新章节:

```markdown
## 9. 数据库设计规范

### 9.1 Schema 与代码同步

数据库 Schema 是真实数据源 (Single Source of Truth),代码必须适配 Schema。

**字段映射表**: `infrastructure/repositories/field_mappings.py`

**使用规范**:
1. 新增表时,先在 Schema 中定义,再编写 Repository
2. 字段映射使用 field_mappings.py 中的常量
3. 所有 enum 值使用小写 snake_case (符合 PostgreSQL 规范)
4. 业务约束在聚合根和数据库都验证 (双重防守)

### 9.2 软删除与硬删除

所有业务表都支持软删除 (is_deleted + deleted_at)。

**使用方式**:
- 默认查询自动过滤 is_deleted=TRUE
- API 支持 permanent=true 参数进行硬删除
- 硬删除需要额外权限验证

**示例**:
```python
# 软删除 (默认)
await repo.delete_project(project_id, permanent=False)

# 硬删除 (不可恢复)
await repo.delete_project(project_id, permanent=True)
```

### 9.3 Append-Only 表

关键业务表 (credit_transactions) 使用 Append-Only 模式,通过触发器防止修改/删除。

**优势**:
- 完整审计追踪
- 防止数据篡改
- 符合合规要求

**使用规范**:
- 只能 INSERT,不能 UPDATE/DELETE
- 通过 RPC 函数执行复杂事务
- 错误记录需要新增 correction 交易

(继续补充其他内容...)
```

**预计时间**: 4 小时

---

#### 3.4 创建 Schema 版本检查脚本 (4 小时)

**创建 `scripts/tools/check_schema_sync.py`**:

```python
#!/usr/bin/env python3
"""
Schema 与代码同步检查工具

功能:
1. 检查 Repository 中引用的表是否存在于 Schema
2. 检查 Repository 中引用的字段是否存在于表中
3. 检查 enum 值是否与数据库 CHECK 约束匹配

使用:
    python scripts/tools/check_schema_sync.py
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Schema 文件路径
SCHEMA_FILE = Path(__file__).parent.parent.parent / "migrations/v2/refactored_schema_v2.sql"
REPO_DIR = Path(__file__).parent.parent.parent / "infrastructure/repositories"

def parse_schema(schema_file: Path) -> Dict[str, Set[str]]:
    """
    解析 Schema 文件,提取所有表名和字段名

    Returns:
        {table_name: set(field_names)}
    """
    schema = {}
    current_table = None

    with open(schema_file, 'r') as f:
        for line in f:
            # 匹配 CREATE TABLE
            match = re.match(r'^CREATE TABLE (\w+) \(', line)
            if match:
                current_table = match.group(1)
                schema[current_table] = set()
                continue

            # 匹配字段定义 (排除约束)
            if current_table:
                field_match = re.match(r'^\s+(\w+)\s+(TEXT|INTEGER|BOOLEAN|UUID|TIMESTAMPTZ|NUMERIC|INET|JSONB|DATE|TEXT\[\])', line)
                if field_match:
                    field_name = field_match.group(1)
                    schema[current_table].add(field_name)

                # 匹配表结束
                if line.strip() == ');':
                    current_table = None

    return schema

def find_table_references(repo_dir: Path) -> Dict[str, List[Tuple[str, int]]]:
    """
    在 Repository 文件中查找表引用

    Returns:
        {table_name: [(file_path, line_number), ...]}
    """
    table_refs = {}

    for repo_file in repo_dir.glob("*.py"):
        if repo_file.name == "__init__.py":
            continue

        with open(repo_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                # 匹配 table("xxx")
                match = re.search(r'\.table\("(\w+)"\)', line)
                if match:
                    table_name = match.group(1)
                    if table_name not in table_refs:
                        table_refs[table_name] = []
                    table_refs[table_name].append((str(repo_file), line_num))

    return table_refs

def find_field_references(repo_dir: Path) -> Dict[str, Dict[str, List[Tuple[str, int]]]]:
    """
    在 Repository 文件中查找字段引用

    Returns:
        {table_name: {field_name: [(file_path, line_number), ...]}}
    """
    field_refs = {}

    for repo_file in repo_dir.glob("*.py"):
        if repo_file.name == "__init__.py":
            continue

        current_table = None
        with open(repo_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                # 匹配 table("xxx")
                table_match = re.search(r'\.table\("(\w+)"\)', line)
                if table_match:
                    current_table = table_match.group(1)
                    if current_table not in field_refs:
                        field_refs[current_table] = {}

                # 匹配 .eq("field", ...) / .select("field, ...")
                if current_table:
                    eq_match = re.search(r'\.(?:eq|neq|gt|gte|lt|lte|in_|contains)\("(\w+)"', line)
                    if eq_match:
                        field_name = eq_match.group(1)
                        if field_name not in field_refs[current_table]:
                            field_refs[current_table][field_name] = []
                        field_refs[current_table][field_name].append((str(repo_file), line_num))

    return field_refs

def check_schema_sync():
    """执行同步检查"""
    print("=" * 80)
    print("Schema 与代码同步检查")
    print("=" * 80)
    print()

    # 1. 解析 Schema
    print("📖 解析 Schema 文件...")
    schema = parse_schema(SCHEMA_FILE)
    print(f"✅ 发现 {len(schema)} 张表")
    print()

    # 2. 查找表引用
    print("🔍 查找代码中的表引用...")
    table_refs = find_table_references(REPO_DIR)
    print(f"✅ 发现 {len(table_refs)} 个表被引用")
    print()

    # 3. 检查表是否存在
    print("🔍 检查表是否存在于 Schema...")
    errors = []
    for table_name, refs in table_refs.items():
        if table_name not in schema:
            for file_path, line_num in refs:
                errors.append(f"❌ 表不存在: {table_name} (引用位置: {file_path}:{line_num})")

    if errors:
        print(f"🔴 发现 {len(errors)} 个表名错误:")
        for error in errors:
            print(f"   {error}")
    else:
        print("✅ 所有表都存在于 Schema")
    print()

    # 4. 查找字段引用
    print("🔍 查找代码中的字段引用...")
    field_refs = find_field_references(REPO_DIR)
    print()

    # 5. 检查字段是否存在
    print("🔍 检查字段是否存在于表中...")
    field_errors = []
    for table_name, fields in field_refs.items():
        if table_name not in schema:
            continue  # 表不存在的错误已在上面报告

        for field_name, refs in fields.items():
            if field_name not in schema[table_name]:
                for file_path, line_num in refs:
                    field_errors.append(
                        f"❌ 字段不存在: {table_name}.{field_name} "
                        f"(引用位置: {file_path}:{line_num})"
                    )

    if field_errors:
        print(f"🔴 发现 {len(field_errors)} 个字段错误:")
        for error in field_errors[:10]:  # 只显示前 10 个
            print(f"   {error}")
        if len(field_errors) > 10:
            print(f"   ... (还有 {len(field_errors) - 10} 个错误)")
    else:
        print("✅ 所有字段都存在于表中")
    print()

    # 6. 总结
    print("=" * 80)
    total_errors = len(errors) + len(field_errors)
    if total_errors > 0:
        print(f"🔴 检查失败: 发现 {total_errors} 个错误")
        print("=" * 80)
        return 1
    else:
        print("✅ 检查通过: Schema 与代码完全同步")
        print("=" * 80)
        return 0

if __name__ == "__main__":
    sys.exit(check_schema_sync())
```

**使用方式**:

```bash
# 在 decodables/ 目录执行
python scripts/tools/check_schema_sync.py

# 示例输出:
# ================================================================================
# Schema 与代码同步检查
# ================================================================================
#
# 📖 解析 Schema 文件...
# ✅ 发现 47 张表
#
# 🔍 查找代码中的表引用...
# ✅ 发现 39 个表被引用
#
# 🔍 检查表是否存在于 Schema...
# 🔴 发现 3 个表名错误:
#    ❌ 表不存在: users (引用位置: infrastructure/repositories/credit_repository.py:57)
#    ❌ 表不存在: users (引用位置: infrastructure/repositories/credit_repository.py:78)
#    ❌ 表不存在: users (引用位置: infrastructure/repositories/user_repository.py:141)
#
# ================================================================================
# 🔴 检查失败: 发现 3 个错误
# ================================================================================
```

**集成到 CI**:

```yaml
# .github/workflows/ci.yml
jobs:
  schema-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check Schema Sync
        run: python scripts/tools/check_schema_sync.py
```

**预计时间**: 4 小时

---

**Phase 3 总计**: 24 小时 (2 个工作日)

---

## 三、执行检查清单

### Phase 1 检查清单

```
□ P0.1 修复表名映射错误
  □ 搜索所有 table("users") 引用
  □ 修改为 table("profiles")
  □ 运行集成测试验证
  □ Git commit + push

□ P0.2 统一枚举值大小写
  □ 修改 CreditBucket/TransactionType 为小写
  □ 移除 Repository 中的 .lower() 转换
  □ 更新所有使用枚举的代码
  □ 运行测试验证

□ P0.3 创建字段映射表
  □ 创建 field_mappings.py
  □ 定义 4-5 个核心表的映射
  □ 实现 map_db_to_domain/map_domain_to_db
  □ 在 Repository 中使用映射表

□ P0.4 添加业务约束验证
  □ 在 UserCredits 中添加 __post_init__()
  □ 验证积分范围 (0-100万/1000万)
  □ 在 deduct()/add() 中添加前置/后置验证
  □ 编写测试用例
```

### Phase 2 检查清单

```
□ P1.1 创建 13 个缺失表
  □ 编写 001_create_missing_tables_p0.sql (5 张表)
  □ 编写 002_create_missing_tables_p1.sql (5 张表)
  □ 编写 003_create_missing_tables_p2.sql (3 张表)
  □ 在开发数据库执行迁移
  □ 验证表创建成功
  □ 同步到 refactored_schema_v2.sql

□ P1.2 添加缺失字段
  □ 编写 profiles 表字段补充 SQL
  □ 编写 projects 表字段补充 SQL
  □ 执行迁移
  □ 验证字段存在

□ P1.3 实现 soft delete
  □ 创建 BaseRepository
  □ 实现 soft_delete/hard_delete/restore
  □ 在 ProjectRepository 中继承
  □ 在 API 中添加 permanent 参数
  □ 测试软删除和恢复
```

### Phase 3 检查清单

```
□ P2.1 完善 Schema 注释
  □ 为所有 47 张表添加 COMMENT
  □ 为关键字段添加注释
  □ 验证注释可见 (psql \d+ table)

□ P2.2 创建数据库设计文档
  □ 编写 DATABASE-SCHEMA-DESIGN.md
  □ 包含设计原则/核心表/索引策略
  □ 包含 RPC 函数说明
  □ Review 并发布

□ P2.3 更新架构指南
  □ 在 BACKEND_ARCHITECTURE_GUIDE.md 添加数据库章节
  □ 补充软删除/Append-Only 说明
  □ 补充字段映射表使用指南

□ P2.4 创建同步检查脚本
  □ 编写 check_schema_sync.py
  □ 测试脚本功能
  □ 集成到 CI/CD
```

---

## 四、质量标准

### 4.1 代码质量标准

```python
# ✅ 正确示例:
from infrastructure.repositories.field_mappings import PROFILES_DB_TO_DOMAIN, map_db_to_domain

class SupabaseUserRepository(IUserRepository):
    async def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        # 1. 使用正确的表名
        result = self.client.table("profiles").select("*").eq("id", user_id).execute()

        if not result.data:
            return None

        # 2. 使用映射表转换
        domain_data = map_db_to_domain(result.data[0], PROFILES_DB_TO_DOMAIN)

        # 3. 构造聚合根
        return UserProfile(
            user_id=domain_data['user_id'],
            tier=UserTier(domain_data['tier']),  # enum 值已是小写
            balance=Credits(
                monthly=domain_data['balance']['monthly'],
                permanent=domain_data['balance']['permanent']
            )
        )

# ❌ 错误示例:
class BadUserRepository:
    async def get_user(self, user_id: str):
        # ❌ 错误 1: 使用不存在的表
        result = self.client.table("users").select("*").execute()

        # ❌ 错误 2: 硬编码字段映射
        return {
            "user_id": result.data[0]["id"],
            "monthly": result.data[0]["credits_monthly"]
        }

        # ❌ 错误 3: 枚举值大小写转换
        tier = UserTier(result.data[0]["tier"].upper())
```

### 4.2 Schema 质量标准

```sql
-- ✅ 正确示例:
CREATE TABLE profiles (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    tier TEXT DEFAULT 't1',
    credits_monthly INTEGER DEFAULT 50,
    credits_permanent INTEGER DEFAULT 0,

    -- 标准审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,

    -- 业务约束
    CONSTRAINT check_tier CHECK (tier IN ('t1', 't2', 't3')),
    CONSTRAINT check_credits_monthly CHECK (credits_monthly >= 0 AND credits_monthly <= 1000000),
    CONSTRAINT check_credits_permanent CHECK (credits_permanent >= 0 AND credits_permanent <= 10000000)
);

-- 索引设计
CREATE UNIQUE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_tier ON profiles(tier);
CREATE INDEX idx_profiles_active ON profiles(created_at DESC) WHERE is_deleted = FALSE;

-- 触发器
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 注释
COMMENT ON TABLE profiles IS '用户档案表,存储 Clerk 认证用户的业务信息';
COMMENT ON COLUMN profiles.tier IS '用户等级 (t1:免费版, t2:基础版, t3:专业版)';
```

---

## 五、风险控制

### 5.1 回滚策略

**触发条件**:
- 测试失败率 > 10%
- 生产环境出现数据不一致
- 关键业务流程中断

**回滚步骤**:
```bash
# 1. 停止部署
git revert <commit-hash>

# 2. 回滚数据库 (如有 Schema 变更)
psql -h localhost -U postgres -d decodables_dev < migrations/v2/rollback/XXX_rollback.sql

# 3. 重启服务
# (Railway 会自动重新部署)

# 4. 验证功能
python scripts/tools/check_schema_sync.py
pytest tests/ -v
```

### 5.2 灰度发布

**Feature Flag 控制**:
```python
# 在 system_configs 表中添加开关
{
    "key": "enable_new_soft_delete",
    "value": "true",
    "description": "启用新的软删除功能"
}

# 在代码中使用
from core.feature_flag import is_feature_enabled

async def delete_project(project_id: str, permanent: bool = False):
    if is_feature_enabled("enable_new_soft_delete"):
        # 使用新的软删除逻辑
        await repo.delete_project(project_id, permanent=permanent)
    else:
        # 使用旧逻辑 (向后兼容)
        await repo.old_delete_project(project_id)
```

---

## 六、总结

### 最优方案特点

1. **双向调整 (70% 代码 + 30% Schema)**
   - 代码修复: 表名/字段名/枚举值
   - Schema 补充: 缺失表/缺失字段/注释

2. **最小变更**
   - Phase 1 (P0): 16 小时 - 修复致命问题
   - Phase 2 (P1): 24 小时 - 补充缺失功能
   - Phase 3 (P2): 24 小时 - 完善文档

3. **长期可维护**
   - 字段映射表 (SSOT)
   - Schema 同步检查脚本
   - CI/CD 集成

4. **遵循最佳实践**
   - PostgreSQL 命名规范 ✅
   - DDD 架构规范 ✅
   - FastAPI 异步最佳实践 ✅

### 预期成果

执行完成后:
- ✅ Schema 与代码 100% 同步
- ✅ 13 个缺失表全部创建
- ✅ 所有枚举值统一为小写
- ✅ 软删除/硬删除完整实现
- ✅ 完整的文档和检查工具
- ✅ CI/CD 自动化检查

---

**文档版本**: v1.0
**最后更新**: 2026-01-10
**基于审查**: Agent a7062f1 (基础分析) + Agent aab95b3 (架构深度分析)
**执行状态**: ⏳ 等待用户确认后开始执行
