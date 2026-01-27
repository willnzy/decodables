#!/usr/bin/env python3
"""
定期清理已过期的软删除记录

使用场景:
- Cron Job 每天凌晨 2 点运行
- 物理删除已过期 90 天的软删除记录

配置:
- CLEANUP_AFTER_DAYS: 90 (默认, 恢复期过期后再等 90 天才物理删除)
- DRY_RUN: True (测试模式，不实际删除)
- BATCH_SIZE: 100 (每批处理数量)

环境变量:
- SUPABASE_URL: Supabase 项目 URL
- SUPABASE_SERVICE_ROLE_KEY: Service Role Key (有完整权限)
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Tuple
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from infrastructure.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# 配置
CLEANUP_AFTER_DAYS = int(os.getenv("CLEANUP_AFTER_DAYS", "90"))  # 过期 90 天后物理删除
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))

# 需要清理的表 (22 张软删除表)
TABLES_TO_CLEANUP = [
    # Phase 2 (14张)
    'profiles', 'projects', 'project_versions', 'assets',
    'marketplace_listings', 'asset_categories', 'system_assets',
    'notifications', 'campaign_participations', 'campaign_dismissals',
    'onboarding_steps', 'user_onboarding_progress', 'referrals',
    'credit_transactions',
    # Phase 3.1 (8张)
    'marketplace_favorites', 'marketplace_reviews', 'campaigns',
    'daily_themes', 'holidays', 'user_asset_prompt_templates',
    'support_tickets', 'support_replies'
]


async def cleanup_table(table_name: str, cutoff_date: datetime) -> Tuple[int, List[str]]:
    """
    清理单个表的过期记录.

    Args:
        table_name: 表名
        cutoff_date: 截止日期 (早于此日期的记录将被删除)

    Returns:
        Tuple of (deleted_count, error_messages)
    """
    client = get_supabase_client()
    deleted_count = 0
    errors = []

    try:
        logger.info(f"  处理表: {table_name}")

        # 查询需要删除的记录 (分批)
        offset = 0
        while True:
            # 查询一批过期记录
            try:
                result = client.table(table_name) \
                    .select("id") \
                    .eq("is_deleted", True) \
                    .lt("recovery_expires_at", cutoff_date.isoformat()) \
                    .range(offset, offset + BATCH_SIZE - 1) \
                    .execute()
            except Exception as e:
                error_msg = f"查询 {table_name} 失败: {e}"
                logger.error(f"  ❌ {error_msg}")
                errors.append(error_msg)
                break

            if not result.data:
                break

            ids = [row["id"] for row in result.data]

            if DRY_RUN:
                logger.info(f"  [DRY RUN] 将删除 {len(ids)} 条记录")
                deleted_count += len(ids)
            else:
                # 物理删除
                try:
                    delete_result = client.table(table_name) \
                        .delete() \
                        .in_("id", ids) \
                        .execute()

                    deleted_count += len(ids)
                    logger.info(f"  ✅ 已删除 {len(ids)} 条记录")
                except Exception as e:
                    error_msg = f"删除 {table_name} 记录失败: {e}"
                    logger.error(f"  ❌ {error_msg}")
                    errors.append(error_msg)
                    break

            offset += BATCH_SIZE

            # 如果返回数量 < BATCH_SIZE，说明已经没有更多记录
            if len(result.data) < BATCH_SIZE:
                break

        logger.info(f"  ✅ {table_name}: 删除 {deleted_count} 条记录")

    except Exception as e:
        error_msg = f"清理 {table_name} 异常: {e}"
        logger.error(f"  ❌ {error_msg}")
        errors.append(error_msg)

    return deleted_count, errors


async def cleanup_expired_soft_deletes():
    """清理所有表的过期软删除记录"""

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=CLEANUP_AFTER_DAYS)

    logger.info("=" * 80)
    logger.info(f"开始清理过期软删除记录")
    logger.info(f"截止日期: {cutoff_date.isoformat()} (过期 {CLEANUP_AFTER_DAYS} 天)")
    logger.info(f"模式: {'DRY RUN (测试)' if DRY_RUN else 'PRODUCTION (实际删除)'}")
    logger.info(f"批次大小: {BATCH_SIZE}")
    logger.info("=" * 80)

    total_deleted = 0
    all_errors = []

    for table_name in TABLES_TO_CLEANUP:
        logger.info(f"\n处理表: {table_name}")
        try:
            count, errors = await cleanup_table(table_name, cutoff_date)
            total_deleted += count
            all_errors.extend(errors)

            if count > 0:
                logger.info(f"  ✅ {table_name}: 删除 {count} 条记录")
            else:
                logger.info(f"  ℹ️  {table_name}: 无需清理")

        except Exception as e:
            error_msg = f"{table_name}: 失败 - {e}"
            logger.error(f"  ❌ {error_msg}")
            all_errors.append(error_msg)

    logger.info("\n" + "=" * 80)
    logger.info(f"清理完成!")
    logger.info(f"总共删除: {total_deleted} 条记录")
    if all_errors:
        logger.warning(f"错误数量: {len(all_errors)}")
        for error in all_errors:
            logger.warning(f"  - {error}")
    logger.info("=" * 80)

    return total_deleted, all_errors


async def send_cleanup_notification(total_deleted: int, errors: List[str]):
    """
    发送清理结果通知到 Slack/Email.

    Args:
        total_deleted: 删除的总记录数
        errors: 错误消息列表
    """
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not slack_webhook:
        logger.info("未配置 SLACK_WEBHOOK_URL，跳过通知")
        return

    import httpx

    mode = "DRY RUN (测试)" if DRY_RUN else "PRODUCTION (实际删除)"
    status_emoji = "✅" if not errors else "⚠️"

    message = f"""
{status_emoji} 软删除清理报告 ({datetime.now().strftime('%Y-%m-%d %H:%M UTC')})

**总计删除**: {total_deleted} 条记录
**模式**: {mode}
**清理周期**: {CLEANUP_AFTER_DAYS} 天
**错误数量**: {len(errors)}

{('**错误列表**:\n' + '\n'.join([f'- {e}' for e in errors[:10]])) if errors else ''}
"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                slack_webhook,
                json={"text": message},
                timeout=10.0
            )
            if response.status_code == 200:
                logger.info("✅ 清理通知已发送到 Slack")
            else:
                logger.warning(f"⚠️  发送 Slack 通知失败: {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️  发送 Slack 通知异常: {e}")


async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        # 执行清理
        total_deleted, errors = await cleanup_expired_soft_deletes()

        # 发送通知
        await send_cleanup_notification(total_deleted, errors)

        # 返回状态码
        if errors:
            logger.warning(f"\n⚠️  清理完成，但有 {len(errors)} 个错误")
            return 1
        else:
            logger.info(f"\n✅ 清理成功! 删除 {total_deleted} 条记录")
            return 0

    except Exception as e:
        logger.error(f"\n❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
