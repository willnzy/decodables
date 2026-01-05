"""
AI Report Service - Deep Business Insights Generation
======================================================
This module transforms raw data into actionable business intelligence
using unified AI service with expert-level System Prompts.

Features:
- Data preprocessing with MoM/YoY calculations
- Anomaly detection and threshold alerts
- Expert System Prompt with 3-section output
- Structured insights for operations, marketing, and product teams
- Multi-provider support via unified AI service
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

from .db_service import supabase

logger = logging.getLogger(__name__)


# ============================================================
# Data Classes & Constants
# ============================================================

class InsightPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MetricTrend(str, Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class MetricData:
    """Represents a single metric with historical context"""
    name: str
    current_value: float
    previous_value: float  # Previous period (for MoM)
    year_ago_value: Optional[float]  # Same period last year (for YoY)
    unit: str = ""
    is_percentage: bool = False
    higher_is_better: bool = True
    
    @property
    def mom_change(self) -> float:
        """Month-over-Month change percentage"""
        if self.previous_value == 0:
            return 100.0 if self.current_value > 0 else 0.0
        return ((self.current_value - self.previous_value) / self.previous_value) * 100
    
    @property
    def yoy_change(self) -> Optional[float]:
        """Year-over-Year change percentage"""
        if self.year_ago_value is None or self.year_ago_value == 0:
            return None
        return ((self.current_value - self.year_ago_value) / self.year_ago_value) * 100
    
    @property
    def trend(self) -> MetricTrend:
        """Determine trend based on change"""
        if abs(self.mom_change) < 5:
            return MetricTrend.STABLE
        return MetricTrend.INCREASING if self.mom_change > 0 else MetricTrend.DECREASING
    
    @property
    def is_anomaly(self) -> bool:
        """Check if the change is anomalous (>30% change)"""
        return abs(self.mom_change) > 30
    
    def to_prompt_string(self) -> str:
        """Format for inclusion in LLM prompt"""
        status = "🔴 ANOMALY" if self.is_anomaly else ""
        trend_emoji = "📈" if self.mom_change > 5 else "📉" if self.mom_change < -5 else "➡️"
        
        value_str = f"{self.current_value:.1f}{self.unit}" if not self.is_percentage else f"{self.current_value:.1f}%"
        mom_str = f"{self.mom_change:+.1f}%"
        yoy_str = f"{self.yoy_change:+.1f}%" if self.yoy_change is not None else "N/A"
        
        return f"- {self.name}: {value_str} {trend_emoji} (MoM: {mom_str}, YoY: {yoy_str}) {status}"


@dataclass
class UserBehaviorTrend:
    """User behavior data for trend analysis"""
    metric_name: str
    daily_values: List[Tuple[str, float]]  # [(date, value), ...]
    description: str = ""
    
    def to_prompt_string(self) -> str:
        """Format trend data for prompt"""
        if not self.daily_values:
            return f"- {self.metric_name}: No data available"
        
        # Show last 7 days trend
        recent = self.daily_values[-7:] if len(self.daily_values) >= 7 else self.daily_values
        trend_data = ", ".join([f"{d}: {v:.0f}" for d, v in recent])
        return f"- {self.metric_name} (last 7 days): [{trend_data}]"


# ============================================================
# Thresholds for Anomaly Detection
# ============================================================

METRIC_THRESHOLDS = {
    "conversion_rate": {"low": 2.0, "high": 15.0, "critical_low": 1.0},
    "churn_rate": {"low": 0, "high": 5.0, "critical_high": 10.0},
    "retention_d7": {"low": 20.0, "high": 100.0, "critical_low": 10.0},
    "ai_success_rate": {"low": 90.0, "high": 100.0, "critical_low": 80.0},
    "error_rate": {"low": 0, "high": 1.0, "critical_high": 5.0},
    "dau_mau_ratio": {"low": 10.0, "high": 50.0, "critical_low": 5.0},
}


# ============================================================
# Expert System Prompt
# ============================================================

EXPERT_SYSTEM_PROMPT = """你是一位拥有 10 年经验的资深数据分析师和产品战略专家，曾为多家 SaaS 公司提供增长咨询。

你的任务是根据提供的数据报表，提供**深度洞察和可执行建议**。

## 分析原则

