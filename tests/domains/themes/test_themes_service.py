"""
Unit tests for ThemesService (Domain Layer).

Tests business logic for Theme System v2.1.

@module tests.domains.themes.test_themes_service
@version 2.1.0
"""
import pytest
import sys
import os
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock, patch

# Import modules directly to avoid import chain issues
import importlib.util

def _load_module(module_name, relative_path):
    """Load a module directly by path."""
    module_path = os.path.join(os.path.dirname(__file__), relative_path)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load constants module
_constants = _load_module("themes_constants", "../../../domains/themes/constants.py")
VALID_CATEGORIES = _constants.VALID_CATEGORIES
REVIEW_STATUS_PENDING = _constants.REVIEW_STATUS_PENDING
REVIEW_STATUS_REVIEWED = _constants.REVIEW_STATUS_REVIEWED
REVIEW_STATUS_REJECTED = _constants.REVIEW_STATUS_REJECTED
REVIEW_STATUS_AUTO_APPROVED = _constants.REVIEW_STATUS_AUTO_APPROVED
REVIEW_ACTION_APPROVE = _constants.REVIEW_ACTION_APPROVE
REVIEW_ACTION_REJECT = _constants.REVIEW_ACTION_REJECT
REVIEW_ACTION_SWITCH = _constants.REVIEW_ACTION_SWITCH

# Load service module - need to mock infrastructure import first
sys.modules['infrastructure'] = MagicMock()
sys.modules['infrastructure.repositories'] = MagicMock()
sys.modules['infrastructure.repositories.themes_repository'] = MagicMock()

_service = _load_module("themes_service", "../../../domains/themes/themes_service.py")
ThemesService = _service.ThemesService


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_db_client():
    """Create mock database client."""
    return MagicMock()


@pytest.fixture
def mock_repository():
    """Create mock ThemesRepository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_date = AsyncMock()
    repo.list_active_themes = AsyncMock()
    repo.list_all = AsyncMock()
    repo.count_all = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.batch_update_review_status = AsyncMock()
    repo.get_existing_dates = AsyncMock()
    repo.get_review_status_stats = AsyncMock()
    return repo


@pytest.fixture
def service(mock_db_client, mock_repository):
    """Create ThemesService with mocked repository."""
    svc = ThemesService(mock_db_client)
    svc.repository = mock_repository
    return svc


@pytest.fixture
def sample_theme():
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
            {"id": "A", "name": "World Book Day", "priority": 75},
            {"id": "B", "name": "Reading Festival", "priority": 60},
            {"id": "C", "name": "Literary Celebration", "priority": 55},
        ],
        "selected_alternative_id": "A",
        "ai_recommended_id": "A",
        "generation_history": [],
        "regenerate_count": 0,
    }


# ==========================================
# Read Operations Tests
# ==========================================

class TestGetThemeById:
    """Tests for get_theme_by_id method."""

    @pytest.mark.asyncio
    async def test_get_theme_by_id_success(self, service, mock_repository, sample_theme):
        """Successfully get theme by ID."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_theme

        # Act
        result = await service.get_theme_by_id("theme-001")

        # Assert
        assert result == sample_theme
        mock_repository.get_by_id.assert_called_once_with("theme-001")

    @pytest.mark.asyncio
    async def test_get_theme_by_id_not_found(self, service, mock_repository):
        """Return None when theme not found."""
        # Arrange
        mock_repository.get_by_id.return_value = None

        # Act
        result = await service.get_theme_by_id("nonexistent")

        # Assert
        assert result is None


class TestGetThemeByDate:
    """Tests for get_theme_by_date method."""

    @pytest.mark.asyncio
    async def test_get_theme_by_date_success(self, service, mock_repository, sample_theme):
        """Successfully get theme by date."""
        # Arrange
        mock_repository.get_by_date.return_value = sample_theme

        # Act
        result = await service.get_theme_by_date(date(2026, 4, 23))

        # Assert
        assert result == sample_theme


class TestListThemes:
    """Tests for list_themes method."""

    @pytest.mark.asyncio
    async def test_list_themes_success(self, service, mock_repository, sample_theme):
        """List themes with pagination."""
        # Arrange
        mock_repository.list_all.return_value = [sample_theme]
        mock_repository.count_all.return_value = 1

        # Act
        result = await service.list_themes(offset=0, limit=10)

        # Assert
        assert result["themes"] == [sample_theme]
        assert result["total"] == 1
        assert result["offset"] == 0
        assert result["limit"] == 10

    @pytest.mark.asyncio
    async def test_list_themes_with_filters(self, service, mock_repository, sample_theme):
        """List themes with filters."""
        # Arrange
        mock_repository.list_all.return_value = [sample_theme]
        mock_repository.count_all.return_value = 1
        filters = {"category": "notable", "review_status": "pending"}

        # Act
        result = await service.list_themes(offset=0, limit=10, filters=filters)

        # Assert
        mock_repository.list_all.assert_called_once_with(offset=0, limit=10, filters=filters)


