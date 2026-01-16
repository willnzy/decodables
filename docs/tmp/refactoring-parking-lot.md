# Refactoring Parking Lot

> **Purpose**: Track issues found during Container DI migration that require future attention.
>
> **Date**: 2026-01-16
> **Phase**: Phase 1 Part C-Final (Clean Sweep)

## Issues Requiring Attention

| Priority | File | Issue Type | Description | Suggested Fix |
|----------|------|------------|-------------|---------------|
| MEDIUM | `api/admin/asset_categories.py:425-433` | Direct DB Access | `get_category_resources` endpoint uses direct `db_client.table("system_resources")` query instead of repository pattern | Create `SystemResourceRepository` with `get_by_category_id()` method, then call from Service |
| LOW | `api/admin/feature_flags.py:646-647` | Wrong DI | `get_client_flags` endpoint uses `user: dict = Depends(get_async_db_client)` - this looks like a bug (should be user auth dependency) | Fix dependency to use proper user authentication |

## Migration Summary

### Files Successfully Migrated (Phase 1 Part C-Final)

1. **static_pages.py** → v1.1.0: Container DI
2. **articles.py** → v1.1.0: Container DI + audit logging
3. **asset_categories.py** → v1.1.0: Container DI (with parking lot item)
4. **webhooks_retry.py** → v1.1.0: `get_webhook_repository()` via Container

### Container Methods Added

- `get_category_service()`: CategoryService construction
- `get_webhook_repository()`: WebhookRepository for read-only queries

### Verification

```bash
# Check for remaining violations
grep -r "from core.database import get_async_db_client" api/admin/*.py
grep -r "from infrastructure.repositories" api/admin/*.py
```

Expected: Only `asset_categories.py:25` (parking lot item) should remain.

---

**Last Updated**: 2026-01-16
**Status**: Active
