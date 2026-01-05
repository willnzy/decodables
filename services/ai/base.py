"""
AI Provider Base Classes
AI 提供商适配器基类

Provides:
- Abstract base class for all AI adapters
- Common interface for text and image generation
- Standardized response format
- Error handling patterns
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ==========================================
# Data Classes
# ==========================================

class AICallType(str, Enum):
    """AI 调用类型"""
    TEXT = "text"
    IMAGE = "image"


@dataclass
class AIMessage:
    """聊天消息"""
    role: str  # "system", "user", "assistant"
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class AIUsage:
    """Token/资源使用量"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    images_generated: int = 0
    
    @property
    def total(self) -> int:
        return self.total_tokens or (self.input_tokens + self.output_tokens)


@dataclass
class AIResponse:
    """
    统一的 AI 响应格式
    
    Attributes:
        success: 是否成功
        content: 响应内容 (文本或图像 URL 列表)
        usage: 资源使用量
        model: 实际使用的模型
        provider: 实际使用的提供商
        latency_ms: 延迟毫秒数
        raw_response: 原始响应 (调试用)
        error: 错误信息
        error_type: 错误类型 (rate_limit, timeout, api_error, etc.)
    """
    success: bool
    content: Union[str, List[str]] = ""
    usage: AIUsage = field(default_factory=AIUsage)
    model: str = ""
    provider: str = ""
    latency_ms: int = 0
    raw_response: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    @classmethod
    def from_error(
        cls, 
        error: str, 
        error_type: str = "unknown",
        provider: str = "",
        model: str = ""
    ) -> "AIResponse":
        """从错误创建响应"""
        return cls(
            success=False,
            error=error,
            error_type=error_type,
            provider=provider,
            model=model
        )


# ==========================================
# Abstract Base Classes
# ==========================================

class BaseTextAdapter(ABC):
    """
    文本 AI 适配器基类
    
    所有文本模型提供商 (OpenAI, Qwen, Gemini, etc.) 都需要实现此接口
    """
    
    provider_name: str = "base"
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> AIResponse:
        """
        聊天补全接口
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            model: 模型名称
            temperature: 温度 (0-2)
            max_tokens: 最大输出 token 数
            response_format: 响应格式 (如 {"type": "json_object"})
            **kwargs: 其他提供商特定参数
            
        Returns:
            AIResponse 对象
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        pass
    
    def is_available(self) -> bool:
        """检查提供商是否可用 (API Key 已配置)"""
        return True


class BaseImageAdapter(ABC):
    """
    图像 AI 适配器基类
    
    所有图像模型提供商 (FAL, OpenAI DALL-E, etc.) 都需要实现此接口
    """
    
    provider_name: str = "base"
    
    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        model: str,
        size: str = "1024x1024",
        num_images: int = 1,
        negative_prompt: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """
        图像生成接口
        
        Args:
            prompt: 图像描述
            model: 模型名称
            size: 图像尺寸
            num_images: 生成数量
            negative_prompt: 负面提示词
            **kwargs: 其他提供商特定参数
            
        Returns:
            AIResponse 对象，content 为图像 URL 列表
        """
        pass
    
    @abstractmethod
    async def image_to_image(
        self,
        prompt: str,
        image_url: str,
        model: str,
        strength: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """
        图生图接口
        
        Args:
            prompt: 图像描述
            image_url: 参考图像 URL
            model: 模型名称
            strength: 参考强度 (0-1)
            **kwargs: 其他参数
            
        Returns:
            AIResponse 对象
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        pass
    
    def is_available(self) -> bool:
        """检查提供商是否可用"""
        return True


# ==========================================
# Error Types
# ==========================================

class AIErrorType:
    """标准化错误类型"""
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    AUTH_ERROR = "auth_error"
    INVALID_REQUEST = "invalid_request"
    MODEL_NOT_FOUND = "model_not_found"
    CONTENT_FILTER = "content_filter"
    QUOTA_EXCEEDED = "quota_exceeded"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


def classify_error(exception: Exception, provider: str = "") -> str:
    """
    根据异常类型分类错误
    
    Args:
        exception: 捕获的异常
        provider: 提供商名称
        
    Returns:
        错误类型字符串
    """
    error_str = str(exception).lower()
    exception_type = type(exception).__name__.lower()
    
    # Rate limiting
    if any(x in error_str for x in ["rate limit", "rate_limit", "429", "too many requests"]):
        return AIErrorType.RATE_LIMIT
    
    # Timeout
    if any(x in error_str for x in ["timeout", "timed out"]) or "timeout" in exception_type:
        return AIErrorType.TIMEOUT
    
    # Authentication
    if any(x in error_str for x in ["auth", "api key", "unauthorized", "401", "403"]):
        return AIErrorType.AUTH_ERROR
    
    # Content filter
    if any(x in error_str for x in ["content filter", "safety", "blocked", "nsfw"]):
        return AIErrorType.CONTENT_FILTER
    
    # Quota
    if any(x in error_str for x in ["quota", "insufficient", "credit"]):
        return AIErrorType.QUOTA_EXCEEDED
    
    # Model not found
    if any(x in error_str for x in ["model not found", "model_not_found", "invalid model"]):
        return AIErrorType.MODEL_NOT_FOUND
    
    # Invalid request
    if any(x in error_str for x in ["invalid", "bad request", "400"]):
        return AIErrorType.INVALID_REQUEST
    
    # Network
    if any(x in error_str for x in ["connection", "network", "dns"]) or "connection" in exception_type:
        return AIErrorType.NETWORK_ERROR
    
    # API error (500s)
    if any(x in error_str for x in ["500", "502", "503", "504", "internal"]):
        return AIErrorType.API_ERROR
    
    return AIErrorType.UNKNOWN
