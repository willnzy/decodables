"""
Service Factory Tests
服务工厂测试

Coverage target: 90%+
Business logic tested:
- Singleton pattern for service instances
- Factory methods return correct service types
- Service caching/reuse
"""

import pytest
from unittest.mock import patch, MagicMock


class TestServiceFactoryClass:
    """Test ServiceFactory class methods"""
    
    def setup_method(self):
        """Reset factory state before each test"""
        from services.service_factory import ServiceFactory
        ServiceFactory._credit_service = None
        ServiceFactory._marketplace_service = None
        ServiceFactory._access_control = None
        ServiceFactory._resource_service = None
    
    def test_get_credit_service_creates_instance(self):
        """get_credit_service creates CreditService instance"""
        from services.service_factory import ServiceFactory, CreditService
        
        service = ServiceFactory.get_credit_service()
        
        assert isinstance(service, CreditService)
    
    def test_get_credit_service_singleton(self):
        """get_credit_service returns same instance"""
        from services.service_factory import ServiceFactory
        
        service1 = ServiceFactory.get_credit_service()
        service2 = ServiceFactory.get_credit_service()
        
        assert service1 is service2
    
    def test_get_marketplace_service_creates_instance(self):
        """get_marketplace_service creates MarketplaceService instance"""
        from services.service_factory import ServiceFactory, MarketplaceService
        
        service = ServiceFactory.get_marketplace_service()
        
        assert isinstance(service, MarketplaceService)
    
    def test_get_marketplace_service_singleton(self):
        """get_marketplace_service returns same instance"""
        from services.service_factory import ServiceFactory
        
        service1 = ServiceFactory.get_marketplace_service()
        service2 = ServiceFactory.get_marketplace_service()
        
        assert service1 is service2
    
    def test_get_access_control_creates_instance(self):
        """get_access_control creates AccessControl instance"""
        from services.service_factory import ServiceFactory, AccessControl
        
        service = ServiceFactory.get_access_control()
        
        assert isinstance(service, AccessControl)
    
    def test_get_access_control_singleton(self):
        """get_access_control returns same instance"""
        from services.service_factory import ServiceFactory
        
        service1 = ServiceFactory.get_access_control()
        service2 = ServiceFactory.get_access_control()
        
        assert service1 is service2
    
    def test_get_resource_service_creates_instance(self):
        """get_resource_service creates ResourceService instance"""
        from services.service_factory import ServiceFactory, ResourceService
        
        service = ServiceFactory.get_resource_service()
        
        assert isinstance(service, ResourceService)
    
    def test_get_resource_service_singleton(self):
        """get_resource_service returns same instance"""
        from services.service_factory import ServiceFactory
        
        service1 = ServiceFactory.get_resource_service()
        service2 = ServiceFactory.get_resource_service()
        
        assert service1 is service2


class TestConvenienceFunctions:
    """Test module-level convenience functions"""
    
    def setup_method(self):
        """Reset factory state before each test"""
        from services.service_factory import ServiceFactory
        ServiceFactory._credit_service = None
        ServiceFactory._marketplace_service = None
        ServiceFactory._access_control = None
        ServiceFactory._resource_service = None
    
    def test_get_credit_service_function(self):
        """get_credit_service function works"""
        from services.service_factory import get_credit_service, CreditService
        
        service = get_credit_service()
        
        assert isinstance(service, CreditService)
    
    def test_get_marketplace_service_function(self):
        """get_marketplace_service function works"""
        from services.service_factory import get_marketplace_service, MarketplaceService
        
        service = get_marketplace_service()
        
        assert isinstance(service, MarketplaceService)
    
    def test_get_access_control_function(self):
        """get_access_control function works"""
        from services.service_factory import get_access_control, AccessControl
        
        service = get_access_control()
        
        assert isinstance(service, AccessControl)
    
    def test_get_resource_service_function(self):
        """get_resource_service function works"""
        from services.service_factory import get_resource_service, ResourceService
        
        service = get_resource_service()
        
        assert isinstance(service, ResourceService)


