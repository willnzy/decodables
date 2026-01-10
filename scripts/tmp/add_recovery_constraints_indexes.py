#!/usr/bin/env python3
"""
添加软删除恢复期约束和索引

目标:
1. 为缺少 recovery_expires_at 的表添加该字段
2. 为所有 22 张软删除表添加 CHECK 约束
3. 为所有 22 张软删除表添加条件索引

Phase 2 表 (14张): profiles, projects, project_versions, assets, marketplace_listings,
                  asset_categories, system_assets, notifications, campaign_participations,
                  campaign_dismissals, onboarding_steps, user_onboarding_progress,
                  referrals, credit_transactions

Phase 3.1 表 (8张): marketplace_favorites, marketplace_reviews, campaigns, daily_themes,
                     holidays, asset_prompt_templates, support_tickets, support_replies
"""

import re
from pathlib import Path

# 定义需要处理的表
PHASE2_TABLES = [
    'profiles', 'projects', 'project_versions', 'assets', 'marketplace_listings',
    'asset_categories', 'system_assets', 'notifications', 'campaign_participations',
    'campaign_dismissals', 'onboarding_steps', 'user_onboarding_progress',
    'referrals', 'credit_transactions'
]

PHASE31_TABLES = [
    'marketplace_favorites', 'marketplace_reviews', 'campaigns', 'daily_themes',
    'holidays', 'asset_prompt_templates', 'support_tickets', 'support_replies'
]

ALL_TABLES = PHASE2_TABLES + PHASE31_TABLES  # 22 张表

DDL_FILE = Path(__file__).parent.parent.parent / 'migrations/v2/refactored_schema_v2.sql'

def add_recovery_field_to_table(content: str, table_name: str) -> tuple[str, bool]:
    """为表添加 recovery_expires_at 字段"""

    # 查找表定义
    table_pattern = rf'CREATE TABLE {table_name}\s*\('
    match = re.search(table_pattern, content, re.IGNORECASE)
    if not match:
        print(f"  ⚠️  未找到表 {table_name}")
        return content, False

    # 检查是否已有 recovery_expires_at 字段
    table_start = match.start()
    # 找到表结束位置 (下一个 );)
    table_end_match = re.search(r'\);', content[table_start:])
    if not table_end_match:
        print(f"  ⚠️  未找到表 {table_name} 的结束标记")
        return content, False

    table_end = table_start + table_end_match.end()
    table_def = content[table_start:table_end]

    if 'recovery_expires_at' in table_def:
        print(f"  ✓ {table_name} 已有 recovery_expires_at 字段")
        return content, False

    # 查找 deleted_at 字段位置
    deleted_at_pattern = r'(\s+deleted_at\s+TIMESTAMPTZ.*?)(\n)'
    match = re.search(deleted_at_pattern, table_def)
    if not match:
        print(f"  ⚠️  {table_name} 未找到 deleted_at 字段")
        return content, False

    # 在 deleted_at 后面添加 recovery_expires_at
    deleted_at_line = match.group(1)
    # 检查是否有逗号
    if deleted_at_line.rstrip().endswith(','):
        new_field = '\n    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录'
    else:
        # 需要在 deleted_at 后面加逗号
        deleted_at_line = deleted_at_line.rstrip() + ','
        new_field = '\n    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录'
        content = content.replace(match.group(1), deleted_at_line)

    # 插入新字段
    insert_pos = table_start + match.end()
    content = content[:insert_pos] + new_field + content[insert_pos:]

    print(f"  ✅ {table_name} 添加 recovery_expires_at 字段")
    return content, True

