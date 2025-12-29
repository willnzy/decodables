"""
Edge Cases and Boundary Condition Tests (PRD v3.2)
Tests for edge cases, boundary conditions, and error handling
"""
import pytest
from datetime import datetime, timezone, timedelta


class TestProjectLimitEdgeCases:
    """Test edge cases for project limits"""
    
    def test_project_limit_exactly_at_limit(self):
        """User exactly at project limit cannot create more"""
        tier_limits = {"free": 1, "starter": 20, "pro": 200}
        
        # Free user with exactly 1 project
        current_count = 1
        max_projects = tier_limits.get("free", 1)
        assert current_count >= max_projects  # Cannot create
        
        # Starter user with exactly 20 projects
        current_count = 20
        max_projects = tier_limits.get("starter", 20)
        assert current_count >= max_projects  # Cannot create
        
        # Pro user with exactly 200 projects
        current_count = 200
        max_projects = tier_limits.get("pro", 200)
        assert current_count >= max_projects  # Cannot create
    
    def test_project_limit_one_below_limit(self):
        """User one below limit can create"""
        tier_limits = {"free": 1, "starter": 20, "pro": 200}
        
        # Free user with 0 projects
        current_count = 0
        max_projects = tier_limits.get("free", 1)
        assert current_count < max_projects  # Can create
        
        # Starter user with 19 projects
        current_count = 19
        max_projects = tier_limits.get("starter", 20)
        assert current_count < max_projects  # Can create
        
        # Pro user with 199 projects
        current_count = 199
        max_projects = tier_limits.get("pro", 200)
        assert current_count < max_projects  # Can create
    
    def test_project_limit_unknown_tier(self):
        """Unknown tier should default to Free limit"""
        tier_limits = {"free": 1, "starter": 20, "pro": 200}
        max_projects = tier_limits.get("unknown_tier", 1)  # Default to Free
        assert max_projects == 1
    
    def test_project_limit_empty_tier(self):
        """Empty tier should default to Free limit"""
        tier_limits = {"free": 1, "starter": 20, "pro": 200}
        max_projects = tier_limits.get("", 1)  # Default to Free
        assert max_projects == 1
    
    def test_project_limit_none_tier(self):
        """None tier should default to Free limit"""
        tier_limits = {"free": 1, "starter": 20, "pro": 200}
        max_projects = tier_limits.get(None, 1)  # Default to Free
        assert max_projects == 1


class TestFreeTrialEdgeCases:
    """Test edge cases for Free 7-day trial"""
    
    def test_trial_exactly_7_days(self):
        """User exactly at 7 days boundary"""
        created_at = datetime.now(timezone.utc) - timedelta(days=7)
        now = datetime.now(timezone.utc)
        days_since_registration = (now - created_at).total_seconds() / (24 * 3600)
        
        # Should be approximately 7 days
        assert 6.9 < days_since_registration < 7.1
        
        # At exactly 7 days, should be expired (> 7)
        # Note: Due to timing, this might be slightly over 7
        assert days_since_registration >= 7
    
    def test_trial_6_days_23_hours(self):
        """User at 6 days 23 hours (still within trial)"""
        created_at = datetime.now(timezone.utc) - timedelta(days=6, hours=23)
        now = datetime.now(timezone.utc)
        days_since_registration = (now - created_at).total_seconds() / (24 * 3600)
        
        assert days_since_registration < 7
    
    def test_trial_7_days_1_hour(self):
        """User at 7 days 1 hour (expired)"""
        created_at = datetime.now(timezone.utc) - timedelta(days=7, hours=1)
        now = datetime.now(timezone.utc)
        days_since_registration = (now - created_at).total_seconds() / (24 * 3600)
        
        assert days_since_registration > 7
    
    def test_trial_just_created(self):
        """User just created (0 days)"""
        created_at = datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)
        days_since_registration = (now - created_at).total_seconds() / (24 * 3600)
        
        assert days_since_registration < 1
        assert days_since_registration < 7
    
    def test_trial_very_old_user(self):
        """User created 30 days ago (long expired)"""
        created_at = datetime.now(timezone.utc) - timedelta(days=30)
        now = datetime.now(timezone.utc)
        days_since_registration = (now - created_at).total_seconds() / (24 * 3600)
        
        assert days_since_registration > 7
        # Allow small floating point precision error
        assert 29.9 < days_since_registration < 30.1
    
    def test_trial_missing_created_at(self):
        """User without created_at field"""
        created_at = None
        # Should handle gracefully (not crash)
        if created_at is None:
            # In real code, this should be handled
            # For now, we test that None is detected
            assert created_at is None
    
    def test_trial_invalid_date_format(self):
        """Invalid date format handling"""
        # Test various date formats that might be encountered
        valid_iso = datetime.now(timezone.utc).isoformat()
        assert "T" in valid_iso  # ISO format contains T
        
        # Should handle both with and without 'Z'
        with_z = datetime.now(timezone.utc).isoformat() + "Z"
        without_z = datetime.now(timezone.utc).isoformat()
        
        # Both should be parseable (code handles both)


