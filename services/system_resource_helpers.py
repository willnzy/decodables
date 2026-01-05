"""
System Resource Helpers
Helper functions for system resource management

@module services.system_resource_helpers
@version 3.24
"""

from typing import Optional
from services.db_service import supabase


# =====================================================
# Constants
# =====================================================

SYSTEM_ASSETS_BUCKET = "make-decodables-s"

ALLOWED_TYPES = ["sticker", "template", "background", "frame", "icon", "pattern"]
ALLOWED_MIME_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# =====================================================
# Helper Functions
# =====================================================

def log_resource_audit(
    resource_id: str,
    action: str,
    old_data: dict,
    new_data: dict,
    changed_by: str
):
    """Log resource changes for audit trail."""
    try:
        supabase.table("system_resource_audit_logs").insert({
            "resource_id": resource_id,
            "action": action,
            "old_data": old_data,
            "new_data": new_data,
            "changed_by": changed_by
        }).execute()
    except Exception as e:
        print(f"[AUDIT] Failed to log: {e}")


def get_image_dimensions(file_bytes: bytes) -> Optional[dict]:
    """Extract image dimensions from file bytes."""
    try:
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(file_bytes))
        return {"width": img.width, "height": img.height}
    except Exception:
        return None
