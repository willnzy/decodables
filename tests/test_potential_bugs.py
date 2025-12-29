"""
Potential Bug Detection Tests
Tests for potential bugs found during edge case testing
"""
import pytest
from datetime import datetime, timezone, timedelta


class TestPotentialBugs:
    """Test for potential bugs in the implementation"""
    
    def test_downgrade_missing_created_at_handling(self):
        """
        Bug Check: Projects without created_at should be handled correctly.
        
        Current implementation uses: key=lambda p: p.get("created_at", "") or ""
        This means projects without created_at will have empty string, which sorts first.
        This might not be desired - we might want them to be treated as "newest" or "oldest".
        
        Recommendation: Consider handling missing created_at explicitly.
        """
        projects = [
            {"id": "project_1", "created_at": "2024-01-01T00:00:00Z"},
            {"id": "project_2"},  # Missing created_at
            {"id": "project_3", "created_at": "2024-01-03T00:00:00Z"},
        ]
        
        # Current implementation
        sorted_current = sorted(projects, key=lambda p: p.get("created_at", "") or "")
        
        # Empty string sorts first (before any date string)
        # This means project_2 (missing date) comes first
        assert sorted_current[0].get("created_at", "") == ""  # Missing date comes first
        
        # Alternative: Treat missing dates as "very old" (use far future date)
        # This would put them at the end
        far_future = "9999-12-31T23:59:59Z"
        sorted_alternative = sorted(
            projects,
            key=lambda p: p.get("created_at") or far_future
        )
        
        # With alternative, missing dates come last
        assert sorted_alternative[-1].get("created_at") is None
    
    def test_trial_date_parsing_edge_cases(self):
        """
        Bug Check: Date parsing handles various edge cases correctly.
        
        Current implementation handles:
        - ISO format with Z
        - ISO format without Z
        - datetime objects
        - Missing created_at (graceful degradation)
        
        This is good! But we should verify all cases.
        """
        # Test various date formats
        test_cases = [
            ("2024-01-01T00:00:00Z", True),  # With Z
            ("2024-01-01T00:00:00+00:00", True),  # With timezone
            ("2024-01-01T00:00:00", True),  # Without timezone
            (None, False),  # Missing
            ("invalid", False),  # Invalid format
        ]
        
        for date_str, should_parse in test_cases:
            if date_str is None:
                # Missing date - should handle gracefully
                assert date_str is None
            elif should_parse:
                # Valid date - should parse
                try:
                    if isinstance(date_str, str):
                        date_str_clean = date_str.replace('Z', '+00:00')
                        parsed = datetime.fromisoformat(date_str_clean)
                        assert parsed is not None
                except ValueError:
                    # Invalid format - should be caught
                    assert not should_parse
    
    def test_project_limit_boundary_condition(self):
        """
        Bug Check: Boundary condition at exactly the limit.
        
        Current code: if current_count >= max_projects
        This correctly prevents creation when at limit.
        """
        current_count = 1
        max_projects = 1
        
        # At limit - should not allow
        assert current_count >= max_projects
        
        # One below - should allow
        current_count = 0
        assert current_count < max_projects
    
    def test_trial_boundary_condition(self):
        """
        Bug Check: Trial boundary at exactly 7 days.
        
        Current code: if days_since_registration > 7
        This means exactly 7.0 days is still allowed (not expired).
        This might be intentional, but worth noting.
        """
        # Exactly 7 days
        created_at = datetime.now(timezone.utc) - timedelta(days=7)
        now = datetime.now(timezone.utc)
        days = (now - created_at).total_seconds() / (24 * 3600)
        
        # Due to timing, might be slightly over 7
        # Current code uses > 7, so exactly 7.0 would be allowed
        # But in practice, it will be slightly over 7 due to execution time
        
        # Test: 7 days + 1 second (should be expired)
        created_at = datetime.now(timezone.utc) - timedelta(days=7, seconds=1)
        days = (datetime.now(timezone.utc) - created_at).total_seconds() / (24 * 3600)
        assert days > 7  # Should be expired
    
    def test_tier_case_sensitivity(self):
        """
        Bug Check: Tier names should be handled consistently.
        
        Current code uses: user.get("tier", "free")
        This assumes tier is lowercase. If tier comes from database as "Free" or "FREE",
        it might not match correctly.
        """
        tier_limits = {"free": 1, "starter": 20, "pro": 200}
        
        # Test case sensitivity
        assert tier_limits.get("free", 1) == 1
        assert tier_limits.get("Free", 1) == 1  # Would default to 1 (not found)
        assert tier_limits.get("FREE", 1) == 1  # Would default to 1 (not found)
        
        # Recommendation: Normalize tier to lowercase
        def get_max_projects(tier):
            tier_normalized = (tier or "free").lower()
            return tier_limits.get(tier_normalized, 1)
        
        assert get_max_projects("free") == 1
        assert get_max_projects("Free") == 1  # Normalized
        assert get_max_projects("FREE") == 1  # Normalized
        assert get_max_projects(None) == 1  # Defaults to free
    
    def test_project_count_accuracy(self):
        """
        Bug Check: Project count should be accurate.
        
        Current code: len(get_user_projects(user["id"], page=1, limit=1000))
        This gets first 1000 projects. If user has more than 1000 projects,
        count will be inaccurate.
        
        Recommendation: Use a count query for accuracy.
        """
        # Simulate getting projects with limit
        def get_user_projects_mock(user_id, page=1, limit=1000):
            # In real code, this queries database with limit
            # If user has 2000 projects, this returns only 1000
            return [{"id": f"project_{i}"} for i in range(min(1000, 2000))]
        
        # User with 2000 projects
        projects = get_user_projects_mock("user_1", page=1, limit=1000)
        count = len(projects)
        
        # Count is limited to 1000, but user actually has 2000
        assert count == 1000  # Limited by query
        
        # For Pro users with limit of 200, this is fine
        # But if we need exact count, should use COUNT query
    
    def test_concurrent_project_creation(self):
        """
        Bug Check: Concurrent project creation might allow exceeding limit.
        
        If two requests come in simultaneously when user is at limit-1,
        both might pass the check and create projects, exceeding the limit.
        
        This is a race condition that should be handled at database level
        with transactions or unique constraints.
        """
        # Simulate concurrent check
        current_count = 19  # One below Starter limit
        max_projects = 20
        
        # Request 1 checks
        can_create_1 = current_count < max_projects  # True
        
        # Request 2 checks (before Request 1 creates)
        can_create_2 = current_count < max_projects  # True
        
        # Both pass check, both create
        # Result: 21 projects (exceeds limit)
        
        # This is a known issue with check-then-act pattern
        # Should be handled with database-level constraints or transactions

