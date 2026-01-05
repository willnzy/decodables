#!/usr/bin/env python3
"""
A/B Experiment Data Aggregation Task
A/B 实验数据聚合任务

Features:
- 每小时聚合实验数据到 experiment_results 表
- 自动启动/结束到期的实验
- 计算并缓存统计显著性

Usage:
    python scheduled_tasks/experiment_aggregator.py              # Run all tasks
    python scheduled_tasks/experiment_aggregator.py --aggregate  # Aggregation only
    python scheduled_tasks/experiment_aggregator.py --schedule   # Scheduling only

@module scheduled_tasks/experiment_aggregator
"""

import os
import sys
import argparse
from datetime import datetime, timedelta, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import supabase client
from services.db_service import supabase

if supabase is None:
    print("❌ Error: Supabase client not initialized.")
    sys.exit(1)


def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


# ==========================================
# Experiment Result Aggregation
# ==========================================

def aggregate_experiment_results():
    """
    聚合实验结果数据
    
    从 experiment_assignments 表聚合数据到 experiment_results 表
    按小时聚合曝光和转化数据
    """
    log("📊 Starting experiment results aggregation...")
    
    now = datetime.now(timezone.utc)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    
    # 获取所有运行中的实验
    experiments = supabase.table("experiments").select("*")\
        .eq("status", "running").execute()
    
    if not experiments.data:
        log("   No running experiments to aggregate")
        return
    
    aggregated_count = 0
    
    for experiment in experiments.data:
        experiment_id = experiment.get("id")
        experiment_key = experiment.get("experiment_key")
        variants = experiment.get("variants", [])
        
        log(f"   Processing experiment: {experiment_key}")
        
        # 为每个变体聚合数据
        for variant in variants:
            variant_key = variant.get("key")
            
            try:
                # 获取该变体在当前小时的参与人数（被分配的）
                participants = supabase.table("experiment_assignments").select("id", count="exact")\
                    .eq("experiment_id", experiment_id)\
                    .eq("variant_key", variant_key)\
                    .gte("assigned_at", current_hour.isoformat())\
                    .lt("assigned_at", (current_hour + timedelta(hours=1)).isoformat()).execute()
                
                hourly_participants = participants.count or 0
                
                # 获取该变体在当前小时的曝光数
                exposures = supabase.table("experiment_assignments").select("id", count="exact")\
                    .eq("experiment_id", experiment_id)\
                    .eq("variant_key", variant_key)\
                    .eq("exposed", True)\
                    .gte("exposed_at", current_hour.isoformat())\
                    .lt("exposed_at", (current_hour + timedelta(hours=1)).isoformat()).execute()
                
                hourly_exposures = exposures.count or 0
                
                # 获取该变体在当前小时的转化数
                conversions = supabase.table("experiment_assignments").select("id", count="exact")\
                    .eq("experiment_id", experiment_id)\
                    .eq("variant_key", variant_key)\
                    .eq("converted", True)\
                    .gte("converted_at", current_hour.isoformat())\
                    .lt("converted_at", (current_hour + timedelta(hours=1)).isoformat()).execute()
                
                hourly_conversions = conversions.count or 0
                
                # 获取该变体的累计数据
                total_exposures_result = supabase.table("experiment_assignments").select("id", count="exact")\
                    .eq("experiment_id", experiment_id)\
                    .eq("variant_key", variant_key)\
                    .eq("exposed", True).execute()
                
                total_exposures = total_exposures_result.count or 0
                
                total_conversions_result = supabase.table("experiment_assignments").select("id", count="exact")\
                    .eq("experiment_id", experiment_id)\
                    .eq("variant_key", variant_key)\
                    .eq("converted", True).execute()
                
                total_conversions = total_conversions_result.count or 0
                
                # 计算转化率
                conversion_rate = (total_conversions / total_exposures * 100) if total_exposures > 0 else 0
                
                # 计算累计转化价值
                conversion_value_result = supabase.table("experiment_assignments").select("conversion_value")\
                    .eq("experiment_id", experiment_id)\
                    .eq("variant_key", variant_key)\
                    .eq("converted", True).execute()
                
                total_conversion_value = sum(
                    r.get("conversion_value", 0) or 0 
                    for r in conversion_value_result.data or []
                )
                
                # Upsert 到 experiment_results 表
                # 表使用 date + hour 作为时间粒度
                result_data = {
                    "experiment_id": experiment_id,
                    "variant_key": variant_key,
                    "date": current_hour.strftime("%Y-%m-%d"),
                    "hour": current_hour.hour,
                    "participants": hourly_participants,
                    "exposures": hourly_exposures,
                    "conversions": hourly_conversions,
                    "conversion_rate": round(conversion_rate, 4),
                    "metrics_data": {
                        "total_exposures": total_exposures,
                        "total_conversions": total_conversions,
                        "total_conversion_value": total_conversion_value,
                    },
                    "updated_at": now.isoformat(),
                }
                
                supabase.table("experiment_results").upsert(
                    result_data,
                    on_conflict="experiment_id,variant_key,date,hour"
                ).execute()
                
                aggregated_count += 1
                
            except Exception as e:
                log(f"   ❌ Error aggregating {experiment_key}/{variant_key}: {e}")
    
    log(f"✅ Experiment aggregation complete: {aggregated_count} variant results updated")


