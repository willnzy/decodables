"""
Pytest Configuration and Fixtures
pytest 配置和 fixtures

This file sets up the test environment to allow testing individual modules
without triggering the full import chain that requires all dependencies.

Features:
- Mock external dependencies (OpenAI, FAL, DashScope, Supabase, Redis)
- Environment variable setup for testing
- Pre-import mocking for modules that require dependencies
"""

import pytest
import sys
import os
import importlib.util
from unittest.mock import MagicMock, patch, AsyncMock

# ==========================================
# Early Mocking (Before Any Imports)
# ==========================================

# Mock dashscope before it's imported anywhere
# This is critical because dashscope may not be installed in CI/local environments
dashscope_mock = MagicMock()
dashscope_mock.Generation = MagicMock()
dashscope_mock.ImageSynthesis = MagicMock()
sys.modules['dashscope'] = dashscope_mock

# Mock fal_client if not installed
if 'fal_client' not in sys.modules:
    fal_mock = MagicMock()
    fal_mock.submit_async = AsyncMock()
    sys.modules['fal_client'] = fal_mock

# 添加项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ==========================================
# Environment Setup
# ==========================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境变量 - 在所有测试前运行"""
    # AI Services
    os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-testing")
    os.environ.setdefault("FAL_KEY", "test-fal-key")
    os.environ.setdefault("DASHSCOPE_API_KEY", "test-dashscope-key")
    os.environ.setdefault("GOOGLE_AI_KEY", "test-google-key")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
    os.environ.setdefault("XAI_API_KEY", "test-xai-key")
    
    # Supabase
    os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co/")
    os.environ.setdefault("SUPABASE_KEY", "test-supabase-key")
    
    # Stripe
    os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_mock")
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_mock")
    
    # Testing flag
    os.environ["TESTING"] = "true"
    
    yield
    
    # Cleanup (optional)
    os.environ.pop("TESTING", None)


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
# Database Mock Fixtures
# ==========================================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client - 完整模拟数据库操作"""
    with patch('services.db_service.supabase') as mock:
        # SELECT operations
        mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
        
        # INSERT operations
        mock.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": 1}])
        
        # UPDATE operations
        mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        # DELETE operations
        mock.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        # RPC operations
        mock.rpc.return_value.execute.return_value = MagicMock(data=None)
        
        # Storage operations
        mock.storage.from_.return_value.upload.return_value = None
        mock.storage.from_.return_value.get_public_url.return_value = "https://test.supabase.co/storage/v1/object/public/test/file.png"
        
        yield mock


@pytest.fixture
def mock_supabase_with_config():
    """Mock Supabase with pre-configured system_configs"""
    with patch('services.db_service.supabase') as mock:
        # Default config response
        def config_response(key):
            configs = {
                "ai_text.default": {"provider": "openai", "model": "gpt-4o-mini"},
                "ai_image.default": {"provider": "fal", "models": {"free": "flux-schnell"}},
                "ai_providers.enabled": {"openai": True, "fal": True, "qwen": False},
                "ai_canary.config": {"enabled": False},
            }
            if key in configs:
                return MagicMock(data=[{"value": configs[key]}])
            return MagicMock(data=[])
        
        mock.table.return_value.select.return_value.eq.side_effect = lambda k, v: MagicMock(
            execute=MagicMock(return_value=config_response(v))
        )
        
        yield mock


# ==========================================
# Cache Mock Fixtures
# ==========================================

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('services.cache.redis_client.get_redis_client') as mock_get:
        with patch('services.cache.redis_client.is_redis_available') as mock_avail:
            redis_mock = MagicMock()
            redis_mock.get.return_value = None
            redis_mock.set.return_value = True
            redis_mock.setex.return_value = True
            redis_mock.delete.return_value = 1
            redis_mock.scan.return_value = (0, [])
            redis_mock.ping.return_value = True
            
            mock_get.return_value = redis_mock
            mock_avail.return_value = True
            
            yield redis_mock


@pytest.fixture
def mock_cache_service():
    """Mock CacheService"""
    with patch('services.cache.cache_service.cache_service') as mock:
        mock.get.return_value = None
        mock.get_json.return_value = None
        mock.get_config.return_value = None
        mock.get_experiment.return_value = None
        mock.get_ai_result.return_value = None
        mock.set.return_value = True
        mock.set_json.return_value = True
        mock.set_config.return_value = True
        mock.delete.return_value = True
        mock.is_redis_active.return_value = False
        mock.get_backend_info.return_value = {"backend": "memory", "redis_available": False}
        yield mock


