"""
AI Reports Models - Data classes and enums

@module services.ai_reports.models
@version 3.24
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


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
    """Represents a single metric with historical context."""
    name: str
    current_value: float
    previous_value: float
    year_ago_value: Optional[float] = None
    unit: str = ""
    is_percentage: bool = False
    higher_is_better: bool = True
    
    @property
    def mom_change(self) -> float:
        """Month-over-Month change percentage."""
        if self.previous_value == 0:
            return 100.0 if self.current_value > 0 else 0.0
        return ((self.current_value - self.previous_value) / self.previous_value) * 100
    
    @property
    def yoy_change(self) -> Optional[float]:
        """Year-over-Year change percentage."""
        if self.year_ago_value is None or self.year_ago_value == 0:
            return None
        return ((self.current_value - self.year_ago_value) / self.year_ago_value) * 100
    
    @property
    def trend(self) -> MetricTrend:
        """Determine trend based on change."""
        if abs(self.mom_change) < 5:
            return MetricTrend.STABLE
        return MetricTrend.INCREASING if self.mom_change > 0 else MetricTrend.DECREASING
    
    @property
    def is_anomaly(self) -> bool:
        """Check if the change is anomalous (>30% change)."""
        return abs(self.mom_change) > 30
    
    def to_prompt_string(self) -> str:
        """Format for inclusion in LLM prompt."""
        status = "🔴 ANOMALY" if self.is_anomaly else ""
        trend_emoji = "📈" if self.mom_change > 5 else "📉" if self.mom_change < -5 else "➡️"
        
        value_str = f"{self.current_value:.1f}{self.unit}" if not self.is_percentage else f"{self.current_value:.1f}%"
        mom_str = f"{self.mom_change:+.1f}%"
        yoy_str = f"{self.yoy_change:+.1f}%" if self.yoy_change is not None else "N/A"
        
        return f"- {self.name}: {value_str} {trend_emoji} (MoM: {mom_str}, YoY: {yoy_str}) {status}"


@dataclass
class UserBehaviorTrend:
    """User behavior data for trend analysis."""
    metric_name: str
    daily_values: List[Tuple[str, float]]
    description: str = ""
    
    def to_prompt_string(self) -> str:
        """Format trend data for prompt."""
        if not self.daily_values:
            return f"- {self.metric_name}: No data available"
        
        recent = self.daily_values[-7:] if len(self.daily_values) >= 7 else self.daily_values
        trend_data = ", ".join([f"{d}: {v:.0f}" for d, v in recent])
        return f"- {self.metric_name} (last 7 days): [{trend_data}]"


# Thresholds for alerts
THRESHOLDS = {
    "dau_drop": -20,
    "churn_spike": 50,
    "revenue_drop": -15,
    "conversion_drop": -25,
}
