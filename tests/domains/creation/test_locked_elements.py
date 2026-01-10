"""
Tests for Locked Elements Check - P1-013

Test Coverage:
- extract_listing_ids_from_canvas()
- check_locked_elements()
- update_project_locked_status()

Created: 2026-01-10
"""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

from domains.creation.locked_elements import (
    extract_listing_ids_from_canvas,
    check_locked_elements,
    update_project_locked_status,
)
from domains.marketplace.aggregates.listing import Listing
from domains.marketplace.value_objects import (
    AssetCategory,
    PriceType,
    ListingMetadata,
    ListingStats,
)


class TestExtractListingIds:
    """Test extract_listing_ids_from_canvas function."""

    def test_extract_from_single_object(self):
        """Test extraction from single canvas object."""
        canvas = {
            "objects": [
                {
                    "type": "image",
                    "metadata": {
                        "listing_id": "list_001"
                    }
                }
            ]
        }

        result = extract_listing_ids_from_canvas(canvas)
        assert result == {"list_001"}

    def test_extract_from_multiple_objects(self):
        """Test extraction from multiple canvas objects."""
        canvas = {
            "objects": [
                {"metadata": {"listing_id": "list_001"}},
                {"metadata": {"listing_id": "list_002"}},
                {"metadata": {"listing_id": "list_003"}},
            ]
        }

        result = extract_listing_ids_from_canvas(canvas)
        assert result == {"list_001", "list_002", "list_003"}

    def test_extract_with_duplicates(self):
        """Test that duplicates are deduplicated (set behavior)."""
        canvas = {
            "objects": [
                {"metadata": {"listing_id": "list_001"}},
                {"metadata": {"listing_id": "list_001"}},  # Duplicate
                {"metadata": {"listing_id": "list_002"}},
            ]
        }

        result = extract_listing_ids_from_canvas(canvas)
        assert result == {"list_001", "list_002"}

    def test_extract_with_missing_metadata(self):
        """Test objects without metadata are skipped."""
        canvas = {
            "objects": [
                {"type": "textbox", "text": "Hello"},  # No metadata
                {"metadata": {"listing_id": "list_001"}},
            ]
        }

        result = extract_listing_ids_from_canvas(canvas)
        assert result == {"list_001"}

    def test_extract_with_empty_metadata(self):
        """Test objects with empty metadata."""
        canvas = {
            "objects": [
                {"metadata": {}},  # Empty metadata
                {"metadata": {"listing_id": "list_001"}},
            ]
        }

        result = extract_listing_ids_from_canvas(canvas)
        assert result == {"list_001"}

    def test_extract_with_invalid_listing_id(self):
        """Test objects with non-string listing_id are skipped."""
        canvas = {
            "objects": [
                {"metadata": {"listing_id": 12345}},  # Invalid: integer
                {"metadata": {"listing_id": "list_001"}},
            ]
        }

        result = extract_listing_ids_from_canvas(canvas)
        assert result == {"list_001"}

    def test_extract_from_none_canvas(self):
        """Test None canvas returns empty set."""
        result = extract_listing_ids_from_canvas(None)
        assert result == set()

    def test_extract_from_empty_canvas(self):
        """Test empty canvas returns empty set."""
        result = extract_listing_ids_from_canvas({})
        assert result == set()

    def test_extract_from_canvas_no_objects(self):
        """Test canvas without objects array."""
        result = extract_listing_ids_from_canvas({"version": "1.0"})
        assert result == set()


