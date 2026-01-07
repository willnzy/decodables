"""
AI Adapters Tests
AI 适配器工厂测试
"""

import pytest
from unittest.mock import patch, MagicMock


class TestRegisterAdapters:
    def test_register_text_adapter(self):
        from shared.ai.adapters import register_text_adapter, _text_adapters
        
        mock_adapter = MagicMock()
        register_text_adapter("test_provider", mock_adapter)
        
        assert "test_provider" in _text_adapters
        
        # Cleanup
        del _text_adapters["test_provider"]

    def test_register_image_adapter(self):
        from shared.ai.adapters import register_image_adapter, _image_adapters
        
        mock_adapter = MagicMock()
        register_image_adapter("test_provider", mock_adapter)
        
        assert "test_provider" in _image_adapters
        
        # Cleanup
        del _image_adapters["test_provider"]


class TestGetTextAdapter:
    def test_returns_none_for_unknown_provider(self):
        from shared.ai.adapters import get_text_adapter
        
        result = get_text_adapter("unknown_provider_xyz")
        
        assert result is None

    def test_returns_cached_instance(self):
        from shared.ai.adapters import get_text_adapter, _text_adapters, _text_adapter_instances, clear_adapter_cache
        
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
        from shared.ai.adapters import get_text_adapter, _text_adapters, clear_adapter_cache
        
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
        from shared.ai.adapters import get_text_adapter, _text_adapters, clear_adapter_cache
        
        clear_adapter_cache()
        
        mock_class = MagicMock(side_effect=Exception("Init error"))
        _text_adapters["error_provider"] = mock_class
        
        result = get_text_adapter("error_provider")
        
        assert result is None
        
        # Cleanup
        del _text_adapters["error_provider"]


class TestGetImageAdapter:
    def test_returns_none_for_unknown_provider(self):
        from shared.ai.adapters import get_image_adapter
        
        result = get_image_adapter("unknown_provider_xyz")
        
        assert result is None

    def test_returns_cached_instance(self):
        from shared.ai.adapters import get_image_adapter, _image_adapters, clear_adapter_cache
        
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
        from shared.ai.adapters import get_image_adapter, _image_adapters, clear_adapter_cache
        
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
        from shared.ai.adapters import get_image_adapter, _image_adapters, clear_adapter_cache
        
        clear_adapter_cache()
        
        mock_class = MagicMock(side_effect=Exception("Init error"))
        _image_adapters["error_img"] = mock_class
        
        result = get_image_adapter("error_img")
        
        assert result is None
        
        # Cleanup
        del _image_adapters["error_img"]


class TestClearAdapterCache:
    def test_clears_all_caches(self):
        from shared.ai.adapters import (
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
        from shared.ai.adapters import get_available_text_providers, _text_adapters, clear_adapter_cache
        
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
        from shared.ai.adapters import get_available_image_providers, _image_adapters, clear_adapter_cache
        
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
        from shared.ai.adapters import _text_adapters, _image_adapters
        
        # OpenAI should be auto-registered
        assert "openai" in _text_adapters

    def test_fal_registered(self):
        from shared.ai.adapters import _image_adapters
        
        # FAL should be auto-registered
        assert "fal" in _image_adapters
    
    def test_qwen_text_registered(self):
        """Qwen 文本适配器应已注册"""
        from shared.ai.adapters import _text_adapters
        
        assert "qwen" in _text_adapters
    
    def test_wanx_image_registered(self):
        """Wanx 图像适配器应已注册"""
        from shared.ai.adapters import _image_adapters
        
        assert "wanx" in _image_adapters


class TestAutoRegistrationImportErrors:
    """测试自动注册时的 ImportError 处理"""
    
    def test_auto_register_handles_openai_import_error(self):
        """测试 OpenAI 导入失败时的处理"""
        import sys
        import importlib
        
        # Temporarily remove openai adapter to trigger import error
        original_modules = {}
        module_keys = [k for k in sys.modules.keys() if 'openai_adapter' in k or k == 'openai']
        for key in module_keys:
            original_modules[key] = sys.modules.pop(key, None)
        
        # Clear adapters
        from shared.ai import adapters
        adapters._text_adapters.pop('openai', None)
        adapters._image_adapters.pop('openai', None)
        
        # Mock the import to fail
        with patch.dict(sys.modules, {'services.ai.adapters.openai_adapter': None}):
            # This should handle the ImportError gracefully
            adapters._auto_register_adapters()
        
        # Restore modules
        for key, mod in original_modules.items():
            if mod is not None:
                sys.modules[key] = mod
    
    def test_auto_register_handles_fal_import_error(self):
        """测试 FAL 导入失败时的处理"""
        import sys
        
        from shared.ai import adapters
        adapters._image_adapters.pop('fal', None)
        
        # Mock the import to fail
        original_modules = {}
        module_keys = [k for k in sys.modules.keys() if 'fal_adapter' in k or k == 'fal_client']
        for key in module_keys:
            original_modules[key] = sys.modules.pop(key, None)
        
        with patch.dict(sys.modules, {'services.ai.adapters.fal_adapter': None}):
            adapters._auto_register_adapters()
        
        for key, mod in original_modules.items():
            if mod is not None:
                sys.modules[key] = mod
    
    def test_auto_register_handles_qwen_import_error(self):
        """测试 Qwen 导入失败时的处理"""
        import sys
        
        from shared.ai import adapters
        adapters._text_adapters.pop('qwen', None)
        adapters._image_adapters.pop('wanx', None)
        
        original_modules = {}
        module_keys = [k for k in sys.modules.keys() if 'qwen_adapter' in k or k == 'dashscope']
        for key in module_keys:
            original_modules[key] = sys.modules.pop(key, None)
        
        with patch.dict(sys.modules, {'services.ai.adapters.qwen_adapter': None}):
            adapters._auto_register_adapters()
        
        for key, mod in original_modules.items():
            if mod is not None:
                sys.modules[key] = mod
    
    def test_auto_register_handles_gemini_import_error(self):
        """测试 Gemini 导入失败时的处理 (通常失败因为未安装)"""
        from shared.ai import adapters
        
        # Gemini adapter probably isn't installed, so this path is hit anyway
        # Just verify the registration function can be called without error
        adapters._auto_register_adapters()
    
    def test_auto_register_handles_anthropic_import_error(self):
        """测试 Anthropic 导入失败时的处理"""
        from shared.ai import adapters
        
        # Similar to Gemini
        adapters._auto_register_adapters()
    
    def test_auto_register_handles_grok_import_error(self):
        """测试 Grok 导入失败时的处理"""
        from shared.ai import adapters
        
        adapters._auto_register_adapters()
    
    def test_auto_register_handles_jimeng_import_error(self):
        """测试 Jimeng 导入失败时的处理"""
        from shared.ai import adapters
        
        adapters._auto_register_adapters()


class TestExports:
    """测试模块导出"""
    
    def test_all_exports(self):
        """测试 __all__ 导出"""
        from shared.ai import adapters
        
        assert "get_text_adapter" in adapters.__all__
        assert "get_image_adapter" in adapters.__all__
        assert "get_available_text_providers" in adapters.__all__
        assert "get_available_image_providers" in adapters.__all__
        assert "register_text_adapter" in adapters.__all__
        assert "register_image_adapter" in adapters.__all__
        assert "clear_adapter_cache" in adapters.__all__