def add_constraint_to_table(content: str, table_name: str) -> tuple[str, bool]:
    """为表添加 recovery_expires_at CHECK 约束"""

    # 查找表定义
    table_pattern = rf'CREATE TABLE {table_name}\s*\('
    match = re.search(table_pattern, content, re.IGNORECASE)
    if not match:
        print(f"  ⚠️  未找到表 {table_name}")
        return content, False

    table_start = match.start()
    table_end_match = re.search(r'\);', content[table_start:])
    if not table_end_match:
        print(f"  ⚠️  未找到表 {table_name} 的结束标记")
        return content, False

    table_end = table_start + table_end_match.end()
    table_def = content[table_start:table_end]

    # 检查是否已有 recovery_expires_at 约束
    constraint_name = f'chk_{table_name}_recovery_expires_at_consistency'
    if constraint_name in table_def:
        print(f"  ✓ {table_name} 已有 recovery_expires_at 约束")
        return content, False

    # 查找插入位置 (在最后一个 CONSTRAINT 之后，或在 ); 之前)
    # 先尝试找最后一个 CONSTRAINT
    constraint_pattern = r'(CONSTRAINT\s+chk_\w+[^)]+\))'
    constraints = list(re.finditer(constraint_pattern, table_def))

    if constraints:
        # 在最后一个约束之后插入
        last_constraint = constraints[-1]
        insert_pos = table_start + last_constraint.end()

        # 添加逗号和新约束
        new_constraint = ',\n    CONSTRAINT ' + constraint_name + '\n    CHECK (\n        recovery_expires_at IS NULL OR\n        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)\n    )'
        content = content[:insert_pos] + new_constraint + content[insert_pos:]

    else:
        # 没有其他约束,在 ); 之前插入
        insert_pos = table_end - 2  # 在 ); 之前
        new_constraint = ',\n\n    CONSTRAINT ' + constraint_name + '\n    CHECK (\n        recovery_expires_at IS NULL OR\n        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)\n    )\n'
        content = content[:insert_pos] + new_constraint + content[insert_pos:]

    print(f"  ✅ {table_name} 添加 recovery_expires_at 约束")
    return content, True

def add_index_after_table(content: str, table_name: str) -> tuple[str, bool]:
    """为表添加可恢复记录条件索引 (在 CREATE TABLE 之后)"""

    # 查找表定义结束位置
    table_pattern = rf'CREATE TABLE {table_name}\s*\('
    match = re.search(table_pattern, content, re.IGNORECASE)
    if not match:
        print(f"  ⚠️  未找到表 {table_name}")
        return content, False

    table_start = match.start()
    table_end_match = re.search(r'\);', content[table_start:])
    if not table_end_match:
        print(f"  ⚠️  未找到表 {table_name} 的结束标记")
        return content, False

    table_end_pos = table_start + table_end_match.end()

    # 检查是否已有该索引
    index_name = f'idx_{table_name}_deleted_recoverable'
    # 搜索表定义之后的 200 行
    search_area = content[table_end_pos:table_end_pos + 2000]
    if index_name in search_area:
        print(f"  ✓ {table_name} 已有可恢复记录索引")
        return content, False

    # 查找下一个 CREATE TABLE 或 CREATE INDEX 的位置
    next_create_match = re.search(r'\n(CREATE TABLE|CREATE INDEX|CREATE UNIQUE INDEX)', content[table_end_pos + 10:])
    if next_create_match:
        insert_pos = table_end_pos + 10 + next_create_match.start()
    else:
        insert_pos = table_end_pos + 10

    # 构建索引 SQL
    index_sql = f"""
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX {index_name}
ON {table_name}(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX {index_name} IS '可恢复删除记录索引 - 只包含未过期的删除记录';

"""

    content = content[:insert_pos] + index_sql + content[insert_pos:]

    print(f"  ✅ {table_name} 添加可恢复记录索引")
    return content, True

def main():
    print("=" * 80)
    print("添加软删除恢复期约束和索引")
    print("=" * 80)

    # 读取 DDL 文件
    print(f"\n📂 读取文件: {DDL_FILE}")
    content = DDL_FILE.read_text(encoding='utf-8')

    modified = False

    # Step 1: 添加 recovery_expires_at 字段
    print("\n" + "=" * 80)
    print("Step 1: 添加 recovery_expires_at 字段到缺失的表")
    print("=" * 80)
    for table in ALL_TABLES:
        content, changed = add_recovery_field_to_table(content, table)
        if changed:
            modified = True

    # Step 2: 添加 CHECK 约束
    print("\n" + "=" * 80)
    print("Step 2: 添加 recovery_expires_at CHECK 约束")
    print("=" * 80)
    for table in ALL_TABLES:
        content, changed = add_constraint_to_table(content, table)
        if changed:
            modified = True

    # Step 3: 添加条件索引
    print("\n" + "=" * 80)
    print("Step 3: 添加可恢复记录条件索引")
    print("=" * 80)
    for table in ALL_TABLES:
        content, changed = add_index_after_table(content, table)
        if changed:
            modified = True

    # 保存修改
    if modified:
        print("\n" + "=" * 80)
        print("💾 保存修改到文件")
        print("=" * 80)
        DDL_FILE.write_text(content, encoding='utf-8')
        print(f"  ✅ 已保存: {DDL_FILE}")
    else:
        print("\n" + "=" * 80)
        print("✓ 无需修改 (所有字段/约束/索引已存在)")
        print("=" * 80)

    print("\n" + "=" * 80)
    print("✅ 完成!")
    print("=" * 80)

if __name__ == '__main__':
    main()