class TestGetCurrentActiveTheme:
    """Tests for get_current_active_theme method."""

    @pytest.mark.asyncio
    async def test_get_current_active_theme_by_date(self, service, mock_repository):
        """Get active theme by specific date field."""
        # Arrange
        theme = {
            "id": "theme-001",
            "name": "Test Theme",
            "date": "2026-04-23",
            "is_active": True,
        }
        mock_repository.list_active_themes.return_value = [theme]

        # Act
        result = await service.get_current_active_theme(date(2026, 4, 23))

        # Assert
        assert result == theme

    @pytest.mark.asyncio
    async def test_get_current_active_theme_by_date_rule(self, service, mock_repository):
        """Get active theme by date rule."""
        # Arrange
        theme = {
            "id": "theme-001",
            "name": "Christmas",
            "date_rule": {"type": "fixed", "start": "12-24", "end": "12-26"},
            "is_active": True,
        }
        mock_repository.list_active_themes.return_value = [theme]

        # Act
        result = await service.get_current_active_theme(date(2026, 12, 25))

        # Assert
        assert result == theme

    @pytest.mark.asyncio
    async def test_get_current_active_theme_no_match(self, service, mock_repository):
        """Return None when no theme matches date."""
        # Arrange
        theme = {
            "id": "theme-001",
            "name": "Christmas",
            "date": "2026-12-25",
            "is_active": True,
        }
        mock_repository.list_active_themes.return_value = [theme]

        # Act
        result = await service.get_current_active_theme(date(2026, 7, 15))

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_active_theme_empty(self, service, mock_repository):
        """Return None when no active themes."""
        # Arrange
        mock_repository.list_active_themes.return_value = []

        # Act
        result = await service.get_current_active_theme(date(2026, 4, 23))

        # Assert
        assert result is None


# ==========================================
# Write Operations Tests
# ==========================================

class TestCreateTheme:
    """Tests for create_theme method."""

    @pytest.mark.asyncio
    async def test_create_theme_basic(self, service, mock_repository):
        """Create theme with basic fields."""
        # Arrange
        created = {"id": "theme-new", "name": "New Theme", "category": "holiday"}
        mock_repository.create.return_value = created

        # Act
        result = await service.create_theme(name="New Theme", category="holiday")

        # Assert
        assert result["id"] == "theme-new"
        mock_repository.create.assert_called_once()
        call_data = mock_repository.create.call_args[0][0]
        assert call_data["name"] == "New Theme"
        assert call_data["category"] == "holiday"

    @pytest.mark.asyncio
    async def test_create_theme_with_all_fields(self, service, mock_repository):
        """Create theme with all optional fields."""
        # Arrange
        created = {"id": "theme-new", "name": "Full Theme"}
        mock_repository.create.return_value = created

        # Act
        result = await service.create_theme(
            name="Full Theme",
            target_date=date(2026, 5, 1),
            category="notable",
            priority=80,
            description="A full theme",
            slogan="Read More",
            theme_config={"colors": {"primary": "#FF0000"}},
            name_i18n={"en": "Full Theme", "zh": "完整主题"},
            ai_generated=True,
            ai_alternatives=[{"id": "A", "name": "Alt A"}],
            review_status="auto_approved",
        )

        # Assert
        assert result["id"] == "theme-new"
        call_data = mock_repository.create.call_args[0][0]
        assert call_data["date"] == "2026-05-01"
        assert call_data["ai_generated"] is True

    @pytest.mark.asyncio
    async def test_create_theme_invalid_category(self, service, mock_repository):
        """Raise error for invalid category."""
        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await service.create_theme(name="Test", category="invalid_category")

        assert "Invalid category" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_theme_invalid_review_status(self, service, mock_repository):
        """Raise error for invalid review status."""
        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await service.create_theme(name="Test", review_status="invalid_status")

        assert "Invalid review_status" in str(exc.value)


