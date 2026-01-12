#!/usr/bin/env python3
"""
Script to migrate API files from sync to async client.

This automates Phase 7 of the AsyncClient migration.
"""

import re
from pathlib import Path

# List of files to migrate (excluding already migrated and backup files)
FILES_TO_MIGRATE = [
    "api/user/articles.py",
    "api/user/config.py",
    "api/user/system_resources.py",
    "api/user/generations.py",
    "api/user/templates.py",
    "api/user/export.py",
    "api/user/generation_pdf.py",
    "api/user/campaigns.py",
    "api/user/generation_story.py",
    "api/admin/themes.py",
    "api/admin/feature_flags.py",
    "api/admin/articles.py",
    "api/admin/experiments.py",
    "api/admin/campaigns.py",
    "api/admin/logs.py",
    "api/admin/config.py",
    "api/admin/users.py",
    "api/admin/events.py",
    "api/admin/subscriptions.py",
    "api/admin/tasks_mgmt.py",
    "api/admin/system.py",
    "api/admin/metrics.py",
]

def migrate_file(filepath: str) -> tuple[bool, str]:
    """
    Migrate a single file to AsyncClient.

    Returns:
        (success, message)
    """
    path = Path(filepath)

    if not path.exists():
        return (False, f"File not found: {filepath}")

    content = path.read_text()
    original_content = content
    modified = False

    # 1. Update imports: get_database_client → get_async_db_client or get_async_db
    if "from core.database import get_database_client" in content:
        # Check if file uses dependency injection pattern or direct call pattern
        if "= Depends(" in content or "def get_" in content:
            # DI pattern: use get_async_db from dependencies module
            content = content.replace(
                "from core.database import get_database_client",
                "from core.database.dependencies import get_async_db"
            )
        else:
            # Direct call pattern: use get_async_db_client
            content = content.replace(
                "from core.database import get_database_client",
                "from core.database import get_async_db_client"
            )
        modified = True

    # 2. Replace get_database_client() calls
    # Pattern 1: Direct call in function body
    if "get_database_client()" in content:
        # Replace with await get_async_db_client()
        content = re.sub(
            r'(\w+)\s*=\s*get_database_client\(\)',
            r'\1 = await get_async_db_client()',
            content
        )

        # For inline usage: SomeRepository(get_database_client())
        content = re.sub(
            r'Repository\(get_database_client\(\)\)',
            r'Repository(await get_async_db_client())',
            content
        )
        modified = True

    # 3. Update dependency injection factory functions
    # Pattern: def get_xxx_service() -> XxxService:
    #              db = get_database_client()
    # Change to: async def get_xxx_service(db = Depends(get_async_db)) -> XxxService:
    pattern_di_factory = re.compile(
        r'def (get_\w+_service)\(\) -> (\w+):\s*\n'
        r'(\s+)"""([^"]+)"""\s*\n'
        r'\3db = get_database_client\(\)',
        re.MULTILINE
    )

    def replace_di_factory(match):
        func_name = match.group(1)
        return_type = match.group(2)
        indent = match.group(3)
        docstring = match.group(4)

        return (
            f'async def {func_name}(db = Depends(get_async_db)) -> {return_type}:\n'
            f'{indent}"""{docstring}"""\n'
            f'{indent}# db provided via dependency injection'
        )

    content = pattern_di_factory.sub(replace_di_factory, content)

    if content != original_content:
        path.write_text(content)
        return (True, f"✅ Migrated: {filepath}")
    else:
        return (False, f"⚠️  No changes needed: {filepath}")


if __name__ == "__main__":
    print("=" * 60)
    print("AsyncClient Migration - Phase 7: API Files")
    print("=" * 60)
    print()

    success_count = 0
    skip_count = 0

    for filepath in FILES_TO_MIGRATE:
        success, message = migrate_file(filepath)
        print(message)

        if success:
            success_count += 1
        else:
            skip_count += 1

    print()
    print("=" * 60)
    print(f"Migration complete: {success_count} migrated, {skip_count} skipped")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Review changes with: git diff")
    print("2. Test the application")
    print("3. Commit changes: git add -A && git commit -m 'refactor(api): migrate remaining files to AsyncClient (Phase 7)'")