class TestCheckLockedElements:
    """Test check_locked_elements function."""

    @pytest.fixture
    def mock_listing_repo(self):
        """Create mock listing repository."""
        return Mock()

    @pytest.fixture
    def sample_listing_t2_t3(self):
        """Create sample listing for t2/t3 users only."""
        from domains.marketplace.value_objects import ResourceType, ListingSource
        return Listing(
            listing_id="list_premium",
            seller_id="user_001",
            resource_type=ResourceType.ASSET,
            category=AssetCategory.STICKER,
            source=ListingSource.USER,
            price_type=PriceType.CREDITS,
            credit_price=50,
            allowed_tiers=["t2", "t3"],  # ← T2/T3 only
            metadata=ListingMetadata(
                title="Premium Sticker",
                description="T2/T3 only",
                tags=["premium"],
                preview_url="https://example.com/preview.jpg",
                file_url="https://example.com/file.png",
                file_size=102400,
                file_format="png",
                license_type="standard",
            ),
            stats=ListingStats(),
        )

    @pytest.fixture
    def sample_listing_all_tiers(self):
        """Create sample listing for all tiers."""
        from domains.marketplace.value_objects import ResourceType, ListingSource
        return Listing(
            listing_id="list_free",
            seller_id="user_002",
            resource_type=ResourceType.ASSET,
            category=AssetCategory.ELEMENT,
            source=ListingSource.USER,
            price_type=PriceType.FREE,
            credit_price=0,
            allowed_tiers=["t1", "t2", "t3"],  # ← All tiers
            metadata=ListingMetadata(
                title="Free Element",
                description="All tiers",
                tags=["free"],
                preview_url="https://example.com/preview2.jpg",
                file_url="https://example.com/file2.png",
                file_size=51200,
                file_format="png",
                license_type="standard",
            ),
            stats=ListingStats(),
        )

    @pytest.mark.asyncio
    async def test_no_locked_elements_for_t3_user(self, mock_listing_repo, sample_listing_t2_t3):
        """Test t3 user has no locked elements."""
        # Setup
        canvas = {
            "objects": [
                {"metadata": {"listing_id": "list_premium"}}
            ]
        }

        mock_listing_repo.get_by_id = AsyncMock(return_value=sample_listing_t2_t3)

        # Execute
        locked = await check_locked_elements(canvas, "t3", mock_listing_repo)

        # Verify
        assert locked == []  # T3 user can access t2/t3 listings

    @pytest.mark.asyncio
    async def test_locked_elements_for_t1_user(self, mock_listing_repo, sample_listing_t2_t3):
        """Test t1 user has locked elements (t2/t3 content)."""
        # Setup
        canvas = {
            "objects": [
                {"metadata": {"listing_id": "list_premium"}}
            ]
        }

        mock_listing_repo.get_by_id = AsyncMock(return_value=sample_listing_t2_t3)

        # Execute
        locked = await check_locked_elements(canvas, "t1", mock_listing_repo)

        # Verify
        assert len(locked) == 1
        assert locked[0]["listing_id"] == "list_premium"
        assert locked[0]["title"] == "Premium Sticker"
        assert locked[0]["allowed_tiers"] == ["t2", "t3"]
        assert locked[0]["reason"] == "tier_restriction"

    @pytest.mark.asyncio
    async def test_mixed_locked_and_accessible(
        self,
        mock_listing_repo,
        sample_listing_t2_t3,
        sample_listing_all_tiers
    ):
        """Test t1 user with mix of accessible and locked elements."""
        # Setup
        canvas = {
            "objects": [
                {"metadata": {"listing_id": "list_premium"}},
                {"metadata": {"listing_id": "list_free"}},
            ]
        }

        async def get_by_id_side_effect(listing_id):
            if listing_id == "list_premium":
                return sample_listing_t2_t3
            elif listing_id == "list_free":
                return sample_listing_all_tiers
            return None

        mock_listing_repo.get_by_id = AsyncMock(side_effect=get_by_id_side_effect)

        # Execute
        locked = await check_locked_elements(canvas, "t1", mock_listing_repo)

        # Verify
        assert len(locked) == 1
        assert locked[0]["listing_id"] == "list_premium"

    @pytest.mark.asyncio
    async def test_listing_not_found_treated_as_locked(self, mock_listing_repo):
        """Test missing listing is treated as locked (fail-safe)."""
        # Setup
        canvas = {
            "objects": [
                {"metadata": {"listing_id": "list_deleted"}}
            ]
        }

        mock_listing_repo.get_by_id = AsyncMock(return_value=None)  # Not found

        # Execute
        locked = await check_locked_elements(canvas, "t1", mock_listing_repo)

        # Verify
        assert len(locked) == 1
        assert locked[0]["listing_id"] == "list_deleted"
        assert locked[0]["reason"] == "not_found"

    @pytest.mark.asyncio
    async def test_fetch_error_treated_as_locked(self, mock_listing_repo):
        """Test fetch error is treated as locked (fail-safe)."""
        # Setup
        canvas = {
            "objects": [
                {"metadata": {"listing_id": "list_error"}}
            ]
        }

        mock_listing_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))

        # Execute
        locked = await check_locked_elements(canvas, "t1", mock_listing_repo)

        # Verify
        assert len(locked) == 1
        assert locked[0]["listing_id"] == "list_error"
        assert locked[0]["reason"] == "fetch_error"

    @pytest.mark.asyncio
    async def test_empty_canvas_no_locked_elements(self, mock_listing_repo):
        """Test empty canvas returns no locked elements."""
        locked = await check_locked_elements({}, "t1", mock_listing_repo)
        assert locked == []

    @pytest.mark.asyncio
    async def test_none_canvas_no_locked_elements(self, mock_listing_repo):
        """Test None canvas returns no locked elements."""
        locked = await check_locked_elements(None, "t1", mock_listing_repo)
        assert locked == []


