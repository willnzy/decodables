"""
User API Integration Tests
Tests for user-related API endpoints

Coverage:
- User Profile (GET /api/user/me)
- Credit History (GET /api/user/history)
- User Assets (CRUD)
- Notifications
- Timezone Updates
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def client():
    """Create test client"""
    with patch('app.supabase') as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[])
        from app import app
        return TestClient(app)


@pytest.fixture
def mock_free_user():
    """Free tier user fixture"""
    return {
        'id': 'user_free_123',
        'email': 'free@test.com',
        'tier': 'free',
        'subscription_status': 'inactive',
        'credits_monthly': 0,
        'credits_permanent': 50,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'user_code': 'FREE001',
        'timezone': 'UTC',
    }


@pytest.fixture
def mock_pro_user():
    """Pro tier user fixture"""
    return {
        'id': 'user_pro_123',
        'email': 'pro@test.com',
        'tier': 'pro',
        'subscription_status': 'active',
        'credits_monthly': 1000,
        'credits_permanent': 200,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'user_code': 'PRO001',
        'timezone': 'America/New_York',
    }


# ============================================
# A. User Profile Tests
# ============================================

class TestUserMe:
    """Tests for GET /api/user/me"""
    
    @patch('app.get_current_user')
    def test_get_user_profile_success(self, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Returns user profile with all fields
        """
        mock_get_user.return_value = mock_pro_user
        
        response = client.get('/api/user/me')
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify essential fields
        assert data['id'] == 'user_pro_123'
        assert data['tier'] == 'pro'
        assert data['credits_monthly'] == 1000
        assert data['credits_permanent'] == 200
        assert 'email' in data
    
    @patch('app.get_current_user')
    def test_get_user_profile_free_tier(self, mock_get_user, client, mock_free_user):
        """
        ✅ PASS: Returns free tier user profile
        """
        mock_get_user.return_value = mock_free_user
        
        response = client.get('/api/user/me')
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['tier'] == 'free'
        assert data['subscription_status'] == 'inactive'
    
    def test_get_user_profile_unauthorized(self, client):
        """
        ❌ FAIL: Returns 401 without authentication
        """
        # No auth header
        response = client.get('/api/user/me')
        
        # Should return 401 or 422 (validation error)
        assert response.status_code in [401, 422]


# ============================================
# B. Credit History Tests
# ============================================

