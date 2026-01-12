# Tier Permissions 后端配置化实施计划

> **版本**: v2.0.0
> **创建日期**: 2026-01-12
> **状态**: 已完成
> **参考文档**: [docs/shared/TIER-PERMISSIONS.md](../shared/TIER-PERMISSIONS.md)

---

## 实施进度

### 全部完成 ✅

| 文件 | 改动 | 状态 |
|------|------|------|
| `domains/identity/constants.py` | 添加 TIER_T4，更新 VALID_TIERS, TIER_LABELS 等 | ✅ |
| `domains/identity/tier_service.py` | 扩展为完整权限服务，添加 FeatureKey 枚举、EMERGENCY_TIER_CONFIGS、can_use_feature() 等方法 | ✅ |
| `domains/creation/service.py` | 移除硬编码 PROJECT_LIMITS，改用 tier_service.get_max_projects() | ✅ |
| `domains/billing/service.py` | 移除硬编码常量，改用 tier_service 获取 operation_cost, signup_bonus, monthly_credits | ✅ |
| `domains/export/export_service.py` | 3 处 `tier != "t3"` 改为 `_check_zip_permission()` 使用 tier_service | ✅ |
| `domains/tools/tools_service.py` | PDF/OCR 权限检查改用 `_check_smart_scan_permission()` 使用 tier_service | ✅ |
| `domains/shared/access_control.py` | `can_use_ocr()` 标记为 deprecated，添加 t4 支持 | ✅ |
| `domains/generation/generation_service.py` | AI 队列优先级改用 `_get_queue_priority()` 使用 tier_service | ✅ |
| `dependencies.py` | 修复 `"pro"` → `"t3"`，添加 t4 支持 | ✅ |
| `api/user/user_assets.py` | `tier != "t3"` 改为 `tier not in ("t3", "t4")` | ✅ |

---

## 1. 实现摘要

### 1.1 核心改动

1. **扩展 TierService** (`domains/identity/tier_service.py`)
   - 添加 `FeatureKey` 枚举定义所有功能权限
   - 添加 `EMERGENCY_TIER_CONFIGS` 作为数据库不可用时的回退
   - 实现 `can_use_feature(tier, feature, is_trial_active)` 方法
   - 实现 `get_monthly_credits()`, `get_max_projects()`, `get_ai_queue_priority()` 等方法

2. **移除所有硬编码**
   - 所有服务类现在通过依赖注入接收 `tier_service`
   - 权限检查使用 `tier_service.can_use_feature()` 而非硬编码 tier 比较
   - 数值限制使用 `tier_service.get_xxx()` 方法获取

3. **添加 t4 (Enterprise) 支持**
   - 所有 tier 检查现在支持 t1, t2, t3, t4
   - 权限继承：t4 >= t3 >= t2 >= t1

### 1.2 权限值类型

| 值 | 含义 | 示例 |
|----|------|------|
| `True` | 始终可用 | t3 的 zip_export |
| `False` | 始终不可用 | t1 的 purchase_marketplace |
| `"trial"` | 仅在试用期内可用 | t1 的 basic_editor |

---

## 2. 新增方法

### TierService 新方法

```python
# 权限检查
async def can_use_feature(user_tier: str, feature: FeatureKey, is_trial_active: bool) -> bool

# 配置获取
async def get_tier_config(tier: str) -> Dict[str, Any]
async def get_monthly_credits(user_tier: str) -> int
async def get_max_projects(user_tier: str) -> int
async def get_ai_queue_priority(user_tier: str) -> str  # "low"/"normal"/"high"
async def get_ai_queue_priority_value(user_tier: str) -> int  # 0/1/2
async def get_topup_discount(user_tier: str) -> float
async def get_signup_bonus() -> int
async def get_operation_cost(operation: str) -> int

# 辅助方法
def is_trial_active(user: Dict, trial_days: int = None) -> bool
```

### FeatureKey 枚举

```python
class FeatureKey(str, Enum):
    # 导出
    PDF_EXPORT = "pdf_export"
    ZIP_EXPORT = "zip_export"

    # 编辑器
    BASIC_EDITOR = "basic_editor"
    VECTOR_TOOLS = "vector_tools"
    FREEHAND_TOOLS = "freehand_tools"
    CLIPBOARD_PASTE = "clipboard_paste"

    # 素材
    PLATFORM_ASSETS = "platform_assets"
    UPLOAD_IMAGE = "upload_image"
    UPLOAD_ADVANCED = "upload_advanced"
    SAVE_ASSETS = "save_assets"
    HISTORY_ASSETS = "history_assets"

    # 市场
    BROWSE_MARKETPLACE = "browse_marketplace"
    PURCHASE_MARKETPLACE = "purchase_marketplace"
    PUBLISH_MARKETPLACE = "publish_marketplace"

    # AI
    AI_FEATURES = "ai_features"

    # t4 专属
    PRIORITY_SUPPORT = "priority_support"
    API_ACCESS = "api_access"
```

---

## 3. 使用方式

### 3.1 权限检查示例

```python
# 检查 ZIP 导出权限
if self._tier_service:
    can_export = await self._tier_service.can_use_feature(
        user_tier=tier,
        feature=FeatureKey.ZIP_EXPORT,
        is_trial_active=is_trial_active
    )
else:
    # Fallback
    can_export = tier.lower() in ("t3", "t4")
```

### 3.2 配置获取示例

```python
# 获取项目限制
if self._tier_service:
    limit = await self._tier_service.get_max_projects(user_tier)
else:
    # Fallback
    from domains.identity.tier_service import EMERGENCY_TIER_CONFIGS
    limit = EMERGENCY_TIER_CONFIGS.get(user_tier, {}).get("max_projects", 1)
```

---

## 4. 配置来源

所有配置从 `system_configs` 表读取，配置项格式：

| key | 示例值 | 说明 |
|-----|--------|------|
| `tier.t1.monthly_credits` | `0` | t1 月度积分 |
| `tier.t1.max_projects` | `1` | t1 项目限制 |
| `tier.t1.ai_queue_priority` | `low` | t1 AI 队列优先级 |
| `tier.t1.topup_discount` | `1.0` | t1 充值折扣 |
| `tier.t1.features` | `{"pdf_export": true, ...}` | t1 功能权限 JSON |
| `credits.signup_bonus` | `100` | 注册赠送积分 |
| `credits.cost.image_generation` | `5` | AI 图片生成成本 |

---

## 5. 回退机制

当数据库不可用或配置缺失时，使用 `EMERGENCY_TIER_CONFIGS` 作为回退：

- 配置值与 `docs/shared/TIER-PERMISSIONS.md` 完全一致
- 每个服务有独立的回退逻辑，确保单个服务失败不影响其他功能
- 所有 fallback 使用均有日志记录 (warning 级别)

---

## 6. 下一步

1. ~~完成所有文件修改~~ ✅
2. ~~Git commit~~ (待执行)
3. 在 DI Container 中注入 TierService 到各服务
4. 初始化 system_configs 表数据
5. 集成测试

---

**END OF DOCUMENT**
