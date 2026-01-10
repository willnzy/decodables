"""
Tests for AI Insights Service

@module tests.domains.stats.test_ai_insights
@version 1.0.0

Test Coverage:
- get_ai_insights()
- get_ai_recommendations()
- get_behavior_analysis()

Created: 2026-01-10
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from domains.stats.ai_insights import (
    get_ai_insights,
    get_ai_recommendations,
    get_behavior_analysis,
)


class TestGetAIInsights:
    """Test get_ai_insights function."""

    @pytest.mark.asyncio
    @patch("domains.stats.ai_insights._get_stats_repo")
    async def test_get_insights_all(self, mock_get_repo):
        """Test getting all insights."""
        # Setup
        mock_repo = Mock()
        mock_repo.admin_get_ai_insights = AsyncMock(return_value=[
            {
                "category": "growth",
                "title": "User Growth",
                "description": "10 new users in the last 7 days",
                "metric_value": 10,
                "trend": "up"
            },
            {
                "category": "engagement",
                "title": "Project Creation",
                "description": "5 projects created in the last 7 days",
                "metric_value": 5,
                "trend": "up"
            }
        ])
        mock_get_repo.return_value = mock_repo

        # Execute
        result = await get_ai_insights("all")

        # Verify
        assert len(result) == 2
        assert result[0]["category"] == "growth"
        assert result[1]["category"] == "engagement"
        mock_repo.admin_get_ai_insights.assert_called_once_with("all")

    @pytest.mark.asyncio
    @patch("domains.stats.ai_insights._get_stats_repo")
    async def test_get_insights_growth(self, mock_get_repo):
        """Test getting growth insights only."""
        # Setup
        mock_repo = Mock()
        mock_repo.admin_get_ai_insights = AsyncMock(return_value=[
            {
                "category": "growth",
                "title": "User Growth",
                "description": "10 new users in the last 7 days",
                "metric_value": 10,
                "trend": "up"
            }
        ])
        mock_get_repo.return_value = mock_repo

        # Execute
        result = await get_ai_insights("growth")

        # Verify
        assert len(result) == 1
        assert result[0]["category"] == "growth"
        mock_repo.admin_get_ai_insights.assert_called_once_with("growth")

    @pytest.mark.asyncio
    @patch("domains.stats.ai_insights._get_stats_repo")
    async def test_get_insights_error_handling(self, mock_get_repo):
        """Test error handling returns empty list."""
        # Setup
        mock_repo = Mock()
        mock_repo.admin_get_ai_insights = AsyncMock(side_effect=Exception("Database error"))
        mock_get_repo.return_value = mock_repo

        # Execute
        result = await get_ai_insights("all")

        # Verify
        assert result == []


class TestGetAIRecommendations:
    """Test get_ai_recommendations function."""

    @pytest.mark.asyncio
    @patch("domains.stats.ai_insights._get_stats_repo")
    async def test_get_recommendations_all(self, mock_get_repo):
        """Test getting all recommendations."""
        # Setup
        mock_repo = Mock()
        mock_repo.admin_get_ai_recommendations = AsyncMock(return_value=[
            {
                "priority": "high",
                "area": "growth",
                "title": "User acquisition below average",
                "description": "Weekly signups are low",
                "action": "Run marketing campaign"
            },
            {
                "priority": "medium",
                "area": "retention",
                "title": "Low project creation rate",
                "description": "Only 30% of users created projects",
                "action": "Improve onboarding"
            }
        ])
        mock_get_repo.return_value = mock_repo

        # Execute
        result = await get_ai_recommendations("all")

        # Verify
        assert len(result) == 2
        assert result[0]["priority"] == "high"
        assert result[1]["priority"] == "medium"
        mock_repo.admin_get_ai_recommendations.assert_called_once_with("all")

    @pytest.mark.asyncio
    @patch("domains.stats.ai_insights._get_stats_repo")
    async def test_get_recommendations_monetization(self, mock_get_repo):
        """Test getting monetization recommendations only."""
        # Setup
        mock_repo = Mock()
        mock_repo.admin_get_ai_recommendations = AsyncMock(return_value=[
            {
                "priority": "high",
                "area": "monetization",
                "title": "Low conversion rate",
                "description": "Only 3% of users are paying",
                "action": "Review pricing"
            }
        ])
        mock_get_repo.return_value = mock_repo

        # Execute
        result = await get_ai_recommendations("monetization")

        # Verify
        assert len(result) == 1
        assert result[0]["area"] == "monetization"
        mock_repo.admin_get_ai_recommendations.assert_called_once_with("monetization")

    @pytest.mark.asyncio
    @patch("domains.stats.ai_insights._get_stats_repo")
    async def test_get_recommendations_error_handling(self, mock_get_repo):
        """Test error handling returns empty list."""
        # Setup
        mock_repo = Mock()
        mock_repo.admin_get_ai_recommendations = AsyncMock(side_effect=Exception("Database error"))
        mock_get_repo.return_value = mock_repo

        # Execute
        result = await get_ai_recommendations("all")

        # Verify
        assert result == []


class TestGetBehaviorAnalysis:
    """Test get_behavior_analysis function."""

    @pytest.mark.asyncio
    @patch("domains.stats.ai_insights._get_stats_repo")
    async def test_get_behavior_analysis_success(self, mock_get_repo):
        """Test successful behavior analysis."""
        # Setup
        mock_repo = Mock()
        mock_repo.admin_get_behavior_analysis = AsyncMock(return_value={
            "patterns": {
                "event_distribution": {"login": 100, "project_create": 50},
                "peak_activity_hour": 14,
                "hourly_activity": {i: i * 10 for i in range(24)},
                "total_events_analyzed": 1000,
                "limited": False
            },
            "segments": {
                "by_tier": {"t1": 80, "t2": 15, "t3": 5},
                "total_users": 100
            },
            "period": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        })
        mock_get_repo.return_value = mock_repo

        # Execute
        result = await get_behavior_analysis("2024-01-01", "2024-01-31")

        # Verify
        assert result["patterns"]["peak_activity_hour"] == 14
        assert result["patterns"]["total_events_analyzed"] == 1000
        assert result["segments"]["total_users"] == 100
        mock_repo.admin_get_behavior_analysis.assert_called_once_with("2024-01-01", "2024-01-31")

    @pytest.mark.asyncio
    @patch("domains.stats.ai_insights._get_stats_repo")
    async def test_get_behavior_analysis_no_dates(self, mock_get_repo):
        """Test behavior analysis with default dates."""
        # Setup
        mock_repo = Mock()
        mock_repo.admin_get_behavior_analysis = AsyncMock(return_value={
            "patterns": {
                "event_distribution": {},
                "peak_activity_hour": 0,
                "hourly_activity": {},
                "total_events_analyzed": 0,
                "limited": False
            },
            "segments": {
                "by_tier": {},
                "total_users": 0
            },
            "period": {
                "start_date": "",
                "end_date": ""
            }
        })
        mock_get_repo.return_value = mock_repo

        # Execute
        result = await get_behavior_analysis()

        # Verify
        assert result["patterns"]["total_events_analyzed"] == 0
        mock_repo.admin_get_behavior_analysis.assert_called_once_with(None, None)

    @pytest.mark.asyncio
    @patch("domains.stats.ai_insights._get_stats_repo")
    async def test_get_behavior_analysis_error_handling(self, mock_get_repo):
        """Test error handling returns default structure."""
        # Setup
        mock_repo = Mock()
        mock_repo.admin_get_behavior_analysis = AsyncMock(side_effect=Exception("Database error"))
        mock_get_repo.return_value = mock_repo

        # Execute
        result = await get_behavior_analysis("2024-01-01", "2024-01-31")

        # Verify
        assert "patterns" in result
        assert "segments" in result
        assert "period" in result
        assert result["patterns"]["total_events_analyzed"] == 0
        assert result["segments"]["total_users"] == 0