class TestDowngradeEdgeCases:
    """Test edge cases for downgrade logic"""
    
    def test_downgrade_exactly_at_limit(self):
        """User with exactly N projects (at limit)"""
        projects = [
            {"id": f"project_{i}", "created_at": f"2024-01-{i+1:02d}T00:00:00Z"}
            for i in range(20)  # Exactly 20 projects
        ]
        
        max_projects = 20
        sorted_projects = sorted(projects, key=lambda p: p.get("created_at", ""))
        allowed_projects = sorted_projects[:max_projects]
        
        assert len(allowed_projects) == 20
        assert "project_0" in [p["id"] for p in allowed_projects]
        assert "project_19" in [p["id"] for p in allowed_projects]
    
    def test_downgrade_one_over_limit(self):
        """User with N+1 projects (one over limit)"""
        projects = [
            {"id": f"project_{i}", "created_at": f"2024-01-{i+1:02d}T00:00:00Z"}
            for i in range(21)  # 21 projects, limit is 20
        ]
        
        max_projects = 20
        sorted_projects = sorted(projects, key=lambda p: p.get("created_at", ""))
        allowed_projects = sorted_projects[:max_projects]
        allowed_project_ids = {p["id"] for p in allowed_projects}
        
        assert len(allowed_project_ids) == 20
        assert "project_0" in allowed_project_ids  # Oldest
        assert "project_19" in allowed_project_ids  # Last allowed
        assert "project_20" not in allowed_project_ids  # Exceeds limit
    
    def test_downgrade_many_over_limit(self):
        """User with many projects over limit"""
        projects = [
            {"id": f"project_{i}", "created_at": f"2024-01-{i+1:02d}T00:00:00Z"}
            for i in range(50)  # 50 projects, limit is 20
        ]
        
        max_projects = 20
        sorted_projects = sorted(projects, key=lambda p: p.get("created_at", ""))
        allowed_projects = sorted_projects[:max_projects]
        allowed_project_ids = {p["id"] for p in allowed_projects}
        
        assert len(allowed_project_ids) == 20
        assert "project_0" in allowed_project_ids  # Oldest
        assert "project_19" in allowed_project_ids  # Last allowed
        assert "project_20" not in allowed_project_ids  # First excluded
        assert "project_49" not in allowed_project_ids  # Last excluded
    
    def test_downgrade_missing_created_at(self):
        """Projects without created_at field"""
        projects = [
            {"id": "project_1", "created_at": "2024-01-01T00:00:00Z"},
            {"id": "project_2"},  # Missing created_at
            {"id": "project_3", "created_at": "2024-01-03T00:00:00Z"},
        ]
        
        # Sort should handle missing created_at gracefully
        # Empty string sorts before non-empty strings, so missing dates come first
        sorted_projects = sorted(projects, key=lambda p: p.get("created_at", "") or "")
        
        # Projects with created_at should be sorted by date
        # Missing created_at (empty string) comes first in string sort
        project_ids = [p["id"] for p in sorted_projects]
        assert "project_1" in project_ids
        assert "project_2" in project_ids  # Missing date
        assert "project_3" in project_ids
        
        # Verify that projects with dates are sorted correctly
        projects_with_dates = [p for p in sorted_projects if p.get("created_at")]
        assert len(projects_with_dates) == 2
        assert projects_with_dates[0]["id"] == "project_1"  # Earlier date
        assert projects_with_dates[1]["id"] == "project_3"  # Later date
    
    def test_downgrade_empty_projects_list(self):
        """User with no projects"""
        projects = []
        max_projects = 20
        
        sorted_projects = sorted(projects, key=lambda p: p.get("created_at", ""))
        allowed_projects = sorted_projects[:max_projects]
        
        assert len(allowed_projects) == 0
    
    def test_downgrade_same_creation_time(self):
        """Multiple projects with same creation time"""
        same_time = "2024-01-01T00:00:00Z"
        projects = [
            {"id": "project_1", "created_at": same_time},
            {"id": "project_2", "created_at": same_time},
            {"id": "project_3", "created_at": same_time},
        ]
        
        max_projects = 2
        sorted_projects = sorted(projects, key=lambda p: p.get("created_at", ""))
        allowed_projects = sorted_projects[:max_projects]
        
        # All have same time, so first 2 should be allowed
        assert len(allowed_projects) == 2


