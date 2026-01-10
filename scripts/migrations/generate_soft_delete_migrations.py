#!/usr/bin/env python3
"""
为剩余表生成软删除迁移 SQL

使用方法:
    python scripts/migrations/generate_soft_delete_migrations.py --batch 1
    python scripts/migrations/generate_soft_delete_migrations.py --batch 2
    python scripts/migrations/generate_soft_delete_migrations.py --batch 3
    python scripts/migrations/generate_soft_delete_migrations.py --all
"""

import argparse
from pathlib import Path
from datetime import datetime

# 定义需要添加软删除的表 (按批次分组)

# Batch 1: P0 核心业务表 (10张)
BATCH1_TABLES = [
    ('users', 'user_id'),  # (表名, 用户ID字段名)
    ('sessions', 'user_id'),
    ('api_keys', 'user_id'),
    ('webhooks', 'user_id'),
    ('integrations', 'user_id'),
    ('workspace_members', 'user_id'),
    ('team_members', 'user_id'),
    ('project_collaborators', 'user_id'),
    ('asset_versions', 'user_id'),
    ('marketplace_orders', 'buyer_id'),  # 注意: 使用 buyer_id
]

# Batch 2: P1 辅助功能表 (15张)
BATCH2_TABLES = [
    ('comments', 'user_id'),
    ('likes', 'user_id'),
    ('shares', 'user_id'),
    ('bookmarks', 'user_id'),
    ('tags', 'user_id'),
    ('categories', None),  # 无 user_id (全局分类)
    ('collections', 'user_id'),
    ('playlists', 'user_id'),
    ('templates', 'user_id'),
    ('presets', 'user_id'),
    ('filters', 'user_id'),
    ('effects', None),  # 无 user_id (系统特效)
    ('animations', None),  # 无 user_id (系统动画)
    ('transitions', None),  # 无 user_id (系统转场)
    ('stickers', None),  # 无 user_id (系统贴纸)
]

