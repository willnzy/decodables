"""
AI Adapters Tests
AI 适配器工厂测试
"""

import pytest
from unittest.mock import patch, MagicMock


class TestRegisterAdapters:
    def test_register_text_adapter(self):
        from services.ai.adapters import register_text_adapter, _text_adapters
        
        mock_adapter = MagicMock()
        register_text_adapter("test_provider", mock_adapter)
        
        assert "test_provider" in _text_adapters
        
        # Cleanup
        del _text_adapters["test_provider"]

    def test_register_image_adapter(self):
        from services.ai.adapters import register_image_adapter, _image_adapters
        
        mock_adapter = MagicMock()
        register_image_adapter("test_provider", mock_adapter)
        
        assert "test_provider" in _image_adapters
        
        # Cleanup
        del _image_adapters["test_provider"]


class TestGetTextAdapter:
    def test_returns_none_for_unknown_provider(self):
        from services.ai.adapters import get_text_adapter
        
        result = get_text_adapter("unknown_provider_xyz")
        
        assert result is None

    def test_returns_cached_instance(self):
        from services.ai.adapters import get_text_adapter, _text_adapters, _text_adapter_instances, clear_adapter_cache
        
        clear_adapter_cache()
        
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_class.return_value = mock_instance
        
        _text_adapters["test_cached"] = mock_class
        
        result1 = get_text_adapter("test_cached")
        result2 = get_text_adapter("test_cached")
        
        assert result1 is result2
        assert mock_class.call_count == 1  # Only called once
        
        # Cleanup
        del _text_adapters["test_cached"]
        clear_adapter_cache()

    def test_returns_none_when_not_available(self):
        from services.ai.adapters import get_text_adapter, _text_adapters, clear_adapter_cache
        
        clear_adapter_cache()
        
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = False
        mock_class.return_value = mock_instance
        
        _text_adapters["unavailable"] = mock_class
        
        result = get_text_adapter("unavailable")
        
        assert result is None
        
        # Cleanup
        del _text_adapters["unavailable"]

    def test_handles_init_exception(self):
        from services.ai.adapters import get_text_adapter, _text_adapters, clear_adapter_cache
        
        clear_adapter_cache()
        
        mock_class = MagicMock(side_effect=Exception("Init error"))
        _text_adapters["error_provider"] = mock_class
        
        result = get_text_adapter("error_provider")
        
        assert result is None
        
        # Cleanup
        del _text_adapters["error_provider"]


class TestGetImageAdapter:
    def test_returns_none_for_unknown_provider(self):
        from services.ai.adapters import get_image_adapter
        
        result = get_image_adapter("unknown_provider_xyz")
        
        assert result is None

    def test_returns_cached_instance(self):
        from services.ai.adapters import get_image_adapter, _image_adapters, clear_adapter_cache
        
        clear_adapter_cache()
        
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_class.return_value = mock_instance
        
        _image_adapters["test_img_cached"] = mock_class
        
        result1 = get_image_adapter("test_img_cached")
        result2 = get_image_adapter("test_img_cached")
        
        assert result1 is result2
        
        # Cleanup
        del _image_adapters["test_img_cached"]
        clear_adapter_cache()

    def test_returns_none_when_not_available(self):
        from services.ai.adapters import get_image_adapter, _image_adapters, clear_adapter_cache
        
        clear_adapter_cache()
        
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = False
        mock_class.return_value = mock_instance
        
        _image_adapters["unavailable_img"] = mock_class
        
        result = get_image_adapter("unavailable_img")
        
        assert result is None
        
        # Cleanup
        del _image_adapters["unavailable_img"]

    def test_handles_init_exception(self):
        from services.ai.adapters import get_image_adapter, _image_adapters, clear_adapter_cache
        
        clear_adapter_cache()
        
        mock_class = MagicMock(side_effect=Exception("Init error"))
        _image_adapters["error_img"] = mock_class
        
        result = get_image_adapter("error_img")
        
        assert result is None
        
        # Cleanup
        del _image_adapters["error_img"]


class TestClearAdapterCache:
    def test_clears_all_caches(self):
        from services.ai.adapters import (
            clear_adapter_cache, 
            _text_adapter_instances, 
            _image_adapter_instances,
            _text_adapters,
            _image_adapters
        )
        
        # Setup mock adapters
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_class.return_value = mock_instance
        
        _text_adapters["clear_test"] = mock_class
        _image_adapters["clear_test_img"] = mock_class
        
        # Populate caches
        _text_adapter_instances["clear_test"] = mock_instance
        _image_adapter_instances["clear_test_img"] = mock_instance
        
        clear_adapter_cache()
        
        assert len(_text_adapter_instances) == 0
        assert len(_image_adapter_instances) == 0
        
        # Cleanup
        del _text_adapters["clear_test"]
        del _image_adapters["clear_test_img"]


class TestGetAvailableProviders:
    def test_get_available_text_providers(self):
        from services.ai.adapters import get_available_text_providers, _text_adapters, clear_adapter_cache
        
        clear_adapter_cache()
        
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_class.return_value = mock_instance
        
        _text_adapters["avail_text"] = mock_class
        
        result = get_available_text_providers()
        
        assert "avail_text" in result
        
        # Cleanup
        del _text_adapters["avail_text"]
        clear_adapter_cache()

    def test_get_available_image_providers(self):
        from services.ai.adapters import get_available_image_providers, _image_adapters, clear_adapter_cache
        
        clear_adapter_cache()
        
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_class.return_value = mock_instance
        
        _image_adapters["avail_img"] = mock_class
        
        result = get_available_image_providers()
        
        assert "avail_img" in result
        
        # Cleanup
        del _image_adapters["avail_img"]
        clear_adapter_cache()


class TestAutoRegistration:
    def test_openai_registered(self):
        from services.ai.adapters import _text_adapters, _image_adapters
        
        # OpenAI should be auto-registered
        assert "openai" in _text_adapters

    def test_fal_registered(self):
        from services.ai.adapters import _image_adapters
        
        # FAL should be auto-registered
        assert "fal" in _image_adapters