def aggregate_experiment_daily_summary():
    """
    生成实验的每日汇总数据
    
    用于历史趋势图表展示
    """
    log("📈 Starting experiment daily summary aggregation...")
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 获取所有非草稿状态的实验
    experiments = supabase.table("experiments").select("*")\
        .in_("status", ["running", "paused", "completed"]).execute()
    
    if not experiments.data:
        log("   No experiments to summarize")
        return
    
    for experiment in experiments.data:
        experiment_id = experiment.get("id")
        experiment_key = experiment.get("experiment_key")
        
        try:
            # 聚合过去30天的每日数据
            daily_data = []
            
            for days_ago in range(30):
                date = today - timedelta(days=days_ago)
                date_str = date.strftime("%Y-%m-%d")
                
                # 从 experiment_results 获取该天的数据
                # 表使用 date 字段
                results = supabase.table("experiment_results").select("*")\
                    .eq("experiment_id", experiment_id)\
                    .eq("date", date_str).execute()
                
                # 按变体聚合
                variant_data = {}
                for result in results.data or []:
                    variant_key = result.get("variant_key")
                    if variant_key not in variant_data:
                        variant_data[variant_key] = {
                            "exposures": 0,
                            "conversions": 0,
                        }
                    variant_data[variant_key]["exposures"] += result.get("exposures", 0)
                    variant_data[variant_key]["conversions"] += result.get("conversions", 0)
                
                daily_data.append({
                    "date": date_str,
                    "variants": variant_data,
                })
            
            # 反转顺序（从旧到新）
            daily_data.reverse()
            
            # 保存到 aggregated_stats
            stats_data = {
                "date": now.strftime("%Y-%m-%d"),
                "stat_type": f"experiment_trend_{experiment_key}",
                "data": {
                    "experiment_key": experiment_key,
                    "experiment_id": experiment_id,
                    "daily_data": daily_data,
                },
                "updated_at": now.isoformat(),
            }
            
            supabase.table("aggregated_stats").upsert(
                stats_data,
                on_conflict="date,stat_type"
            ).execute()
            
        except Exception as e:
            log(f"   ❌ Error summarizing {experiment_key}: {e}")
    
    log("✅ Experiment daily summary complete")


# ==========================================
# Experiment Auto-Scheduling
# ==========================================