class TestUpdateTheme:
    """Tests for update_theme method."""

    @pytest.mark.asyncio
    async def test_update_theme_success(self, service, mock_repository, sample_theme):
        """Successfully update a theme."""
        # Arrange
        updated = {**sample_theme, "name": "Updated Theme"}
        mock_repository.update.return_value = updated

        # Act
        result = await service.update_theme("theme-001", {"name": "Updated Theme"})

        # Assert
        assert result["name"] == "Updated Theme"

    @pytest.mark.asyncio
    async def test_update_theme_invalid_category(self, service, mock_repository):
        """Raise error for invalid category in update."""
        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await service.update_theme("theme-001", {"category": "invalid"})

        assert "Invalid category" in str(exc.value)


class TestDeleteTheme:
    """Tests for delete_theme method."""

    @pytest.mark.asyncio
    async def test_delete_theme_success(self, service, mock_repository):
        """Successfully delete a theme."""
        # Arrange
        mock_repository.delete.return_value = True

        # Act
        result = await service.delete_theme("theme-001")

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_theme_not_found(self, service, mock_repository):
        """Return False when theme not found."""
        # Arrange
        mock_repository.delete.return_value = False

        # Act
        result = await service.delete_theme("nonexistent")

        # Assert
        assert result is False


# ==========================================
# Review Operations Tests
# ==========================================

class TestReviewTheme:
    """Tests for review_theme method."""

    @pytest.mark.asyncio
    async def test_review_approve(self, service, mock_repository, sample_theme):
        """Approve a theme."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_theme
        updated = {**sample_theme, "review_status": REVIEW_STATUS_REVIEWED}
        mock_repository.update.return_value = updated

        # Act
        result = await service.review_theme(
            theme_id="theme-001",
            action=REVIEW_ACTION_APPROVE,
            admin_id="admin-001",
            notes="Looks good",
        )

        # Assert
        assert result["message"] == "Theme approved successfully"
        assert result["theme"]["review_status"] == REVIEW_STATUS_REVIEWED

    @pytest.mark.asyncio
    async def test_review_reject(self, service, mock_repository, sample_theme):
        """Reject a theme."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_theme
        updated = {**sample_theme, "review_status": REVIEW_STATUS_REJECTED}
        mock_repository.update.return_value = updated

        # Act
        result = await service.review_theme(
            theme_id="theme-001",
            action=REVIEW_ACTION_REJECT,
            admin_id="admin-001",
            notes="Not suitable",
        )

        # Assert
        assert result["message"] == "Theme rejected successfully"

    @pytest.mark.asyncio
    async def test_review_switch_alternative(self, service, mock_repository, sample_theme):
        """Switch to different alternative."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_theme
        updated = {**sample_theme, "selected_alternative_id": "B", "name": "Reading Festival"}
        mock_repository.update.return_value = updated

        # Act
        result = await service.review_theme(
            theme_id="theme-001",
            action=REVIEW_ACTION_SWITCH,
            admin_id="admin-001",
            alternative_id="B",
        )

        # Assert
        assert result["message"] == "Theme switched successfully"
        call_data = mock_repository.update.call_args[0][1]
        assert call_data["selected_alternative_id"] == "B"

    @pytest.mark.asyncio
    async def test_review_switch_missing_alternative_id(self, service, mock_repository, sample_theme):
        """Raise error when switch action missing alternative_id."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_theme

        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await service.review_theme(
                theme_id="theme-001",
                action=REVIEW_ACTION_SWITCH,
                admin_id="admin-001",
            )

        assert "alternative_id required" in str(exc.value)

    @pytest.mark.asyncio
    async def test_review_switch_invalid_alternative(self, service, mock_repository, sample_theme):
        """Raise error when alternative not found."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_theme

        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await service.review_theme(
                theme_id="theme-001",
                action=REVIEW_ACTION_SWITCH,
                admin_id="admin-001",
                alternative_id="Z",  # Not in alternatives
            )

        assert "Alternative Z not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_review_theme_not_found(self, service, mock_repository):
        """Raise error when theme not found."""
        # Arrange
        mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await service.review_theme(
                theme_id="nonexistent",
                action=REVIEW_ACTION_APPROVE,
                admin_id="admin-001",
            )

        assert "Theme not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_review_unknown_action(self, service, mock_repository, sample_theme):
        """Raise error for unknown action."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_theme

        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await service.review_theme(
                theme_id="theme-001",
                action="invalid_action",
                admin_id="admin-001",
            )

        assert "Unknown action" in str(exc.value)


