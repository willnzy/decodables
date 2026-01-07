"""
Storage Service Providers - Concrete implementations of IStorageService.

@module shared.storage.providers
@version 1.0.0
"""

from .supabase_provider import SupabaseStorageProvider

__all__ = [
    "SupabaseStorageProvider",
]