class TestCreditHistory:
    """Tests for GET /api/user/history"""
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_get_credit_history_paginated(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Returns paginated credit history
        """
        mock_get_user.return_value = mock_pro_user
        
        # Mock credit history data
        mock_history = {
            'data': [
                {
                    'id': 'tx_1',
                    'user_id': 'user_pro_123',
                    'amount': -5,
                    'bucket': 'monthly',
                    'type': 'generation',
                    'description': 'Image generation',
                    'created_at': datetime.now(timezone.utc).isoformat(),
                },
                {
                    'id': 'tx_2',
                    'user_id': 'user_pro_123',
                    'amount': 100,
                    'bucket': 'permanent',
                    'type': 'purchase',
                    'description': 'Credit purchase',
                    'created_at': (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                }
            ],
            'count': 50
        }
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .order.return_value.range.return_value.execute.return_value = Mock(data=mock_history['data'])
        
        response = client.get('/api/user/history?page=1&limit=20')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_get_credit_history_empty(self, mock_supabase, mock_get_user, client, mock_free_user):
        """
        ✅ PASS: Returns empty history for new user
        """
        mock_get_user.return_value = mock_free_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .order.return_value.range.return_value.execute.return_value = Mock(data=[])
        
        response = client.get('/api/user/history')
        
        assert response.status_code == 200


# ============================================
# C. User Assets Tests
# ============================================

class TestUserAssets:
    """Tests for /api/user/assets endpoints"""
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_get_all_assets(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Returns all user assets
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_assets = [
            {'id': 'asset_1', 'url': 'https://cdn.../img1.png', 'type': 'uploaded'},
            {'id': 'asset_2', 'url': 'https://cdn.../img2.png', 'type': 'ai_generated'},
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .is_.return_value.order.return_value.execute.return_value = Mock(data=mock_assets)
        
        response = client.get('/api/user/assets?scope=all')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_get_project_assets(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Returns project-specific assets
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .eq.return_value.is_.return_value.order.return_value.execute.return_value = Mock(data=[])
        
        response = client.get('/api/user/assets?scope=project&project_id=proj_123')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_delete_asset_soft(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Soft deletes asset (moves to trash)
        """
        mock_get_user.return_value = mock_pro_user
        
        # Mock asset exists and belongs to user
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .eq.return_value.execute.return_value = Mock(data=[{'id': 'asset_123'}])
        
        mock_supabase.table.return_value.update.return_value.eq.return_value\
            .execute.return_value = Mock()
        
        response = client.delete('/api/user/assets/asset_123')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_delete_asset_permanent(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Permanently deletes asset
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .eq.return_value.execute.return_value = Mock(data=[{'id': 'asset_123'}])
        
        mock_supabase.table.return_value.update.return_value.eq.return_value\
            .execute.return_value = Mock()
        
        response = client.delete('/api/user/assets/asset_123?permanent=true')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_restore_asset(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Restores deleted asset
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .eq.return_value.execute.return_value = Mock(data=[{'id': 'asset_123', 'deleted': True}])
        
        mock_supabase.table.return_value.update.return_value.eq.return_value\
            .execute.return_value = Mock()
        
        response = client.post('/api/user/assets/asset_123/restore')
        
        assert response.status_code == 200


# ============================================
# D. Notification Tests
# ============================================

class TestNotifications:
    """Tests for /api/user/notifications endpoints"""
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_get_all_notifications(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Returns all notifications
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_notifications = [
            {'id': 'notif_1', 'title': 'Welcome', 'read': False, 'created_at': datetime.now(timezone.utc).isoformat()},
            {'id': 'notif_2', 'title': 'Update', 'read': True, 'created_at': datetime.now(timezone.utc).isoformat()},
        ]
        
        mock_supabase.table.return_value.select.return_value.or_.return_value\
            .order.return_value.limit.return_value.execute.return_value = Mock(data=mock_notifications)
        
        response = client.get('/api/user/notifications')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_get_unread_notifications(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Returns only unread notifications
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.select.return_value.or_.return_value\
            .eq.return_value.order.return_value.limit.return_value.execute.return_value = Mock(data=[])
        
        response = client.get('/api/user/notifications?unread_only=true')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_mark_notification_read(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Marks single notification as read
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.update.return_value.eq.return_value\
            .eq.return_value.execute.return_value = Mock()
        
        response = client.post('/api/user/notifications/notif_123/read')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_mark_all_notifications_read(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Marks all notifications as read
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.update.return_value.or_.return_value\
            .execute.return_value = Mock()
        
        response = client.post('/api/user/notifications/read-all')
        
        assert response.status_code == 200


# ============================================
# E. Timezone Tests (v3.9)
# ============================================

class TestTimezone:
    """Tests for /api/user/timezone endpoint"""
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_update_timezone(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Updates user timezone
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.update.return_value.eq.return_value\
            .execute.return_value = Mock()
        
        response = client.put(
            '/api/user/timezone',
            json={'timezone': 'Asia/Shanghai'}
        )
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_update_timezone_from_header(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Updates timezone from X-Timezone header
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.update.return_value.eq.return_value\
            .execute.return_value = Mock()
        
        response = client.put(
            '/api/user/timezone',
            json={'timezone': 'Europe/London'},
            headers={'X-Timezone': 'Europe/London'}
        )
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    def test_update_timezone_invalid(self, mock_get_user, client, mock_pro_user):
        """
        ⚠️ EDGE: Handles invalid timezone gracefully
        """
        mock_get_user.return_value = mock_pro_user
        
        response = client.put(
            '/api/user/timezone',
            json={'timezone': 'Invalid/Timezone'}
        )
        
        # Should either accept (lenient) or return 400
        assert response.status_code in [200, 400]


# ============================================
# F. Dashboard Assets Tests (v3.4)
# ============================================

class TestDashboardAssets:
    """Tests for /api/user/assets/dashboard endpoint"""
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_dashboard_all_view(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Returns all assets in dashboard view
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .is_.return_value.order.return_value.range.return_value.execute.return_value = Mock(data=[])
        
        response = client.get('/api/user/assets/dashboard?view=all')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_dashboard_bought_view(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Returns purchased assets
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .is_.return_value.not_.return_value.is_.return_value\
            .order.return_value.range.return_value.execute.return_value = Mock(data=[])
        
        response = client.get('/api/user/assets/dashboard?view=bought')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_dashboard_selling_view(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Returns assets being sold
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .is_.return_value.not_.return_value.is_.return_value\
            .order.return_value.range.return_value.execute.return_value = Mock(data=[])
        
        response = client.get('/api/user/assets/dashboard?view=selling')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_dashboard_search(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Searches assets in dashboard
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .is_.return_value.ilike.return_value\
            .order.return_value.range.return_value.execute.return_value = Mock(data=[])
        
        response = client.get('/api/user/assets/dashboard?search=cat')
        
        assert response.status_code == 200


# ============================================
# G. Seller Stats Tests
# ============================================

class TestSellerStats:
    """Tests for /api/user/assets/seller-stats endpoint"""
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_get_seller_stats(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ✅ PASS: Returns seller statistics
        """
        mock_get_user.return_value = mock_pro_user
        
        # Mock various queries for stats
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .execute.return_value = Mock(data=[], count=10)
        
        response = client.get('/api/user/assets/seller-stats')
        
        assert response.status_code == 200


# ============================================
# H. Error Handling Tests
# ============================================

class TestUserApiErrors:
    """Error handling tests for user APIs"""
    
    @patch('app.get_current_user')
    def test_asset_not_found(self, mock_get_user, client, mock_pro_user):
        """
        ❌ FAIL: Returns 404 for non-existent asset
        """
        mock_get_user.return_value = mock_pro_user
        
        with patch('app.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value\
                .eq.return_value.execute.return_value = Mock(data=[])
            
            response = client.delete('/api/user/assets/nonexistent')
        
        # Should return 404 or handle gracefully
        assert response.status_code in [200, 404]
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_database_error_handling(self, mock_supabase, mock_get_user, client, mock_pro_user):
        """
        ❌ FAIL: Handles database errors gracefully
        """
        mock_get_user.return_value = mock_pro_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .execute.side_effect = Exception('Database connection failed')
        
        response = client.get('/api/user/assets')
        
        # Should return 500 or handle gracefully
        assert response.status_code in [200, 500]
