"""
Service Factory
Creates and provides service instances

@module services/service_factory
"""

from functools import lru_cache
from .db_service import supabase
from .credit_service import CreditService
from .marketplace_service import MarketplaceService
from .access_control import AccessControl
from .resource_service import ResourceService


class ServiceFactory:
    """
    Factory for creating service instances.
    Uses singleton pattern for efficiency.
    """
    
    _credit_service: CreditService = None
    _marketplace_service: MarketplaceService = None
    _access_control: AccessControl = None
    _resource_service: ResourceService = None
    
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
    
    @classmethod
    def get_resource_service(cls) -> ResourceService:
        """Get ResourceService singleton."""
        if cls._resource_service is None:
            cls._resource_service = ResourceService(supabase)
        return cls._resource_service


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


def get_resource_service() -> ResourceService:
    """Get ResourceService instance."""
    return ServiceFactory.get_resource_service()


# Re-export service classes for type hints
__all__ = [
    'ServiceFactory',
    'get_credit_service',
    'get_marketplace_service', 
    'get_access_control',
    'get_resource_service',
    'CreditService',
    'MarketplaceService',
    'AccessControl',
    'ResourceService',
]

