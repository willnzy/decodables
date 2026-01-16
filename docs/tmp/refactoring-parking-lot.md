# Refactoring Parking Lot

> **Purpose**: Track issues found during Container DI migration that require future attention.
>
> **Date**: 2026-01-16
> **Phase**: Phase 1 Part E (Parking Lot Clearance) - COMPLETED

## Issues Status

| Priority | File | Issue Type | Status | Resolution |
|----------|------|------------|--------|------------|
| ~~MEDIUM~~ | ~~`api/admin/asset_categories.py:425-433`~~ | ~~Direct DB Access~~ | ✅ RESOLVED | v1.2.0: Added `get_by_category_id()` to `SupabaseSystemResourceRepository`, used via Container |
| ~~LOW~~ | ~~`api/admin/feature_flags.py:646-647`~~ | ~~Wrong DI~~ | ✅ RESOLVED | v3.30: Changed `Depends(get_async_db_client)` to `Depends(get_current_user_optional)` |

## Migration Summary

### Phase 1 Part C-Final (2026-01-16)
Files successfully migrated:
1. **static_pages.py** → v1.1.0: Container DI
2. **articles.py** → v1.1.0: Container DI + audit logging
3. **asset_categories.py** → v1.1.0: Container DI (with parking lot item)
4. **webhooks_retry.py** → v1.1.0: `get_webhook_repository()` via Container

### Phase 1 Part E (2026-01-16) - Parking Lot Clearance
Issues resolved:
1. **asset_categories.py** → v1.2.0: `get_category_resources` now uses Container
2. **feature_flags.py** → v3.30: `get_client_flags` fixed wrong DI

### Container Methods Added (Total)

- `get_category_service()`: CategoryService construction
- `get_webhook_repository()`: WebhookRepository for read-only queries
- `get_system_resource_repository()`: SystemResourceRepository for category resources

### Final Verification

```bash
# Check for remaining violations in api/admin/
grep -r "from core.database import get_async_db_client" api/admin/*.py
grep -r "from infrastructure.repositories" api/admin/*.py
```

**Expected Result**: No matches found ✅

---

**Last Updated**: 2026-01-16
**Status**: ✅ CLEARED - All parking lot items resolved
