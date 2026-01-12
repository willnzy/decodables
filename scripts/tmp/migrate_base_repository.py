#!/usr/bin/env python3
"""
Script to migrate BaseRepository from sync to async client.

This automates Phase 4 of the AsyncClient migration.
"""

import re

# Read the original file
with open('infrastructure/repositories/base_repository.py', 'r') as f:
    content = f.read()

# 1. Update module docstring
content = content.replace(
    '@version 1.0.0',
    '@version 2.0.0 (AsyncClient Migration)'
)

content = content.replace(
    'Provides common functionality for soft delete, hard delete, and automatic filtering.\nAll concrete repositories should inherit from this class.\n"""',
    '''Provides common functionality for soft delete, hard delete, and automatic filtering.
All concrete repositories should inherit from this class.

IMPORTANT: v2.0 uses AsyncClient for native async/await operations.
- Repositories MUST be initialized with AsyncClient via dependency injection
- No more run_in_threadpool wrapping needed
- All database operations are truly async
"""'''
)

# 2. Update imports
content = content.replace(
    'from core.database import get_supabase_client, retry_on_network_error',
    '# v2.0: Import async retry decorator only (client passed via dependency injection)\nfrom core.database import retry_on_network_error_async'
)

# 3. Update class docstring
old_class_doc = '''    """
    Abstract base repository with common CRUD operations.

    Provides:
    - Soft delete support (is_deleted flag)
    - Hard delete support (is_permanently_deleted flag or actual deletion)
    - Automatic filtering of deleted records
    - Common database operations
    - Lazy client initialization

    Subclasses must implement:
    - table_name: str property
    - _map_to_entity(row: Dict) -> T
    - _map_to_row(entity: T) -> Dict
    """'''

new_class_doc = '''    """
    Abstract base repository with common CRUD operations.

    v2.0 Changes:
    - Now requires AsyncClient (no lazy loading of sync client)
    - All operations are truly async (no blocking)
    - Must be injected via FastAPI dependency

    Provides:
    - Soft delete support (is_deleted flag)
    - Hard delete support (is_permanently_deleted flag or actual deletion)
    - Automatic filtering of deleted records
    - Common database operations
    - Full async/await support

    Subclasses must implement:
    - table_name: str property
    - _map_to_entity(row: Dict) -> T
    - _map_to_row(entity: T) -> Dict
    """'''

content = content.replace(old_class_doc, new_class_doc)

# 4. Update __init__ method
old_init = '''    def __init__(self, client=None):
        """
        Initialize repository with optional Supabase client.

        Args:
            client: Supabase client instance (optional, will lazy load if None)
        """
        self._client = client

    @property
    def client(self):
        """Lazy load Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client'''

new_init = '''    def __init__(self, client):
        """
        Initialize repository with AsyncClient.

        v2.0: Client is now required (no lazy loading).
        Use FastAPI dependency injection to provide AsyncClient.

        Args:
            client: Supabase AsyncClient instance (required)

        Example:
            from core.database import get_async_db
            from fastapi import Depends

            async def get_user_repo(db = Depends(get_async_db)):
                return UserRepository(client=db)
        """
        if client is None:
            raise ValueError(
                "AsyncClient is required for BaseRepository v2.0. "
                "Use FastAPI dependency injection: Depends(get_async_db)"
            )
        self._client = client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client'''

content = content.replace(old_init, new_init)

# 5. Replace all @retry_on_network_error() with @retry_on_network_error_async()
content = content.replace('@retry_on_network_error()', '@retry_on_network_error_async()')

# 6. Add await before all .execute() calls that don't already have it
# Pattern: find ".execute()" not preceded by "await "
content = re.sub(r'(?<!await\s)\.execute\(\)', r'await .execute()', content)

# 7. Fix any double "await await" that might have been created
content = content.replace('await await', 'await')

# Write the migrated file
with open('infrastructure/repositories/base_repository.py', 'w') as f:
    f.write(content)

print("✅ BaseRepository migrated to v2.0 (AsyncClient)")
print("Changes:")
print("  - Updated imports (retry_on_network_error_async)")
print("  - Modified __init__ to require AsyncClient")
print("  - Added 'await' before all .execute() calls")
print("  - Updated all decorators to async version")