class TestModuleExports:
    """Test module __all__ exports"""
    
    def test_all_exports_defined(self):
        """__all__ exports are properly defined"""
        from services import service_factory
        
        expected_exports = [
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
        
        for export in expected_exports:
            assert export in service_factory.__all__
    
    def test_service_classes_importable(self):
        """Service classes can be imported from module"""
        from services.service_factory import (
            ServiceFactory,
            CreditService,
            MarketplaceService,
            AccessControl,
            ResourceService,
        )
        
        assert ServiceFactory is not None
        assert CreditService is not None
        assert MarketplaceService is not None
        assert AccessControl is not None
        assert ResourceService is not None


class TestServiceDependencies:
    """Test service dependencies are injected correctly"""
    
    def setup_method(self):
        """Reset factory state before each test"""
        from services.service_factory import ServiceFactory
        ServiceFactory._credit_service = None
        ServiceFactory._marketplace_service = None
        ServiceFactory._access_control = None
        ServiceFactory._resource_service = None
    
    def test_credit_service_has_supabase(self):
        """CreditService receives supabase client"""
        from services.service_factory import ServiceFactory
        
        service = ServiceFactory.get_credit_service()
        
        # CreditService should have supabase attribute
        assert hasattr(service, 'supabase')
    
    def test_marketplace_service_has_supabase(self):
        """MarketplaceService receives supabase client"""
        from services.service_factory import ServiceFactory
        
        service = ServiceFactory.get_marketplace_service()
        
        assert hasattr(service, 'supabase')
    
    def test_resource_service_has_supabase(self):
        """ResourceService receives supabase client"""
        from services.service_factory import ServiceFactory
        
        service = ServiceFactory.get_resource_service()
        
        assert hasattr(service, 'supabase')
    
    def test_access_control_no_external_deps(self):
        """AccessControl has no external dependencies"""
        from services.service_factory import ServiceFactory
        
        service = ServiceFactory.get_access_control()
        
        # AccessControl is initialized without arguments
        assert service is not None


class TestFactoryStateIsolation:
    """Test that factory state is properly isolated"""
    
    def test_different_service_types_independent(self):
        """Different service types have independent instances"""
        from services.service_factory import ServiceFactory
        
        # Reset state
        ServiceFactory._credit_service = None
        ServiceFactory._marketplace_service = None
        
        credit_service = ServiceFactory.get_credit_service()
        marketplace_service = ServiceFactory.get_marketplace_service()
        
        # They should be different objects
        assert credit_service is not marketplace_service
        
        # But each should be a singleton
        assert ServiceFactory.get_credit_service() is credit_service
        assert ServiceFactory.get_marketplace_service() is marketplace_service


class TestServiceFunctionality:
    """Test that created services have expected functionality"""
    
    def setup_method(self):
        """Reset factory state"""
        from services.service_factory import ServiceFactory
        ServiceFactory._credit_service = None
        ServiceFactory._marketplace_service = None
        ServiceFactory._access_control = None
        ServiceFactory._resource_service = None
    
    def test_access_control_has_methods(self):
        """AccessControl has expected methods"""
        from services.service_factory import get_access_control
        
        service = get_access_control()
        
        # Check for expected methods from business logic
        assert hasattr(service, 'is_member')
        assert hasattr(service, 'can_access_resource')
        assert hasattr(service, 'publish_permission')
        assert hasattr(service, 'can_use_stickers')
        assert hasattr(service, 'can_use_ocr')
    
    def test_credit_service_has_methods(self):
        """CreditService has expected methods"""
        from services.service_factory import get_credit_service
        
        service = get_credit_service()
        
        # Check for expected methods
        assert hasattr(service, 'get_balance')
        assert hasattr(service, 'get_total')
        assert hasattr(service, 'has_enough')
