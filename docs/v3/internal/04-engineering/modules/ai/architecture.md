# AI 服务模块架构

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `shared/ai/`, `domains/generation/`

---

## 一、模块概述

### 1.1 职责范围

AI 服务模块负责：
- **图像生成**: AI 生图 (FAL.ai Flux)
- **文本生成**: AI 文案 (OpenAI/Qwen)
- **OCR 识别**: 图像文字识别
- **提示词处理**: 增强、翻译、安全检查

### 1.2 模块划分

| 层级 | 模块 | 职责 |
|------|------|------|
| **Shared** | `shared/ai/` | AI 基础设施、适配器、统一服务 |
| **Domain** | `domains/generation/` | 生成业务逻辑 |
| **API** | `api/user/generations.py` | API 端点 |

---

## 二、代码结构

### 2.1 shared/ai/ 结构

```
shared/ai/
├── __init__.py
├── adapters/                 # AI 提供商适配器
│   ├── fal_adapter.py        # FAL.ai (图像)
│   ├── openai_adapter.py     # OpenAI (文本)
│   └── qwen_adapter.py       # Qwen (文本)
├── unified_image_service.py  # 统一图像服务
├── unified_text_service.py   # 统一文本服务
├── image_generator.py        # 图像生成器
├── story_generator.py        # 故事生成器
├── theme_generator.py        # 主题生成器
├── model_config.py           # 模型配置
├── model_config_service.py   # 配置服务
├── prompt_enhancer.py        # 提示词增强
├── prompt_guard.py           # 提示词安全
├── prompt_templates.py       # 提示词模板
├── canary.py                 # 灰度发布
├── usage_tracker.py          # 用量追踪
├── retry.py                  # 重试机制
├── ai_cache.py               # 缓存
├── base.py                   # 基础类型
├── interfaces.py             # 接口定义
└── types.py                  # 类型定义
```

### 2.2 domains/generation/ 结构

```
domains/generation/
├── __init__.py
├── generation_service.py     # 生成服务
├── history_service.py        # 历史记录
├── inspiration_service.py    # 灵感服务
├── pdf_service.py            # PDF 生成
├── story_service.py          # 故事服务
└── repository.py             # Repository 接口
```

---

## 三、统一服务架构

### 3.1 UnifiedImageService

```python
class UnifiedImageService:
    """
    统一图像 AI 服务
    
    功能:
    - 模型配置管理 (按用户等级)
    - 灰度发布支持
    - 使用量追踪
    - 自动降级 (Fallback)
    """
    
    async def generate(
        self,
        prompt: str,
        user_id: Optional[str] = None,
        tier: str = "t1",
        size: str = "landscape_4_3",
        num_images: int = 1,
        **kwargs
    ) -> AIResponse:
        """
        统一图像生成接口
        
        1. 获取模型配置 (基于 tier)
        2. 检查灰度分流
        3. 调用适配器生成
        4. 记录用量
        5. 失败时自动降级
        """
```

### 3.2 UnifiedTextService

```python
class UnifiedTextService:
    """
    统一文本 AI 服务
    
    功能:
    - OpenAI / Qwen 双提供商
    - 结果缓存
    - 灰度发布
    - 自动降级
    """
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        user_id: Optional[str] = None,
        tier: str = "t1",
        **kwargs
    ) -> AIResponse:
        """统一文本生成接口"""
```

---

## 四、AI 提供商

### 4.1 FAL.ai (图像)

```python
class FalAdapter:
    """FAL.ai 图像生成适配器"""
    
    # 支持的模型
    MODELS = {
        "flux-schnell": "fal-ai/flux/schnell",
        "flux-dev": "fal-ai/flux/dev",
        "flux-pro": "fal-ai/flux-pro",
    }
    
    # 支持的尺寸
    SIZES = {
        "landscape_4_3": {"width": 1024, "height": 768},
        "square": {"width": 1024, "height": 1024},
        "portrait_4_3": {"width": 768, "height": 1024},
    }
```

### 4.2 OpenAI (文本)

```python
class OpenAIAdapter:
    """OpenAI 文本生成适配器"""
    
    # 支持的模型
    MODELS = {
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
    }
```

### 4.3 Qwen (文本)

```python
class QwenAdapter:
    """Qwen 文本生成适配器 (阿里云)"""
    
    # 支持的模型
    MODELS = {
        "qwen-turbo": "qwen-turbo",
        "qwen-plus": "qwen-plus",
    }
```

---

## 五、模型配置

### 5.1 按 Tier 配置

```python
# 图像模型配置 (按 Tier)
IMAGE_MODEL_CONFIG = {
    "t1": {
        "provider": "fal",
        "model": "flux-schnell",
        "max_images": 1,
    },
    "t2": {
        "provider": "fal",
        "model": "flux-schnell",
        "max_images": 2,
    },
    "t3": {
        "provider": "fal",
        "model": "flux-dev",
        "max_images": 4,
    },
}
```

### 5.2 动态配置

```python
async def get_image_model_config(tier: str) -> dict:
    """
    获取图像模型配置
    
    优先级:
    1. system_configs 表配置
    2. 环境变量
    3. 默认配置
    """
```

---

## 六、提示词处理

### 6.1 提示词增强

