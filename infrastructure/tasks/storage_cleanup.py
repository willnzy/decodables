"""
Storage Cleanup Task (v3.19 - Log Hygiene)

Cleans up temporary AI-generated files from Supabase Storage.

@module infrastructure.tasks.storage_cleanup

Files in {user_id}/temp/{YYYY-MM-DD}/ directories older than 7 days
will be automatically deleted to save storage costs.

The date-based folder structure makes cleanup extremely efficient:
- No need to check individual file metadata
- Simply delete entire date folders that are past retention

Run frequency: Daily at 3:00 AM UTC

Changes:
- v3.19: Replaced print statements with proper logging
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Storage configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUCKET_NAME = "make-decodables-u"  # User content bucket
TEMP_RETENTION_DAYS = 7  # Keep temp files for 7 days

# Ensure URL has trailing slash
if SUPABASE_URL and not SUPABASE_URL.endswith('/'):
    SUPABASE_URL = SUPABASE_URL + '/'

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


def is_date_folder(folder_name: str) -> bool:
    """Check if folder name is a date format (YYYY-MM-DD)."""
    try:
        datetime.strptime(folder_name, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def get_expired_date_folders() -> List[Dict[str, Any]]:
    """
    Get list of date folders that are past retention period.
    
    Structure: {user_id}/temp/{YYYY-MM-DD}/{task_id}/files
    
    Returns:
        List of expired folder info: [{'user_id': ..., 'date': ..., 'path': ...}, ...]
    """
    if not supabase:
        logger.error("Supabase client not configured")
        return []
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=TEMP_RETENTION_DAYS)
    cutoff_str = cutoff_date.strftime('%Y-%m-%d')
    expired_folders = []
    
    try:
        # List all user directories in bucket
        result = supabase.storage.from_(BUCKET_NAME).list()
        
        if not result:
            return []
        
        # Iterate through user directories
        for item in result:
            if item.get('id') is None:  # It's a folder
                user_folder = item.get('name')
                if not user_folder:
                    continue
                
                # Check for temp folder
                try:
                    temp_contents = supabase.storage.from_(BUCKET_NAME).list(f"{user_folder}/temp")
                    if temp_contents:
                        for date_folder in temp_contents:
                            if date_folder.get('id') is None:  # It's a folder
                                date_name = date_folder.get('name')
                                if not date_name:
                                    continue
                                
                                # Check if it's a date folder and is expired
                                if is_date_folder(date_name) and date_name <= cutoff_str:
                                    expired_folders.append({
                                        'user_id': user_folder,
                                        'date': date_name,
                                        'path': f"{user_folder}/temp/{date_name}"
                                    })
                except Exception as e:
                    # No temp folder or error accessing it - skip
                    pass
                    
    except Exception as e:
        logger.error(f"Error listing bucket: {e}")
    
    return expired_folders


def get_all_files_in_folder(folder_path: str) -> List[str]:
    """
    Recursively get all file paths in a folder.
    
    Args:
        folder_path: Path to the folder
        
    Returns:
        List of full file paths
    """
    if not supabase:
        return []
    
    all_files = []
    
    try:
        contents = supabase.storage.from_(BUCKET_NAME).list(folder_path)
        
        for item in contents:
            item_name = item.get('name')
            if not item_name:
                continue
                
            full_path = f"{folder_path}/{item_name}"
            
            if item.get('id'):  # It's a file
                all_files.append(full_path)
            else:  # It's a folder - recurse
                all_files.extend(get_all_files_in_folder(full_path))
                
    except Exception as e:
        logger.warning(f"Error listing folder {folder_path}: {e}")
    
    return all_files


def delete_date_folder(folder_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete all files in a date folder.
    
    Args:
        folder_info: {'user_id': ..., 'date': ..., 'path': ...}
        
    Returns:
        Deletion result
    """
    if not supabase:
        return {'deleted': 0, 'failed': 0, 'error': 'Supabase not configured'}
    
    folder_path = folder_info['path']
    
    # Get all files in this date folder (including task subfolders)
    all_files = get_all_files_in_folder(folder_path)
    
    if not all_files:
        return {'deleted': 0, 'failed': 0, 'path': folder_path}
    
    # Delete in batches of 100
    deleted = 0
    failed = 0
    batch_size = 100
    
    for i in range(0, len(all_files), batch_size):
        batch = all_files[i:i + batch_size]
        try:
            supabase.storage.from_(BUCKET_NAME).remove(batch)
            deleted += len(batch)
        except Exception as e:
            logger.error(f"Error deleting batch from {folder_path}: {e}")
            failed += len(batch)
    
    return {
        'deleted': deleted,
        'failed': failed,
        'path': folder_path
    }


