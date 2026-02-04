# 数据迁移脚本

> **版本**: v1.0
> **日期**: 2026-02-04
> **状态**: 🔴 待实现
> **脚本位置**: `decodables/scripts/migrations/entitlement/`

---

## 相关设计文档

| 设计文档 | 本文档章节 |
|----------|-----------|
| 02-tier-config.md | §2.1 |
| 15-credits-lifecycle.md | §2.2 |
| 全部设计文档 | §3 |

---

## 目录

- [§1. 迁移策略](#1-迁移策略)
- [§2. 数据迁移脚本](#2-数据迁移脚本)
  - [§2.1 Tier 配置迁移](#21-tier-配置迁移)
  - [§2.2 积分数据迁移](#22-积分数据迁移)
- [§3. Schema 迁移脚本](#3-schema-迁移脚本)
- [§4. 回滚脚本](#4-回滚脚本)
- [§5. 验证脚本](#5-验证脚本)

---

## §1. 迁移策略

### 1.1 迁移原则

1. **增量迁移**: 新表先创建，数据逐步迁移
2. **双写期**: 新旧系统并行写入，验证一致性
3. **灰度切换**: 逐步切换流量到新系统
4. **可回滚**: 每步操作都有回滚方案

### 1.2 迁移阶段

```
Phase 1: Schema 准备 (Day 1)
├── 创建新表 (不影响现有功能)
├── 创建索引
└── 创建 RPC 函数

Phase 2: 数据迁移 (Day 2-3)
├── 迁移 Tier 配置到 system_configs
├── 迁移用户积分到 credit_pools
└── 验证数据完整性

Phase 3: 双写验证 (Day 4-7)
├── 新旧系统并行写入
├── 对比数据一致性
└── 修复差异

Phase 4: 切换 (Day 8)
├── 切换读取到新系统
├── 停止旧系统写入
└── 监控告警
```

### 1.3 脚本命名规范

```
{序号}_{描述}.py

示例:
001_create_entitlement_tables.py
002_migrate_tier_configs.py
003_migrate_credit_pools.py
004_verify_migration.py
005_cleanup_legacy_tables.py
```

---

## §2. 数据迁移脚本

### §2.1 Tier 配置迁移

**文件**: `scripts/migrations/entitlement/002_migrate_tier_configs.py`

**目的**: 将硬编码的 Tier 配置迁移到 `system_configs` 表

```python
#!/usr/bin/env python3
"""
迁移 Tier 配置到 system_configs 表

Usage:
    python scripts/migrations/entitlement/002_migrate_tier_configs.py
    python scripts/migrations/entitlement/002_migrate_tier_configs.py --dry-run
    python scripts/migrations/entitlement/002_migrate_tier_configs.py --rollback
"""

import asyncio
import argparse
import json
from datetime import datetime
from supabase import create_client, AsyncClient

# Tier 功能配置 (来源: 01-permission-matrix.md)
TIER_FEATURES = {
    "t1": {
        "platform_assets": True,
        "vector_tools": True,
        "freehand_tools": True,
        "pdf_export": True,
        "pdf_print": True,
        "can_subscribe": True,
        "clipboard_paste": "trial",
        "ai_features": "trial",
        "smart_scan": "trial",
        "zip_export": "trial",
        "publish_paid": "trial",
        "publish_free": "trial",
        "browse_marketplace": "trial",
        "purchase_marketplace": "trial",
        "can_upload_custom_assets": "trial",
        "recover_deleted": False,
        "can_invite_members": False,
        "can_purchase_credits": False,
    },
    "t2": {
        "platform_assets": True,
        "vector_tools": True,
        "freehand_tools": True,
        "pdf_export": True,
        "pdf_print": True,
        "can_subscribe": True,
        "clipboard_paste": "trial",
        "ai_features": True,
        "smart_scan": "trial",
        "zip_export": "trial",
        "publish_paid": "trial",
        "publish_free": True,
        "browse_marketplace": True,
        "purchase_marketplace": True,
        "can_upload_custom_assets": "trial",
        "recover_deleted": False,
        "can_invite_members": False,
        "can_purchase_credits": True,
    },
    "t3": {
        "platform_assets": True,
        "vector_tools": True,
        "freehand_tools": True,
        "pdf_export": True,
        "pdf_print": True,
        "can_subscribe": True,
        "clipboard_paste": True,
        "ai_features": True,
        "smart_scan": True,
        "zip_export": True,
        "publish_paid": True,
        "publish_free": True,
        "browse_marketplace": True,
        "purchase_marketplace": True,
        "can_upload_custom_assets": True,
        "recover_deleted": True,
        "can_invite_members": True,
        "can_purchase_credits": True,
    },
    "t4": {
        # t4 继承 t3 所有权限
        "platform_assets": True,
        "vector_tools": True,
        "freehand_tools": True,
        "pdf_export": True,
        "pdf_print": True,
        "can_subscribe": True,
        "clipboard_paste": True,
        "ai_features": True,
        "smart_scan": True,
        "zip_export": True,
        "publish_paid": True,
        "publish_free": True,
        "browse_marketplace": True,
        "purchase_marketplace": True,
        "can_upload_custom_assets": True,
        "recover_deleted": True,
        "can_invite_members": True,
        "can_purchase_credits": True,
    },
}

# Tier 配额配置
TIER_QUOTAS = {
    "t1": {"max_projects": 3, "max_pages_per_project": 6, "max_custom_assets": 0},
    "t2": {"max_projects": 50, "max_pages_per_project": 24, "max_custom_assets": 0},
    "t3": {"max_projects": -1, "max_pages_per_project": -1, "max_custom_assets": -1},
    "t4": {"max_projects": -1, "max_pages_per_project": -1, "max_custom_assets": -1},
}

# Tier 显示名称
TIER_DISPLAY_NAMES = {
    "t1": "Free Plan",
    "t2": "Starter Plan",
    "t3": "Pro Plan",
    "t4": "Enterprise",
}


async def migrate(client: AsyncClient, dry_run: bool = False):
    """执行迁移"""
    print(f"{'[DRY RUN] ' if dry_run else ''}开始迁移 Tier 配置...")

    configs = [
        {
            "key": "TIER_FEATURES",
            "value": TIER_FEATURES,
            "description": "Tier 功能权限配置",
        },
        {
            "key": "TIER_QUOTAS",
            "value": TIER_QUOTAS,
            "description": "Tier 配额限制",
        },
        {
            "key": "TIER_DISPLAY_NAMES",
            "value": TIER_DISPLAY_NAMES,
            "description": "Tier 显示名称",
        },
    ]

    for config in configs:
        print(f"  迁移配置: {config['key']}")

        if dry_run:
            print(f"    [DRY RUN] 将插入: {json.dumps(config['value'], indent=2)[:100]}...")
            continue

        # 检查是否已存在
        existing = await client.table("system_configs") \
            .select("id") \
            .eq("key", config["key"]) \
            .maybeSingle() \
            .execute()

        if existing.data:
            # 更新
            await client.table("system_configs") \
                .update({
                    "value": config["value"],
                    "description": config["description"],
                    "updated_at": datetime.utcnow().isoformat(),
                }) \
                .eq("key", config["key"]) \
                .execute()
            print(f"    ✓ 已更新")
        else:
            # 插入
            await client.table("system_configs") \
                .insert({
                    "key": config["key"],
                    "value": config["value"],
                    "description": config["description"],
                }) \
                .execute()
            print(f"    ✓ 已插入")

    print("Tier 配置迁移完成!")


async def rollback(client: AsyncClient, dry_run: bool = False):
    """回滚迁移"""
    print(f"{'[DRY RUN] ' if dry_run else ''}开始回滚 Tier 配置...")

    keys = ["TIER_FEATURES", "TIER_QUOTAS", "TIER_DISPLAY_NAMES"]

    for key in keys:
        print(f"  删除配置: {key}")

        if dry_run:
            print(f"    [DRY RUN] 将删除 key={key}")
            continue

        await client.table("system_configs") \
            .delete() \
            .eq("key", key) \
            .execute()
        print(f"    ✓ 已删除")

    print("回滚完成!")


async def main():
    parser = argparse.ArgumentParser(description="迁移 Tier 配置")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不执行")
    parser.add_argument("--rollback", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    # 初始化 Supabase client
    from core.config import settings
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    if args.rollback:
        await rollback(client, args.dry_run)
    else:
        await migrate(client, args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
```

### §2.2 积分数据迁移

**文件**: `scripts/migrations/entitlement/003_migrate_credit_pools.py`

**目的**: 将用户积分数据迁移到新的 `credit_pools` 表 (二维模型)

```python
#!/usr/bin/env python3
"""
迁移用户积分到 credit_pools 表 (二维模型)

旧模型:
- profiles.credits_monthly (月度积分)
- profiles.credits_permanent (永久积分)

新模型:
- credit_pools (source_type + expires_at)

Usage:
    python scripts/migrations/entitlement/003_migrate_credit_pools.py
    python scripts/migrations/entitlement/003_migrate_credit_pools.py --dry-run
    python scripts/migrations/entitlement/003_migrate_credit_pools.py --batch-size 100
"""

import asyncio
import argparse
from datetime import datetime, timedelta
from typing import List, Dict
from supabase import create_client, AsyncClient


async def get_users_with_credits(client: AsyncClient, offset: int, limit: int) -> List[Dict]:
    """获取有积分的用户"""
    result = await client.table("profiles") \
        .select("id, credits_monthly, credits_permanent, tier") \
        .or_("credits_monthly.gt.0,credits_permanent.gt.0") \
        .range(offset, offset + limit - 1) \
        .execute()
    return result.data


async def migrate_user_credits(
    client: AsyncClient,
    user: Dict,
    dry_run: bool = False
) -> Dict:
    """迁移单个用户的积分"""
    user_id = user["id"]
    credits_monthly = user.get("credits_monthly", 0)
    credits_permanent = user.get("credits_permanent", 0)
    tier = user.get("tier", "t1")

    stats = {"pools_created": 0, "total_credits": 0}

    # 1. 迁移月度积分 (订阅来源，有过期时间)
    if credits_monthly > 0:
        # 假设月度积分月底过期
        now = datetime.utcnow()
        end_of_month = datetime(now.year, now.month + 1, 1) - timedelta(days=1)

        if dry_run:
            print(f"    [DRY RUN] 创建月度积分池: {credits_monthly}")
        else:
            await client.table("credit_pools").insert({
                "user_id": user_id,
                "source_type": "subscription",
                "initial_amount": credits_monthly,
                "balance": credits_monthly,
                "expires_at": end_of_month.isoformat(),
            }).execute()

        stats["pools_created"] += 1
        stats["total_credits"] += credits_monthly

    # 2. 迁移永久积分
    if credits_permanent > 0:
        # 判断来源：如果是 t1 用户且积分 <= 100，可能是注册赠送
        if tier == "t1" and credits_permanent <= 100:
            source_type = "bonus_signup"
        else:
            source_type = "purchase"  # 默认当作购买

        if dry_run:
            print(f"    [DRY RUN] 创建永久积分池 ({source_type}): {credits_permanent}")
        else:
            await client.table("credit_pools").insert({
                "user_id": user_id,
                "source_type": source_type,
                "initial_amount": credits_permanent,
                "balance": credits_permanent,
                "expires_at": None,  # 永久
            }).execute()

        stats["pools_created"] += 1
        stats["total_credits"] += credits_permanent

    return stats


async def migrate(client: AsyncClient, batch_size: int, dry_run: bool = False):
    """执行批量迁移"""
    print(f"{'[DRY RUN] ' if dry_run else ''}开始迁移积分数据...")

    offset = 0
    total_users = 0
    total_pools = 0
    total_credits = 0

    while True:
        users = await get_users_with_credits(client, offset, batch_size)

        if not users:
            break

        print(f"处理第 {offset + 1} - {offset + len(users)} 个用户...")

        for user in users:
            print(f"  用户 {user['id'][:8]}... (monthly={user.get('credits_monthly', 0)}, permanent={user.get('credits_permanent', 0)})")

            stats = await migrate_user_credits(client, user, dry_run)

            total_pools += stats["pools_created"]
            total_credits += stats["total_credits"]
            total_users += 1

        offset += batch_size

    print(f"\n迁移完成!")
    print(f"  处理用户数: {total_users}")
    print(f"  创建积分池: {total_pools}")
    print(f"  总积分数: {total_credits}")


async def verify(client: AsyncClient):
    """验证迁移结果"""
    print("验证迁移结果...")

    # 1. 对比总积分
    old_total = await client.rpc("sum_old_credits").execute()
    new_total = await client.rpc("sum_new_credits").execute()

    print(f"  旧系统总积分: {old_total.data}")
    print(f"  新系统总积分: {new_total.data}")

    if old_total.data != new_total.data:
        print(f"  ⚠️ 警告: 积分总数不一致!")
    else:
        print(f"  ✓ 积分总数一致")

    # 2. 抽样验证
    sample = await client.table("profiles") \
        .select("id, credits_monthly, credits_permanent") \
        .or_("credits_monthly.gt.0,credits_permanent.gt.0") \
        .limit(10) \
        .execute()

    for user in sample.data:
        old_sum = user.get("credits_monthly", 0) + user.get("credits_permanent", 0)

        new_pools = await client.table("credit_pools") \
            .select("balance") \
            .eq("user_id", user["id"]) \
            .execute()

        new_sum = sum(p["balance"] for p in new_pools.data)

        status = "✓" if old_sum == new_sum else "⚠️"
        print(f"  {status} 用户 {user['id'][:8]}...: 旧={old_sum}, 新={new_sum}")


async def rollback(client: AsyncClient, dry_run: bool = False):
    """回滚迁移 (清空 credit_pools 表)"""
    print(f"{'[DRY RUN] ' if dry_run else ''}开始回滚积分迁移...")

    if dry_run:
        count = await client.table("credit_pools").select("id", count="exact").execute()
        print(f"  [DRY RUN] 将删除 {count.count} 条记录")
    else:
        # 注意: 生产环境应该更谨慎，可能需要备份
        await client.table("credit_pools").delete().neq("id", "").execute()
        print(f"  ✓ 已清空 credit_pools 表")

    print("回滚完成!")


async def main():
    parser = argparse.ArgumentParser(description="迁移用户积分")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不执行")
    parser.add_argument("--rollback", action="store_true", help="回滚迁移")
    parser.add_argument("--verify", action="store_true", help="验证迁移结果")
    parser.add_argument("--batch-size", type=int, default=100, help="批处理大小")
    args = parser.parse_args()

    from core.config import settings
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    if args.rollback:
        await rollback(client, args.dry_run)
    elif args.verify:
        await verify(client)
    else:
        await migrate(client, args.batch_size, args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## §3. Schema 迁移脚本

**文件**: `scripts/migrations/entitlement/001_create_entitlement_tables.py`

**目的**: 创建 Entitlement 系统所需的所有表

```python
#!/usr/bin/env python3
"""
创建 Entitlement 系统表

此脚本创建以下表:
- user_feature_overrides
- feature_flags
- user_groups / user_group_members
- config_versions
- workspace_overrides
- trial_records
- credit_pools / credit_transactions
- invoices
- refunds
- promotions / user_promotions
- referral_codes / referral_rewards
- education_verifications

Usage:
    python scripts/migrations/entitlement/001_create_entitlement_tables.py
"""

import asyncio
from supabase import create_client


SQL_STATEMENTS = [
    # 详见 01-database-schema.md 中的完整 SQL
    """
    CREATE TABLE IF NOT EXISTS user_feature_overrides (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        feature_key VARCHAR(50) NOT NULL,
        override_value JSONB NOT NULL,
        reason VARCHAR(100),
        granted_by UUID REFERENCES profiles(id),
        expires_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(user_id, feature_key)
    );
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_user_feature_overrides_user
    ON user_feature_overrides(user_id);
    """,

    # ... 其他表的 SQL
]


async def create_tables(client):
    """创建所有表"""
    print("开始创建 Entitlement 表...")

    for i, sql in enumerate(SQL_STATEMENTS, 1):
        print(f"  执行语句 {i}/{len(SQL_STATEMENTS)}...")
        await client.rpc("exec_sql", {"sql": sql}).execute()

    print("所有表创建完成!")


async def main():
    from core.config import settings
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    await create_tables(client)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## §4. 回滚脚本

**文件**: `scripts/migrations/entitlement/rollback_all.py`

```python
#!/usr/bin/env python3
"""
回滚所有 Entitlement 迁移

WARNING: 此操作会删除所有 Entitlement 相关数据!

Usage:
    python scripts/migrations/entitlement/rollback_all.py --confirm
"""

import asyncio
import argparse


TABLES_TO_DROP = [
    "education_verifications",
    "referral_rewards",
    "referral_codes",
    "user_promotions",
    "promotions",
    "refunds",
    "invoices",
    "credit_transactions",
    "credit_pools",
    "trial_records",
    "workspace_overrides",
    "config_versions",
    "user_group_members",
    "user_groups",
    "feature_flags",
    "user_feature_overrides",
]


async def rollback(client, confirm: bool):
    """执行回滚"""
    if not confirm:
        print("⚠️ 警告: 此操作会删除所有 Entitlement 数据!")
        print("使用 --confirm 参数确认执行")
        return

    print("开始回滚...")

    for table in TABLES_TO_DROP:
        print(f"  删除表: {table}")
        await client.rpc("exec_sql", {
            "sql": f"DROP TABLE IF EXISTS {table} CASCADE"
        }).execute()

    # 删除 system_configs 中的配置
    await client.table("system_configs") \
        .delete() \
        .in_("key", ["TIER_FEATURES", "TIER_QUOTAS", "TIER_DISPLAY_NAMES"]) \
        .execute()

    print("回滚完成!")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    from core.config import settings
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    await rollback(client, args.confirm)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## §5. 验证脚本

**文件**: `scripts/migrations/entitlement/004_verify_migration.py`

```python
#!/usr/bin/env python3
"""
验证 Entitlement 迁移完整性

检查项:
1. 所有表是否创建成功
2. 所有索引是否创建成功
3. 所有 RPC 函数是否创建成功
4. 配置数据是否正确
5. 积分数据是否一致

Usage:
    python scripts/migrations/entitlement/004_verify_migration.py
"""

import asyncio
from supabase import create_client


REQUIRED_TABLES = [
    "user_feature_overrides",
    "feature_flags",
    "user_groups",
    "user_group_members",
    "config_versions",
    "workspace_overrides",
    "trial_records",
    "credit_pools",
    "credit_transactions",
    "invoices",
    "refunds",
    "promotions",
    "user_promotions",
    "referral_codes",
    "referral_rewards",
    "education_verifications",
]

REQUIRED_RPC_FUNCTIONS = [
    "consume_credits_fefo",
    "deduct_credits_for_refund",
    "get_user_feature_permission",
]

REQUIRED_CONFIGS = [
    "TIER_FEATURES",
    "TIER_QUOTAS",
    "TIER_DISPLAY_NAMES",
]


async def verify_tables(client) -> bool:
    """验证表是否存在"""
    print("验证表结构...")
    all_pass = True

    for table in REQUIRED_TABLES:
        try:
            await client.table(table).select("id").limit(1).execute()
            print(f"  ✓ {table}")
        except Exception as e:
            print(f"  ✗ {table}: {e}")
            all_pass = False

    return all_pass


async def verify_rpc_functions(client) -> bool:
    """验证 RPC 函数是否存在"""
    print("验证 RPC 函数...")
    all_pass = True

    for func in REQUIRED_RPC_FUNCTIONS:
        try:
            # 尝试调用，会失败但能验证函数存在
            await client.rpc(func, {}).execute()
            print(f"  ✓ {func}")
        except Exception as e:
            if "does not exist" in str(e):
                print(f"  ✗ {func}: 函数不存在")
                all_pass = False
            else:
                print(f"  ✓ {func} (存在，参数验证失败是预期的)")

    return all_pass


async def verify_configs(client) -> bool:
    """验证配置数据"""
    print("验证配置数据...")
    all_pass = True

    for config_key in REQUIRED_CONFIGS:
        result = await client.table("system_configs") \
            .select("value") \
            .eq("key", config_key) \
            .maybeSingle() \
            .execute()

        if result.data:
            print(f"  ✓ {config_key}")
        else:
            print(f"  ✗ {config_key}: 配置不存在")
            all_pass = False

    return all_pass


async def verify_credit_consistency(client) -> bool:
    """验证积分数据一致性"""
    print("验证积分数据一致性...")

    # 获取旧系统总积分
    old_result = await client.table("profiles") \
        .select("credits_monthly, credits_permanent") \
        .execute()

    old_total = sum(
        (u.get("credits_monthly", 0) or 0) + (u.get("credits_permanent", 0) or 0)
        for u in old_result.data
    )

    # 获取新系统总积分
    new_result = await client.table("credit_pools") \
        .select("balance") \
        .execute()

    new_total = sum(p.get("balance", 0) or 0 for p in new_result.data)

    print(f"  旧系统总积分: {old_total}")
    print(f"  新系统总积分: {new_total}")

    if old_total == new_total:
        print(f"  ✓ 积分数据一致")
        return True
    else:
        print(f"  ✗ 积分数据不一致! 差异: {abs(old_total - new_total)}")
        return False


async def main():
    print("=" * 50)
    print("Entitlement 迁移验证")
    print("=" * 50)

    from core.config import settings
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    results = []
    results.append(("表结构", await verify_tables(client)))
    results.append(("RPC 函数", await verify_rpc_functions(client)))
    results.append(("配置数据", await verify_configs(client)))
    results.append(("积分一致性", await verify_credit_consistency(client)))

    print("\n" + "=" * 50)
    print("验证结果汇总")
    print("=" * 50)

    all_pass = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False

    print("\n" + ("全部通过!" if all_pass else "存在问题，请检查!"))
    return all_pass


if __name__ == "__main__":
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
```

---

## 附录: 执行清单

```bash
# 1. 创建表 (Day 1)
python scripts/migrations/entitlement/001_create_entitlement_tables.py

# 2. 迁移 Tier 配置
python scripts/migrations/entitlement/002_migrate_tier_configs.py --dry-run  # 预览
python scripts/migrations/entitlement/002_migrate_tier_configs.py            # 执行

# 3. 迁移积分数据
python scripts/migrations/entitlement/003_migrate_credit_pools.py --dry-run  # 预览
python scripts/migrations/entitlement/003_migrate_credit_pools.py            # 执行

# 4. 验证迁移
python scripts/migrations/entitlement/004_verify_migration.py

# 5. 如需回滚
python scripts/migrations/entitlement/rollback_all.py --confirm
```

---

**END OF DOCUMENT**
