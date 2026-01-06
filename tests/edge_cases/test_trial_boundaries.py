"""
试用期边界条件测试

测试 30 天试用期的边界情况

@module tests/edge_cases/test_trial_boundaries
@version v3.24
"""

import pytest
from datetime import datetime, timezone, timedelta


TRIAL_DAYS = 30


class TestTrialBoundaries:
    """测试试用期边界条件"""
    
    @staticmethod
    def days_since_registration(created_at):
        """计算注册天数"""
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - created_at).total_seconds() / (24 * 3600)
    
    @staticmethod
    def is_in_trial(days):
        """判断是否在试用期"""
        return days <= TRIAL_DAYS
    
    def test_boundary_day_0(self):
        """【边界条件】刚注册（第0天）"""
        created_at = datetime.now(timezone.utc)
        days = self.days_since_registration(created_at)
        
        assert days < 1
        assert self.is_in_trial(days) is True
    
    def test_boundary_day_1(self):
        """【边界条件】第1天"""
        created_at = datetime.now(timezone.utc) - timedelta(days=1)
        days = self.days_since_registration(created_at)
        
        assert 0.9 < days < 1.1
        assert self.is_in_trial(days) is True
    
    def test_boundary_day_29(self):
        """【边界条件】第29天"""
        created_at = datetime.now(timezone.utc) - timedelta(days=29)
        days = self.days_since_registration(created_at)
        
        assert 28.9 < days < 29.1
        assert self.is_in_trial(days) is True
    
    def test_boundary_day_29_23_hours(self):
        """【边界条件】29天23小时"""
        created_at = datetime.now(timezone.utc) - timedelta(days=29, hours=23)
        days = self.days_since_registration(created_at)
        
        assert days < 30
        assert self.is_in_trial(days) is True
    
    def test_boundary_day_30_exact(self):
        """【边界条件】正好第30天 - 仍在试用期内"""
        # 使用 29.99 天来测试 <= 30 的边界
        created_at = datetime.now(timezone.utc) - timedelta(days=29, hours=23, minutes=59)
        days = self.days_since_registration(created_at)
        
        assert 29.9 < days < 30.1
        assert self.is_in_trial(days) is True  # <= 30 仍在试用期
    
    def test_boundary_day_30_1_hour(self):
        """【边界条件】30天1小时 - 试用期已过"""
        created_at = datetime.now(timezone.utc) - timedelta(days=30, hours=1)
        days = self.days_since_registration(created_at)
        
        assert days > 30
        assert self.is_in_trial(days) is False
    
    def test_boundary_day_31(self):
        """【边界条件】第31天 - 试用期已过"""
        created_at = datetime.now(timezone.utc) - timedelta(days=31)
        days = self.days_since_registration(created_at)
        
        assert 30.9 < days < 31.1
        assert self.is_in_trial(days) is False
    
    def test_boundary_very_old_user(self):
        """【边界条件】老用户（60天前注册）"""
        created_at = datetime.now(timezone.utc) - timedelta(days=60)
        days = self.days_since_registration(created_at)
        
        assert days > 30
        assert self.is_in_trial(days) is False


class TestTrialDateParsing:
    """测试日期解析边界条件"""
    
    def test_iso_format_with_z(self):
        """【边界条件】ISO 格式带 Z 后缀"""
        date_str = "2024-01-01T00:00:00Z"
        parsed = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        
        assert parsed.tzinfo is not None
    
    def test_iso_format_with_timezone(self):
        """【边界条件】ISO 格式带时区"""
        date_str = "2024-01-01T00:00:00+00:00"
        parsed = datetime.fromisoformat(date_str)
        
        assert parsed.tzinfo is not None
    
    def test_iso_format_without_timezone(self):
        """【边界条件】ISO 格式无时区"""
        date_str = "2024-01-01T00:00:00"
        parsed = datetime.fromisoformat(date_str)
        
        # 无时区时需要手动添加
        assert parsed.tzinfo is None
        parsed_utc = parsed.replace(tzinfo=timezone.utc)
        assert parsed_utc.tzinfo is not None
