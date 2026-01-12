"""
Unit tests for ThemesRepository (Infrastructure Layer).

Tests Supabase repository implementation for Theme System v2.1.

@module tests.domains.themes.test_themes_repository
@version 2.1.0
"""
import pytest
import sys
import os
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, AsyncMock

# Import the repository directly to avoid import chain issues
import importlib.util

_repo_path = os.path.join(
    os.path.dirname(__file__),
    "../../../infrastructure/repositories/themes_repository.py"
)
_spec = importlib.util.spec_from_file_location("themes_repository", _repo_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
SupabaseThemesRepository = _module.SupabaseThemesRepository


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_supabase():
    """Create mock Supabase client."""
    client = MagicMock()
    return client


@pytest.fixture
def repository(mock_supabase):
    """Create ThemesRepository instance with mock client."""
    return SupabaseThemesRepository(mock_supabase)


@pytest.fixture
def sample_theme_data():
    """Sample theme data for testing."""
    return {
        "id": "theme-001",
        "name": "World Book Day",
        "date": "2026-04-23",
        "category": "notable",
        "priority": 75,
        "slogan": "Read, Dream, Grow",
        "description": "Celebrating the joy of reading",
        "is_active": True,
        "is_deleted": False,
        "review_status": "pending",
        "ai_generated": True,
        "ai_alternatives": [
            {"id": "A", "name": "World Book Day"},
            {"id": "B", "name": "Reading Festival"},
        ],
        "selected_alternative_id": "A",
        "created_at": "2026-01-12T10:00:00Z",
        "updated_at": "2026-01-12T10:00:00Z",
    }


# ==========================================
# Read Operations Tests
# ==========================================

class TestGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, repository, mock_supabase, sample_theme_data):
        """Successfully get theme by ID."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = sample_theme_data
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id("theme-001")

        # Assert
        assert result == sample_theme_data
        mock_supabase.table.assert_called_with("daily_themes")

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_supabase):
        """Return None when theme not found."""
        # Arrange
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("PGRST116: Not found")

        # Act
        result = await repository.get_by_id("nonexistent-id")

        # Assert
        assert result is None


class TestGetByDate:
    """Tests for get_by_date method."""

    @pytest.mark.asyncio
    async def test_get_by_date_success(self, repository, mock_supabase, sample_theme_data):
        """Successfully get theme by date."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = [sample_theme_data]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        # Act
        result = await repository.get_by_date(date(2026, 4, 23))

        # Assert
        assert result == sample_theme_data
        mock_supabase.table.assert_called_with("daily_themes")

    @pytest.mark.asyncio
    async def test_get_by_date_not_found(self, repository, mock_supabase):
        """Return None when no theme for date."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        # Act
        result = await repository.get_by_date(date(2026, 12, 31))

        # Assert
        assert result is None


class TestListAll:
    """Tests for list_all method."""

    @pytest.mark.asyncio
    async def test_list_all_basic(self, repository, mock_supabase, sample_theme_data):
        """List all themes with default pagination."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = [sample_theme_data]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        # Act
        result = await repository.list_all()

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "World Book Day"

    @pytest.mark.asyncio
    async def test_list_all_with_filters(self, repository, mock_supabase, sample_theme_data):
        """List themes with category filter."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = [sample_theme_data]

        # Build mock chain
        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.lte.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = mock_result

        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_query

        # Act
        result = await repository.list_all(
            offset=0,
            limit=10,
            filters={
                "category": "notable",
                "review_status": "pending",
                "date_from": "2026-01-01",
                "date_to": "2026-12-31",
            }
        )

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_all_empty(self, repository, mock_supabase):
        """Return empty list when no themes."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        # Act
        result = await repository.list_all()

        # Assert
        assert result == []


class TestCountAll:
    """Tests for count_all method."""

    @pytest.mark.asyncio
    async def test_count_all_basic(self, repository, mock_supabase):
        """Count all themes."""
        # Arrange
        mock_result = MagicMock()
        mock_result.count = 42
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        # Act
        result = await repository.count_all()

        # Assert
        assert result == 42

    @pytest.mark.asyncio
    async def test_count_all_with_filters(self, repository, mock_supabase):
        """Count themes with filters."""
        # Arrange
        mock_result = MagicMock()
        mock_result.count = 10

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_result

        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_query

        # Act
        result = await repository.count_all(filters={"category": "holiday"})

        # Assert
        assert result == 10


# ==========================================
# Write Operations Tests
# ==========================================