1. **不要只描述数据**（例如"销售额上升了 10%"）
2. **要分析"为什么"**（归因分析：是功能改进？营销活动？季节因素？）
3. **要提出"接下来该怎么做"**（具体、可执行的建议）
4. **关注异常值**（标记为 🔴 ANOMALY 的指标需要重点分析）
5. **考虑相关性**（多个指标之间可能存在因果关系）

## 输出格式要求

请使用 **Markdown** 格式输出，严格按照以下三个章节结构：

---

## 📊 第一部分：核心洞察 (Key Insights)

针对每个关键发现，请按以下结构分析：

### 洞察 1: [简洁标题]
- **现象**: 描述数据中观察到的现象
- **归因分析**: 可能的原因（至少列出 2-3 个假设）
- **影响评估**: 对业务的潜在影响
- **优先级**: 🔴 紧急 / 🟡 重要 / 🟢 关注

（针对数据中的 3-5 个关键发现重复以上结构）

---

## 🎯 第二部分：运营策略建议 (Operational Strategy)

基于数据洞察，为运营团队提供 **具体可执行** 的建议：

### 建议 1: [行动名称]
- **问题**: 要解决的具体问题
- **行动**: 具体要做什么（步骤化）
- **预期效果**: 量化的预期改善
- **实施周期**: 短期（1-2周）/ 中期（1-2月）/ 长期（3月+）
- **所需资源**: 人力、预算估计

（提供 3-5 条优先级排序的建议）

---

## 💡 第三部分：产品设计指导 (Product Design Implications)

基于用户行为数据，为产品团队指出改进方向：

### 产品改进 1: [功能/流程名称]
- **数据依据**: 引用具体的行为数据
- **用户痛点**: 推测用户遇到的问题
- **改进建议**: 具体的产品/UX 改进方案
- **优先级**: P0 / P1 / P2
- **成功指标**: 如何衡量改进效果

（提供 3-5 条产品建议）

---

## 注意事项

