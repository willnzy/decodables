"""
AI 模块常量定义

@module domains.platform.ai.constants
@version 1.0.0

v1.0.0: 初始创建
- 从 api/admin/ai_models.py 迁移常量 (DDD 架构迁移)
- 添加参数验证范围常量
"""

# ==========================================
# AI 提供商
# ==========================================

# 有效的 AI 提供商列表
VALID_PROVIDERS = {"openai", "fal", "dashscope", "anthropic", "replicate"}


# ==========================================
# 参数范围验证
# ==========================================

# 温度范围 (Temperature)
TEMPERATURE_MIN = 0.0
TEMPERATURE_MAX = 2.0

# Token 限制
MAX_TOKENS_MIN = 1
MAX_TOKENS_MAX = 32000

# Canary 灰度百分比范围
CANARY_PERCENTAGE_MIN = 0
CANARY_PERCENTAGE_MAX = 100

# 使用统计天数范围
USAGE_DAYS_MIN = 1
USAGE_DAYS_MAX = 365


# ==========================================
# 配置键名 (Config Keys)
# ==========================================

# 用户模型配置键
CONFIG_KEY_TEXT_MODEL = "ai_model.user.text_reasoning"
CONFIG_KEY_IMAGE_MODEL = "ai_model.user.image_generation"
CONFIG_KEY_ADMIN_MODEL = "ai_model.admin.analysis"

# AI 提供商配置键
CONFIG_KEY_ENABLED_PROVIDERS = "ai_providers.enabled"
CONFIG_KEY_PROVIDER_MODELS = "ai_providers.models"
CONFIG_KEY_PROVIDER_TIMEOUTS = "ai_providers.timeouts"
CONFIG_KEY_PROVIDER_COSTS = "ai_providers.costs"
CONFIG_KEY_RETRY_CONFIG = "ai_providers.retry"

# Canary 配置键
CONFIG_KEY_CANARY = "ai_canary.config"


# ==========================================
# 缓存键前缀
# ==========================================

CACHE_PREFIX_TEXT = "md:ai:text:"
CACHE_PREFIX_IMAGE = "md:ai:image:"
CACHE_PREFIX_ALL = "md:ai:*"


# ==========================================
# 用户等级 (Tier)
# ==========================================

TIER_FREE = "t1"
TIER_STARTER = "t2"
TIER_PRO = "t3"
TIER_ALL = "all"

VALID_TIERS = {TIER_FREE, TIER_STARTER, TIER_PRO, TIER_ALL}


# ==========================================
# 缓存类型
# ==========================================

CACHE_TYPE_TEXT = "text"
CACHE_TYPE_IMAGE = "image"
CACHE_TYPE_ALL = "all"

VALID_CACHE_TYPES = {CACHE_TYPE_TEXT, CACHE_TYPE_IMAGE, CACHE_TYPE_ALL}
