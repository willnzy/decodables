"""
Migration script: Fix asset marketplace_listings resource_url

Problem: Asset listings currently store full URL in resource_url, 
         but should store asset.id for consistency with project listings.

Usage: python scripts/fix_asset_resource_url.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables required")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def fix_asset_resource_urls():
    """
    Update asset marketplace_listings to use asset.id instead of asset.url
    """
    print("=" * 60)
    print("Fix Asset Marketplace Listings - resource_url Migration")
    print("=" * 60)
    
    # Step 1: Get all asset listings that have URL-style resource_url
    print("\n[1] Finding asset listings with URL-style resource_url...")
    
    listings_res = supabase.table("marketplace_listings").select(
        "id, title, resource_url, resource_type, seller_id"
    ).eq("resource_type", "asset").eq("is_deleted", False).execute()
    
    asset_listings = listings_res.data or []
    print(f"    Found {len(asset_listings)} asset listings")
    
    if not asset_listings:
        print("    No asset listings to migrate.")
        return
    
    # Step 2: Filter listings where resource_url looks like a URL (not a UUID)
    url_based_listings = [
        l for l in asset_listings 
        if l["resource_url"] and l["resource_url"].startswith("http")
    ]
    
    print(f"    {len(url_based_listings)} listings have URL-style resource_url")
    
    if not url_based_listings:
        print("    All listings already use asset ID. No migration needed.")
        return
    
    # Step 3: Get all assets to build URL -> ID mapping
    print("\n[2] Building URL to asset ID mapping...")
    
    # Get unique URLs from listings
    listing_urls = [l["resource_url"] for l in url_based_listings]
    
    # Query assets that match these URLs
    assets_res = supabase.table("assets").select("id, url").in_("url", listing_urls).execute()
    assets = assets_res.data or []
    
    # Build URL -> ID map
    url_to_id = {a["url"]: a["id"] for a in assets}
    print(f"    Found {len(url_to_id)} matching assets")
    
    # Step 4: Update each listing
    print("\n[3] Updating listings...")
    
    updated = 0
    failed = 0
    
    for listing in url_based_listings:
        listing_id = listing["id"]
        old_url = listing["resource_url"]
        
        if old_url not in url_to_id:
            print(f"    ❌ Listing {listing_id}: No matching asset found for URL")
            failed += 1
            continue
        
        new_id = url_to_id[old_url]
        
        try:
            supabase.table("marketplace_listings").update({
                "resource_url": new_id
            }).eq("id", listing_id).execute()
            
            print(f"    ✅ Listing {listing_id}: Updated resource_url to {new_id}")
            updated += 1
        except Exception as e:
            print(f"    ❌ Listing {listing_id}: Update failed - {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Migration Complete")
    print("=" * 60)
    print(f"Total listings processed: {len(url_based_listings)}")
    print(f"Successfully updated: {updated}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\n⚠️  Some listings failed to update. Please check manually.")
    else:
        print("\n✅ All asset listings now use asset ID as resource_url")


if __name__ == "__main__":
    fix_asset_resource_urls()
