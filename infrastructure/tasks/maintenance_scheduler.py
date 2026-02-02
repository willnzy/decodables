"""
维护任务调度服务

定期执行数据库清理和优化任务，防止日志表无限增长。

参考业界实践：
- Stripe: 自动日志轮转和归档
- AWS CloudWatch: 日志保留策略
- Google Cloud Logging: 自动过期策略

v3.31: 支持传入 db client 参数，解决 BackgroundScheduler 中
       "Event loop is closed" 问题。详见 docs/main/backend-architecture.md 1.3.1.3
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MaintenanceScheduler:
    """维护任务调度器"""
    
    @staticmethod
    async def cleanup_user_creation_logs(
        retention_days: int = 90,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        清理旧的用户创建日志

        Args:
            retention_days: 保留天数（默认 90 天）
            db: 可选的数据库客户端（用于 BackgroundScheduler 场景）

        Returns:
            清理结果统计
        """
        try:
            if db is None:
                from core.database import get_async_db_client
                db = await get_async_db_client()
            
            result = await db.rpc('cleanup_old_user_creation_logs', {
                'p_retention_days': retention_days
            }).execute()
            
            deleted_count = result.data if result.data else 0
            
            logger.info(
                f"✅ Cleaned up {deleted_count} old user creation logs (retention: {retention_days} days)",
                extra={
                    "task": "cleanup_user_creation_logs",
                    "deleted_count": deleted_count,
                    "retention_days": retention_days,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "retention_days": retention_days,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(
                f"❌ Failed to cleanup user creation logs: {e}",
                extra={
                    "task": "cleanup_user_creation_logs",
                    "error": str(e)
                }
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    
    @staticmethod
    async def cleanup_error_logs(
        retention_days: int = 30,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        清理旧的错误日志

        Args:
            retention_days: 保留天数（默认 30 天）
            db: 可选的数据库客户端（用于 BackgroundScheduler 场景）

        Returns:
            清理结果统计
        """
        try:
            if db is None:
                from core.database import get_async_db_client
                db = await get_async_db_client()
            
            result = await db.rpc('cleanup_old_error_logs', {
                'p_retention_days': retention_days
            }).execute()
            
            deleted_count = result.data if result.data else 0
            
            logger.info(
                f"✅ Cleaned up {deleted_count} old error logs (retention: {retention_days} days)",
                extra={
                    "task": "cleanup_error_logs",
                    "deleted_count": deleted_count,
                    "retention_days": retention_days
                }
            )
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "retention_days": retention_days
            }
            
        except Exception as e:
            logger.error(
                f"❌ Failed to cleanup error logs: {e}",
                extra={
                    "task": "cleanup_error_logs",
                    "error": str(e)
                }
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    
    @staticmethod
    async def cleanup_activity_logs(
        retention_days: int = 180,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        清理旧的活动日志

        Args:
            retention_days: 保留天数（默认 180 天）
            db: 可选的数据库客户端（用于 BackgroundScheduler 场景）

        Returns:
            清理结果统计
        """
        try:
            if db is None:
                from core.database import get_async_db_client
                db = await get_async_db_client()
            
            result = await db.rpc('cleanup_old_activity_logs', {
                'p_retention_days': retention_days
            }).execute()
            
            deleted_count = result.data if result.data else 0
            
            logger.info(
                f"✅ Cleaned up {deleted_count} old activity logs (retention: {retention_days} days)",
                extra={
                    "task": "cleanup_activity_logs",
                    "deleted_count": deleted_count,
                    "retention_days": retention_days
                }
            )
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "retention_days": retention_days
            }
            
        except Exception as e:
            logger.error(
                f"❌ Failed to cleanup activity logs: {e}",
                extra={
                    "task": "cleanup_activity_logs",
                    "error": str(e)
                }
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    
    @staticmethod
    async def get_log_tables_stats(db: Optional[Any] = None) -> Dict[str, Any]:
        """
        获取日志表统计信息

        Args:
            db: 可选的数据库客户端（用于 BackgroundScheduler 场景）

        Returns:
            日志表统计数据
        """
        try:
            if db is None:
                from core.database import get_async_db_client
                db = await get_async_db_client()
            
            result = await db.rpc('get_log_tables_stats').execute()
            
            stats = result.data if result.data else []
            
            return {
                "success": True,
                "stats": stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(
                f"❌ Failed to get log tables stats: {e}",
                extra={
                    "task": "get_log_tables_stats",
                    "error": str(e)
                }
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    
    @staticmethod
    async def cleanup_expired_soft_deletes(db: Optional[Any] = None) -> Dict[str, Any]:
        """
        WS-25 (GROW-01): Purge expired soft-deleted records.

        Calls the cleanup_expired_soft_deletes() RPC which permanently removes
        records where recovery_expires_at has passed (assets, projects, tickets, replies).

        Args:
            db: Optional database client (for BackgroundScheduler context)

        Returns:
            Cleanup result statistics
        """
        try:
            if db is None:
                from core.database import get_async_db_client
                db = await get_async_db_client()

            result = await db.rpc('cleanup_expired_soft_deletes').execute()

            data = result.data if result.data else {}
            total = data.get('total_purged', 0) if isinstance(data, dict) else 0

            logger.info(
                f"✅ Purged {total} expired soft-deleted records",
                extra={
                    "task": "cleanup_expired_soft_deletes",
                    "details": data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

            return {
                "success": True,
                "total_purged": total,
                "details": data,
            }

        except Exception as e:
            logger.error(
                f"❌ Failed to cleanup expired soft-deletes: {e}",
                extra={
                    "task": "cleanup_expired_soft_deletes",
                    "error": str(e)
                }
            )
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def run_daily_maintenance(db: Optional[Any] = None) -> Dict[str, Any]:
        """
        运行每日维护任务

        执行所有日常清理任务并返回汇总结果

        Args:
            db: 可选的数据库客户端（用于 BackgroundScheduler 场景）

        Returns:
            维护任务执行结果汇总
        """
        logger.info("🔧 Starting daily maintenance tasks...")

        results = {}

        # 1. 清理用户创建日志（90 天）
        results['user_creation_logs'] = await MaintenanceScheduler.cleanup_user_creation_logs(90, db=db)

        # 2. 清理错误日志（30 天）
        results['error_logs'] = await MaintenanceScheduler.cleanup_error_logs(30, db=db)

        # 3. WS-25: Purge expired soft-deleted records
        results['expired_soft_deletes'] = await MaintenanceScheduler.cleanup_expired_soft_deletes(db=db)

        # 4. 获取统计信息
        results['stats'] = await MaintenanceScheduler.get_log_tables_stats(db=db)

        # 计算总删除数
        total_deleted = (
            results['user_creation_logs'].get('deleted_count', 0) +
            results['error_logs'].get('deleted_count', 0) +
            results['expired_soft_deletes'].get('total_purged', 0)
        )
        
        logger.info(
            f"✅ Daily maintenance completed. Total deleted: {total_deleted} records",
            extra={
                "task": "daily_maintenance",
                "total_deleted": total_deleted,
                "results": results
            }
        )
        
        # ✅ Sentry: 捕获维护任务完成事件
        try:
            from infrastructure.monitoring.sentry_helpers import SentryMonitoring, SentryLevel
            SentryMonitoring.capture_maintenance_event(
                task_name="daily_maintenance",
                result={
                    "success": True,
                    "total_deleted": total_deleted,
                    "details": results
                },
                level=SentryLevel.INFO
            )
        except Exception:
            pass
        
        return {
            "success": True,
            "total_deleted": total_deleted,
            "details": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    
    @staticmethod
    async def run_weekly_maintenance(db: Optional[Any] = None) -> Dict[str, Any]:
        """
        运行每周维护任务

        包括清理活动日志和数据库优化

        Args:
            db: 可选的数据库客户端（用于 BackgroundScheduler 场景）

        Returns:
            维护任务执行结果汇总
        """
        logger.info("🔧 Starting weekly maintenance tasks...")

        results = {}

        # 1. 清理活动日志（180 天）
        results['activity_logs'] = await MaintenanceScheduler.cleanup_activity_logs(180, db=db)

        # 2. 数据库 VACUUM ANALYZE（通过 RPC）
        # 注意：VACUUM 不能在事务中执行，需要特殊处理
        # 这里只记录日志，实际 VACUUM 需要在 Supabase 后台或 pg_cron 中执行
        logger.info("ℹ️ VACUUM ANALYZE should be run manually or via pg_cron")
        results['vacuum'] = {"success": True, "message": "Requires manual execution"}

        # 3. 获取统计信息
        results['stats'] = await MaintenanceScheduler.get_log_tables_stats(db=db)
        
        total_deleted = results['activity_logs'].get('deleted_count', 0)
        
        logger.info(
            f"✅ Weekly maintenance completed. Total deleted: {total_deleted} records",
            extra={
                "task": "weekly_maintenance",
                "total_deleted": total_deleted,
                "results": results
            }
        )
        
        return {
            "success": True,
            "total_deleted": total_deleted,
            "details": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
