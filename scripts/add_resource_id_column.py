"""
Migration script: Add resource_id column to marketplace_listings

This adds a new column `resource_id` to store the actual resource ID (asset.id or project.id)
separately from `resource_url` (which stores URLs for assets).

Usage: python scripts/add_resource_id_column.py
"""

import os
import sys
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables required")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# UUID pattern for validation
UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)


def is_valid_uuid(val):
    return bool(val and UUID_PATTERN.match(str(val)))


def migrate():
    """
    Add resource_id column and populate it for existing listings
    """
    print("=" * 60)
    print("Migration: Add resource_id column to marketplace_listings")
    print("=" * 60)
    
    # Step 1: Check if column already exists by trying to select it
    print("\n[1] Checking if resource_id column exists...")
    try:
        test_res = supabase.table("marketplace_listings").select("resource_id").limit(1).execute()
        print("    Column already exists. Proceeding with data population...")
    except Exception as e:
        if "column" in str(e).lower() and "does not exist" in str(e).lower():
            print("    Column does not exist. Please run the SQL migration first:")
            print("    ALTER TABLE marketplace_listings ADD COLUMN resource_id UUID;")
            print("\n    Run this SQL in Supabase SQL Editor, then re-run this script.")
            return
        else:
            raise e
    
    # Step 2: Get all listings where resource_id is NULL
    print("\n[2] Finding listings with NULL resource_id...")
    
    listings_res = supabase.table("marketplace_listings").select(
        "id, title, resource_url, resource_type, resource_id"
    ).is_("resource_id", "null").eq("is_deleted", False).execute()
    
    listings = listings_res.data or []
    print(f"    Found {len(listings)} listings to update")
    
    if not listings:
        print("    All listings already have resource_id. Migration complete.")
        return
    
    # Step 3: Separate by type
    project_listings = [l for l in listings if l["resource_type"] == "project"]
    asset_listings = [l for l in listings if l["resource_type"] == "asset"]
    
    print(f"    - Project listings: {len(project_listings)}")
    print(f"    - Asset listings: {len(asset_listings)}")
    
    updated = 0
    failed = 0
    
    # Step 4: Update project listings
    # For projects, resource_url is already the project ID
    print("\n[3] Updating project listings...")
    for listing in project_listings:
        listing_id = listing["id"]
        resource_url = listing["resource_url"]
        
        if is_valid_uuid(resource_url):
            try:
                supabase.table("marketplace_listings").update({
                    "resource_id": resource_url
                }).eq("id", listing_id).execute()
                print(f"    ✅ Project listing {listing_id}: set resource_id = {resource_url}")
                updated += 1
            except Exception as e:
                print(f"    ❌ Project listing {listing_id}: {e}")
                failed += 1
        else:
            print(f"    ⚠️  Project listing {listing_id}: resource_url is not a valid UUID")
            failed += 1
    
    # Step 5: Update asset listings
    # For assets, we need to find the asset by URL
    print("\n[4] Updating asset listings...")
    
    if asset_listings:
        # Get unique URLs
        asset_urls = [l["resource_url"] for l in asset_listings if l["resource_url"]]
        
        # Query assets by URL
        assets_res = supabase.table("assets").select("id, url").in_("url", asset_urls).execute()
        url_to_id = {a["url"]: a["id"] for a in (assets_res.data or [])}
        
        for listing in asset_listings:
            listing_id = listing["id"]
            resource_url = listing["resource_url"]
            
            if resource_url in url_to_id:
                asset_id = url_to_id[resource_url]
                try:
                    supabase.table("marketplace_listings").update({
                        "resource_id": asset_id
                    }).eq("id", listing_id).execute()
                    print(f"    ✅ Asset listing {listing_id}: set resource_id = {asset_id}")
                    updated += 1
                except Exception as e:
                    print(f"    ❌ Asset listing {listing_id}: {e}")
                    failed += 1
            else:
                print(f"    ⚠️  Asset listing {listing_id}: no matching asset found for URL")
                failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Migration Complete")
    print("=" * 60)
    print(f"Total listings processed: {len(listings)}")
    print(f"Successfully updated: {updated}")
    print(f"Failed/Skipped: {failed}")
    
    if failed > 0:
        print("\n⚠️  Some listings need manual review.")
    else:
        print("\n✅ All listings now have resource_id populated!")


if __name__ == "__main__":
    migrate()
