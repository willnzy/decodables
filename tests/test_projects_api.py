"""
Tests for Projects API endpoints (PRD v3.2)
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app import app
from routers.projects import create_project, update_project, ProjectCreate, ProjectUpdate
from dependencies import get_current_user


@pytest.fixture
def client():
    return TestClient(app)


class TestProjectCreation:
    """Test project creation with tier limits (PRD v3.2)"""
    
    @patch('routers.projects.get_current_user')
    @patch('routers.projects.get_user_projects')
    @patch('routers.projects.db_create_project')
    def test_create_project_free_under_limit(self, mock_create, mock_get_projects, mock_get_user):
        """Free user can create 1 project"""
        mock_get_user.return_value = {
            "id": "user_free_123",
            "tier": "free",
        }
        mock_get_projects.return_value = []  # No existing projects
        
        result = mock_create.return_value = {"id": "project_1", "title": "Test"}
        
        req = ProjectCreate(title="Test Project")
        
        response = create_project(req, mock_get_user.return_value)
        assert response == result
        mock_create.assert_called_once()
    
    @patch('routers.projects.get_current_user')
    @patch('routers.projects.get_user_projects')
    def test_create_project_free_limit_reached(self, mock_get_projects, mock_get_user):
        """Free user cannot create more than 1 project"""
        mock_get_user.return_value = {
            "id": "user_free_123",
            "tier": "free",
        }
        mock_get_projects.return_value = [{"id": "project_1"}]  # Already has 1 project
        
        req = ProjectCreate(title="Test Project")
        
        with pytest.raises(HTTPException) as exc_info:
            create_project(req, mock_get_user.return_value)
        
        assert exc_info.value.status_code == 403
        assert "maximum number of projects (1)" in str(exc_info.value.detail)
    
    @patch('routers.projects.get_current_user')
    @patch('routers.projects.get_user_projects')
    def test_create_project_starter_limit_reached(self, mock_get_projects, mock_get_user):
        """Starter user cannot create more than 20 projects"""
        mock_get_user.return_value = {
            "id": "user_starter_123",
            "tier": "starter",
        }
        # Create 20 projects
        mock_get_projects.return_value = [{"id": f"project_{i}"} for i in range(20)]
        
        req = ProjectCreate(title="Test Project")
        
        with pytest.raises(HTTPException) as exc_info:
            create_project(req, mock_get_user.return_value)
        
        assert exc_info.value.status_code == 403
        assert "maximum number of projects (20)" in str(exc_info.value.detail)
    
    @patch('routers.projects.get_current_user')
    @patch('routers.projects.get_user_projects')
    def test_create_project_pro_limit_reached(self, mock_get_projects, mock_get_user):
        """Pro user cannot create more than 200 projects"""
        mock_get_user.return_value = {
            "id": "user_pro_123",
            "tier": "pro",
        }
        # Create 200 projects
        mock_get_projects.return_value = [{"id": f"project_{i}"} for i in range(200)]
        
        req = ProjectCreate(title="Test Project")
        
        with pytest.raises(HTTPException) as exc_info:
            create_project(req, mock_get_user.return_value)
        
        assert exc_info.value.status_code == 403
        assert "maximum number of projects (200)" in str(exc_info.value.detail)


class TestProjectUpdate:
    """Test project update with Free 7-day trial check (PRD v3.2)"""
    
    @patch('routers.projects.get_current_user')
    @patch('routers.projects.get_user_projects')
    @patch('routers.projects.save_project')
    def test_update_project_free_within_trial(self, mock_save, mock_get_projects, mock_get_user):
        """Free user can update project within 7-day trial"""
        mock_get_user.return_value = {
            "id": "user_free_123",
            "tier": "free",
            "created_at": datetime.now(timezone.utc).isoformat(),  # Just created
        }
        mock_get_projects.return_value = [{"id": "project_1", "created_at": datetime.now(timezone.utc).isoformat()}]
        
        req = ProjectUpdate(canvas_data={"test": "data"})
        
        response = update_project("project_1", req, mock_get_user.return_value)
        assert response["status"] == "saved"
        mock_save.assert_called_once()
    
    @patch('routers.projects.get_current_user')
    def test_update_project_free_trial_expired(self, mock_get_user):
        """Free user cannot update project after 7-day trial expires"""
        mock_get_user.return_value = {
            "id": "user_free_expired_123",
            "tier": "free",
            "created_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),  # 8 days ago
        }
        
        req = ProjectUpdate(canvas_data={"test": "data"})
        
        with pytest.raises(HTTPException) as exc_info:
            update_project("project_1", req, mock_get_user.return_value)
        
        assert exc_info.value.status_code == 403
        assert "7-day trial period has expired" in str(exc_info.value.detail)
    
    @patch('routers.projects.get_current_user')
    @patch('routers.projects.get_user_projects')
    def test_update_project_downgraded_limit_exceeded(self, mock_get_projects, mock_get_user):
        """User who downgraded cannot edit projects exceeding new tier limit"""
        mock_get_user.return_value = {
            "id": "user_starter_123",
            "tier": "starter",  # Downgraded from Pro
        }
        # User has 25 projects (exceeds Starter limit of 20)
        projects = [
            {"id": f"project_{i}", "created_at": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat()}
            for i in range(25)
        ]
        mock_get_projects.return_value = projects
        
        req = ProjectUpdate(canvas_data={"test": "data"})
        
        # Try to edit project_21 (not in top 20 by creation date)
        with pytest.raises(HTTPException) as exc_info:
            update_project("project_21", req, mock_get_user.return_value)
        
        assert exc_info.value.status_code == 403
        assert "exceeded the project limit" in str(exc_info.value.detail)
    
    @patch('routers.projects.get_current_user')
    @patch('routers.projects.get_user_projects')
    @patch('routers.projects.save_project')
    def test_update_project_downgraded_within_limit(self, mock_save, mock_get_projects, mock_get_user):
        """User who downgraded can edit projects within new tier limit"""
        mock_get_user.return_value = {
            "id": "user_starter_123",
            "tier": "starter",
        }
        # User has 25 projects, but editing project_5 (within top 20)
        projects = [
            {"id": f"project_{i}", "created_at": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat()}
            for i in range(25)
        ]
        mock_get_projects.return_value = projects
        
        req = ProjectUpdate(canvas_data={"test": "data"})
        
        response = update_project("project_5", req, mock_get_user.return_value)
        assert response["status"] == "saved"
        mock_save.assert_called_once()

