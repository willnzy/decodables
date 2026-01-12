"""
Identity Domain Constants - Tier system codes and levels.

@module domains.identity.constants
@version 1.0.0

These constants define the tier system codes used throughout the application.
System codes (t1/t2/t3) are permanent and used in database fields and business logic.
Display names are configurable via system_configs and should be fetched via TierService.
"""

# System codes (永不改变)
TIER_T1 = "t1"  # First Tier
TIER_T2 = "t2"  # Second Tier
TIER_T3 = "t3"  # Third Tier
TIER_T4 = "t4"  # Fourth Tier (预留)

# Valid tier codes set
VALID_TIERS = {TIER_T1, TIER_T2, TIER_T3, TIER_T4}

# Fixed descriptive labels (for documentation and logs)
TIER_LABELS = {
    TIER_T1: "First Tier",
    TIER_T2: "Second Tier",
    TIER_T3: "Third Tier",
    TIER_T4: "Fourth Tier",
}

# Tier levels for comparison (higher = better tier)
TIER_LEVELS = {
    TIER_T1: 1,  # First Tier (Free)
    TIER_T2: 2,  # Second Tier (Starter)
    TIER_T3: 3,  # Third Tier (Pro)
    TIER_T4: 4,  # Fourth Tier (Enterprise)
}

# Default display names (can be overridden via system_configs)
# These will be used as fallback if config is not available
DEFAULT_TIER_DISPLAY_NAMES = {
    TIER_T1: "Free Plan",
    TIER_T2: "Starter Plan",
    TIER_T3: "Pro Plan",
    TIER_T4: "Enterprise Plan",
}

# Monthly credits per tier (as per TIER-PERMISSIONS.md)
# - t1: 0 monthly credits (100 bonus credits on registration, permanent)
# - t2: 100 monthly credits
# - t3: 200 monthly credits
TIER_MONTHLY_CREDITS = {
    TIER_T1: 0,    # Free Plan - no monthly credits
    TIER_T2: 100,  # Starter Plan - 100 monthly credits
    TIER_T3: 200,  # Pro Plan - 200 monthly credits
    TIER_T4: 500,  # Enterprise Plan - TBD, placeholder
}

# Monthly prices per tier in USD (as per TIER-PERMISSIONS.md)
TIER_MONTHLY_PRICES = {
    TIER_T1: 0.0,   # Free Plan
    TIER_T2: 6.9,   # Starter Plan - $6.9/month
    TIER_T3: 9.9,   # Pro Plan - $9.9/month
    TIER_T4: 0.0,   # Enterprise Plan - custom pricing
}

# Trial period configuration (can be overridden via system_configs)
DEFAULT_TRIAL_DURATION_DAYS = 30  # Free tier users get 30-day trial with full access


def is_valid_tier(tier: str) -> bool:
    """Check if a tier code is valid."""
    return tier in VALID_TIERS


def get_tier_level(tier: str) -> int:
    """Get numeric level for tier comparison."""
    return TIER_LEVELS.get(tier, 0)


def compare_tiers(tier1: str, tier2: str) -> int:
    """
    Compare two tiers.

    Returns:
        -1 if tier1 < tier2
         0 if tier1 == tier2
         1 if tier1 > tier2
    """
    level1 = get_tier_level(tier1)
    level2 = get_tier_level(tier2)

    if level1 < level2:
        return -1
    elif level1 > level2:
        return 1
    else:
        return 0


def is_premium_tier(tier: str) -> bool:
    """Check if tier is a paid/premium tier (t2, t3, or t4)."""
    return tier in {TIER_T2, TIER_T3, TIER_T4}


def normalize_tier(tier: str) -> str:
    """
    Normalize tier string to system code.

    Handles backward compatibility for legacy tier names:
    - "t1" / "Free Plan" → "t1"
    - "t2" / "Starter Plan" → "t2"
    - "t3" / "Pro Plan" → "t3"

    Args:
        tier: Tier string (can be legacy name or system code)

    Returns:
        Normalized system code (t1/t2/t3)

    Raises:
        ValueError: If tier string is invalid
    """
    if not tier:
        raise ValueError("Tier cannot be empty")

    tier_lower = tier.lower().strip()

    # Legacy name mappings
    legacy_mappings = {
        "t1": TIER_T1,
        "free plan": TIER_T1,
        "free": TIER_T1,
        "t2": TIER_T2,
        "starter plan": TIER_T2,
        "starter": TIER_T2,
        "t3": TIER_T3,
        "pro plan": TIER_T3,
        "pro": TIER_T3,
        "t4": TIER_T4,
        "enterprise plan": TIER_T4,
        "enterprise": TIER_T4,
    }

    # Check legacy mappings first
    if tier_lower in legacy_mappings:
        return legacy_mappings[tier_lower]

    # Check if already a valid system code
    if tier_lower in VALID_TIERS:
        return tier_lower

    raise ValueError(f"Invalid tier: {tier}. Must be one of: t1, t2, t3, t4")
