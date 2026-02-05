# 配置与权限系统设计

> **同步范围**: [backend]
> **状态**: 🟢 已验证 (来源: 代码分析 + v2 文档)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `api/admin/config.py`, `api/admin/tiers.py`, `api/admin/feature_flags.py`

---

## 一、概述

### 1.1 核心能力

| 模块 | 说明 |
|------|------|
| System Config | 系统配置的 CRUD |
| Rate Limits | 限流配置管理 |
| Tier Config | Tier 权益配置 |
| Feature Flags | 功能开关管理 |

### 1.2 配置优先级

```
Kill Switch > User Override > Tier 权限 > Feature Flag > Default
```

---

## 二、System Config

### 2.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/admin/config` | GET | 获取所有配置 |
| `/api/v2/admin/config/{key}` | GET | 获取单个配置 |
| `/api/v2/admin/config` | PUT | 更新配置 |
| `/api/v2/admin/config/batch` | PUT | 批量更新 |
| `/api/v2/admin/config/cache/clear` | POST | 清除配置缓存 |

### 2.2 数据结构

```python
class SystemConfig:
    key: str              # 配置键
    value: Any            # 配置值
    value_type: ValueType # 值类型
    config_group: Group   # 配置分组
    description: str      # 描述
    is_active: bool       # 是否启用

# 值类型
class ValueType(str, Enum):
    TEXT = "text"
    JSON = "json"
    NUMBER = "number"
    BOOLEAN = "boolean"

# 配置分组
class ConfigGroup(str, Enum):
    GENERAL = "general"
    PRICING = "pricing"
    LIMITS = "limits"
    UI = "ui"
    SYSTEM = "system"
    AI = "ai"
    FEATURES = "features"
```

### 2.3 常用配置项

| Key | 分组 | 说明 |
|-----|------|------|
| `pricing.t2.monthly` | pricing | T2 月费 |
| `pricing.t3.monthly` | pricing | T3 月费 |
| `credits.monthly.t2` | pricing | T2 月度积分 |
| `credits.monthly.t3` | pricing | T3 月度积分 |
| `limits.project.max` | limits | 最大项目数 |
| `limits.asset.max_mb` | limits | 素材大小限制 |
| `ai.model.default` | ai | 默认 AI 模型 |
| `ai.cost.image` | ai | AI 生图成本 |

---

## 三、Rate Limits

### 3.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/admin/config/rate-limits` | GET | 获取限流配置 |
| `/api/v2/admin/config/rate-limits/preset` | POST | 应用预设 |
| `/api/v2/admin/config/rate-limits/presets` | GET | 获取所有预设 |

### 3.2 预设类型

```python
class RateLimitPreset(str, Enum):
    STRICT = "strict"      # 严格: 低限制
    NORMAL = "normal"      # 正常: 标准限制
    RELAXED = "relaxed"    # 宽松: 高限制
    DISABLED = "disabled"  # 禁用: 无限制

# 预设配置
PRESETS = {
    "strict": {
        "api_general": {"limit": 30, "window": 60},
        "api_write": {"limit": 5, "window": 60},
        "ai_generation": {"limit": 5, "window": 300}
    },
    "normal": {
        "api_general": {"limit": 60, "window": 60},
        "api_write": {"limit": 10, "window": 60},
        "ai_generation": {"limit": 10, "window": 300}
    },
    "relaxed": {
        "api_general": {"limit": 120, "window": 60},
        "api_write": {"limit": 20, "window": 60},
        "ai_generation": {"limit": 20, "window": 300}
    }
}
```

---

## 四、Tier Config

### 4.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/admin/tiers` | GET | 获取所有 Tier |
| `/api/v2/admin/tiers/{tier_code}` | GET | 获取 Tier 详情 |
| `/api/v2/admin/tiers/{tier_code}` | PUT | 更新 Tier 配置 |

### 4.2 数据结构

```python
class TierConfig:
    code: str              # t1/t2/t3/t4
    display_name: str      # 显示名称
    description: str       # 描述
    
    # 价格
    price_original: float  # 原价
    price_current: float   # 现价
    
    # 积分
    monthly_credits: int   # 月度积分
    
    # 功能权益
    features: TierFeatures

class TierFeatures:
    max_projects: int
    max_assets: int
    max_asset_size_mb: int
    ai_enabled: bool
    export_enabled: bool
    watermark_free: bool
```