class TestUpdateProjectLockedStatus:
    """Test update_project_locked_status function."""

    @pytest.fixture
    def mock_project(self):
        """Create mock project aggregate."""
        project = Mock()
        project.id = "proj_001"
        project.canvas_data = {}
        project.contains_locked_elements = False
        return project

    @pytest.fixture
    def mock_listing_repo(self):
        """Create mock listing repository."""
        return Mock()

    @pytest.mark.asyncio
    async def test_update_status_with_locked_elements(self, mock_project, mock_listing_repo):
        """Test status updated to True when locked elements found."""
        # Setup
        canvas = {"objects": [{"metadata": {"listing_id": "list_premium"}}]}

        # Mock listing with t2/t3 restriction
        listing = Mock()
        listing.listing_id = "list_premium"
        listing.metadata.title = "Premium Item"
        listing.allowed_tiers = ["t2", "t3"]  # ← Correct: at Listing level

        mock_listing_repo.get_by_id = AsyncMock(return_value=listing)

        # Execute
        has_locked = await update_project_locked_status(
            mock_project,
            canvas,
            "t1",  # Free user
            mock_listing_repo
        )

        # Verify
        assert has_locked is True
        assert mock_project.contains_locked_elements is True

    @pytest.mark.asyncio
    async def test_update_status_without_locked_elements(self, mock_project, mock_listing_repo):
        """Test status updated to False when no locked elements."""
        # Setup
        canvas = {"objects": [{"metadata": {"listing_id": "list_free"}}]}

        # Mock listing with all tiers
        listing = Mock()
        listing.listing_id = "list_free"
        listing.metadata.title = "Free Item"
        listing.allowed_tiers = ["t1", "t2", "t3"]  # ← Correct: at Listing level, not metadata

        mock_listing_repo.get_by_id = AsyncMock(return_value=listing)

        # Execute
        has_locked = await update_project_locked_status(
            mock_project,
            canvas,
            "t1",
            mock_listing_repo
        )

        # Verify
        assert has_locked is False
        assert mock_project.contains_locked_elements is False

    @pytest.mark.asyncio
    async def test_uses_project_canvas_data_if_not_provided(self, mock_project, mock_listing_repo):
        """Test uses project's canvas_data if none provided."""
        # Setup
        mock_project.canvas_data = {"objects": [{"metadata": {"listing_id": "list_001"}}]}

        listing = Mock()
        listing.listing_id = "list_001"
        listing.metadata.title = "Item"
        listing.allowed_tiers = ["t1", "t2", "t3"]  # ← Correct: at Listing level

        mock_listing_repo.get_by_id = AsyncMock(return_value=listing)

        # Execute (no canvas_data parameter)
        has_locked = await update_project_locked_status(
            mock_project,
            None,  # Will use project.canvas_data
            "t1",
            mock_listing_repo
        )

        # Verify
        assert mock_listing_repo.get_by_id.called
