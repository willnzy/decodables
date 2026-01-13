# Make Decodables 数据库完整指南

> **版本**: 2.1
> **更新日期**: 2026-01-12

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

**Part 3: 数据库视图与安全** ⭐ 新增
1. [视图命名规范](#31-视图命名规范)
2. [Row Level Security (RLS)](#32-row-level-security-rls)

---

# Part 1: 数据库 Schema 文件位置

**更新时间**: 2026-01-11
**重要**: ⚠️ 数据库 Schema 管理规范已更新

## 1.1 主 Schema 文件 (3个)

### ⭐ 新规范 (2026-01-11 更新)

**所有数据库变更直接更新以下 3 个主 Schema 文件，不再创建迁移脚本。**

#### 主 Schema 文件位置

```
decodables/migrations/v2/
├── 01_core_business.sql        ⭐ 核心业务表 (用户/项目/积分/市场)
├── 02_platform_services.sql    ⭐ 平台服务表 (配置/实验/事件/通知)
└── 03_infrastructure.sql       ⭐ 基础设施表 (日志/队列/分析/支持)
```

**文件说明**:

| 文件 | 表数量 | 内容 | 状态 |
|------|--------|------|------|
| **01_core_business.sql** | 25 | profiles, projects, credits, marketplace, system_resources, asset_categories | ✅ 主文件 |
| **02_platform_services.sql** | 32 | system_configs, feature_flags, experiments, events, notifications | ✅ 主文件 |
| **03_infrastructure.sql** | 12 | error_logs, task_queues, analytics, support_tickets | ✅ 主文件 |

**重要更新 (2026-01-11)**:
- ✅ **system_resources 表** - 已添加到 01_core_business.sql (Lines 828-901)
- ✅ **asset_categories 表** - 已添加 LTREE 层级支持 + 4 个 RPC 函数
- ✅ **4 个关联表** - asset_tags, asset_tag_relations, user_recent_assets, user_favorite_assets

---

## 1.2 文件结构

```
decodables/
├── migrations/
│   ├── v2/
│   │   ├── 01_core_business.sql       ⭐ 核心业务 Schema
│   │   ├── 02_platform_services.sql   ⭐ 平台服务 Schema
│   │   ├── 03_infrastructure.sql      ⭐ 基础设施 Schema
│   │   ├── docs/
│   │   │   ├── README.md             # V2 文档索引
│   │   │   ├── REFACTORING_REPORT.md # 重构报告
│   │   │   └── MIGRATION_GUIDE.md    # 迁移指南
│   │   └── patches/                  # 历史补丁 (已归档)
│   │
│   └── V1/                           # 已废弃 (仅供参考)
│       └── ddl.sql                   ❌ 旧版 (v3.27)
│
└── docs/
    └── database-guide.md             # 本文档
```

---

## 1.3 如何使用

### 1.3.1 Schema 管理规范

#### ❌ 禁止事项

```
❌ 不要创建 migrations/v1.28__add_xxx.sql (迁移脚本)
❌ 不要创建 migrations/v3/04_xxx.sql (中间脚本)
❌ 不要创建任何临时迁移文件
```

#### ✅ 正确做法

**数据库变更流程**:

```
1. 确定变更属于哪个类别:
   - 核心业务? → 编辑 migrations/v2/01_core_business.sql
   - 平台服务? → 编辑 migrations/v2/02_platform_services.sql
   - 基础设施? → 编辑 migrations/v2/03_infrastructure.sql

2. 直接在对应文件中添加/修改表定义

3. git commit + push

4. (生产环境) 手动执行 SQL 或使用 Supabase Migration
```

**示例 - 添加新表**:

```bash
# 错误做法 ❌
# 创建 migrations/v3/05_create_new_table.sql

# 正确做法 ✅
# 直接编辑 migrations/v2/01_core_business.sql
vim /Users/zhangyi/Code_all/AI-WEB/decodables/migrations/v2/01_core_business.sql

# 在文件末尾添加新表定义
CREATE TABLE new_table (
  id UUID PRIMARY KEY,
  ...
);

# 提交
git add migrations/v2/01_core_business.sql
git commit -m "feat(db): add new_table"
git push
```

### 1.3.2 版本历史

| 版本 | 文件路径 | 管理方式 | 状态 | 说明 |
|------|----------|----------|------|------|
| **v2.1** (当前) | `migrations/v2/01-03_*.sql` (3个文件) | ✅ 直接编辑主文件 | ✅ 使用中 | 2026-01-11 更新 |
| v2.0 | `migrations/v2/refactored_schema_v2.sql` | 单一文件 | ✅ 已拆分 | 已拆分为 3 个文件 |
| v1.0 | `migrations/V1/ddl.sql` | 单一文件 | ❌ 已废弃 | 旧版 |

---

### 1.3.3 新环境初始化

```bash
# 1. 使用 V2 主 Schema 文件初始化数据库 (按顺序执行)
psql -U postgres -d decodables < migrations/v2/01_core_business.sql
psql -U postgres -d decodables < migrations/v2/02_platform_services.sql
psql -U postgres -d decodables < migrations/v2/03_infrastructure.sql
```

### 1.3.4 查看 Schema 定义

```bash
# 查看核心业务表
cat migrations/v2/01_core_business.sql

# 查看特定表
grep -A 50 "CREATE TABLE system_resources" migrations/v2/01_core_business.sql
grep -A 50 "CREATE TABLE asset_categories" migrations/v2/01_core_business.sql

# 查看所有表名
grep "CREATE TABLE" migrations/v2/01_core_business.sql
grep "CREATE TABLE" migrations/v2/02_platform_services.sql
grep "CREATE TABLE" migrations/v2/03_infrastructure.sql
```

### 1.3.5 查看 RPC 函数

```bash
# 查看 asset_categories 相关的 RPC 函数
grep -A 20 "CREATE OR REPLACE FUNCTION get_category_descendants" migrations/v2/01_core_business.sql
grep -A 20 "CREATE OR REPLACE FUNCTION get_category_ancestors" migrations/v2/01_core_business.sql
grep -A 20 "CREATE OR REPLACE FUNCTION get_category_siblings" migrations/v2/01_core_business.sql
grep -A 20 "CREATE OR REPLACE FUNCTION move_category" migrations/v2/01_core_business.sql
```

---

## 1.4 重要提示

### 1.4.1 数据库变更规范

**所有数据库变更必须直接编辑 3 个主 Schema 文件，不要创建迁移脚本。**

❌ **错误做法**:
```bash
# 错误: 创建迁移脚本
touch migrations/v3/05_add_new_table.sql
```

✅ **正确做法**:
```bash
# 正确: 直接编辑主 Schema 文件
vim migrations/v2/01_core_business.sql  # 在文件中添加新表定义
git add migrations/v2/01_core_business.sql
git commit -m "feat(db): add new table"
```

### 1.4.2 变更提交流程

```
1. 确定变更类型
   ├─ 核心业务表? → migrations/v2/01_core_business.sql
   ├─ 平台服务表? → migrations/v2/02_platform_services.sql
   └─ 基础设施表? → migrations/v2/03_infrastructure.sql

2. 直接在文件中编辑
   ├─ 添加新表定义
   ├─ 修改现有表
   ├─ 添加索引
   └─ 添加 RPC 函数

3. Git 提交
   └─ git add migrations/v2/*.sql
   └─ git commit -m "feat(db): description"
   └─ git push

4. 生产环境部署
   └─ 手动执行 SQL 或使用 Supabase Migration
```

---

## 1.5 相关文档

### 主 Schema 文档

- [01_core_business.sql](../../migrations/v2/01_core_business.sql) - 核心业务表 ⭐
- [02_platform_services.sql](../../migrations/v2/02_platform_services.sql) - 平台服务表 ⭐
- [03_infrastructure.sql](../../migrations/v2/03_infrastructure.sql) - 基础设施表 ⭐
- [V2/docs/README.md](../../migrations/v2/docs/README.md) - V2 文档索引

### Asset-Category 系统文档

- [asset-category-design.md](../shared/asset-category-design.md) - 素材分类系统设计
- Asset-Category API 实现:
  - [domains/content/category_repository.py](../../domains/content/category_repository.py) - Repository 接口
  - [domains/content/category_service.py](../../domains/content/category_service.py) - 业务逻辑
  - [api/admin/asset_categories.py](../../api/admin/asset_categories.py) - Admin API (7 endpoints)

### System-Resources 系统文档

- system_resources 表定义: `migrations/v2/01_core_business.sql` Lines 828-901
- 关联表: asset_tags, asset_tag_relations, user_recent_assets, user_favorite_assets

### 业务逻辑文档

- [backend-business-logic.md](backend-business-logic.md) - 后端架构和业务规则
- [backend-architecture.md](backend-architecture.md) - DDD 架构指南

---

## 1.6 维护者信息

**责任人**: 开发团队
**最后更新**: 2026-01-11
**版本**: v2.1

**重要更新 (2026-01-12)**:
- ✅ **error_logs 表扩展** - 新增 14 个前端错误日志字段 (支持 errorLogger.ts)
  - 新字段: error_id, error_code, message, status_code, endpoint, method, stack_trace, page_url, user_agent, session_id, user_code, context, client_timestamp, source
  - 索引: idx_error_logs_error_id, idx_error_logs_session_id
  - 迁移脚本: `scripts/migrations/add_frontend_error_log_fields.sql`

**重要更新 (2026-01-11)**:
- ✅ Schema 管理规范更新: 直接编辑主文件，不再创建迁移脚本
- ✅ system_resources 表完整实现 (25 字段, 7 索引)
- ✅ asset_categories LTREE 层级支持 + 4 RPC 函数
- ✅ Asset-Category 管理 API (7 endpoints)

如有疑问,请参考:
- Schema 文件: `migrations/v2/01_core_business.sql`
- DDD 架构指南: `docs/main/backend-architecture.md`

---

**快速链接**:
- [核心业务 Schema](../../migrations/v2/01_core_business.sql) ⭐
- [平台服务 Schema](../../migrations/v2/02_platform_services.sql) ⭐
- [基础设施 Schema](../../migrations/v2/03_infrastructure.sql) ⭐
- [Asset-Category 设计文档](../shared/asset-category-design.md)

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

### 核心业务表 (01_core_business.sql)

| 映射表 | 数据库表 | 领域对象 | 软删除 |
|--------|----------|----------|--------|
| `PROFILES_DB_TO_DOMAIN` | profiles | UserProfile | ✅ |
| `CREDIT_TX_DB_TO_DOMAIN` | credit_transactions | CreditTransaction | ❌ |
| `PROJECTS_DB_TO_DOMAIN` | projects | Project | ✅ |
| `LISTINGS_DB_TO_DOMAIN` | marketplace_listings | Listing | ✅ |
| `PURCHASES_DB_TO_DOMAIN` | marketplace_purchases | Purchase | ❌ |
| `ASSETS_DB_TO_DOMAIN` | assets | Asset | ✅ |
| `ASSET_CATEGORIES_DB_TO_DOMAIN` | asset_categories | AssetCategory | ✅ |
| `SYSTEM_ASSETS_DB_TO_DOMAIN` | system_assets | SystemAsset | ❌ |
| `USER_DISCOUNTS_DB_TO_DOMAIN` | user_discounts | UserDiscount | ❌ |

### 平台服务表 (02_platform_services.sql)

| 映射表 | 数据库表 | 领域对象 | 软删除 |
|--------|----------|----------|--------|
| `CONFIGS_DB_TO_DOMAIN` | system_configs | SystemConfig | ❌ |
| `NOTIFICATIONS_DB_TO_DOMAIN` | notifications | Notification | ❌ |
| `FEATURE_FLAGS_DB_TO_DOMAIN` | feature_flags | FeatureFlag | ❌ |
| `EXPERIMENTS_DB_TO_DOMAIN` | experiments | Experiment | ❌ |
| `CAMPAIGNS_DB_TO_DOMAIN` | campaigns | Campaign | ✅ |
| `DAILY_THEMES_DB_TO_DOMAIN` | daily_themes | DailyTheme | ✅ |
| `HOLIDAYS_DB_TO_DOMAIN` | holidays | Holiday | ✅ |
| `USER_EVENTS_DB_TO_DOMAIN` | user_events | UserEvent | ❌ (append-only) |
| `CONTENT_REPORTS_DB_TO_DOMAIN` | content_reports | ContentReport | ❌ |
| `V_MARKETPLACE_REPORTS_DB_TO_DOMAIN` | v_marketplace_reports (视图) | ContentReport | ❌ |

### 基础设施表 (03_infrastructure.sql)

| 映射表 | 数据库表 | 领域对象 | 软删除 |
|--------|----------|----------|--------|
| `ERROR_LOGS_DB_TO_DOMAIN` | error_logs | ErrorLog | ❌ | ⭐ v3.1.0 前端字段支持 |
| `API_LOGS_DB_TO_DOMAIN` | api_logs | ApiLog | ❌ |
| `ADMIN_OPERATIONS_DB_TO_DOMAIN` | admin_operations | AdminOperation | ❌ |
| `AGGREGATED_STATS_DB_TO_DOMAIN` | aggregated_stats | AggregatedStat | ❌ |
| `SUPPORT_TICKETS_DB_TO_DOMAIN` | support_tickets | SupportTicket | ✅ |
| `SUPPORT_REPLIES_DB_TO_DOMAIN` | support_replies | SupportReply | ✅ |
| `PAYMENT_RECORDS_DB_TO_DOMAIN` | payment_records | PaymentRecord | ❌ |

> 📝 **完整映射表**: 查看 `infrastructure/repositories/field_mappings.py` 获取所有 50+ 个表的映射定义

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

# Part 3: 数据库视图与安全

## 3.1 视图命名规范

**更新时间**: 2026-01-12

所有数据库视图统一使用 `v_` 前缀，便于区分表和视图。

### 当前视图列表

| 视图名称 | 基础表 | 用途 | 所在文件 |
|----------|--------|------|----------|
| `v_projects` | projects | 添加 owner_id 别名 | 01_core_business.sql |
| `v_marketplace_reports` | content_reports | Repository 兼容 | 02_platform_services.sql |
| `v_ai_usage_last_30_days` | ai_usage_daily | 30天 AI 使用统计 | 03_infrastructure.sql |

### 代码中使用视图

```python
# ✅ 正确: 使用统一的 v_ 前缀视图名
result = self.client.table("v_marketplace_reports").select("*").execute()

# ❌ 错误: 使用旧的视图名
result = self.client.table("marketplace_reports").select("*").execute()
```

### 字段映射

视图的字段映射与其基础表共享：

```python
from infrastructure.repositories.field_mappings import (
    V_MARKETPLACE_REPORTS_DB_TO_DOMAIN,  # 推荐使用
    MARKETPLACE_REPORTS_DB_TO_DOMAIN,     # 兼容旧代码 (已废弃)
)
```

---

## 3.2 Row Level Security (RLS)

**更新时间**: 2026-01-12

### RLS 策略说明

所有 69 个表已启用 Row Level Security (RLS)，但**未添加任何策略**。

**效果**:
- `service_role` key (后端使用) → ✅ 正常访问所有数据 (绕过 RLS)
- `anon` key (前端泄露风险) → ❌ 拒绝所有访问

### 为什么这样设计？

| 原因 | 说明 |
|------|------|
| **架构匹配** | 前端不直接访问 Supabase，所有请求通过后端 API |
| **认证分离** | 认证由 Clerk 处理，不是 Supabase Auth |
| **安全深度防御** | 即使 anon key 泄露，数据也受保护 |
| **简化管理** | 权限逻辑集中在后端代码 |

### RLS 启用位置

所有 RLS 启用语句集中在 `03_infrastructure.sql` 末尾:

```sql
-- 03_infrastructure.sql:1834-1917
-- Row Level Security (RLS) 启用
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
-- ... 其他 67 个表
```

### 添加自定义策略 (可选)

如果将来需要让前端直接访问部分表，可以添加策略:

```sql
-- 示例: 允许匿名用户读取公开的 listings
CREATE POLICY "Public listings are viewable by everyone"
ON marketplace_listings FOR SELECT
USING (is_public = true AND status = 'published');
```

---

# Part 4: 数据库维护任务

> **版本**: v3.30  
> **更新日期**: 2026-01-13

## 4.1 维护任务概述

### 问题背景

日志表（`user_creation_logs`, `error_logs`, `activity_logs`）会随着系统运行不断增长，如果不定期清理，会导致：

- ❌ 数据库存储空间不断增长
- ❌ 查询性能下降
- ❌ 备份时间延长
- ❌ 成本增加

### 解决方案

**自动化清理任务** + **监控视图**

---

## 4.2 清理函数

### 位置

```
decodables/migrations/v2/03_infrastructure.sql
```

### 可用函数

| 函数名 | 功能 | 默认保留天数 | 调用方式 |
|--------|------|--------------|----------|
| `cleanup_old_user_creation_logs()` | 清理用户创建日志 | 90 天 | 应用层定时任务 |
| `cleanup_old_error_logs()` | 清理错误日志 | 30 天 | 应用层定时任务 |
| `cleanup_old_activity_logs()` | 清理活动日志 | 180 天 | 应用层定时任务 |

### 使用示例

```sql
-- 手动执行清理
SELECT cleanup_old_user_creation_logs(90);  -- 清理 90 天前的日志
SELECT cleanup_old_error_logs(30);          -- 清理 30 天前的日志
SELECT cleanup_old_activity_logs(180);      -- 清理 180 天前的日志（保留关键事件）

-- 查看清理结果
SELECT * FROM get_log_tables_stats();
```

---

## 4.3 监控视图

### v_table_sizes

**用途**: 监控所有表的大小

```sql
SELECT * FROM v_table_sizes 
WHERE tablename IN ('user_creation_logs', 'error_logs', 'activity_logs');
```

**输出示例**:
| schemaname | tablename | total_size | table_size | indexes_size |
|------------|-----------|------------|------------|--------------|
| public | user_creation_logs | 2.5 MB | 1.8 MB | 700 KB |
| public | error_logs | 1.2 MB | 900 KB | 300 KB |
| public | activity_logs | 15 MB | 12 MB | 3 MB |

### get_log_tables_stats()

**用途**: 获取日志表详细统计

```sql
SELECT * FROM get_log_tables_stats();
```

**输出示例**:
| table_name | total_rows | old_rows | retention_days | next_cleanup_count | table_size |
|------------|------------|----------|----------------|--------------------| -----------|
| user_creation_logs | 50000 | 12000 | 90 | 12000 | 2.5 MB |
| error_logs | 8000 | 3000 | 30 | 3000 | 1.2 MB |
| activity_logs | 250000 | 80000 | 180 | 80000 | 15 MB |

---

## 4.4 调度策略

### 方式 1: 应用层定时任务（推荐）

**位置**: `infrastructure/tasks/maintenance_scheduler.py`  
**调度器**: `scheduler.py` (APScheduler)

```python
# 每天 4:00 AM UTC
scheduler.add_job(
    run_daily_maintenance,
    CronTrigger(hour=4, minute=0),
    id="daily_maintenance"
)

# 每周日 5:00 AM UTC
scheduler.add_job(
    run_weekly_maintenance,
    CronTrigger(day_of_week='sun', hour=5, minute=0),
    id="weekly_maintenance"
)
```

**优点**:
- ✅ 与应用代码统一管理
- ✅ 易于测试和监控
- ✅ 支持 Sentry 告警
- ✅ Railway 原生支持

**缺点**:
- ⚠️ 多实例部署时需要环境变量控制（`ENABLE_SCHEDULER=true` 只在 1 个实例）

### 方式 2: Supabase Cron（可选）

**位置**: Supabase Dashboard > Database > Cron Jobs

```sql
-- 任务 1: 每天 3:00 AM 清理用户创建日志
Schedule: 0 3 * * *
SQL: SELECT cleanup_old_user_creation_logs(90);

-- 任务 2: 每天 4:00 AM 清理错误日志
Schedule: 0 4 * * *
SQL: SELECT cleanup_old_error_logs(30);

-- 任务 3: 每周日 5:00 AM 清理活动日志
Schedule: 0 5 * * 0
SQL: SELECT cleanup_old_activity_logs(180);
```

**优点**:
- ✅ 不依赖应用实例
- ✅ 数据库层面保证执行

**缺点**:
- ⚠️ Supabase 免费版可能不支持 Cron
- ⚠️ 无法集成 Sentry 告警
- ⚠️ 需要手动配置

---

## 4.5 最佳实践

### 1. 定期检查表大小

**频率**: 每月 1 次

```sql
-- 查看所有表大小
SELECT * FROM v_table_sizes ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 20;

-- 查看日志表统计
SELECT * FROM get_log_tables_stats();
```

### 2. 告警阈值

| 日志表 | 警告阈值 | 处理方式 |
|--------|----------|----------|
| user_creation_logs | >100 MB | 减少保留天数（90→60） |
| error_logs | >50 MB | 检查错误频率，解决根本问题 |
| activity_logs | >500 MB | 考虑分区或归档到 S3 |

### 3. 关键事件永久保留

```sql
-- cleanup_old_activity_logs() 会自动排除这些关键事件
WHERE action NOT IN ('user_signup', 'subscription_purchase');
```

### 4. 手动干预

如果自动清理失效，手动执行：

```sql
-- 1. 备份关键数据（可选）
CREATE TABLE activity_logs_backup AS 
SELECT * FROM activity_logs WHERE action IN ('user_signup', 'subscription_purchase');

-- 2. 执行清理
SELECT cleanup_old_activity_logs(180);

-- 3. 验证结果
SELECT COUNT(*) FROM activity_logs;
SELECT * FROM get_log_tables_stats();

-- 4. 优化表
VACUUM ANALYZE activity_logs;
```

---

## 4.6 故障排查

### 问题 1: 清理任务未运行

**症状**: 日志表持续增长，`get_log_tables_stats()` 显示 `old_rows` 数量不断增加

**排查步骤**:

```bash
# 1. 检查调度器日志
railway logs --filter "maintenance"

# 2. 检查环境变量
railway variables | grep ENABLE_SCHEDULER

# 3. 手动测试清理函数
psql -c "SELECT cleanup_old_error_logs(30);"
```

**解决方案**:
- 确保至少有 1 个实例 `ENABLE_SCHEDULER=true`
- 检查 `scheduler.py` 是否正确配置
- 验证数据库函数是否存在

### 问题 2: 清理效率低

**症状**: 清理任务执行时间过长（>5 分钟）

**排查步骤**:

```sql
-- 查看索引
SELECT * FROM pg_indexes 
WHERE tablename IN ('user_creation_logs', 'error_logs', 'activity_logs');

-- 查看表统计
SELECT * FROM pg_stat_user_tables 
WHERE relname IN ('user_creation_logs', 'error_logs', 'activity_logs');
```

**解决方案**:
```sql
-- 1. 重建索引
REINDEX TABLE user_creation_logs;

-- 2. 更新统计
ANALYZE user_creation_logs;

-- 3. 分批删除（对大表）
DELETE FROM activity_logs 
WHERE created_at < NOW() - INTERVAL '180 days' 
  AND action NOT IN ('user_signup', 'subscription_purchase')
LIMIT 10000;  -- 分批删除
```

---

## 4.7 未来增强

### 潜在优化方向

1. **日志归档到 S3**（长期存储）
   - 保留 90 天在数据库
   - 归档到 Supabase Storage
   - 提供归档查询接口

2. **表分区** (PostgreSQL Partitioning)
   - 按月分区 `activity_logs`
   - 自动清理旧分区
   - 提升查询性能

3. **Grafana 可视化**
   - 实时监控表增长趋势
   - 告警通知（Slack/Email）
   - 历史数据分析

---

**文档版本**: v3.30
**最后更新**: 2026-01-13
**维护者**: 后端团队
