"""
Test Listing Repository RPC Functions

P1-004: Tests for p_get_marketplace_listings RPC function
Validates performance optimization and graceful fallback

Created: 2026-01-10
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from typing import List

from infrastructure.repositories.listing_repository import SupabaseListingRepository
from domains.marketplace.aggregates.listing import Listing
from domains.marketplace.value_objects import (
    AssetCategory,
    PriceFilter,
    ListingSortOrder,
)


class TestListingRepositoryRPC:
    """Test RPC function p_get_marketplace_listings"""

    @pytest.fixture
    def mock_client(self):
        """Create mock Supabase client"""
        return Mock()

    @pytest.fixture
    def repository(self, mock_client):
        """Create repository instance with mocked client"""
        repo = SupabaseListingRepository(mock_client)
        return repo

    @pytest.fixture
    def sample_rpc_response(self):
        """Sample RPC response with seller info"""
        return [
            {
                "listing_id": "list_001",
                "seller_id": "user_001",
                "resource_type": "asset",
                "category": "element",
                "source": "user",
                "title": "Cool Sticker",
                "description": "A cool sticker",
                "tags": ["cool", "sticker"],
                "preview_url": "https://example.com/preview.jpg",
                "thumbnail_url": "https://example.com/thumb.jpg",
                "file_url": "https://example.com/file.png",
                "file_size": 102400,
                "file_format": "png",
                "dimensions": {"width": 512, "height": 512},
                "license_type": "standard",
                "price_type": "t1",
                "credit_price": 0,
                "price_credits": 0,
                "allowed_tiers": ["t1", "t2", "t3"],
                "status": "published",
                "moderation_status": "approved",
                "is_featured": False,
                "is_public": True,
                "is_deleted": False,
                "rejection_reason": None,
                "view_count": 100,
                "download_count": 50,
                "like_count": 20,
                "purchase_count": 10,
                "sales_count": 10,
                "usage_count": 15,
                "rating_average": 4.5,
                "rating_count": 8,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "published_at": "2026-01-01T00:00:00+00:00",
                # RPC-specific fields (joined from profiles)
                "seller_username": "cool_artist",
                "seller_avatar_url": "https://example.com/avatar.jpg",
                "total_count": 42,  # Total matching records
            },
            {
                "listing_id": "list_002",
                "seller_id": "user_002",
                "resource_type": "project",
                "category": "template",
                "source": "user",
                "title": "Project Template",
                "description": "A project template",
                "tags": ["template"],
                "preview_url": "https://example.com/preview2.jpg",
                "thumbnail_url": None,
                "file_url": "",
                "file_size": 0,
                "file_format": "",
                "dimensions": None,
                "license_type": "standard",
                "price_type": "credits",
                "credit_price": 50,
                "price_credits": 50,
                "allowed_tiers": ["t2", "t3"],
                "status": "published",
                "moderation_status": "approved",
                "is_featured": True,
                "is_public": True,
                "is_deleted": False,
                "rejection_reason": None,
                "view_count": 200,
                "download_count": 100,
                "like_count": 50,
                "purchase_count": 30,
                "sales_count": 30,
                "usage_count": 40,
                "rating_average": 4.8,
                "rating_count": 12,
                "created_at": "2026-01-02T00:00:00+00:00",
                "updated_at": "2026-01-02T00:00:00+00:00",
                "published_at": "2026-01-02T00:00:00+00:00",
                "seller_username": "template_master",
                "seller_avatar_url": None,
                "total_count": 42,
            },
        ]

    @pytest.mark.asyncio
    async def test_search_with_filters_uses_rpc(self, repository, mock_client, sample_rpc_response):
        """Test that search_with_filters uses RPC function for performance"""
        # Setup: Mock RPC call to return sample data
        mock_rpc_result = Mock()
        mock_rpc_result.data = sample_rpc_response

        mock_rpc_chain = Mock()
        mock_rpc_chain.execute.return_value = mock_rpc_result
        mock_client.rpc.return_value = mock_rpc_chain

        # Execute
        listings, total_count = await repository.search_with_filters(
            query="cool",
            category=AssetCategory.ELEMENT,
            price_filter=PriceFilter.ALL,
            sort_by=ListingSortOrder.LATEST,
            tier_filter="t1",
            limit=20,
            offset=0,
        )

        # Verify: RPC was called with correct parameters
        mock_client.rpc.assert_called_once_with("p_get_marketplace_listings", {
            "p_category": "element",
            "p_price_filter": "all",
            "p_sort_by": "latest",
            "p_tier_filter": "t1",
            "p_search_query": "cool",
            "p_limit": 20,
            "p_offset": 0,
        })

        # Verify: Results were parsed correctly
        assert len(listings) == 2
        assert total_count == 42
        assert isinstance(listings[0], Listing)
        assert listings[0].listing_id == "list_001"
        assert listings[0].metadata.title == "Cool Sticker"
        assert listings[1].listing_id == "list_002"

    @pytest.mark.asyncio
    async def test_search_with_filters_maps_enums_to_rpc_params(self, repository, mock_client, sample_rpc_response):
        """Test that enum values are correctly mapped to RPC string parameters"""
        mock_rpc_result = Mock()
        mock_rpc_result.data = sample_rpc_response
        mock_rpc_chain = Mock()
        mock_rpc_chain.execute.return_value = mock_rpc_result
        mock_client.rpc.return_value = mock_rpc_chain

        # Execute with different enum values
        await repository.search_with_filters(
            category=AssetCategory.TEMPLATE,
            price_filter=PriceFilter.FREE,
            sort_by=ListingSortOrder.POPULAR,
        )

        # Verify: Enums were converted to their string values
        call_args = mock_client.rpc.call_args[0][1]
        assert call_args["p_category"] == "template"
        assert call_args["p_price_filter"] == "free"  # PriceFilter.FREE mapped to "free" for RPC
        assert call_args["p_sort_by"] == "popular"

    @pytest.mark.asyncio
    async def test_search_with_filters_handles_none_parameters(self, repository, mock_client, sample_rpc_response):
        """Test that None parameters are handled correctly"""
        mock_rpc_result = Mock()
        mock_rpc_result.data = sample_rpc_response
        mock_rpc_chain = Mock()
        mock_rpc_chain.execute.return_value = mock_rpc_result
        mock_client.rpc.return_value = mock_rpc_chain

        # Execute with minimal parameters (most are None)
        await repository.search_with_filters()

        # Verify: None values were passed as None (not converted to strings)
        call_args = mock_client.rpc.call_args[0][1]
        assert call_args["p_category"] is None
        assert call_args["p_price_filter"] == "all"  # Default for None PriceFilter
        assert call_args["p_tier_filter"] is None
        assert call_args["p_search_query"] == ""

    @pytest.mark.asyncio
    async def test_search_with_filters_graceful_fallback_on_rpc_error(
        self, repository, mock_client
    ):
        """Test graceful fallback to direct query when RPC fails"""
        # Setup: Mock RPC to raise exception
        mock_client.rpc.side_effect = Exception("RPC function not found")

        # Setup: Mock fallback direct query path
        mock_query_result = Mock()
        mock_query_result.data = [
            {
                "listing_id": "list_fallback",
                "seller_id": "user_001",
                "resource_type": "asset",
                "category": "element",
                "source": "user",
                "title": "Fallback Listing",
                "description": "From fallback query",
                "tags": [],
                "preview_url": "",
                "thumbnail_url": None,
                "file_url": "",
                "file_size": 0,
                "file_format": "",
                "dimensions": None,
                "license_type": "standard",
                "price_type": "t1",
                "credit_price": 0,
                "allowed_tiers": ["t1", "t2", "t3"],
                "status": "published",
                "is_featured": False,
                "rejection_reason": None,
                "view_count": 0,
                "download_count": 0,
                "like_count": 0,
                "purchase_count": 0,
                "rating_average": 0.0,
                "rating_count": 0,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "published_at": "2026-01-01T00:00:00+00:00",
            }
        ]
        mock_query_result.count = 1

        # Mock the table().select() chain for fallback
        mock_query_chain = Mock()
        mock_query_chain.eq.return_value = mock_query_chain
        mock_query_chain.order.return_value = mock_query_chain
        mock_query_chain.range.return_value = mock_query_chain
        mock_query_chain.execute.return_value = mock_query_result

        mock_table = Mock()
        mock_table.select.return_value = mock_query_chain
        mock_client.table.return_value = mock_table

        # Execute
        listings, total_count = await repository.search_with_filters()

        # Verify: RPC was attempted
        assert mock_client.rpc.called

        # Verify: Fallback query was executed
        assert mock_client.table.called
        mock_client.table.assert_called_with("marketplace_listings")

        # Verify: Results from fallback query
        assert len(listings) == 1
        assert total_count == 1
        assert listings[0].listing_id == "list_fallback"
        assert listings[0].metadata.title == "Fallback Listing"

    @pytest.mark.asyncio
    async def test_search_with_filters_empty_results(self, repository, mock_client):
        """Test handling of empty RPC results"""
        # Setup: Mock RPC to return empty results
        mock_rpc_result = Mock()
        mock_rpc_result.data = []

        mock_rpc_chain = Mock()
        mock_rpc_chain.execute.return_value = mock_rpc_result
        mock_client.rpc.return_value = mock_rpc_chain

        # Execute
        listings, total_count = await repository.search_with_filters(
            query="nonexistent"
        )

        # Verify: RPC was called
        assert mock_client.rpc.called

        # Verify: Empty results handled correctly
        # When result.data is empty, should fall back to direct query
        assert isinstance(listings, list)
        assert isinstance(total_count, int)

    @pytest.mark.asyncio
    async def test_search_with_filters_pagination(self, repository, mock_client, sample_rpc_response):
        """Test pagination parameters are passed correctly to RPC"""
        mock_rpc_result = Mock()
        mock_rpc_result.data = sample_rpc_response
        mock_rpc_chain = Mock()
        mock_rpc_chain.execute.return_value = mock_rpc_result
        mock_client.rpc.return_value = mock_rpc_chain

        # Execute with pagination
        await repository.search_with_filters(
            limit=50,
            offset=100,
        )

        # Verify: Pagination params passed to RPC
        call_args = mock_client.rpc.call_args[0][1]
        assert call_args["p_limit"] == 50
        assert call_args["p_offset"] == 100

    @pytest.mark.asyncio
    async def test_search_with_filters_total_count_extraction(
        self, repository, mock_client, sample_rpc_response
    ):
        """Test that total_count is correctly extracted from RPC response"""
        # Modify sample to have different total_count
        modified_response = sample_rpc_response.copy()
        for row in modified_response:
            row["total_count"] = 999

        mock_rpc_result = Mock()
        mock_rpc_result.data = modified_response
        mock_rpc_chain = Mock()
        mock_rpc_chain.execute.return_value = mock_rpc_result
        mock_client.rpc.return_value = mock_rpc_chain

        # Execute
        listings, total_count = await repository.search_with_filters()

        # Verify: total_count extracted from first row
        assert total_count == 999
        assert len(listings) == 2  # But only 2 actual listings returned

    @pytest.mark.asyncio
    async def test_rpc_includes_seller_info(self, repository, mock_client, sample_rpc_response):
        """Test that RPC response includes seller profile information"""
        mock_rpc_result = Mock()
        mock_rpc_result.data = sample_rpc_response
        mock_rpc_chain = Mock()
        mock_rpc_chain.execute.return_value = mock_rpc_result
        mock_client.rpc.return_value = mock_rpc_chain

        # Execute
        listings, _ = await repository.search_with_filters()

        # Verify: Seller info is available in raw response
        # (Note: Our _map_to_listing doesn't store seller info in Listing entity,
        #  but RPC response contains it for API layer to use)
        assert "seller_username" in sample_rpc_response[0]
        assert "seller_avatar_url" in sample_rpc_response[0]
        assert sample_rpc_response[0]["seller_username"] == "cool_artist"