- 引用数据时请使用原始数值，不要编造数据
- 异常值（🔴 ANOMALY）必须重点分析
- 建议必须具体可执行，避免空泛的"提升用户体验"类建议
- 考虑资源限制，给出优先级排序
"""


# ============================================================
# Data Collection Functions
# ============================================================

def get_date_ranges() -> Dict[str, Tuple[datetime, datetime]]:
    """Get standard date ranges for comparison"""
    now = datetime.now(timezone.utc)
    
    return {
        "current_30d": (now - timedelta(days=30), now),
        "previous_30d": (now - timedelta(days=60), now - timedelta(days=30)),
        "current_7d": (now - timedelta(days=7), now),
        "previous_7d": (now - timedelta(days=14), now - timedelta(days=7)),
        "year_ago_30d": (now - timedelta(days=395), now - timedelta(days=365)),
    }


def collect_growth_metrics() -> List[MetricData]:
    """Collect growth-related metrics with historical comparison"""
    ranges = get_date_ranges()
    metrics = []
    
    try:
        # DAU (Daily Active Users) - average over period
        def get_dau(start: datetime, end: datetime) -> float:
            activities = supabase.table("activity_logs").select("user_id, created_at")\
                .gte("created_at", start.isoformat())\
                .lt("created_at", end.isoformat()).execute()
            
            if not activities.data:
                return 0
            
            # Group by date and count unique users
            daily_users = defaultdict(set)
            for a in activities.data:
                date = a["created_at"][:10]
                daily_users[date].add(a["user_id"])
            
            if not daily_users:
                return 0
            return sum(len(users) for users in daily_users.values()) / len(daily_users)
        
        current_dau = get_dau(*ranges["current_7d"])
        previous_dau = get_dau(*ranges["previous_7d"])
        
        metrics.append(MetricData(
            name="Daily Active Users (DAU)",
            current_value=current_dau,
            previous_value=previous_dau,
            year_ago_value=None,  # TODO: implement year-ago lookup
            higher_is_better=True
        ))
        
        # New User Registrations
        def get_new_users(start: datetime, end: datetime) -> int:
            result = supabase.table("profiles").select("id", count="exact")\
                .gte("created_at", start.isoformat())\
                .lt("created_at", end.isoformat()).execute()
            return result.count or 0
        
        current_new = get_new_users(*ranges["current_30d"])
        previous_new = get_new_users(*ranges["previous_30d"])
        
        metrics.append(MetricData(
            name="New User Registrations",
            current_value=current_new,
            previous_value=previous_new,
            year_ago_value=None,
            higher_is_better=True
        ))
        
        # MAU (Monthly Active Users)
        def get_mau(start: datetime, end: datetime) -> int:
            activities = supabase.table("activity_logs").select("user_id")\
                .gte("created_at", start.isoformat())\
                .lt("created_at", end.isoformat()).execute()
            return len(set(a["user_id"] for a in (activities.data or [])))
        
        current_mau = get_mau(*ranges["current_30d"])
        previous_mau = get_mau(*ranges["previous_30d"])
        
        metrics.append(MetricData(
            name="Monthly Active Users (MAU)",
            current_value=current_mau,
            previous_value=previous_mau,
            year_ago_value=None,
            higher_is_better=True
        ))
        
        # DAU/MAU Ratio (stickiness)
        if current_mau > 0:
            dau_mau_ratio = (current_dau / current_mau) * 100
            prev_dau_mau = (previous_dau / previous_mau) * 100 if previous_mau > 0 else 0
            
            metrics.append(MetricData(
                name="DAU/MAU Ratio (Stickiness)",
                current_value=dau_mau_ratio,
                previous_value=prev_dau_mau,
                year_ago_value=None,
                is_percentage=True,
                higher_is_better=True
            ))
        
    except Exception as e:
        logger.error(f"Error collecting growth metrics: {e}")
    
    return metrics


def collect_conversion_metrics() -> List[MetricData]:
    """Collect conversion and commercial metrics"""
    ranges = get_date_ranges()
    metrics = []
    
    try:
        # Free to Paid Conversion Rate
        def get_conversion_rate(start: datetime, end: datetime) -> Tuple[float, int, int]:
            total = supabase.table("profiles").select("id", count="exact")\
                .gte("created_at", start.isoformat())\
                .lt("created_at", end.isoformat()).execute()
            
            paid = supabase.table("profiles").select("id", count="exact")\
                .gte("created_at", start.isoformat())\
                .lt("created_at", end.isoformat())\
                .in_("tier", ["starter", "pro"]).execute()
            
            total_count = total.count or 0
            paid_count = paid.count or 0
            rate = (paid_count / total_count * 100) if total_count > 0 else 0
            return rate, paid_count, total_count
        
        current_rate, current_paid, current_total = get_conversion_rate(*ranges["current_30d"])
        previous_rate, _, _ = get_conversion_rate(*ranges["previous_30d"])
        
        metrics.append(MetricData(
            name="Free-to-Paid Conversion Rate",
            current_value=current_rate,
            previous_value=previous_rate,
            year_ago_value=None,
            is_percentage=True,
            higher_is_better=True
        ))
        
        # Revenue (from credit_transactions)
        def get_revenue(start: datetime, end: datetime) -> float:
            txs = supabase.table("credit_transactions").select("amount")\
                .gte("created_at", start.isoformat())\
                .lt("created_at", end.isoformat())\
                .gt("amount", 0).execute()  # Only positive (purchases)
            return sum(t.get("amount", 0) for t in (txs.data or [])) / 100  # cents to dollars
        
        current_revenue = get_revenue(*ranges["current_30d"])
        previous_revenue = get_revenue(*ranges["previous_30d"])
        
        metrics.append(MetricData(
            name="Total Revenue",
            current_value=current_revenue,
            previous_value=previous_revenue,
            year_ago_value=None,
            unit="$",
            higher_is_better=True
        ))
        
        # ARPU (Average Revenue Per User)
        def get_arpu(start: datetime, end: datetime) -> float:
            revenue = get_revenue(start, end)
            mau = supabase.table("activity_logs").select("user_id")\
                .gte("created_at", start.isoformat())\
                .lt("created_at", end.isoformat()).execute()
            unique_users = len(set(a["user_id"] for a in (mau.data or [])))
            return (revenue / unique_users) if unique_users > 0 else 0
        
        current_arpu = get_arpu(*ranges["current_30d"])
        previous_arpu = get_arpu(*ranges["previous_30d"])
        
        metrics.append(MetricData(
            name="ARPU (Average Revenue Per User)",
            current_value=current_arpu,
            previous_value=previous_arpu,
            year_ago_value=None,
            unit="$",
            higher_is_better=True
        ))
        
    except Exception as e:
        logger.error(f"Error collecting conversion metrics: {e}")
    
    return metrics


def collect_retention_metrics() -> List[MetricData]:
    """Collect retention and churn metrics"""
    ranges = get_date_ranges()
    metrics = []
    
    try:
        now = datetime.now(timezone.utc)
        
        # Day 1 Retention
        def get_d1_retention(cohort_start: datetime, cohort_end: datetime) -> float:
            # Users who signed up in the period
            cohort = supabase.table("profiles").select("id")\
                .gte("created_at", cohort_start.isoformat())\
                .lt("created_at", cohort_end.isoformat()).execute()
            
            cohort_ids = [u["id"] for u in (cohort.data or [])]
            if not cohort_ids:
                return 0
            
            # Users who were active the next day
            next_day_start = cohort_end
            next_day_end = cohort_end + timedelta(days=1)
            
            active = supabase.table("activity_logs").select("user_id")\
                .in_("user_id", cohort_ids)\
                .gte("created_at", next_day_start.isoformat())\
                .lt("created_at", next_day_end.isoformat()).execute()
            
            retained = len(set(a["user_id"] for a in (active.data or [])))
            return (retained / len(cohort_ids)) * 100
        
        # Get D1 retention for users who signed up 7-14 days ago
        d1_cohort_start = now - timedelta(days=14)
        d1_cohort_end = now - timedelta(days=7)
        current_d1 = get_d1_retention(d1_cohort_start, d1_cohort_end)
        
        # Previous period
        prev_d1_start = now - timedelta(days=28)
        prev_d1_end = now - timedelta(days=21)
        previous_d1 = get_d1_retention(prev_d1_start, prev_d1_end)
        
        metrics.append(MetricData(
            name="Day 1 Retention Rate",
            current_value=current_d1,
            previous_value=previous_d1,
            year_ago_value=None,
            is_percentage=True,
            higher_is_better=True
        ))
        
        # Churn Risk (users inactive for 14+ days)
        all_users = supabase.table("profiles").select("id").execute()
        recent_active = supabase.table("activity_logs").select("user_id")\
            .gte("created_at", (now - timedelta(days=14)).isoformat()).execute()
        
        recent_active_set = set(a["user_id"] for a in (recent_active.data or []))
        total_users = len(all_users.data or [])
        churn_risk = len([u for u in (all_users.data or []) if u["id"] not in recent_active_set])
        churn_rate = (churn_risk / total_users * 100) if total_users > 0 else 0
        
        metrics.append(MetricData(
            name="Churn Risk Rate (14+ days inactive)",
            current_value=churn_rate,
            previous_value=churn_rate,  # Simplified
            year_ago_value=None,
            is_percentage=True,
            higher_is_better=False
        ))
        
    except Exception as e:
        logger.error(f"Error collecting retention metrics: {e}")
    
    return metrics


def collect_product_metrics() -> List[MetricData]:
    """Collect product usage and health metrics"""
    ranges = get_date_ranges()
    metrics = []
    
    try:
        # Project Completion Rate
        def get_completion_rate(start: datetime, end: datetime) -> float:
            projects = supabase.table("projects").select("id, thumbnail_url")\
                .gte("created_at", start.isoformat())\
                .lt("created_at", end.isoformat()).execute()
            
            total = len(projects.data or [])
            completed = len([p for p in (projects.data or []) if p.get("thumbnail_url")])
            return (completed / total * 100) if total > 0 else 0
        
        current_completion = get_completion_rate(*ranges["current_30d"])
        previous_completion = get_completion_rate(*ranges["previous_30d"])
        
        metrics.append(MetricData(
            name="Project Completion Rate",
            current_value=current_completion,
            previous_value=previous_completion,
            year_ago_value=None,
            is_percentage=True,
            higher_is_better=True
        ))
        
        # AI Generation Success Rate
        def get_ai_success_rate(start: datetime, end: datetime) -> float:
            # Check analytics_events for AI generation events
            try:
                success = supabase.table("analytics_events").select("id", count="exact")\
                    .eq("event_name", "ai_generation_complete")\
                    .gte("created_at", start.isoformat())\
                    .lt("created_at", end.isoformat()).execute()
                
                failed = supabase.table("analytics_events").select("id", count="exact")\
                    .eq("event_name", "ai_generation_failed")\
                    .gte("created_at", start.isoformat())\
                    .lt("created_at", end.isoformat()).execute()
                
                total = (success.count or 0) + (failed.count or 0)
                return ((success.count or 0) / total * 100) if total > 0 else 95.0  # Default to 95% if no data
            except:
                return 95.0  # Default
        
        current_ai_rate = get_ai_success_rate(*ranges["current_7d"])
        previous_ai_rate = get_ai_success_rate(*ranges["previous_7d"])
        
        metrics.append(MetricData(
            name="AI Generation Success Rate",
            current_value=current_ai_rate,
            previous_value=previous_ai_rate,
            year_ago_value=None,
            is_percentage=True,
            higher_is_better=True
        ))
        
        # Feature Adoption Rate (advanced features)
        def get_feature_adoption(start: datetime, end: datetime) -> float:
            activities = supabase.table("activity_logs").select("user_id, action")\
                .gte("created_at", start.isoformat())\
                .lt("created_at", end.isoformat()).execute()
            
            advanced_actions = ["smart_scan", "regenerate", "export_pdf", "ai_generate"]
            all_users = set()
            advanced_users = set()
            
            for a in (activities.data or []):
                all_users.add(a["user_id"])
                if a.get("action") in advanced_actions:
                    advanced_users.add(a["user_id"])
            
            return (len(advanced_users) / len(all_users) * 100) if all_users else 0
        
        current_adoption = get_feature_adoption(*ranges["current_30d"])
        previous_adoption = get_feature_adoption(*ranges["previous_30d"])
        
        metrics.append(MetricData(
            name="Advanced Feature Adoption Rate",
            current_value=current_adoption,
            previous_value=previous_adoption,
            year_ago_value=None,
            is_percentage=True,
            higher_is_better=True
        ))
        
    except Exception as e:
        logger.error(f"Error collecting product metrics: {e}")
    
    return metrics


def collect_user_behavior_trends() -> List[UserBehaviorTrend]:
    """Collect daily user behavior trends for the last 30 days"""
    trends = []
    now = datetime.now(timezone.utc)
    
    try:
        # Daily project creations
        daily_projects = []
        for i in range(30):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            count = supabase.table("projects").select("id", count="exact")\
                .gte("created_at", day_start.isoformat())\
                .lt("created_at", day_end.isoformat()).execute()
            
            daily_projects.append((day.strftime("%m/%d"), count.count or 0))
        
        daily_projects.reverse()
        trends.append(UserBehaviorTrend(
            metric_name="Daily Project Creations",
            daily_values=daily_projects,
            description="Number of new projects created each day"
        ))
        
        # Daily active users
        daily_dau = []
        for i in range(30):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            activities = supabase.table("activity_logs").select("user_id")\
                .gte("created_at", day_start.isoformat())\
                .lt("created_at", day_end.isoformat()).execute()
            
            unique_users = len(set(a["user_id"] for a in (activities.data or [])))
            daily_dau.append((day.strftime("%m/%d"), unique_users))
        
        daily_dau.reverse()
        trends.append(UserBehaviorTrend(
            metric_name="Daily Active Users",
            daily_values=daily_dau,
            description="Unique users active each day"
        ))
        
    except Exception as e:
        logger.error(f"Error collecting behavior trends: {e}")
    
    return trends


def identify_anomalies(metrics: List[MetricData]) -> List[str]:
    """Identify anomalies and generate warning messages"""
    warnings = []
    
    for metric in metrics:
        if metric.is_anomaly:
            direction = "increased" if metric.mom_change > 0 else "decreased"
            impact = "positive" if (metric.mom_change > 0) == metric.higher_is_better else "negative"
            
            warnings.append(
                f"⚠️ {metric.name} has {direction} by {abs(metric.mom_change):.1f}% "
                f"(from {metric.previous_value:.1f} to {metric.current_value:.1f}). "
                f"This is a {impact} change that requires attention."
            )
        
        # Check against thresholds
        threshold_key = metric.name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        for key, thresholds in METRIC_THRESHOLDS.items():
            if key in threshold_key:
                if "critical_low" in thresholds and metric.current_value < thresholds["critical_low"]:
                    warnings.append(f"🔴 CRITICAL: {metric.name} is critically low at {metric.current_value:.1f}")
                elif "critical_high" in thresholds and metric.current_value > thresholds["critical_high"]:
                    warnings.append(f"🔴 CRITICAL: {metric.name} is critically high at {metric.current_value:.1f}")
                break
    
    return warnings


# ============================================================
# Main Report Generation Function
# ============================================================

async def generate_ai_business_report(
    report_type: str = "comprehensive",
    time_range: str = "30d"
) -> Dict[str, Any]:
    """
    Generate a comprehensive AI-powered business intelligence report.
    
    Uses unified AI service with admin model configuration.
    
    Args:
        report_type: "comprehensive" | "growth" | "product" | "commercial"
        time_range: "7d" | "30d" | "90d"
    
    Returns:
        Dict containing:
        - report_markdown: The full AI-generated report in Markdown
        - metrics_summary: Structured metrics data
        - anomalies: List of detected anomalies
        - generated_at: Timestamp
    """
    from .ai.unified_text_service import unified_text
    from .ai.model_config import get_admin_model_config
    
    logger.info(f"Generating AI business report: type={report_type}, range={time_range}")
    
    # Collect all metrics
    growth_metrics = collect_growth_metrics()
    conversion_metrics = collect_conversion_metrics()
    retention_metrics = collect_retention_metrics()
    product_metrics = collect_product_metrics()
    behavior_trends = collect_user_behavior_trends()
    
    all_metrics = growth_metrics + conversion_metrics + retention_metrics + product_metrics
    
    # Identify anomalies
    anomalies = identify_anomalies(all_metrics)
    
    # Build the data context for LLM
    metrics_context = f"""