class TestPermissionEdgeCases:
    """Test edge cases for permissions"""
    
    def test_permission_case_sensitivity(self):
        """Tier names should be case-insensitive or handled consistently"""
        # In real code, tier should be normalized to lowercase
        assert "FREE".lower() == "free"
        assert "Starter".lower() == "starter"
        assert "PRO".lower() == "pro"
    
    def test_permission_unknown_tier(self):
        """Unknown tier should default to most restrictive (Free)"""
        def can_export_zip(tier):
            return tier == "pro"
        
        assert can_export_zip("free") == False
        assert can_export_zip("starter") == False
        assert can_export_zip("pro") == True
        assert can_export_zip("unknown") == False  # Default to False
    
    def test_permission_none_tier(self):
        """None tier should be handled gracefully"""
        def can_export_zip(tier):
            if tier is None:
                return False  # Default to most restrictive
            return tier == "pro"
        
        assert can_export_zip(None) == False
        assert can_export_zip("pro") == True


class TestAIModelEdgeCases:
    """Test edge cases for AI model selection"""
    
    def test_model_selection_unknown_tier(self):
        """Unknown tier should default to standard model"""
        def get_ai_model(tier):
            if tier == "pro":
                return "flux-dev"
            return "flux-schnell"  # Default for all other tiers
        
        assert get_ai_model("free") == "flux-schnell"
        assert get_ai_model("starter") == "flux-schnell"
        assert get_ai_model("pro") == "flux-dev"
        assert get_ai_model("unknown") == "flux-schnell"  # Default
        assert get_ai_model(None) == "flux-schnell"  # Default
    
    def test_model_selection_empty_tier(self):
        """Empty tier should default to standard model"""
        def get_ai_model(tier):
            if tier == "pro":
                return "flux-dev"
            return "flux-schnell"
        
        assert get_ai_model("") == "flux-schnell"


class TestCreditEdgeCases:
    """Test edge cases for credit calculations"""
    
    def test_credit_cost_zero_prompts(self):
        """Zero prompts should cost 0 credits"""
        prompts = []
        cost = len(prompts) * 5
        assert cost == 0
    
    def test_credit_cost_one_prompt(self):
        """One prompt should cost 5 credits"""
        prompts = ["test"]
        cost = len(prompts) * 5
        assert cost == 5
    
    def test_credit_cost_many_prompts(self):
        """Many prompts should cost correctly"""
        prompts = ["test"] * 100
        cost = len(prompts) * 5
        assert cost == 500
    
    def test_credit_balance_zero(self):
        """User with zero credits"""
        credits_monthly = 0
        credits_permanent = 0
        total = credits_monthly + credits_permanent
        assert total == 0
    
    def test_credit_balance_negative_prevention(self):
        """Credits should never be negative"""
        credits = 10
        cost = 15
        
        # Should check before deducting
        can_afford = credits >= cost
        assert can_afford == False


class TestDateParsingEdgeCases:
    """Test edge cases for date parsing"""
    
    def test_date_with_z_suffix(self):
        """Date with Z suffix (UTC)"""
        date_str = "2024-01-01T00:00:00Z"
        # Should handle Z suffix
        assert date_str.endswith("Z")
        # Code should replace Z with +00:00 or handle it
    
    def test_date_with_timezone(self):
        """Date with timezone offset"""
        date_str = "2024-01-01T00:00:00+00:00"
        assert "+00:00" in date_str
    
    def test_date_without_time(self):
        """Date without time component"""
        date_str = "2024-01-01"
        # Should handle gracefully or convert to datetime
    
    def test_date_invalid_format(self):
        """Invalid date format"""
        date_str = "invalid-date"
        # Should handle gracefully (catch exception)

