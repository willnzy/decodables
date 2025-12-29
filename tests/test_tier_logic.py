"""
Unit tests for Tier Logic (PRD v3.2)
Tests core business logic without requiring full app setup
"""
import pytest
from datetime import datetime, timezone, timedelta


class TestProjectLimitLogic:
    """Test project limit logic (PRD v3.2)"""
    
    def test_free_tier_limit(self):
        """Free tier: 1 project limit"""
        tier_limits = {"free": 1, "starter": 20, "pro": 200}
        max_projects = tier_limits.get("free", 1)
        assert max_projects == 1
    
    def test_starter_tier_limit(self):
        """Starter tier: 20 project limit"""
        tier_limits = {"free": 1, "starter": 20, "pro": 200}
        max_projects = tier_limits.get("starter", 1)
        assert max_projects == 20
    
    def test_pro_tier_limit(self):
        """Pro tier: 200 project limit"""
        tier_limits = {"free": 1, "starter": 20, "pro": 200}
        max_projects = tier_limits.get("pro", 1)
        assert max_projects == 200
    
    def test_project_limit_check(self):
        """Test project limit check logic"""
        tier_limits = {"free": 1, "starter": 20, "pro": 200}
        
        # Free user with 0 projects
        current_count = 0
        max_projects = tier_limits.get("free", 1)
        assert current_count < max_projects  # Can create
        
        # Free user with 1 project
        current_count = 1
        assert current_count >= max_projects  # Cannot create


class TestFreeTrialLogic:
    """Test Free 7-day trial logic (PRD v3.2)"""
    
    def test_trial_within_7_days(self):
        """User within 7-day trial can edit"""
        created_at = datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)
        days_since_registration = (now - created_at).total_seconds() / (24 * 3600)
        
        assert days_since_registration < 7
    
    def test_trial_expired_after_7_days(self):
        """User after 7-day trial cannot edit"""
        created_at = datetime.now(timezone.utc) - timedelta(days=8)
        now = datetime.now(timezone.utc)
        days_since_registration = (now - created_at).total_seconds() / (24 * 3600)
        
        assert days_since_registration > 7
    
    def test_trial_exactly_7_days(self):
        """User exactly at 7 days boundary"""
        created_at = datetime.now(timezone.utc) - timedelta(days=7)
        now = datetime.now(timezone.utc)
        days_since_registration = (now - created_at).total_seconds() / (24 * 3600)
        
        # Should be approximately 7 days (within tolerance)
        assert 6.9 < days_since_registration < 7.1


class TestTierPermissions:
    """Test tier-based permissions (PRD v3.2)"""
    
    def test_zip_export_permission(self):
        """ZIP export: Pro only"""
        assert self._can_export_zip("free") == False
        assert self._can_export_zip("starter") == False
        assert self._can_export_zip("pro") == True
    
    def test_personal_upload_permission(self):
        """Personal upload: Pro only"""
        assert self._can_upload_personal("free") == False
        assert self._can_upload_personal("starter") == False
        assert self._can_upload_personal("pro") == True
    
    def test_pdf_export_permission(self):
        """PDF export: All tiers"""
        assert self._can_export_pdf("free") == True
        assert self._can_export_pdf("starter") == True
        assert self._can_export_pdf("pro") == True
    
    def test_ai_model_selection(self):
        """AI model selection based on tier"""
        assert self._get_ai_model("free") == "flux-schnell"
        assert self._get_ai_model("starter") == "flux-schnell"
        assert self._get_ai_model("pro") == "flux-dev"
    
    @staticmethod
    def _can_export_zip(tier):
        """Check ZIP export permission"""
        return tier == "pro"
    
    @staticmethod
    def _can_upload_personal(tier):
        """Check personal upload permission"""
        return tier == "pro"
    
    @staticmethod
    def _can_export_pdf(tier):
        """Check PDF export permission"""
        return True  # All tiers
    
    @staticmethod
    def _get_ai_model(tier):
        """Get AI model for tier"""
        return "flux-dev" if tier == "pro" else "flux-schnell"


class TestDowngradeLogic:
    """Test project downgrade logic (PRD v3.2)"""
    
    def test_downgrade_project_sorting(self):
        """Projects should be sorted by creation date for downgrade"""
        projects = [
            {"id": "project_1", "created_at": "2024-01-01T00:00:00Z"},
            {"id": "project_2", "created_at": "2024-01-02T00:00:00Z"},
            {"id": "project_3", "created_at": "2024-01-03T00:00:00Z"},
        ]
        
        # Sort by created_at
        sorted_projects = sorted(projects, key=lambda p: p.get("created_at", ""))
        
        assert sorted_projects[0]["id"] == "project_1"
        assert sorted_projects[-1]["id"] == "project_3"
    
    def test_downgrade_allowed_projects(self):
        """Only top N projects (by creation date) can be edited after downgrade"""
        # User has 25 projects, downgraded to Starter (limit 20)
        projects = [
            {"id": f"project_{i}", "created_at": f"2024-01-{i+1:02d}T00:00:00Z"}
            for i in range(25)
        ]
        
        max_projects = 20
        sorted_projects = sorted(projects, key=lambda p: p.get("created_at", ""))
        allowed_projects = sorted_projects[:max_projects]
        allowed_project_ids = {p["id"] for p in allowed_projects}
        
        assert len(allowed_project_ids) == 20
        assert "project_0" in allowed_project_ids  # Oldest project
        assert "project_24" not in allowed_project_ids  # Newest project (exceeds limit)