## 数据报告时间范围
- 当前周期: 最近 {time_range}
- 对比周期: 上一个 {time_range}
- 生成时间: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

## 核心增长指标 (Growth Metrics)
{chr(10).join(m.to_prompt_string() for m in growth_metrics)}

## 商业转化指标 (Conversion & Commercial Metrics)
{chr(10).join(m.to_prompt_string() for m in conversion_metrics)}

## 用户留存指标 (Retention Metrics)
{chr(10).join(m.to_prompt_string() for m in retention_metrics)}

## 产品健康指标 (Product Health Metrics)
{chr(10).join(m.to_prompt_string() for m in product_metrics)}

## 用户行为趋势 (User Behavior Trends)
{chr(10).join(t.to_prompt_string() for t in behavior_trends)}

## 异常检测警报 (Anomaly Alerts)
{chr(10).join(anomalies) if anomalies else "当前无异常警报"}
"""
    
    # Call unified AI service with admin model
    try:
        result = await unified_text.chat(
            messages=[
                {"role": "system", "content": EXPERT_SYSTEM_PROMPT},
                {"role": "user", "content": f"请分析以下数据并生成商业洞察报告：\n\n{metrics_context}"}
            ],
            use_admin_model=True,
            use_cache=False,  # Reports should always be fresh
            temperature=0.7,
            max_tokens=4000,
        )
        
        report_markdown = result.content
        config = get_admin_model_config()
        model_used = f"{config.provider}/{config.model}"
        
    except Exception as e:
        logger.error(f"[AIReport] Error generating report: {e}")
        report_markdown = f"## 报告生成失败\n\n无法生成 AI 分析报告: {str(e)}\n\n请稍后重试。"
        model_used = "error"
    
    # Build structured response
    return {
        "report_markdown": report_markdown,
        "metrics_summary": {
            "growth": [asdict(m) for m in growth_metrics],
            "conversion": [asdict(m) for m in conversion_metrics],
            "retention": [asdict(m) for m in retention_metrics],
            "product": [asdict(m) for m in product_metrics],
        },
        "anomalies": anomalies,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_type": report_type,
        "time_range": time_range,
        "model_used": model_used,
    }


def get_quick_insights() -> List[Dict[str, Any]]:
    """
    Generate quick insights without full LLM call (rule-based).
    Used for dashboard preview before full report generation.
    """
    growth_metrics = collect_growth_metrics()
    conversion_metrics = collect_conversion_metrics()
    all_metrics = growth_metrics + conversion_metrics
    
    insights = []
    
    for metric in all_metrics:
        if metric.is_anomaly:
            priority = "critical" if abs(metric.mom_change) > 50 else "high"
            
            insights.append({
                "id": f"anomaly_{metric.name.lower().replace(' ', '_')}",
                "category": "anomaly",
                "priority": priority,
                "title": f"{metric.name} 异常变化",
                "summary": f"{metric.name} 环比变化 {metric.mom_change:+.1f}%，需要关注",
                "metric_value": metric.current_value,
                "change_percent": metric.mom_change,
            })
    
    return insights[:5]  # Return top 5 insights
