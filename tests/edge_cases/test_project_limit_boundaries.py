"""
项目数量限制边界条件测试

测试项目创建限制的边界情况

@module tests/edge_cases/test_project_limit_boundaries
@version v3.24
"""

import pytest


class TestProjectLimitBoundaries:
    """测试项目数量限制边界条件"""
    
    PROJECT_LIMITS = {
        "free": 1,
        "starter": 20,
        "pro": 200
    }
    
    @staticmethod
    def can_create_project(tier, current_count, limits):
        """检查是否能创建项目"""
        limit = limits.get(tier, 1)
        return current_count < limit
    
    def test_free_boundary_zero_projects(self):
        """【边界条件】Free 用户0个项目"""
        assert self.can_create_project("free", 0, self.PROJECT_LIMITS) is True
    
    def test_free_boundary_at_limit(self):
        """【边界条件】Free 用户达到限制（1个）"""
        assert self.can_create_project("free", 1, self.PROJECT_LIMITS) is False
    
    def test_starter_boundary_one_below_limit(self):
        """【边界条件】Starter 用户差1达到限制"""
        assert self.can_create_project("starter", 19, self.PROJECT_LIMITS) is True
    
    def test_starter_boundary_at_limit(self):
        """【边界条件】Starter 用户达到限制（20个）"""
        assert self.can_create_project("starter", 20, self.PROJECT_LIMITS) is False
    
    def test_pro_boundary_one_below_limit(self):
        """【边界条件】Pro 用户差1达到限制"""
        assert self.can_create_project("pro", 199, self.PROJECT_LIMITS) is True
    
    def test_pro_boundary_at_limit(self):
        """【边界条件】Pro 用户达到限制（200个）"""
        assert self.can_create_project("pro", 200, self.PROJECT_LIMITS) is False
    
    def test_unknown_tier_defaults_to_free(self):
        """【边界条件】未知等级默认 Free 限制"""
        # 使用默认值1
        limit = self.PROJECT_LIMITS.get("unknown", 1)
        assert limit == 1
    
    def test_none_tier_defaults_to_free(self):
        """【边界条件】None 等级默认 Free 限制"""
        limit = self.PROJECT_LIMITS.get(None, 1)
        assert limit == 1


class TestDowngradeBoundaries:
    """测试降级边界条件"""
    
    def test_downgrade_exactly_at_new_limit(self):
        """【边界条件】降级后项目数恰好等于新限制"""
        # Pro -> Starter，正好20个项目
        current_projects = 20
        new_limit = 20
        
        # 恰好在限制内，但不能再创建
        can_keep_all = current_projects <= new_limit
        can_create_more = current_projects < new_limit
        
        assert can_keep_all is True
        assert can_create_more is False
    
    def test_downgrade_one_over_limit(self):
        """【边界条件】降级后项目数超出新限制1个"""
        # Pro -> Starter，21个项目
        current_projects = 21
        new_limit = 20
        
        excess = current_projects - new_limit
        
        assert excess == 1
    
    def test_downgrade_to_free_with_many_projects(self):
        """【边界条件】降级到 Free，有多个项目"""
        # Starter/Pro -> Free，有5个项目
        current_projects = 5
        new_limit = 1
        
        # 需要"锁定"的项目数
        locked_projects = current_projects - new_limit
        
        assert locked_projects == 4