def check_experiment_schedules():
    """
    检查并执行实验自动调度
    
    - 自动启动到达 start_at 时间的实验
    - 自动结束到达 end_at 时间的实验
    """
    log("⏰ Checking experiment schedules...")
    
    now = datetime.now(timezone.utc)
    
    # 1. 自动启动到期的实验
    pending_start = supabase.table("experiments").select("*")\
        .eq("status", "draft")\
        .not_.is_("start_at", "null")\
        .lte("start_at", now.isoformat()).execute()
    
    for experiment in pending_start.data or []:
        experiment_key = experiment.get("experiment_key")
        try:
            supabase.table("experiments").update({
                "status": "running",
                "updated_at": now.isoformat(),
            }).eq("experiment_key", experiment_key).execute()
            
            log(f"   ✅ Auto-started experiment: {experiment_key}")
        except Exception as e:
            log(f"   ❌ Failed to auto-start {experiment_key}: {e}")
    
    # 2. 自动结束到期的实验
    pending_end = supabase.table("experiments").select("*")\
        .eq("status", "running")\
        .not_.is_("end_at", "null")\
        .lte("end_at", now.isoformat()).execute()
    
    for experiment in pending_end.data or []:
        experiment_key = experiment.get("experiment_key")
        try:
            supabase.table("experiments").update({
                "status": "completed",
                "updated_at": now.isoformat(),
            }).eq("experiment_key", experiment_key).execute()
            
            log(f"   ✅ Auto-completed experiment: {experiment_key}")
        except Exception as e:
            log(f"   ❌ Failed to auto-complete {experiment_key}: {e}")
    
    started_count = len(pending_start.data or [])
    completed_count = len(pending_end.data or [])
    
    log(f"✅ Schedule check complete: {started_count} started, {completed_count} completed")


def cleanup_old_assignments():
    """
    清理过期的实验分配数据
    
    对于已完成超过90天的实验，删除详细分配记录
    保留聚合数据用于历史分析
    """
    log("🧹 Cleaning up old experiment assignments...")
    
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=90)
    
    # 获取已完成超过90天的实验
    old_experiments = supabase.table("experiments").select("id, experiment_key")\
        .eq("status", "completed")\
        .lt("end_at", cutoff_date.isoformat()).execute()
    
    if not old_experiments.data:
        log("   No old experiments to clean up")
        return
    
    deleted_count = 0
    
    for experiment in old_experiments.data or []:
        experiment_id = experiment.get("id")
        experiment_key = experiment.get("experiment_key")
        
        try:
            # 删除分配记录（保留聚合数据）
            result = supabase.table("experiment_assignments").delete()\
                .eq("experiment_id", experiment_id).execute()
            
            deleted_count += len(result.data or [])
            log(f"   Cleaned up assignments for: {experiment_key}")
        except Exception as e:
            log(f"   ❌ Failed to cleanup {experiment_key}: {e}")
    
    log(f"✅ Cleanup complete: {deleted_count} assignment records removed")


# ==========================================
# Task Runners
# ==========================================

def run_hourly_experiment_tasks():
    """每小时运行的实验任务"""
    log("🕐 Running hourly experiment tasks...")
    
    check_experiment_schedules()
    aggregate_experiment_results()
    
    log("✅ Hourly experiment tasks complete")


def run_daily_experiment_tasks():
    """每日运行的实验任务"""
    log("📅 Running daily experiment tasks...")
    
    aggregate_experiment_daily_summary()
    cleanup_old_assignments()
    
    log("✅ Daily experiment tasks complete")


def run_all_experiment_tasks():
    """运行所有实验任务"""
    log("🚀 Running all experiment tasks...")
    
    run_hourly_experiment_tasks()
    run_daily_experiment_tasks()
    
    log("🎉 All experiment tasks complete!")


def main():
    parser = argparse.ArgumentParser(description="Run A/B experiment aggregation tasks")
    parser.add_argument("--aggregate", action="store_true", help="Run aggregation only")
    parser.add_argument("--schedule", action="store_true", help="Run scheduling only")
    parser.add_argument("--daily", action="store_true", help="Run daily tasks only")
    parser.add_argument("--hourly", action="store_true", help="Run hourly tasks only")
    args = parser.parse_args()
    
    try:
        if args.aggregate:
            aggregate_experiment_results()
            aggregate_experiment_daily_summary()
        elif args.schedule:
            check_experiment_schedules()
        elif args.daily:
            run_daily_experiment_tasks()
        elif args.hourly:
            run_hourly_experiment_tasks()
        else:
            run_all_experiment_tasks()
    except Exception as e:
        log(f"❌ Task failed: {e}")
        raise


if __name__ == "__main__":
    main()