### 4.3 Tier 对照表

| 字段 | T1 (Free) | T2 (Starter) | T3 (Pro) |
|------|-----------|--------------|----------|
| 价格 | $0 | $6.9/月 | $9.9/月 |
| 月度积分 | 0 | 100 | 200 |
| 最大项目 | 3 | 20 | 无限 |
| 最大素材 | 50 | 500 | 无限 |
| AI 生成 | ❌ | ✅ | ✅ |
| 无水印 | ❌ | ✅ | ✅ |

---

## 五、Feature Flags

### 5.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/admin/feature-flags` | GET | Flag 列表 |
| `/api/v2/admin/feature-flags` | POST | 创建 Flag |
| `/api/v2/admin/feature-flags/{key}` | GET | Flag 详情 |
| `/api/v2/admin/feature-flags/{key}` | PATCH | 更新 Flag |
| `/api/v2/admin/feature-flags/{key}/toggle` | POST | 切换状态 |
| `/api/v2/admin/feature-flags/{key}` | DELETE | 删除 Flag |
| `/api/v2/admin/feature-flags/test-evaluation` | POST | 测试评估 |
| `/api/v2/admin/feature-flags/{key}/audit` | GET | 审计日志 |

### 5.2 数据结构

```python
class FeatureFlag:
    key: str                    # Flag 键
    flag_type: FlagType        # 类型
    enabled: bool              # 是否启用
    rollout_percentage: int    # 灰度百分比 (0-100)
    allowed_tiers: List[str]   # 允许的 Tier
    description: str           # 描述
    status: FlagStatus         # 状态
    environment: Environment   # 环境

class FlagType(str, Enum):
    BOOLEAN = "boolean"
    MULTIVARIATE = "multivariate"
    EXPERIMENT = "experiment"

class FlagStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"

class Environment(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
```

### 5.3 常用 Feature Flags

| Key | 类型 | 说明 |
|-----|------|------|
| `ai_page_generation` | boolean | AI 生成页面 |
| `new_editor_v2` | percentage | 新编辑器灰度 |
| `pricing_experiment` | experiment | 定价 A/B 测试 |
| `marketplace_beta` | boolean | 商城 Beta |

---

## 六、缓存管理

### 6.1 缓存层级

```
┌─────────────────────────────────────┐
│         Application Cache           │
│  (Python dict, 5 min TTL)          │
├─────────────────────────────────────┤
│            Redis Cache              │
│  (30 min TTL)                       │
├─────────────────────────────────────┤
│          Database                   │
│  (system_configs table)             │
└─────────────────────────────────────┘
```

### 6.2 缓存失效

```python
async def update_config(key: str, value: Any):
    # 更新数据库
    await db.update_config(key, value)
    
    # 失效 Redis 缓存
    await redis.delete(f"config:{key}")
    
    # 失效应用缓存
    app_cache.invalidate(key)
    
    # 广播更新事件
    await publish_event("config_updated", {"key": key})
```

---

## 七、安全与护栏

### 7.1 权限控制

- 所有端点需要 Admin 角色
- 敏感配置 (pricing, ai) 需要额外确认

### 7.2 校验规则

```python
# Key 校验
def validate_config_key(key: str):
    if len(key) > 100:
        raise ValueError("Key too long")
    if not re.match(r'^[a-z0-9_.]+$', key):
        raise ValueError("Invalid key format")

# Tier code 校验
def validate_tier_code(code: str):
    if code not in ["t1", "t2", "t3", "t4"]:
        raise ValueError("Invalid tier code")
```

### 7.3 审计日志

```python
AuditLog(
    action="config_updated",
    target_type="system_config",
    target_id=key,
    operator_id=admin_id,
    details={
        "old_value": old_value,
        "new_value": new_value
    }
)
```

---

## 八、相关文档

- [Admin API 端点](../../api/admin-endpoints.md)
- [Feature Flag 引擎](../../../02-standards/feature-flag-engine.md)
- [权益系统设计](../../../05-business/entitlement/system-design.md)

---

**END OF DOCUMENT**