def run_storage_cleanup() -> Dict[str, Any]:
    """
    Main cleanup function.
    
    Efficiently cleans up expired temp folders by date.
    
    Returns:
        Summary of cleanup results
    """
    from infrastructure.logging.task_logger import TaskLogger

    cutoff_date_str = (datetime.now(timezone.utc) - timedelta(days=TEMP_RETENTION_DAYS)).strftime('%Y-%m-%d')
    logger.info(f"Starting storage cleanup (retention: {TEMP_RETENTION_DAYS} days, cutoff: {cutoff_date_str})")

    with TaskLogger('storage_cleanup', 'daily') as task_logger:
        # Step 1: Find expired date folders
        logger.info("Scanning for expired date folders...")
        expired_folders = get_expired_date_folders()
        logger.info(f"Found {len(expired_folders)} expired date folders")
        
        # Step 2: Delete each expired folder
        total_deleted = 0
        total_failed = 0
        folders_cleaned = 0
        
        for folder_info in expired_folders:
            logger.debug(f"Cleaning {folder_info['path']}...")
            result = delete_date_folder(folder_info)
            total_deleted += result['deleted']
            total_failed += result['failed']
            if result['deleted'] > 0:
                folders_cleaned += 1
        
        # Set result summary
        result = {
            'expired_folders_found': len(expired_folders),
            'folders_cleaned': folders_cleaned,
            'files_deleted': total_deleted,
            'files_failed': total_failed,
            'retention_days': TEMP_RETENTION_DAYS,
            'cutoff_date': (datetime.now(timezone.utc) - timedelta(days=TEMP_RETENTION_DAYS)).strftime('%Y-%m-%d'),
            'bucket': BUCKET_NAME
        }
        
        task_logger.set_result(result)

        logger.info(f"Storage cleanup complete: {folders_cleaned} folders cleaned, {total_deleted} files deleted")
        if total_failed > 0:
            logger.warning(f"Storage cleanup had {total_failed} failed file deletions")

        return result


def run_cleanup_dry_run() -> Dict[str, Any]:
    """
    Dry run - show what would be deleted without actually deleting.
    
    Returns:
        Summary of files that would be deleted
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=TEMP_RETENTION_DAYS)
    logger.info(f"DRY RUN: Scanning for expired date folders (retention: {TEMP_RETENTION_DAYS} days, cutoff: {cutoff_date.strftime('%Y-%m-%d')})")

    expired_folders = get_expired_date_folders()

    total_files = 0

    if expired_folders:
        logger.info(f"Folders that would be deleted ({len(expired_folders)} folders):")
        for folder_info in expired_folders:
            files = get_all_files_in_folder(folder_info['path'])
            file_count = len(files)
            total_files += file_count
            logger.info(f"  - {folder_info['path']} ({file_count} files)")

        logger.info(f"Total: {len(expired_folders)} folders, {total_files} files")
    else:
        logger.info("No expired folders found")
    
    return {
        'folders_found': len(expired_folders),
        'files_found': total_files,
        'dry_run': True
    }


# CLI entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up temporary storage files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting')
    parser.add_argument('--days', type=int, default=TEMP_RETENTION_DAYS, help=f'Retention period in days (default: {TEMP_RETENTION_DAYS})')
    
    args = parser.parse_args()
    
    if args.days != TEMP_RETENTION_DAYS:
        TEMP_RETENTION_DAYS = args.days
    
    if args.dry_run:
        run_cleanup_dry_run()
    else:
        run_storage_cleanup()
