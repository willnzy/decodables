"""
Pytest Configuration and Fixtures
pytest 配置和 fixtures

This file sets up the test environment to allow testing individual modules
without triggering the full import chain that requires all dependencies.
"""

import pytest
import sys
import os
import importlib.util
from unittest.mock import MagicMock, patch

# 添加项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ==========================================
# Environment Setup
# ==========================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境变量"""
    os.environ.setdefault("OPENAI_API_KEY", "test-key-for-testing")
    os.environ.setdefault("FAL_KEY", "test-fal-key")
    os.environ.setdefault("DASHSCOPE_API_KEY", "test-dashscope-key")
    os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co/")
    os.environ.setdefault("SUPABASE_KEY", "test-supabase-key")
    yield


# ==========================================
# Module Loading Helpers
# ==========================================

def load_module_directly(module_name: str, file_path: str):
    """
    直接从文件加载模块，避免触发完整的导入链
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def ai_base_module():
    """加载 AI base 模块"""
    return load_module_directly(
        "services.ai.base",
        os.path.join(PROJECT_ROOT, "services/ai/base.py")
    )


# ==========================================
# Mock Fixtures
# ==========================================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    with patch('services.db_service.supabase') as mock:
        mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
        mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock.rpc.return_value.execute.return_value = MagicMock(data=None)
        yield mock


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('services.cache.redis_client.get_redis_client') as mock:
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.delete.return_value = 1
        mock.return_value = redis_mock
        yield redis_mock


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    with patch('openai.OpenAI') as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_fal_client():
    """Mock FAL client"""
    with patch('fal_client.submit_async') as mock:
        yield mock


# ==========================================
# Test User Fixtures
# ==========================================

@pytest.fixture
def mock_free_user():
    """Free tier user"""
    return {
        "id": "user_free_123",
        "email": "free@test.com",
        "tier": "free",
        "role": "user",
    }


@pytest.fixture
def mock_pro_user():
    """Pro tier user"""
    return {
        "id": "user_pro_456",
        "email": "pro@test.com",
        "tier": "pro",
        "role": "user",
    }


@pytest.fixture
def mock_admin_user():
    """Admin user"""
    return {
        "id": "admin_789",
        "email": "admin@test.com",
        "tier": "pro",
        "role": "admin",
    }


# ==========================================
# AI Response Fixtures
# ==========================================

@pytest.fixture
def successful_text_response():
    """成功的文本 AI 响应"""
    from services.ai.base import AIResponse, AIUsage
    return AIResponse(
        success=True,
        content="Test response content",
        usage=AIUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        model="gpt-4o-mini",
        provider="openai",
        latency_ms=150
    )


@pytest.fixture
def successful_image_response():
    """成功的图像 AI 响应"""
    from services.ai.base import AIResponse, AIUsage
    return AIResponse(
        success=True,
        content=["https://example.com/image1.png", "https://example.com/image2.png"],
        usage=AIUsage(images_generated=2),
        model="flux-schnell",
        provider="fal",
        latency_ms=2500
    )


@pytest.fixture
def failed_response():
    """失败的 AI 响应"""
    from services.ai.base import AIResponse, AIErrorType
    return AIResponse(
        success=False,
        error="Rate limit exceeded",
        error_type=AIErrorType.RATE_LIMIT,
        provider="openai",
        model="gpt-4o"
    )