class TestCreate:
    """Tests for create method."""

    @pytest.mark.asyncio
    async def test_create_success(self, repository, mock_supabase):
        """Successfully create a theme."""
        # Arrange
        new_theme = {
            "name": "New Theme",
            "date": "2026-05-01",
            "category": "special",
        }
        created_theme = {**new_theme, "id": "theme-new"}

        mock_result = MagicMock()
        mock_result.data = [created_theme]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        # Act
        result = await repository.create(new_theme)

        # Assert
        assert result["id"] == "theme-new"
        assert result["name"] == "New Theme"
        mock_supabase.table.return_value.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_adds_timestamps(self, repository, mock_supabase):
        """Create adds created_at and updated_at timestamps."""
        # Arrange
        new_theme = {"name": "Test Theme"}
        mock_result = MagicMock()
        mock_result.data = [{"id": "theme-1", **new_theme}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        # Act
        await repository.create(new_theme)

        # Assert
        insert_call = mock_supabase.table.return_value.insert.call_args
        inserted_data = insert_call[0][0]
        assert "created_at" in inserted_data
        assert "updated_at" in inserted_data


class TestUpdate:
    """Tests for update method."""

    @pytest.mark.asyncio
    async def test_update_success(self, repository, mock_supabase, sample_theme_data):
        """Successfully update a theme."""
        # Arrange
        updated_data = {**sample_theme_data, "name": "Updated Theme"}
        mock_result = MagicMock()
        mock_result.data = [updated_data]
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        # Act
        result = await repository.update("theme-001", {"name": "Updated Theme"})

        # Assert
        assert result["name"] == "Updated Theme"

    @pytest.mark.asyncio
    async def test_update_not_found(self, repository, mock_supabase):
        """Return None when theme not found."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        # Act
        result = await repository.update("nonexistent", {"name": "Test"})

        # Assert
        assert result is None


class TestDelete:
    """Tests for delete method (soft delete)."""

    @pytest.mark.asyncio
    async def test_delete_success(self, repository, mock_supabase):
        """Successfully soft delete a theme."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = [{"id": "theme-001", "is_deleted": True}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        # Act
        result = await repository.delete("theme-001")

        # Assert
        assert result is True
        # Verify soft delete fields
        update_call = mock_supabase.table.return_value.update.call_args
        update_data = update_call[0][0]
        assert update_data["is_deleted"] is True
        assert "deleted_at" in update_data

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_supabase):
        """Return False when theme not found."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        # Act
        result = await repository.delete("nonexistent")

        # Assert
        assert result is False


# ==========================================
# Review Operations Tests
# ==========================================

class TestBatchUpdateReviewStatus:
    """Tests for batch_update_review_status method."""

    @pytest.mark.asyncio
    async def test_batch_update_success(self, repository, mock_supabase):
        """Successfully batch update review status."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = [{"id": "theme-1"}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        # Act
        result = await repository.batch_update_review_status(
            theme_ids=["theme-1", "theme-2", "theme-3"],
            review_status="reviewed",
            reviewed_by="admin-001",
        )

        # Assert
        assert result == 3  # All 3 updated successfully

    @pytest.mark.asyncio
    async def test_batch_update_partial(self, repository, mock_supabase):
        """Handle partial batch update (some not found)."""
        # Arrange
        def mock_update(*args, **kwargs):
            mock_result = MagicMock()
            # First two succeed, third fails (not found)
            call_count = mock_supabase.table.return_value.update.call_count
            if call_count <= 2:
                mock_result.data = [{"id": f"theme-{call_count}"}]
            else:
                mock_result.data = []
            return mock_result

        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.side_effect = mock_update

        # Act
        result = await repository.batch_update_review_status(
            theme_ids=["theme-1", "theme-2", "nonexistent"],
            review_status="reviewed",
            reviewed_by="admin-001",
        )

        # Assert
        assert result == 2  # Only 2 updated


# ==========================================
# Statistics Operations Tests
# ==========================================

class TestGetExistingDates:
    """Tests for get_existing_dates method."""

    @pytest.mark.asyncio
    async def test_get_existing_dates_success(self, repository, mock_supabase):
        """Successfully get existing dates."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = [
            {"date": "2026-01-15"},
            {"date": "2026-01-20"},
            {"date": "2026-01-25"},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = mock_result

        # Act
        result = await repository.get_existing_dates(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        # Assert
        assert len(result) == 3
        assert date(2026, 1, 15) in result
        assert date(2026, 1, 20) in result
        assert date(2026, 1, 25) in result

    @pytest.mark.asyncio
    async def test_get_existing_dates_empty(self, repository, mock_supabase):
        """Return empty set when no themes."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = mock_result

        # Act
        result = await repository.get_existing_dates(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        # Assert
        assert result == set()


class TestGetReviewStatusStats:
    """Tests for get_review_status_stats method."""

    @pytest.mark.asyncio
    async def test_get_review_status_stats_success(self, repository, mock_supabase):
        """Successfully get review status statistics."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = [
            {"review_status": "pending"},
            {"review_status": "pending"},
            {"review_status": "auto_approved"},
            {"review_status": "reviewed"},
            {"review_status": "reviewed"},
            {"review_status": "reviewed"},
            {"review_status": "rejected"},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = mock_result

        # Act
        result = await repository.get_review_status_stats(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        # Assert
        assert result["pending"] == 2
        assert result["auto_approved"] == 1
        assert result["reviewed"] == 3
        assert result["rejected"] == 1

    @pytest.mark.asyncio
    async def test_get_review_status_stats_empty(self, repository, mock_supabase):
        """Return zero counts when no themes."""
        # Arrange
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = mock_result

        # Act
        result = await repository.get_review_status_stats(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        # Assert
        assert result == {
            "pending": 0,
            "auto_approved": 0,
            "reviewed": 0,
            "rejected": 0,
        }