# ==========================================
# AI Client Mock Fixtures
# ==========================================

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client - 完整模拟"""
    with patch('openai.OpenAI') as mock_class:
        mock_client = MagicMock()
        
        # Chat completion
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_client.chat.completions.create.return_value = mock_response
        
        # Image generation
        mock_image_response = MagicMock()
        mock_image_response.data = [MagicMock(url="https://test.openai.com/image.png")]
        mock_client.images.generate.return_value = mock_image_response
        
        mock_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_fal_client():
    """Mock FAL client"""
    with patch('fal_client.submit_async') as mock_submit:
        mock_result = MagicMock()
        mock_result.images = [{"url": "https://fal.ai/test-image.png"}]
        mock_submit.return_value = mock_result
        yield mock_submit


@pytest.fixture
def mock_dashscope():
    """Mock DashScope (Qwen/Wanx) client"""
    with patch('dashscope.Generation') as mock_gen:
        with patch('dashscope.ImageSynthesis') as mock_img:
            # Text generation
            text_response = MagicMock()
            text_response.status_code = 200
            text_response.output = MagicMock(
                choices=[MagicMock(message=MagicMock(content="Qwen response"))]
            )
            text_response.usage = MagicMock(input_tokens=10, output_tokens=20, total_tokens=30)
            mock_gen.call.return_value = text_response
            
            # Image generation
            image_response = MagicMock()
            image_response.status_code = 200
            image_response.output = MagicMock(
                results=[MagicMock(url="https://dashscope.aliyun.com/image.png")]
            )
            mock_img.call.return_value = image_response
            
            yield {"generation": mock_gen, "image_synthesis": mock_img}


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
def mock_starter_user():
    """Starter tier user"""
    return {
        "id": "user_starter_456",
        "email": "starter@test.com",
        "tier": "starter",
        "role": "user",
    }


@pytest.fixture
def mock_pro_user():
    """Pro tier user"""
    return {
        "id": "user_pro_789",
        "email": "pro@test.com",
        "tier": "pro",
        "role": "user",
    }


@pytest.fixture
def mock_admin_user():
    """Admin user"""
    return {
        "id": "admin_001",
        "email": "admin@test.com",
        "tier": "pro",
        "role": "admin",
    }


@pytest.fixture
def mock_user_with_credits():
    """User with sufficient credits"""
    return {
        "id": "user_credits_999",
        "email": "credits@test.com",
        "tier": "starter",
        "role": "user",
        "credits": {
            "balance_monthly": 500,
            "balance_permanent": 100,
        }
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


# ==========================================
# FastAPI Test Client
# ==========================================

@pytest.fixture
def client():
    """FastAPI test client with mocked dependencies"""
    # Import here to avoid triggering imports at module level
    from fastapi.testclient import TestClient
    
    # Mock dependencies before importing app
    with patch('services.db_service.supabase') as mock_db:
        mock_db.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
        
        # Import app after mocking
        from app import app
        
        yield TestClient(app)


# ==========================================
# Config Service Mock
# ==========================================

@pytest.fixture
def mock_config_service():
    """Mock ConfigService for testing"""
    with patch('services.config_service.get_config') as mock:
        def get_config_mock(key, default=None):
            configs = {
                "ai_text.default": {"provider": "openai", "model": "gpt-4o-mini"},
                "ai_image.default": {"provider": "fal", "models": {"free": "flux-schnell", "pro": "flux-dev"}},
                "ai_admin.default": {"provider": "openai", "model": "gpt-4o"},
                "ai_providers.enabled": {"openai": True, "fal": True, "qwen": False, "wanx": False},
                "ai_providers.models": {
                    "openai": {"text": ["gpt-4o-mini", "gpt-4o"], "image": ["dall-e-3"]},
                    "fal": {"image": ["flux-schnell", "flux-dev"]},
                    "qwen": {"text": ["qwen-turbo", "qwen-plus"]},
                    "wanx": {"image": ["wan2.6-t2i"]},
                },
                "ai_canary.config": {"enabled": False},
            }
            return configs.get(key, default)
        
        mock.side_effect = get_config_mock
        yield mock


# ==========================================
# Experiment Service Mock
# ==========================================

@pytest.fixture
def mock_experiment_service():
    """Mock ExperimentService for A/B testing"""
    with patch('services.experiment_service.ExperimentService') as mock_class:
        mock_service = MagicMock()
        mock_service.get_variant.return_value = "control"
        mock_service.get_experiment.return_value = {
            "key": "test_experiment",
            "status": "running",
            "variants": [
                {"name": "control", "weight": 50},
                {"name": "variant_a", "weight": 50},
            ]
        }
        mock_class.return_value = mock_service
        yield mock_service


# ==========================================
# HTTP Request Mock
# ==========================================

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession for async HTTP requests"""
    with patch('aiohttp.ClientSession') as mock_class:
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = b"fake image data"
        mock_response.json.return_value = {"success": True}
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        mock_class.return_value.__aenter__.return_value = mock_session
        
        yield mock_session


# ==========================================
# Utility Functions
# ==========================================

def assert_ai_response_success(response, expected_provider=None, expected_model=None):
    """Helper to assert AI response is successful"""
    from services.ai.base import AIResponse
    assert isinstance(response, AIResponse)
    assert response.success is True
    assert response.error is None
    if expected_provider:
        assert response.provider == expected_provider
    if expected_model:
        assert response.model == expected_model


def assert_ai_response_failure(response, expected_error_type=None):
    """Helper to assert AI response is failure"""
    from services.ai.base import AIResponse
    assert isinstance(response, AIResponse)
    assert response.success is False
    assert response.error is not None
    if expected_error_type:
        assert response.error_type == expected_error_type
