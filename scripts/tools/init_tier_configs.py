#!/usr/bin/env python3
"""
Tier Configuration Initialization Script (Python Version)

Purpose: Insert tier display name configurations into system_configs table
Version: 1.0.0
Date: 2026-01-09

This script initializes the configurable tier display names that admins
can modify through the Admin API.

Usage:
    python scripts/tools/init_tier_configs.py
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.database import get_supabase_client
from infrastructure.repositories.config_repository import SupabaseConfigRepository


TIER_CONFIGS = [
    # Tier Display Names (可配置)
    {
        "key": "tier.t1.display_name",
        "value": "Free Plan",
        "value_type": "text",
        "config_group": "tier",
        "description": "First Tier 显示名称 (可通过 Admin API 修改)",
        "is_active": True,
        "is_editable": True,
    },
    {
        "key": "tier.t2.display_name",
        "value": "Starter Plan",
        "value_type": "text",
        "config_group": "tier",
        "description": "Second Tier 显示名称 (可通过 Admin API 修改)",
        "is_active": True,
        "is_editable": True,
    },
    {
        "key": "tier.t3.display_name",
        "value": "Pro Plan",
        "value_type": "text",
        "config_group": "tier",
        "description": "Third Tier 显示名称 (可通过 Admin API 修改)",
        "is_active": True,
        "is_editable": True,
    },

    # Tier Monthly Credits (参考值，实际使用代码中的常量)
    {
        "key": "tier.t1.monthly_credits",
        "value": "0",
        "value_type": "integer",
        "config_group": "tier",
        "description": "First Tier 月度积分",
        "is_active": True,
        "is_editable": False,
    },
    {
        "key": "tier.t2.monthly_credits",
        "value": "200",
        "value_type": "integer",
        "config_group": "tier",
        "description": "Second Tier 月度积分",
        "is_active": True,
        "is_editable": False,
    },
    {
        "key": "tier.t3.monthly_credits",
        "value": "500",
        "value_type": "integer",
        "config_group": "tier",
        "description": "Third Tier 月度积分",
        "is_active": True,
        "is_editable": False,
    },
]


async def init_tier_configs():
    """Initialize tier configurations in system_configs table."""

    print("=" * 80)
    print("Tier Configuration Initialization")
    print("=" * 80)

    client = get_supabase_client()
    config_repo = SupabaseConfigRepository(client)

    success_count = 0
    skip_count = 0
    error_count = 0

    for config in TIER_CONFIGS:
        key = config["key"]

        try:
            # Check if config already exists
            existing = await config_repo.get_by_key(key)

            if existing:
                print(f"⏭️  SKIP: {key} (already exists with value: '{existing}')")
                skip_count += 1
                continue

            # Insert new config
            await config_repo.upsert(
                key=config["key"],
                value=config["value"],
                value_type=config["value_type"],
                config_group=config["config_group"],
                description=config["description"],
                is_active=config["is_active"],
                is_editable=config["is_editable"],
            )

            print(f"✅ INSERT: {key} = '{config['value']}'")
            success_count += 1

        except Exception as e:
            print(f"❌ ERROR: {key} - {e}")
            error_count += 1

    print("\n" + "=" * 80)
    print(f"Summary:")
    print(f"  ✅ Inserted: {success_count}")
    print(f"  ⏭️  Skipped:  {skip_count}")
    print(f"  ❌ Errors:   {error_count}")
    print("=" * 80)

    # Verify inserted data
    print("\nVerifying inserted configurations:")
    print("-" * 80)

    all_configs = await config_repo.get_all(group="tier")

    if all_configs:
        print(f"{'Key':<35} {'Value':<20} {'Type':<10} {'Editable'}")
        print("-" * 80)
        for cfg in sorted(all_configs, key=lambda x: x.get('key', '')):
            print(
                f"{cfg.get('key', 'N/A'):<35} "
                f"{cfg.get('value', 'N/A'):<20} "
                f"{cfg.get('value_type', 'N/A'):<10} "
                f"{'✅' if cfg.get('is_editable') else '❌'}"
            )
    else:
        print("⚠️  No tier configurations found!")

    print("=" * 80)

    return success_count, skip_count, error_count


if __name__ == "__main__":
    try:
        success, skip, error = asyncio.run(init_tier_configs())

        # Exit with error code if any errors occurred
        if error > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n⚠️  Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
