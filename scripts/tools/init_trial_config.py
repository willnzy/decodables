#!/usr/bin/env python3
"""
Trial Period Configuration Initialization Script

Purpose: Initialize trial period configuration in system_configs table
Usage: python scripts/tools/init_trial_config.py

This script adds the trial.duration_days configuration to system_configs.
Admins can modify this value later via Admin API.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from infrastructure.repositories.config_repository import SupabaseConfigRepository
from core.database import get_supabase_client


async def init_trial_config():
    """Initialize trial period configuration."""
    print("=" * 70)
    print("Trial Period Configuration Initialization")
    print("=" * 70)
    print()

    # Initialize repository
    client = get_supabase_client()
    config_repo = SupabaseConfigRepository(client)

    # Check if config already exists
    print("Checking existing configuration...")
    existing = await config_repo.get_by_key("trial.duration_days")

    if existing:
        print(f"⚠️  Trial configuration already exists: trial.duration_days = {existing}")
        print("   Skipping initialization.")
        print()
        return

    # Insert trial configuration
    print("Inserting trial configuration...")

    config = {
        "key": "trial.duration_days",
        "value": "30",
        "value_type": "integer",
        "config_group": "trial",
        "description": "Free tier 试用期天数 (可通过 Admin API 修改)",
        "is_active": True,
        "is_editable": True,
    }

    try:
        await config_repo.upsert(**config)
        print(f"✅ Inserted: {config['key']} = {config['value']}")
    except Exception as e:
        print(f"❌ Failed to insert {config['key']}: {e}")
        return

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"✅ Trial configuration initialized successfully")
    print(f"   - trial.duration_days = 30 days")
    print()
    print("To modify this value, use:")
    print("   TierService.update_trial_duration_days(days)")
    print()


if __name__ == "__main__":
    asyncio.run(init_trial_config())