# Batch 3: P2 统计分析表 (13张)
BATCH3_TABLES = [
    ('analytics_events', 'user_id'),
    ('user_activities', 'user_id'),
    ('feature_usage', 'user_id'),
    ('error_logs', 'user_id'),
    ('audit_logs', 'user_id'),
    ('metrics', None),  # 无 user_id (系统指标)
    ('reports', 'user_id'),
    ('exports', 'user_id'),
    ('imports', 'user_id'),
    ('backups', None),  # 无 user_id (系统备份)
    ('jobs', None),  # 无 user_id (任务队列)
    ('schedules', None),  # 无 user_id (定时任务)
    ('webhooks_logs', None'),  # 无 user_id (系统日志)
]


def generate_soft_delete_migration(table_name: str, user_id_field: str = None) -> str:
    """
    生成软删除迁移 SQL.

    Args:
        table_name: 表名
        user_id_field: 用户ID字段名 (如果有)

    Returns:
        完整的迁移 SQL
    """

    # 基础字段添加
    sql = f"""-- ============================================================================
-- 为 {table_name} 添加软删除支持
-- ============================================================================

-- 1. 添加软删除字段
ALTER TABLE {table_name}
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

COMMENT ON COLUMN {table_name}.is_deleted IS '软删除标记: true=已删除, false=正常';
COMMENT ON COLUMN {table_name}.deleted_at IS '删除时间戳';
COMMENT ON COLUMN {table_name}.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 2. 添加约束
ALTER TABLE {table_name}
ADD CONSTRAINT IF NOT EXISTS chk_{table_name}_deleted_at_consistency
CHECK (
    (is_deleted = false AND deleted_at IS NULL) OR
    (is_deleted = true AND deleted_at IS NOT NULL)
);

ALTER TABLE {table_name}
ADD CONSTRAINT IF NOT EXISTS chk_{table_name}_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

-- 3. 添加索引
"""

    # 如果有 user_id 字段,添加用户相关索引
    if user_id_field:
        sql += f"""-- 活跃记录索引 (用户的未删除记录)
CREATE INDEX IF NOT EXISTS idx_{table_name}_active
ON {table_name}({user_id_field}, created_at DESC)
WHERE is_deleted = FALSE;

-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX IF NOT EXISTS idx_{table_name}_deleted_recoverable
ON {table_name}({user_id_field}, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_{table_name}_active IS '活跃记录索引 - 只包含未删除的记录';
COMMENT ON INDEX idx_{table_name}_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';
"""
    else:
        # 无 user_id,只添加通用索引
        sql += f"""-- 活跃记录索引
CREATE INDEX IF NOT EXISTS idx_{table_name}_active
ON {table_name}(created_at DESC)
WHERE is_deleted = FALSE;

COMMENT ON INDEX idx_{table_name}_active IS '活跃记录索引 - 只包含未删除的记录';
"""

    # 添加触发器
    sql += f"""
-- 4. 添加自动更新 deleted_at 的触发器
DROP TRIGGER IF EXISTS trg_{table_name}_set_deleted_at ON {table_name};
CREATE TRIGGER trg_{table_name}_set_deleted_at
    BEFORE INSERT OR UPDATE ON {table_name}
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

COMMENT ON TRIGGER trg_{table_name}_set_deleted_at ON {table_name} IS '软删除时自动设置 deleted_at 时间戳';

-- 5. 迁移现有数据 (如果需要)
-- 如果有标记为已删除但缺少 deleted_at 的记录,补充时间戳
UPDATE {table_name}
SET deleted_at = updated_at,
    recovery_expires_at = updated_at + INTERVAL '30 days'
WHERE is_deleted = true
  AND deleted_at IS NULL;

"""

    return sql


def generate_batch_migration(batch_number: int) -> str:
    """
    生成批次迁移文件.

    Args:
        batch_number: 批次号 (1/2/3)

    Returns:
        完整的迁移 SQL 文件内容
    """

    if batch_number == 1:
        tables = BATCH1_TABLES
        batch_name = "Batch 1 - 核心业务表"
    elif batch_number == 2:
        tables = BATCH2_TABLES
        batch_name = "Batch 2 - 辅助功能表"
    elif batch_number == 3:
        tables = BATCH3_TABLES
        batch_name = "Batch 3 - 统计分析表"
    else:
        raise ValueError(f"Invalid batch number: {batch_number}")

    sql = f"""-- ============================================================================
-- 软删除支持扩展 - {batch_name}
-- ============================================================================
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 批次: Batch {batch_number}
-- 表数量: {len(tables)} 张
--
-- 重要提示:
-- ⚠️ 执行前请先备份数据库!
-- ⚠️ 建议在非高峰时段执行
-- ⚠️ 大表可能需要较长时间
-- ============================================================================

BEGIN;
SET client_min_messages = WARNING;

"""

    for table_name, user_id_field in tables:
        sql += generate_soft_delete_migration(table_name, user_id_field)
        sql += "\n"

    sql += f"""
-- ============================================================================
-- 迁移完成 - {batch_name}
-- ============================================================================
COMMIT;

-- 验证迁移结果
DO $$
DECLARE
    table_name TEXT;
    missing_columns TEXT[];
BEGIN
"""

    for table_name, _ in tables:
        sql += f"""
    -- 检查 {table_name}
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = '{table_name}'
        AND column_name = 'recovery_expires_at'
    ) THEN
        missing_columns := array_append(missing_columns, '{table_name}');
    END IF;
"""

    sql += """
    IF array_length(missing_columns, 1) > 0 THEN
        RAISE EXCEPTION '迁移失败! 以下表缺少字段: %', missing_columns;
    ELSE
        RAISE NOTICE '✅ 迁移成功! 所有表已添加软删除支持';
    END IF;
END $$;
"""

    return sql


def main():
    parser = argparse.ArgumentParser(description='生成软删除迁移 SQL')
    parser.add_argument(
        '--batch',
        type=int,
        choices=[1, 2, 3],
        help='生成指定批次的迁移 SQL (1/2/3)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='生成所有批次的迁移 SQL'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='migrations/v3',
        help='输出目录 (默认: migrations/v3)'
    )

    args = parser.parse_args()

    if not args.batch and not args.all:
        parser.error('必须指定 --batch N 或 --all')

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    batches_to_generate = [args.batch] if args.batch else [1, 2, 3]

    for batch_num in batches_to_generate:
        sql = generate_batch_migration(batch_num)

        output_file = output_dir / f"00{batch_num + 2}_add_soft_delete_batch{batch_num}.sql"

        output_file.write_text(sql, encoding='utf-8')

        table_count = len(BATCH1_TABLES if batch_num == 1 else BATCH2_TABLES if batch_num == 2 else BATCH3_TABLES)

        print(f"✅ 生成 Batch {batch_num}: {output_file}")
        print(f"   包含 {table_count} 张表")

    print(f"\n✅ 迁移 SQL 生成完成!")
    print(f"输出目录: {output_dir.absolute()}")


if __name__ == '__main__':
    main()
