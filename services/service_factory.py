"""
Service Factory
Creates and provides service instances

@module services/service_factory
"""

from functools import lru_cache
from db_service import supabase
from .credit_service import CreditService
from .marketplace_service import MarketplaceService
from .access_control import AccessControl


class ServiceFactory:
    """
    Factory for creating service instances.
    Uses singleton pattern for efficiency.
    """
    
    _credit_service: CreditService = None
    _marketplace_service: MarketplaceService = None
    _access_control: AccessControl = None
    
    @classmethod
    def get_credit_service(cls) -> CreditService:
        """Get CreditService singleton."""
        if cls._credit_service is None:
            cls._credit_service = CreditService(supabase)
        return cls._credit_service
    
    @classmethod
    def get_marketplace_service(cls) -> MarketplaceService:
        """Get MarketplaceService singleton."""
        if cls._marketplace_service is None:
            cls._marketplace_service = MarketplaceService(supabase)
        return cls._marketplace_service
    
    @classmethod
    def get_access_control(cls) -> AccessControl:
        """Get AccessControl singleton."""
        if cls._access_control is None:
            cls._access_control = AccessControl()
        return cls._access_control


# Convenience functions
def get_credit_service() -> CreditService:
    """Get CreditService instance."""
    return ServiceFactory.get_credit_service()


def get_marketplace_service() -> MarketplaceService:
    """Get MarketplaceService instance."""
    return ServiceFactory.get_marketplace_service()


def get_access_control() -> AccessControl:
    """Get AccessControl instance."""
    return ServiceFactory.get_access_control()


# Re-export service classes for type hints
__all__ = [
    'ServiceFactory',
    'get_credit_service',
    'get_marketplace_service', 
    'get_access_control',
    'CreditService',
    'MarketplaceService',
    'AccessControl',
]