class TestRegenerateTheme:
    """Tests for regenerate_theme method."""

    @pytest.mark.asyncio
    async def test_regenerate_theme_success(self, service, mock_repository, sample_theme):
        """Successfully regenerate a theme."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_theme
        new_alternatives = [
            {"id": "X", "name": "New Theme X", "priority": 80},
            {"id": "Y", "name": "New Theme Y", "priority": 70},
        ]
        updated = {**sample_theme, "ai_alternatives": new_alternatives}
        mock_repository.update.return_value = updated

        # Act
        result = await service.regenerate_theme(
            theme_id="theme-001",
            admin_id="admin-001",
            new_alternatives=new_alternatives,
            recommended_id="X",
            reason="Need better alternatives",
        )

        # Assert
        assert result["message"] == "Theme regenerated successfully"
        assert result["history_count"] == 1

        # Verify history was saved
        call_data = mock_repository.update.call_args[0][1]
        assert len(call_data["generation_history"]) == 1
        assert call_data["regenerate_count"] == 1

    @pytest.mark.asyncio
    async def test_regenerate_theme_not_found(self, service, mock_repository):
        """Raise error when theme not found."""
        # Arrange
        mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await service.regenerate_theme(
                theme_id="nonexistent",
                admin_id="admin-001",
                new_alternatives=[],
                recommended_id="A",
            )

        assert "Theme not found" in str(exc.value)


class TestGetThemeHistory:
    """Tests for get_theme_history method."""

    @pytest.mark.asyncio
    async def test_get_theme_history_success(self, service, mock_repository, sample_theme):
        """Get theme history successfully."""
        # Arrange
        sample_theme["generation_history"] = [
            {"generated_at": "2026-01-10T10:00:00Z", "alternatives": []},
        ]
        mock_repository.get_by_id.return_value = sample_theme

        # Act
        result = await service.get_theme_history("theme-001")

        # Assert
        assert result["theme_id"] == "theme-001"
        assert len(result["history"]) == 1
        assert result["regenerate_count"] == 0

    @pytest.mark.asyncio
    async def test_get_theme_history_not_found(self, service, mock_repository):
        """Raise error when theme not found."""
        # Arrange
        mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await service.get_theme_history("nonexistent")

        assert "Theme not found" in str(exc.value)


class TestBatchApproveThemes:
    """Tests for batch_approve_themes method."""

    @pytest.mark.asyncio
    async def test_batch_approve_success(self, service, mock_repository):
        """Batch approve multiple themes."""
        # Arrange
        mock_repository.batch_update_review_status.return_value = 3

        # Act
        result = await service.batch_approve_themes(
            theme_ids=["theme-1", "theme-2", "theme-3"],
            admin_id="admin-001",
        )

        # Assert
        assert result["approved"] == 3
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_batch_approve_partial(self, service, mock_repository):
        """Handle partial batch approve."""
        # Arrange
        mock_repository.batch_update_review_status.return_value = 2

        # Act
        result = await service.batch_approve_themes(
            theme_ids=["theme-1", "theme-2", "nonexistent"],
            admin_id="admin-001",
        )

        # Assert
        assert result["approved"] == 2
        assert result["failed"] == 1


# ==========================================
# Statistics Operations Tests
# ==========================================

class TestGetGenerationStatus:
    """Tests for get_generation_status method."""

    @pytest.mark.asyncio
    async def test_get_generation_status_complete(self, service, mock_repository):
        """Get status when all themes generated."""
        # Arrange
        today = date.today()
        all_dates = {today + timedelta(days=i) for i in range(10)}
        mock_repository.get_existing_dates.return_value = all_dates
        mock_repository.get_review_status_stats.return_value = {
            "pending": 2,
            "auto_approved": 5,
            "reviewed": 3,
            "rejected": 0,
        }

        # Act
        result = await service.get_generation_status(days=10)

        # Assert
        assert result["total_days"] == 10
        assert result["generated"] == 10
        assert result["missing"] == 0
        assert result["recommendation"] == "complete"

    @pytest.mark.asyncio
    async def test_get_generation_status_partial(self, service, mock_repository):
        """Get status with some missing themes."""
        # Arrange
        today = date.today()
        # Only 5 out of 10 days have themes
        existing = {today + timedelta(days=i) for i in range(5)}
        mock_repository.get_existing_dates.return_value = existing
        mock_repository.get_review_status_stats.return_value = {
            "pending": 0, "auto_approved": 0, "reviewed": 0, "rejected": 0
        }

        # Act
        result = await service.get_generation_status(days=10)

        # Assert
        assert result["generated"] == 5
        assert result["missing"] == 5
        assert result["recommendation"] == "partial"

    @pytest.mark.asyncio
    async def test_get_generation_status_full_needed(self, service, mock_repository):
        """Get status when full generation needed."""
        # Arrange
        mock_repository.get_existing_dates.return_value = set()
        mock_repository.get_review_status_stats.return_value = {
            "pending": 0, "auto_approved": 0, "reviewed": 0, "rejected": 0
        }

        # Act
        result = await service.get_generation_status(days=300)

        # Assert
        assert result["missing"] == 300
        assert result["recommendation"] == "full"


# ==========================================
# Date Matching Business Logic Tests
# ==========================================

class TestDateMatching:
    """Tests for date matching business logic."""

    def test_fixed_date_rule_match(self, service):
        """Fixed date rule matches within range."""
        date_rule = {"type": "fixed", "start": "12-24", "end": "12-26"}
        assert service._is_theme_active(date_rule, date(2026, 12, 25)) is True

    def test_fixed_date_rule_no_match(self, service):
        """Fixed date rule doesn't match outside range."""
        date_rule = {"type": "fixed", "start": "12-24", "end": "12-26"}
        assert service._is_theme_active(date_rule, date(2026, 12, 27)) is False

    def test_fixed_date_rule_year_wrap(self, service):
        """Fixed date rule handles year wrap (Dec-Jan)."""
        date_rule = {"type": "fixed", "start": "12-31", "end": "01-02"}
        assert service._is_theme_active(date_rule, date(2026, 12, 31)) is True
        assert service._is_theme_active(date_rule, date(2026, 1, 1)) is True
        assert service._is_theme_active(date_rule, date(2026, 6, 15)) is False

    def test_dynamic_us_thanksgiving(self, service):
        """Calculate US Thanksgiving correctly."""
        # 2026: November 1 is Sunday, so 4th Thursday is Nov 26
        thanksgiving = service._calculate_dynamic_date("us_thanksgiving", 2026)
        assert thanksgiving == date(2026, 11, 26)

    def test_dynamic_black_friday(self, service):
        """Calculate Black Friday correctly."""
        black_friday = service._calculate_dynamic_date("black_friday", 2026)
        assert black_friday == date(2026, 11, 27)

    def test_dynamic_mothers_day(self, service):
        """Calculate Mother's Day correctly."""
        # 2026: May 1 is Friday, so 2nd Sunday is May 10
        mothers_day = service._calculate_dynamic_date("mothers_day", 2026)
        assert mothers_day == date(2026, 5, 10)

    def test_dynamic_fathers_day(self, service):
        """Calculate Father's Day correctly."""
        # 2026: June 1 is Monday, so 3rd Sunday is June 21
        fathers_day = service._calculate_dynamic_date("fathers_day", 2026)
        assert fathers_day == date(2026, 6, 21)

    def test_dynamic_mlk_day(self, service):
        """Calculate MLK Day correctly."""
        # 2026: Jan 1 is Thursday, so 3rd Monday is Jan 19
        mlk = service._calculate_dynamic_date("mlk_day", 2026)
        assert mlk == date(2026, 1, 19)

    def test_dynamic_memorial_day(self, service):
        """Calculate Memorial Day correctly."""
        # 2026: May 31 is Sunday, last Monday is May 25
        memorial = service._calculate_dynamic_date("memorial_day", 2026)
        assert memorial == date(2026, 5, 25)

    def test_dynamic_labor_day(self, service):
        """Calculate Labor Day correctly."""
        # 2026: Sep 1 is Tuesday, first Monday is Sep 7
        labor = service._calculate_dynamic_date("labor_day", 2026)
        assert labor == date(2026, 9, 7)

    def test_dynamic_unknown_rule(self, service):
        """Return None for unknown dynamic rule."""
        result = service._calculate_dynamic_date("unknown_holiday", 2026)
        assert result is None

    def test_dynamic_date_rule_match(self, service):
        """Dynamic date rule matches with offset."""
        date_rule = {
            "type": "dynamic",
            "rule": "us_thanksgiving",
            "offset_start": -1,  # Day before
            "offset_end": 3,     # 3 days after
        }
        # Thanksgiving 2026 is Nov 26
        assert service._is_theme_active(date_rule, date(2026, 11, 25)) is True  # Day before
        assert service._is_theme_active(date_rule, date(2026, 11, 26)) is True  # Thanksgiving
        assert service._is_theme_active(date_rule, date(2026, 11, 27)) is True  # Black Friday
        assert service._is_theme_active(date_rule, date(2026, 11, 29)) is True  # 3 days after
        assert service._is_theme_active(date_rule, date(2026, 11, 30)) is False  # 4 days after

    def test_empty_date_rule(self, service):
        """Return False for empty date rule."""
        assert service._is_theme_active({}, date(2026, 1, 1)) is False
        assert service._is_theme_active(None, date(2026, 1, 1)) is False