```python
class PromptEnhancer:
    """
    提示词增强器
    
    功能:
    - 自动补充细节
    - 风格优化
    - 语言翻译 (中→英)
    """
    
    async def enhance(self, prompt: str, style: str = None) -> str:
        """增强提示词"""
```

### 6.2 提示词安全

```python
class PromptGuard:
    """
    提示词安全检查
    
    功能:
    - 敏感词过滤
    - NSFW 检测
    - 政治敏感检测
    """
    
    async def check(self, prompt: str) -> GuardResult:
        """检查提示词安全性"""
```

### 6.3 提示词模板

```python
PROMPT_TEMPLATES = {
    "story_page": """
        Create a children's book illustration for:
        Story: {story}
        Page: {page_number}
        Scene: {scene}
        Style: {style}
    """,
    
    "theme_background": """
        Create a seamless pattern for:
        Theme: {theme}
        Style: {style}
        Colors: {colors}
    """,
}
```

---

## 七、灰度发布

### 7.1 Canary 机制

```python
async def should_use_canary(
    user_id: str,
    feature: str,
    tier: str
) -> Tuple[bool, Optional[dict]]:
    """
    判断是否使用灰度版本
    
    基于:
    - user_id 哈希分桶
    - feature_flags 配置
    - 灰度比例
    """
```

### 7.2 灰度配置示例

```json
{
  "feature": "image_generation",
  "canary_percent": 10,
  "canary_config": {
    "provider": "fal",
    "model": "flux-pro"
  }
}
```

---

## 八、错误处理

### 8.1 自动降级

```python
async def generate_with_fallback(self, prompt: str, **kwargs):
    """
    带自动降级的生成
    
    1. 尝试主模型
    2. 失败后尝试备用模型
    3. 全部失败返回错误
    """
    try:
        return await self.primary_adapter.generate(prompt, **kwargs)
    except AIError:
        return await self.fallback_adapter.generate(prompt, **kwargs)
```

### 8.2 重试机制

```python
@retry(
    max_attempts=3,
    backoff=exponential_backoff(base=1, max=30),
    retry_on=(AITimeoutError, AIRateLimitError)
)
async def call_ai_api(self, **kwargs):
    """带重试的 AI 调用"""
```

### 8.3 错误类型

```python
class AIErrorType(Enum):
    RATE_LIMIT = "rate_limit"      # 429
    TIMEOUT = "timeout"            # 超时
    CONTENT_FILTER = "content"     # 内容被过滤
    INVALID_REQUEST = "invalid"    # 请求无效
    SERVER_ERROR = "server"        # 服务器错误
```

---

## 九、积分消耗

### 9.1 消耗成本

| 功能 | 积分消耗 |
|------|----------|
| AI 生图 | 5 |
| OCR 识别 | 10 |
| AI 文字 | 1 |

### 9.2 消耗流程

```python
async def generate_image(user_id: str, prompt: str):
    """
    AI 生图流程:
    1. 检查积分余额 >= 5
    2. 扣除积分 (原子操作)
    3. 调用 AI 服务
    4. 失败时退还积分 (可选)
    """
```

---

## 十、API 端点

### 10.1 图像生成

| 端点 | 方法 | 说明 |
|------|------|------|
| `/generations/image` | POST | AI 生图 |
| `/generations/image/{id}` | GET | 获取生成结果 |

### 10.2 历史记录

| 端点 | 方法 | 说明 |
|------|------|------|
| `/generations/history` | GET | 生成历史 |
| `/generations/history/{id}` | DELETE | 删除记录 |

### 10.3 灵感

| 端点 | 方法 | 说明 |
|------|------|------|
| `/generations/inspiration` | GET | 获取灵感提示 |

---

## 十一、数据库表

### 11.1 ai_call_logs 表

```sql
CREATE TABLE ai_call_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES profiles(id),
    
    -- 调用信息
    operation TEXT NOT NULL,  -- image_generation, text_generation, ocr
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    
    -- 请求/响应
    prompt TEXT,
    response_summary TEXT,
    
    -- 计量
    input_tokens INTEGER,
    output_tokens INTEGER,
    credits_consumed INTEGER,
    
    -- 状态
    status TEXT NOT NULL,  -- success, failed, timeout
    error_message TEXT,
    latency_ms INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 11.2 generation_history 表

```sql
CREATE TABLE generation_history (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES profiles(id),
    
    type TEXT NOT NULL,  -- image, text, ocr
    prompt TEXT,
    result_url TEXT,
    result_data JSONB,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 十二、监控指标

### 12.1 关键指标

| 指标 | 说明 |
|------|------|
| `ai_request_total` | 请求总数 |
| `ai_request_success` | 成功请求数 |
| `ai_request_latency` | 请求延迟 |
| `ai_credits_consumed` | 积分消耗 |
| `ai_fallback_triggered` | 降级触发次数 |

### 12.2 告警规则

| 条件 | 告警 |
|------|------|
| 错误率 > 10% | P1 |
| 延迟 p99 > 30s | P2 |
| 降级率 > 20% | P2 |

---

## 十三、相关文档

- [积分系统](../../05-business/credits-system/overview.md)
- [API 参考 - 生成](../../03-api/generations.md)
- [功能规格 - AI 生成](../../02-product/features/ai-generation.md)

---

**END OF DOCUMENT**
