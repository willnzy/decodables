"""
Locked Elements Helper - Check if canvas contains elements locked by tier downgrade.

@module domains.creation.locked_elements
@version 1.0.0

Business Logic:
- When user downgrades (e.g., t3 → t1), previously used premium elements become "locked"
- Each marketplace listing has allowed_tiers (e.g., ['t2', 't3'] = t2/t3 only)
- This module checks if canvas_data contains elements that user's current tier cannot access

Usage:
    locked_elements = await check_locked_elements(
        canvas_data=project.canvas_data,
        user_tier="t1",
        listing_repo=listing_repository
    )

    if locked_elements:
        # Option 1: Block save
        # Option 2: Make project read-only
        # Option 3: Warn user
"""

import logging
from typing import Dict, List, Any, Optional, Set

logger = logging.getLogger(__name__)


def extract_listing_ids_from_canvas(canvas_data: Optional[Dict[str, Any]]) -> Set[str]:
    """
    Extract all marketplace listing IDs from canvas_data.

    Canvas data structure example:
    {
        "objects": [
            {
                "type": "image",
                "src": "https://...",
                "metadata": {
                    "listing_id": "list_001",  # <- Extract this
                    "category": "sticker"
                }
            },
            {
                "type": "textbox",
                "text": "Hello",
                "metadata": {
                    "listing_id": "list_002",  # <- Extract this
                    "category": "font"
                }
            }
        ]
    }

    Args:
        canvas_data: Canvas JSON data (Fabric.js format)

    Returns:
        Set of listing IDs found in canvas

    Example:
        >>> canvas = {"objects": [{"metadata": {"listing_id": "list_001"}}]}
        >>> extract_listing_ids_from_canvas(canvas)
        {'list_001'}
    """
    if not canvas_data:
        return set()

    listing_ids = set()

    # Extract from objects array
    objects = canvas_data.get("objects", [])
    if not isinstance(objects, list):
        logger.warning(f"canvas_data.objects is not a list: {type(objects)}")
        return listing_ids

    for obj in objects:
        if not isinstance(obj, dict):
            continue

        # Check metadata.listing_id
        metadata = obj.get("metadata", {})
        if isinstance(metadata, dict):
            listing_id = metadata.get("listing_id")
            if listing_id and isinstance(listing_id, str):
                listing_ids.add(listing_id)

    return listing_ids


async def check_locked_elements(
    canvas_data: Optional[Dict[str, Any]],
    user_tier: str,
    listing_repo,  # SupabaseListingRepository instance
) -> List[Dict[str, Any]]:
    """
    Check if canvas contains elements locked by user's current tier.

    Business Rules:
    - Each listing has allowed_tiers (e.g., ['t2', 't3'])
    - User with tier 't1' cannot access listings with allowed_tiers = ['t2', 't3']
    - If user downgraded (t3 → t1), previously used t3 elements become "locked"

    Args:
        canvas_data: Canvas JSON data
        user_tier: Current user tier ('t1', 't2', 't3')
        listing_repo: Repository instance to fetch listing metadata

    Returns:
        List of locked elements (each with listing_id, title, allowed_tiers)
        Empty list if no locked elements found

    Example:
        >>> locked = await check_locked_elements(canvas, "t1", listing_repo)
        >>> if locked:
        ...     print(f"Found {len(locked)} locked elements")
        ...     for elem in locked:
        ...         print(f"  - {elem['title']} (requires: {elem['allowed_tiers']})")
    """
    # Step 1: Extract all listing IDs from canvas
    listing_ids = extract_listing_ids_from_canvas(canvas_data)

    if not listing_ids:
        return []

    # Step 2: Fetch listing metadata from database
    locked_elements = []

    for listing_id in listing_ids:
        try:
            # Fetch listing info
            listing = await listing_repo.get_by_id(listing_id)

            if not listing:
                # Listing not found (might be deleted) - treat as locked
                logger.warning(f"Listing {listing_id} not found in database")
                locked_elements.append({
                    "listing_id": listing_id,
                    "title": "Unknown Listing",
                    "allowed_tiers": [],
                    "reason": "not_found"
                })
                continue

            # Step 3: Check if user's tier is in allowed_tiers
            allowed_tiers = listing.allowed_tiers or []

            if user_tier not in allowed_tiers:
                # Element is locked for this user
                locked_elements.append({
                    "listing_id": listing.listing_id,
                    "title": listing.metadata.title,
                    "allowed_tiers": allowed_tiers,
                    "reason": "tier_restriction"
                })
                logger.info(f"Locked element found: {listing.metadata.title} (requires {allowed_tiers}, user has {user_tier})")

        except Exception as e:
            # If fetching fails, treat as locked (fail-safe)
            logger.error(f"Error fetching listing {listing_id}: {e}")
            locked_elements.append({
                "listing_id": listing_id,
                "title": "Error Loading Listing",
                "allowed_tiers": [],
                "reason": "fetch_error"
            })

    return locked_elements


async def update_project_locked_status(
    project,  # Project aggregate
    canvas_data: Optional[Dict[str, Any]],
    user_tier: str,
    listing_repo,
) -> bool:
    """
    Update project's contains_locked_elements field.

    This function should be called after updating project canvas_data
    to ensure the locked status is always accurate.

    Args:
        project: Project aggregate instance
        canvas_data: Updated canvas data (optional if unchanged)
        user_tier: User's current tier
        listing_repo: Repository instance

    Returns:
        True if locked elements were found

    Example:
        >>> # In UpdateProjectHandler
        >>> project.canvas_data = command.canvas_data
        >>> has_locked = await update_project_locked_status(
        ...     project, command.canvas_data, user.tier, listing_repo
        ... )
        >>> if has_locked:
        ...     logger.warning(f"Project {project.id} contains locked elements")
    """
    # Use provided canvas_data or project's current canvas_data
    data_to_check = canvas_data if canvas_data is not None else project.canvas_data

    # Check for locked elements
    locked_elements = await check_locked_elements(
        canvas_data=data_to_check,
        user_tier=user_tier,
        listing_repo=listing_repo
    )

    # Update project's locked status
    has_locked = len(locked_elements) > 0
    project.contains_locked_elements = has_locked

    return has_locked
