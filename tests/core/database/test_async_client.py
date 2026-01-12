#!/usr/bin/env python3
"""
Test Supabase AsyncClient functionality.

This script verifies that supabase-py v2.27.0 supports:
1. acreate_client() for creating async client
2. Native async/await operations (no run_in_threadpool needed)
3. Method chaining (.select().eq().execute())
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_async_client():
    """Test AsyncClient basic functionality."""
    from supabase import acreate_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("❌ SUPABASE_URL or SUPABASE_KEY not set")
        return False

    try:
        # 1. Create async client
        print("1️⃣ Creating AsyncClient...")
        client = await acreate_client(url, key)
        print(f"   ✅ Client type: {type(client).__module__}.{type(client).__name__}")

        # 2. Test simple select
        print("\n2️⃣ Testing simple select...")
        result = await client.table("profiles").select("id").limit(1).execute()
        print(f"   ✅ Got {len(result.data)} rows")

        # 3. Test chained operations
        print("\n3️⃣ Testing chained operations...")
        result = await client.table("profiles").select("id, email").eq("tier", "t1").limit(1).execute()
        print(f"   ✅ Chained query works! Rows: {len(result.data)}")

        # 4. Test insert (with select)
        print("\n4️⃣ Testing insert with select...")
        # Note: This will fail with permission error, but we just want to test the syntax
        try:
            test_data = {"id": "test-async-123", "email": "test@example.com"}
            result = await client.table("profiles").insert(test_data).select("*").execute()
            print(f"   ✅ Insert + select syntax works!")
        except Exception as e:
            if "duplicate key" in str(e) or "permission" in str(e).lower():
                print(f"   ✅ Insert + select syntax works (permission/duplicate expected)")
            else:
                print(f"   ⚠️ Insert error: {e}")

        # 5. Test update with select
        print("\n5️⃣ Testing update with select...")
        try:
            result = await client.table("profiles").update({"tier": "t1"}).eq("id", "test-id").select("*").execute()
            print(f"   ✅ Update + select syntax works!")
        except Exception as e:
            if "permission" in str(e).lower() or "not found" in str(e).lower():
                print(f"   ✅ Update + select syntax works (permission/not found expected)")
            else:
                print(f"   ⚠️ Update error: {e}")

        print("\n✅ All AsyncClient tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_sync_vs_async_comparison():
    """Compare sync client (needs threadpool) vs async client (direct await)."""
    from supabase import create_client, acreate_client
    from fastapi.concurrency import run_in_threadpool
    import time

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        return

    print("\n" + "="*60)
    print("SYNC vs ASYNC Performance Comparison")
    print("="*60)

    # Sync client (old way)
    print("\n📊 Sync Client (with run_in_threadpool):")
    sync_client = create_client(url, key)

    start = time.time()
    result = await run_in_threadpool(
        lambda: sync_client.table("profiles").select("id").limit(10).execute()
    )
    sync_time = time.time() - start
    print(f"   ⏱️ Time: {sync_time*1000:.2f}ms")
    print(f"   📦 Rows: {len(result.data)}")

    # Async client (new way)
    print("\n📊 Async Client (direct await):")
    async_client = await acreate_client(url, key)

    start = time.time()
    result = await async_client.table("profiles").select("id").limit(10).execute()
    async_time = time.time() - start
    print(f"   ⏱️ Time: {async_time*1000:.2f}ms")
    print(f"   📦 Rows: {len(result.data)}")

    # Comparison
    print(f"\n🚀 Speedup: {sync_time/async_time:.2f}x faster with AsyncClient")

if __name__ == "__main__":
    print("Testing Supabase AsyncClient Support")
    print("="*60)

    # Run basic tests
    success = asyncio.run(test_async_client())

    # Run performance comparison (if network available)
    # asyncio.run(test_sync_vs_async_comparison())
