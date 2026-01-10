# Make Decodables 数据库完整指南

> **版本**: 2.0
> **更新日期**: 2026-01-10

---

## 目录

**Part 1: 数据库 Schema 文件位置**
1. [主 DDL 文件](#part-1-数据库-schema-文件位置)
2. [文件结构](#12-文件结构)
3. [如何使用](#13-如何使用)
4. [重要提示](#14-重要提示)

**Part 2: 字段映射表使用指南**
1. [概述](#part-2-字段映射表使用指南)
2. [可用映射表](#22-可用映射表)
3. [基本用法](#23-基本用法)
4. [高级用法](#24-高级用法)
5. [最佳实践](#25-最佳实践)
6. [完整示例](#26-完整示例)
7. [测试映射表](#27-测试映射表)
8. [维护指南](#28-维护指南)
9. [常见问题 FAQ](#29-常见问题-faq)

---

# Part 1: 数据库 Schema 文件位置

**更新时间**: 2026-01-10
**重要**: 数据库 DDL 文件已从 V1 迁移到 V2

## 1.1 主 DDL 文件

### ⭐ 主 DDL 文件 (单一数据源)

**文件路径**: [`migrations/v2/refactored_schema_v2.sql`](../../migrations/v2/refactored_schema_v2.sql)

**版本**: v4.0
**表数量**: 60 张
**总行数**: ~4,000 行
**状态**: ✅ 当前使用

**用途**:
- 新环境初始化
- 数据库结构参考
- Schema 对比基准
- 完整的表定义、索引、触发器、函数

---

## 1.2 文件结构

```
decodables/
├── migrations/
│   ├── v2/
│   │   ├── refactored_schema_v2.sql  ⭐ 主 DDL (v4.0)
│   │   ├── docs/
│   │   │   ├── README.md             # V2 文档索引
│   │   │   ├── REFACTORING_REPORT.md # 重构报告
│   │   │   └── MIGRATION_GUIDE.md    # 迁移指南
│   │   └── patches/                  # V2 补丁
│   │
│   ├── v3/                           # Phase 3 软删除迁移
│   │   └── 001_add_soft_delete_to_core_tables.sql
│   │
│   └── V1/                           # 已废弃 (仅供参考)
│       └── ddl.sql                   ❌ 旧版 (v3.27)
│
└── docs/
    └── DATABASE-GUIDE.md             # 本文档
```

---

## 1.3 如何使用

### 1.3.1 版本历史

| 版本 | 文件路径 | 表数量 | 状态 | 说明 |
|------|----------|--------|------|------|
| **v4.0** | `migrations/v2/refactored_schema_v2.sql` | 60 | ✅ 当前使用 | DDD 架构重构 + Phase 2/3 |
| v3.27 | `migrations/V1/ddl.sql` | 42 | ❌ 已废弃 | 旧版生产环境 |

---

### 1.3.2 V4.0 主要改进

#### 架构重构

- ✅ 统一命名规范 (Snake Case)
- ✅ 标准化审计字段 (created_at, updated_at, is_deleted, deleted_at)
- ✅ 补充缺失的 13 张表
- ✅ 修复现有表的缺失字段
- ✅ 补充缺失的索引、触发器、函数

#### 软删除支持

**Phase 2 完成** (16 张表):
- profiles, projects, project_versions, assets
- marketplace_listings, asset_categories, system_assets
- notifications, campaign_participations, campaign_dismissals
- onboarding_steps, user_onboarding_progress
- referrals, page_prompt_templates
- credit_transactions, payment_records

**Phase 3.1 新增** (8 张表):
- marketplace_favorites, marketplace_reviews
- campaigns, daily_themes, holidays
- asset_prompt_templates
- support_tickets, support_replies

**合计**: 24/60 (40%) 表支持软删除

---

### 1.3.3 新环境初始化

```bash
# 1. 使用 V2 主 DDL 初始化数据库
psql -U postgres -d decodables < migrations/v2/refactored_schema_v2.sql

# 2. (可选) 应用 Phase 3 增量迁移
psql -U postgres -d decodables < migrations/v3/001_add_soft_delete_to_core_tables.sql
```

### 1.3.4 查看 Schema 定义

```bash
# 查看完整 Schema
cat migrations/v2/refactored_schema_v2.sql

# 查看特定表
grep -A 50 "CREATE TABLE profiles" migrations/v2/refactored_schema_v2.sql

# 查看所有表名
grep "CREATE TABLE" migrations/v2/refactored_schema_v2.sql
```

### 1.3.5 Schema 对比

```bash
# 对比 V1 和 V2 差异
diff migrations/V1/ddl.sql migrations/v2/refactored_schema_v2.sql

# 查看新增的表
grep "CREATE TABLE" migrations/v2/refactored_schema_v2.sql | \
  grep -v -f <(grep "CREATE TABLE" migrations/V1/ddl.sql)
```

---

## 1.4 重要提示

### 1.4.1 不要使用旧版 DDL

❌ **错误**:
```bash
# 不要使用 V1 DDL (已废弃)
psql < migrations/V1/ddl.sql
```

✅ **正确**:
```bash
# 使用 V2 主 DDL
psql < migrations/v2/refactored_schema_v2.sql
```

### 1.4.2 Schema 同步规则

当进行数据库变更时:

1. **创建增量迁移文件**
   ```
   migrations/v3/XXX_description.sql
   ```

2. **同步到主 DDL**
   ```
   更新 migrations/v2/refactored_schema_v2.sql
   ```

3. **更新版本号**
   ```sql
   -- 文件头部
   -- Make Decodables - Refactored Database Schema (vX.X)
   ```

4. **提交 Git**
   ```bash
   git add migrations/v2/refactored_schema_v2.sql migrations/v3/*.sql
   git commit -m "feat(db): description"
   ```

---

## 1.5 相关文档

### V2 数据库文档

- [refactored_schema_v2.sql](../../migrations/v2/refactored_schema_v2.sql) - 完整 DDL (v4.0)
- [V2/docs/README.md](../../migrations/v2/docs/README.md) - V2 文档索引
- [V2/docs/REFACTORING_REPORT.md](../../migrations/v2/docs/REFACTORING_REPORT.md) - 重构报告

### Phase 3 软删除文档

- [SOFT-DELETE-UNIFICATION-PLAN.md](../tmp/SOFT-DELETE-UNIFICATION-PLAN.md) - 软删除统一化计划
- [PHASE-3.1-COMPLETION-REPORT.md](../tmp/PHASE-3.1-COMPLETION-REPORT.md) - Phase 3.1 完成报告

### 业务逻辑文档

- [后台业务逻辑说明.md](后台业务逻辑说明.md) - 后端架构和业务规则

---

## 1.6 维护者信息

**责任人**: 开发团队
**最后更新**: 2026-01-10
**版本**: v2.0

如有疑问,请参考:
- V2 重构报告: `migrations/v2/docs/REFACTORING_REPORT.md`
- 提交 Issue: GitHub Issues

---

**快速链接**:
- [主 DDL 文件](../../migrations/v2/refactored_schema_v2.sql) ⭐
- [V2 文档目录](../../migrations/v2/docs/)
- [Phase 3 迁移目录](../../migrations/v3/)

---

# Part 2: 字段映射表使用指南

**创建时间**: 2026-01-10
**版本**: 1.0.0
**文件**: `infrastructure/repositories/field_mappings.py`

## 2.1 概述

字段映射表是数据库字段与领域对象属性的**单一真实来源 (Single Source of Truth)**。所有 Repository 实现必须使用这些映射来确保一致性。

**核心优势**:
- ✅ 统一的字段映射规则
- ✅ 减少硬编码错误
- ✅ 便于维护和重构
- ✅ 自动化验证支持

---

## 2.2 可用映射表

| 映射表 | 数据库表 | 领域对象 |
|--------|----------|----------|
| `PROFILES_DB_TO_DOMAIN` | profiles | UserProfile |
| `CREDIT_TX_DB_TO_DOMAIN` | credit_transactions | CreditTransaction |
| `PROJECTS_DB_TO_DOMAIN` | projects | Project |
| `LISTINGS_DB_TO_DOMAIN` | marketplace_listings | Listing |
| `PURCHASES_DB_TO_DOMAIN` | marketplace_purchases | Purchase |
| `CONFIGS_DB_TO_DOMAIN` | system_configs | SystemConfig |

---

## 2.3 基本用法

### 2.3.1 导入映射表

```python
from infrastructure.repositories.field_mappings import (
    PROFILES_DB_TO_DOMAIN,
    map_db_to_domain,
    map_domain_to_db,
)
```

### 2.3.2 数据库记录 → 领域对象 (查询场景)

```python
# 示例: 从 profiles 表查询用户
class SupabaseUserRepository(IUserRepository):
    async def get_by_id(self, user_id: str) -> Optional[UserProfile]:
        # 1. 查询数据库
        result = self.client.table("profiles").select("*").eq("id", user_id).execute()

        if not result.data:
            return None

        db_record = result.data[0]

        # 2. 使用映射转换
        domain_data = map_db_to_domain(db_record, PROFILES_DB_TO_DOMAIN)
        # domain_data = {
        #     'user_id': 'user_2abc3def',  # profiles.id → user_id
        #     'email': 'test@example.com',
        #     'tier': 't2',
        #     'credits_monthly': 200,
        #     'credits_permanent': 50,
        #     ...
        # }

        # 3. 构造领域对象
        return UserProfile(
            user_id=domain_data['user_id'],
            email=domain_data['email'],
            tier=UserTier(domain_data['tier']),
            credits_monthly=domain_data['credits_monthly'],
            credits_permanent=domain_data['credits_permanent'],
            # ...
        )
```

### 2.3.3 领域对象 → 数据库记录 (插入/更新场景)

```python
# 示例: 保存用户到 profiles 表
class SupabaseUserRepository(IUserRepository):
    async def save(self, user: UserProfile) -> UserProfile:
        # 1. 准备领域数据
        domain_data = {
            'user_id': user.user_id,
            'email': user.email,
            'tier': user.tier.value,
            'credits_monthly': user.credits_monthly,
            'credits_permanent': user.credits_permanent,
        }

        # 2. 使用映射转换为数据库格式
        db_data = map_domain_to_db(domain_data, PROFILES_DB_TO_DOMAIN)
        # db_data = {
        #     'id': 'user_2abc3def',  # user_id → profiles.id
        #     'email': 'test@example.com',
        #     'tier': 't2',
        #     'credits_monthly': 200,
        #     'credits_permanent': 50,
        # }

        # 3. 插入/更新数据库
        result = self.client.table("profiles").upsert(
            db_data,
            on_conflict="id"
        ).execute()

        return self._map_to_profile(result.data[0])
```

---

## 2.4 高级用法

### 2.4.1 获取所有数据库字段 (用于 SELECT)

```python
from infrastructure.repositories.field_mappings import get_db_fields, PROFILES_DB_TO_DOMAIN

# 获取所有字段名
fields = get_db_fields(PROFILES_DB_TO_DOMAIN)
# ['id', 'email', 'tier', 'credits_monthly', 'credits_permanent', ...]

# 构造 SELECT 语句
select_clause = ", ".join(fields)
result = self.client.table("profiles").select(select_clause).execute()
```

### 2.4.2 验证数据库记录 (防御性编程)

```python
from infrastructure.repositories.field_mappings import validate_db_record, PROFILES_DB_TO_DOMAIN

# 验证必需字段
try:
    validate_db_record(
        db_record,
        PROFILES_DB_TO_DOMAIN,
        required_fields=['id', 'email']  # 必需字段列表
    )
except ValueError as e:
    logger.error(f"数据库记录验证失败: {e}")
    raise
```

### 2.4.3 处理嵌套对象

映射表支持嵌套路径 (使用 `.` 分隔):

```python
# 定义映射 (示例)
NESTED_MAPPING = {
    'balance_monthly': 'balance.monthly',      # 嵌套路径
    'balance_permanent': 'balance.permanent',
}

# 数据库 → 领域对象
db_record = {
    'balance_monthly': 100,
    'balance_permanent': 50,
}

domain_data = map_db_to_domain(db_record, NESTED_MAPPING)
# {
#     'balance': {
#         'monthly': 100,
#         'permanent': 50
#     }
# }

# 领域对象 → 数据库
domain_obj = {
    'balance': {
        'monthly': 100,
        'permanent': 50
    }
}

db_data = map_domain_to_db(domain_obj, NESTED_MAPPING)
# {
#     'balance_monthly': 100,
#     'balance_permanent': 50
# }
```

---

## 2.5 最佳实践

### ✅ DO (推荐做法)

1. **始终使用映射表**
   ```python
   # ✅ 正确: 使用映射表
   domain_data = map_db_to_domain(db_record, PROFILES_DB_TO_DOMAIN)
   user_id = domain_data['user_id']
   ```

2. **集中管理字段映射**
   ```python
   # ✅ 正确: 在 field_mappings.py 中定义
   PROFILES_DB_TO_DOMAIN = {
       'id': 'user_id',
       'email': 'email',
       # ...
   }
   ```

3. **验证必需字段**
   ```python
   # ✅ 正确: 验证数据完整性
   validate_db_record(db_record, PROFILES_DB_TO_DOMAIN, ['id', 'email'])
   ```

4. **使用类型注解**
   ```python
   # ✅ 正确: 明确类型
   def _map_to_profile(self, row: Dict[str, Any]) -> UserProfile:
       domain_data = map_db_to_domain(row, PROFILES_DB_TO_DOMAIN)
       # ...
   ```

### ❌ DON'T (避免做法)

1. **硬编码字段映射**
   ```python
   # ❌ 错误: 硬编码映射
   user_id = db_record["id"]  # 应该使用 map_db_to_domain
   ```

2. **重复定义映射**
   ```python
   # ❌ 错误: 在 Repository 中重复定义
   class MyRepository:
       FIELD_MAPPING = {'id': 'user_id'}  # 应该使用 field_mappings.py
   ```

3. **忽略映射表的更新**
   ```python
   # ❌ 错误: 数据库新增字段但不更新映射表
   # 数据库: ALTER TABLE profiles ADD COLUMN phone TEXT;
   # field_mappings.py: (没有添加 'phone' 映射) ❌
   ```

4. **使用魔法字符串**
   ```python
   # ❌ 错误: 魔法字符串
   result.data[0]["user_id"]  # 字段名可能改变

   # ✅ 正确: 使用映射
   domain_data = map_db_to_domain(result.data[0], PROFILES_DB_TO_DOMAIN)
   domain_data['user_id']
   ```

---

## 2.6 完整示例

### 2.6.1 UserRepository 的完整实现

```python
from typing import Optional
from infrastructure.repositories.field_mappings import (
    PROFILES_DB_TO_DOMAIN,
    map_db_to_domain,
    map_domain_to_db,
    validate_db_record,
)
from domains.identity.entities import UserProfile
from domains.identity.value_objects import UserTier

class SupabaseUserRepository:
    def __init__(self, client):
        self.client = client

    async def get_by_id(self, user_id: str) -> Optional[UserProfile]:
        """
        获取用户 (使用映射表)
        """
        # 1. 查询数据库
        result = self.client.table("profiles").select("*").eq("id", user_id).execute()

        if not result.data:
            return None

        db_record = result.data[0]

        # 2. 验证必需字段
        validate_db_record(db_record, PROFILES_DB_TO_DOMAIN, ['id', 'email'])

        # 3. 使用映射转换
        domain_data = map_db_to_domain(db_record, PROFILES_DB_TO_DOMAIN)

        # 4. 构造领域对象
        return UserProfile(
            user_id=domain_data['user_id'],
            email=domain_data['email'],
            tier=UserTier(domain_data['tier']),
            credits_monthly=domain_data.get('credits_monthly', 0),
            credits_permanent=domain_data.get('credits_permanent', 0),
            display_name=domain_data.get('display_name'),
            created_at=domain_data.get('created_at'),
        )

    async def save(self, user: UserProfile) -> UserProfile:
        """
        保存用户 (使用映射表)
        """
        # 1. 准备领域数据
        domain_data = {
            'user_id': user.user_id,
            'email': user.email,
            'tier': user.tier.value,
            'credits_monthly': user.credits_monthly,
            'credits_permanent': user.credits_permanent,
            'display_name': user.display_name,
        }

        # 2. 使用映射转换
        db_data = map_domain_to_db(domain_data, PROFILES_DB_TO_DOMAIN)

        # 3. 保存到数据库
        result = self.client.table("profiles").upsert(
            db_data,
            on_conflict="id"
        ).select("*").execute()

        # 4. 返回更新后的对象
        return self.get_by_id(user.user_id)
```

### 2.6.2 CreditTransactionRepository

```python
from infrastructure.repositories.field_mappings import (
    CREDIT_TX_DB_TO_DOMAIN,
    map_db_to_domain,
)
from domains.billing.value_objects import TransactionType, CreditBucket

class SupabaseCreditRepository:
    async def get_transactions(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[CreditTransaction]:
        """
        获取用户交易历史 (使用映射表)
        """
        # 1. 查询数据库
        result = self.client.table("credit_transactions").select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()

        # 2. 使用映射批量转换
        transactions = []
        for db_record in result.data:
            domain_data = map_db_to_domain(db_record, CREDIT_TX_DB_TO_DOMAIN)

            tx = CreditTransaction(
                transaction_id=domain_data['transaction_id'],
                user_id=domain_data['user_id'],
                tx_type=TransactionType(domain_data['tx_type']),
                bucket=CreditBucket(domain_data['bucket']),
                amount=domain_data['amount'],
                balance_monthly_after=domain_data['balance_monthly_after'],
                balance_permanent_after=domain_data['balance_permanent_after'],
                description=domain_data.get('description'),
                created_at=domain_data.get('created_at'),
            )
            transactions.append(tx)

        return transactions
```

---

## 2.7 测试映射表

### 单元测试示例

```python
# tests/infrastructure/test_field_mappings.py
import pytest
from infrastructure.repositories.field_mappings import (
    PROFILES_DB_TO_DOMAIN,
    map_db_to_domain,
    map_domain_to_db,
)

def test_map_db_to_domain():
    """测试数据库记录映射到领域对象"""
    db_record = {
        "id": "user_123",
        "email": "test@example.com",
        "tier": "t2",
        "credits_monthly": 200,
    }

    domain_data = map_db_to_domain(db_record, PROFILES_DB_TO_DOMAIN)

    assert domain_data['user_id'] == "user_123"  # id → user_id
    assert domain_data['email'] == "test@example.com"
    assert domain_data['tier'] == "t2"
    assert domain_data['credits_monthly'] == 200


def test_map_domain_to_db():
    """测试领域对象映射到数据库记录"""
    domain_data = {
        "user_id": "user_123",
        "email": "test@example.com",
        "tier": "t2",
        "credits_monthly": 200,
    }

    db_data = map_domain_to_db(domain_data, PROFILES_DB_TO_DOMAIN)

    assert db_data['id'] == "user_123"  # user_id → id
    assert db_data['email'] == "test@example.com"
    assert db_data['tier'] == "t2"
    assert db_data['credits_monthly'] == 200


def test_round_trip_mapping():
    """测试往返映射 (database → domain → database)"""
    original_db_record = {
        "id": "user_123",
        "email": "test@example.com",
        "tier": "t2",
    }

    # Database → Domain
    domain_data = map_db_to_domain(original_db_record, PROFILES_DB_TO_DOMAIN)

    # Domain → Database
    restored_db_record = map_domain_to_db(domain_data, PROFILES_DB_TO_DOMAIN)

    # 验证一致性
    assert restored_db_record['id'] == original_db_record['id']
    assert restored_db_record['email'] == original_db_record['email']
    assert restored_db_record['tier'] == original_db_record['tier']
```

---

## 2.8 维护指南

### 2.8.1 何时更新映射表

1. **数据库 Schema 变更**:
   - 新增字段 → 添加到映射表
   - 删除字段 → 从映射表移除
   - 重命名字段 → 更新映射表

2. **领域对象变更**:
   - 属性重命名 → 更新映射表右侧 (domain_path)
   - 属性类型变更 → 确保映射兼容

### 2.8.2 更新流程

```
1. 修改数据库 Schema (migrations/*.sql)
   ↓
2. 更新 field_mappings.py 中的映射表
   ↓
3. 更新 Repository 实现 (如果需要)
   ↓
4. 运行测试验证
   ↓
5. 提交代码
```

### 2.8.3 验证映射表一致性

使用 `validate_mapping_consistency()` 验证:

```python
from infrastructure.repositories.field_mappings import validate_mapping_consistency

# 假设从 Schema 中提取的字段列表
schema_fields = ["id", "email", "tier", "credits_monthly", "credits_permanent", "created_at"]

# 验证映射表
result = validate_mapping_consistency(
    "PROFILES_DB_TO_DOMAIN",
    PROFILES_DB_TO_DOMAIN,
    schema_fields
)

if not result['valid']:
    print(f"缺失字段: {result['missing_in_mapping']}")
    print(f"多余字段: {result['extra_in_mapping']}")
```

---

## 2.9 常见问题 FAQ

### Q1: 为什么不直接硬编码字段名？

**A**: 硬编码会导致:
- ❌ 字段名变更时需要修改多处代码
- ❌ 容易出现拼写错误
- ❌ 难以批量重构
- ✅ 使用映射表统一管理,修改一处即可

### Q2: 映射表会影响性能吗？

**A**: 性能影响微乎其微:
- 映射转换只是字典查找操作 (O(1))
- 相比数据库查询,开销可忽略不计
- 代码可维护性的提升远大于微小性能损失

### Q3: 如何处理复杂的数据转换？

**A**: 映射表只负责字段名映射,复杂转换应在 Repository 中处理:

```python
# field_mappings.py: 只映射字段名
PROFILES_DB_TO_DOMAIN = {
    'tier': 'tier',  # 字段名映射
}

# repository: 处理类型转换
domain_data = map_db_to_domain(db_record, PROFILES_DB_TO_DOMAIN)
tier = UserTier(domain_data['tier'])  # 字符串 → Enum
```

### Q4: 新手如何快速上手？

**A**: 按以下步骤:
1. 查看 `field_mappings.py` 了解可用映射表
2. 参考本文档的"基本用法"示例
3. 参考现有 Repository 实现 (如 user_repository.py)
4. 编写单元测试验证理解

---

**文档版本**: v2.0
**最后更新**: 2026-01-10
**维护者**: 后端团队
