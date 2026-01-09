"""
AI Reports Generator - Report generation functions

@module services.ai_reports.report_generator
@version 3.24
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

import openai

from .models import MetricData, InsightPriority, THRESHOLDS
from .collectors import (
    collect_growth_metrics,
    collect_conversion_metrics,
    collect_retention_metrics,
    collect_product_metrics,
    collect_user_behavior_trends,
)

logger = logging.getLogger(__name__)

# Initialize OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# System prompt for AI analysis
SYSTEM_PROMPT = """You are a senior SaaS business analyst with expertise in:
- Growth metrics (DAU, MAU, cohort analysis)
- Revenue optimization (MRR, ARPU, churn)
- Product analytics (feature adoption, user journeys)

Analyze the provided metrics and generate insights in JSON format:
{
  "executive_summary": "Brief overview of business health",
  "key_insights": [
    {
      "title": "Insight title",
      "description": "Detailed explanation",
      "priority": "critical|high|medium|low",
      "category": "growth|revenue|product|risk",
      "recommendation": "Actionable recommendation"
    }
  ],
  "anomalies": ["List of detected anomalies"],
  "recommendations": ["Top 3 prioritized actions"]
}

Focus on actionable insights, not just data descriptions."""


def identify_anomalies(metrics: List[MetricData]) -> List[str]:
    """Identify anomalous metrics based on thresholds."""
    anomalies = []
    
    for metric in metrics:
        if metric.is_anomaly:
            direction = "increased" if metric.mom_change > 0 else "decreased"
            anomalies.append(
                f"{metric.name} {direction} by {abs(metric.mom_change):.1f}% "
                f"({metric.previous_value:.1f} → {metric.current_value:.1f})"
            )
    
    return anomalies


def generate_ai_business_report(
    report_type: str = "comprehensive",
    time_range: str = "30d"
) -> Dict[str, Any]:
    """
    Generate comprehensive AI business report.

    Args:
        report_type: Report type - "comprehensive", "growth", "engagement", "revenue", "quick"
        time_range: Time range - "7d", "30d", "90d", "365d"

    Returns:
        Report dictionary with insights
    """
    if not openai_client:
        return {
            "error": "OpenAI API not configured",
            "fallback": get_quick_insights()
        }

    # Map report_type to analysis parameters
    analysis_depth_map = {
        "quick": "quick",
        "comprehensive": "deep",
        "growth": "standard",
        "engagement": "standard",
        "revenue": "standard"
    }
    analysis_depth = analysis_depth_map.get(report_type, "standard")

    # Map report_type to focus areas
    focus_areas = None
    if report_type in ["growth", "engagement", "revenue"]:
        focus_areas = [report_type]

    # Collect all metrics
    all_metrics = []
    all_metrics.extend(collect_growth_metrics())
    all_metrics.extend(collect_conversion_metrics())
    all_metrics.extend(collect_retention_metrics())
    all_metrics.extend(collect_product_metrics())

    behavior_trends = collect_user_behavior_trends()

    # Build prompt
    metrics_text = "\n".join([m.to_prompt_string() for m in all_metrics])
    trends_text = "\n".join([t.to_prompt_string() for t in behavior_trends])
    anomalies = identify_anomalies(all_metrics)

    user_prompt = f"""Analyze these SaaS metrics:

## Growth & Engagement Metrics
{metrics_text}

## User Behavior Trends
{trends_text}

## Detected Anomalies
{chr(10).join(['- ' + a for a in anomalies]) if anomalies else 'None detected'}

Report Type: {report_type}
Time Range: {time_range}
Analysis Depth: {analysis_depth}
Focus Areas: {', '.join(focus_areas) if focus_areas else 'All areas'}

Provide actionable insights and recommendations."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
            timeout=30  # AI-MEDIUM-9: Add timeout
        )

        result = json.loads(response.choices[0].message.content)
        result["metrics_analyzed"] = len(all_metrics)
        result["report_type"] = report_type
        result["time_range"] = time_range
        result["generated_at"] = __import__('datetime').datetime.now().isoformat()

        return result

    except Exception as e:
        logger.error(f"AI report generation failed: {e}")
        return {
            "error": str(e),
            "fallback": get_quick_insights()
        }


def get_quick_insights() -> List[Dict[str, Any]]:
    """Get quick rule-based insights without AI."""
    insights = []
    
    metrics = collect_growth_metrics()
    
    for metric in metrics:
        if metric.is_anomaly:
            direction = "up" if metric.mom_change > 0 else "down"
            good = (metric.higher_is_better and metric.mom_change > 0) or \
                   (not metric.higher_is_better and metric.mom_change < 0)
            
            insights.append({
                "title": f"{metric.name} {direction} significantly",
                "description": f"Changed by {metric.mom_change:+.1f}% vs previous period",
                "priority": InsightPriority.HIGH.value if not good else InsightPriority.MEDIUM.value,
                "category": "growth",
                "metric_value": metric.current_value,
                "change": metric.mom_change,
            })
    
    # Add conversion metrics
    conv_metrics = collect_conversion_metrics()
    for metric in conv_metrics:
        if metric.current_value < 3:  # Low conversion warning
            insights.append({
                "title": "Low conversion rate detected",
                "description": f"Conversion rate at {metric.current_value:.1f}%",
                "priority": InsightPriority.HIGH.value,
                "category": "revenue",
                "recommendation": "Review onboarding flow and pricing page",
            })
    
    return insights
