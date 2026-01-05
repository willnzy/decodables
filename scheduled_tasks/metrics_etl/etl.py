"""
Metrics ETL - Extract, Transform, Load operations

@module scheduled_tasks.metrics_etl.etl
@version 3.24
"""

from datetime import datetime, timedelta, timezone, date
from typing import Dict, Optional

from .utils import get_supabase, log
from .calculator import MetricsCalculator


class MetricsETL:
    """ETL pipeline for SaaS metrics."""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.calculator = MetricsCalculator()
    
    def run_daily(self, target_date: Optional[date] = None):
        """Run daily ETL for all metrics."""
        if target_date is None:
            target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        
        log(f"📊 Starting daily ETL for {target_date}")
        
        try:
            # Calculate all metrics
            metrics = {
                "date": target_date.isoformat(),
                "dau": self.calculator.calculate_dau(target_date),
                "wau": self.calculator.calculate_wau(target_date),
                "mau": self.calculator.calculate_mau(target_date),
                "new_users": self.calculator.calculate_new_users(target_date),
                "mrr": self.calculator.calculate_mrr(target_date),
                "arpu": self.calculator.calculate_arpu(target_date),
                "retention": self.calculator.calculate_retention(target_date - timedelta(days=7)),
                "conversion": self.calculator.calculate_conversion_rate(target_date),
            }
            
            # Store metrics
            self._store_metrics("daily_metrics", target_date, metrics)
            
            log(f"✅ Daily ETL complete: DAU={metrics['dau']}, MRR=${metrics['mrr']['total']}")
            
            return metrics
            
        except Exception as e:
            log(f"❌ Daily ETL failed: {e}", "ERROR")
            return None
    
    def run_hourly(self):
        """Run hourly quick metrics."""
        log("⏰ Starting hourly ETL")
        
        try:
            now = datetime.now(timezone.utc)
            hour_start = now.replace(minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)
            
            # Quick activity count
            result = self.supabase.table("analytics_events").select("id", count="exact")\
                .gte("created_at", hour_start.isoformat())\
                .lt("created_at", hour_end.isoformat()).execute()
            
            metrics = {
                "hour": hour_start.isoformat(),
                "events": result.count or 0,
            }
            
            self._store_hourly_metrics(metrics)
            
            log(f"✅ Hourly ETL complete: {metrics['events']} events")
            
            return metrics
            
        except Exception as e:
            log(f"❌ Hourly ETL failed: {e}", "ERROR")
            return None
    
    def backfill(self, days: int):
        """Backfill metrics for specified number of days."""
        log(f"🔄 Starting backfill for {days} days")
        
        today = datetime.now(timezone.utc).date()
        
        for i in range(days, 0, -1):
            target = today - timedelta(days=i)
            self.run_daily(target)
        
        log(f"✅ Backfill complete for {days} days")
    
    def _store_metrics(self, metric_type: str, target_date: date, data: Dict):
        """Store metrics to database."""
        try:
            self.supabase.table("aggregated_stats").upsert({
                "date": target_date.isoformat(),
                "stat_type": metric_type,
                "data": data,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }, on_conflict="date,stat_type").execute()
        except Exception as e:
            log(f"⚠️ Failed to store metrics: {e}", "WARNING")
    
    def _store_hourly_metrics(self, data: Dict):
        """Store hourly metrics."""
        try:
            self.supabase.table("hourly_metrics").insert(data).execute()
        except Exception as e:
            log(f"⚠️ Failed to store hourly metrics: {e}", "WARNING")


def run_daily_etl():
    """Run daily ETL."""
    etl = MetricsETL()
    return etl.run_daily()


def run_hourly_etl():
    """Run hourly ETL."""
    etl = MetricsETL()
    return etl.run_hourly()


def backfill_metrics(days: int):
    """Backfill metrics."""
    etl = MetricsETL()
    etl.backfill(days)
