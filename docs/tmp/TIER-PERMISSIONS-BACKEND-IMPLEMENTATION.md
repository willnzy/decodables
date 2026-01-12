# Tier Permissions 后端配置化实施计划

> **版本**: v1.1.0
> **创建日期**: 2026-01-12
> **状态**: 进行中 (Phase 1-2 部分完成)
> **参考文档**: [docs/shared/TIER-PERMISSIONS.md](../shared/TIER-PERMISSIONS.md)

---

## 实施进度

### 已完成 ✅

| 文件 | 改动 |
|------|------|
| `domains/identity/constants.py` | 添加 TIER_T4，更新 VALID_TIERS, TIER_LABELS 等 |
| `domains/identity/tier_service.py` | 扩展为完整权限服务，添加 FeatureKey 枚举、EMERGENCY_TIER_CONFIGS、can_use_feature() 等方法 |
| `domains/creation/service.py` | 移除硬编码 PROJECT_LIMITS，改用 tier_service.get_max_projects() |
| `domains/billing/service.py` | 移除硬编码常量，改用 tier_service 获取 operation_cost, signup_bonus, monthly_credits |

### 待完成 ⏳

| 文件 | 改动 |
|------|------|
| `domains/export/export_service.py` | 3 处 `tier != "t3"` 改为 `tier_service.can_use_feature(tier, FeatureKey.ZIP_EXPORT)` |
| `domains/tools/tools_service.py` | PDF/OCR 权限检查改用 tier_service |
| `domains/shared/access_control.py` | `can_use_ocr()` 改用 tier_service |
| `domains/generation/generation_service.py` | AI 队列优先级改用 `tier_service.get_ai_queue_priority_value()` |
| `dependencies.py` | 修复 `"pro"` → `"t3"` |
| `api/user/user_assets.py` | `tier != "t3"` 改用 tier_service |

---

## 1. 目标

将后端所有硬编码的 Tier 权限检查改为从 `system_configs` 表读取配置，实现：
- Admin 页面可配置所有权限
- 前后端权限一致性
- 无需代码部署即可调整权限

---

## 2. 当前问题汇总

### 2.1 硬编码位置清单

| 文件 | 行号 | 问题 | 正确值 (来自文档) |
|------|------|------|------------------|
| `domains/creation/service.py` | 35-39 | `PROJECT_LIMITS = {"t1": 5, "t2": 50, "t3": 500}` | t1:1, t2:10, t3:200 |
| `domains/billing/service.py` | 47-52 | `TIER_ALLOWANCES = {"t1": 0, "t2": 500, "t3": 1000}` | t1:0, t2:100, t3:200 |
| `domains/billing/service.py` | 55 | `SIGNUP_BONUS = 50` | 100 |
| `domains/identity/constants.py` | 28-32 | `TIER_MONTHLY_CREDITS = {"t1": 0, "t2": 200, "t3": 500}` | t1:0, t2:100, t3:200 |
| `domains/tools/tools_service.py` | 121 | `tier != "t3"` 硬编码 PDF 权限 | 应检查 features.upload_advanced |
| `domains/export/export_service.py` | 202,259,437 | `tier.lower() != "t3"` 硬编码导出权限 | 应检查 features.zip_export |
| `api/user/user_assets.py` | 122 | `user["tier"] != "t3"` 硬编码资产范围 | 应检查 features.history_assets |
| `domains/shared/access_control.py` | 171-199 | `can_use_ocr()` 硬编码 tier 检查 | 应检查 features.ai_features |
| `domains/generation/generation_service.py` | 387,434 | 硬编码 AI 队列优先级 | 应读取 tier.{tier}.ai_queue_priority |
| `dependencies.py` | 155 | `tier != "pro"` 硬编码字符串 | 应使用 "t3" |

### 2.2 数据不一致

| 配置项 | TIER-PERMISSIONS.md | 后端当前值 |
|--------|---------------------|------------|
| t1 项目限制 | 1 | 5 |
| t2 项目限制 | 10 | 50 |
| t3 项目限制 | 200 | 500 |
| t2 月度积分 | 100 | 200 或 500 (不同文件) |
| t3 月度积分 | 200 | 500 或 1000 (不同文件) |
| 注册赠送 | 100 | 50 |

---

## 3. 实施方案

### 3.1 新建 TierPermissionService

**文件**: `domains/identity/tier_permission_service.py`

```python
"""
Tier Permission Service - 统一的权限检查服务

从 system_configs 表读取配置，提供统一的权限检查接口。
"""

from typing import Optional, Dict, Any, Union
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FeatureKey(str, Enum):
    """功能权限 Key"""
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


class TierPermissionService:
    """
    Tier 权限服务

    提供统一的权限检查接口，从 system_configs 读取配置。
    支持三种权限值: true (可用), false (不可用), "trial" (试用期可用)
    """

    # 紧急回退配置 (仅在数据库完全不可用时使用)
    EMERGENCY_FALLBACK = {
        "t1": {
            "monthly_credits": 0,
            "max_projects": 1,
            "ai_queue_priority": "low",
            "topup_discount": 1.0,
            "features": {
                "pdf_export": True,
                "zip_export": "trial",
                "basic_editor": "trial",
                "vector_tools": "trial",
                "freehand_tools": "trial",
                "clipboard_paste": "trial",
                "platform_assets": "trial",
                "upload_image": "trial",
                "upload_advanced": "trial",
                "save_assets": "trial",
                "history_assets": "trial",
                "browse_marketplace": "trial",
                "purchase_marketplace": False,
                "publish_marketplace": False,
                "ai_features": "trial",
            }
        },
        "t2": {
            "monthly_credits": 100,
            "max_projects": 10,
            "ai_queue_priority": "normal",
            "topup_discount": 1.0,
            "features": {
                "pdf_export": True,
                "zip_export": False,
                "basic_editor": True,
                "vector_tools": False,
                "freehand_tools": False,
                "clipboard_paste": False,
                "platform_assets": True,
                "upload_image": True,
                "upload_advanced": False,
                "save_assets": False,
                "history_assets": False,
                "browse_marketplace": True,
                "purchase_marketplace": False,
                "publish_marketplace": True,
                "ai_features": True,
            }
        },
        "t3": {
            "monthly_credits": 200,
            "max_projects": 200,
            "ai_queue_priority": "high",
            "topup_discount": 0.9,
            "features": {
                "pdf_export": True,
                "zip_export": True,
                "basic_editor": True,
                "vector_tools": True,
                "freehand_tools": True,
                "clipboard_paste": True,
                "platform_assets": True,
                "upload_image": True,
                "upload_advanced": True,
                "save_assets": True,
                "history_assets": True,
                "browse_marketplace": True,
                "purchase_marketplace": True,
                "publish_marketplace": True,
                "ai_features": True,
            }
        },
    }

    def __init__(self, config_service: 'ConfigService'):
        """
        初始化权限服务

        Args:
            config_service: ConfigService 实例 (用于读取 system_configs)
        """
        self._config_service = config_service
        self._cache: Dict[str, Any] = {}

    async def get_tier_config(self, tier: str) -> Dict[str, Any]:
        """
        获取 Tier 完整配置

        Args:
            tier: Tier 代码 (t1/t2/t3/t4)

        Returns:
            包含所有配置的字典
        """
        cache_key = f"tier_config_{tier}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # 从数据库读取配置
            config = {
                "monthly_credits": await self._get_config_value(f"tier.{tier}.monthly_credits", int),
                "max_projects": await self._get_config_value(f"tier.{tier}.max_projects", int),
                "ai_queue_priority": await self._get_config_value(f"tier.{tier}.ai_queue_priority", str),
                "topup_discount": await self._get_config_value(f"tier.{tier}.topup_discount", float),
                "features": await self._get_config_value(f"tier.{tier}.features", dict),
            }

            # 验证必须字段
            if config["features"] is None:
                raise ValueError(f"Missing features config for tier {tier}")

            self._cache[cache_key] = config
            return config

        except Exception as e:
            logger.error(
                f"[CRITICAL] Failed to load tier config from database, using fallback",
                extra={"tier": tier, "error": str(e)}
            )
            return self.EMERGENCY_FALLBACK.get(tier, self.EMERGENCY_FALLBACK["t1"])

    async def can_use_feature(
        self,
        user_tier: str,
        feature: Union[FeatureKey, str],
        is_trial_active: bool = False
    ) -> bool:
        """
        检查用户是否可以使用某功能

        Args:
            user_tier: 用户 Tier (t1/t2/t3/t4)
            feature: 功能 Key
            is_trial_active: t1 用户是否在试用期内

        Returns:
            True 如果可以使用，False 否则
        """
        feature_key = feature.value if isinstance(feature, FeatureKey) else feature

        config = await self.get_tier_config(user_tier)
        features = config.get("features", {})
        feature_value = features.get(feature_key)

        if feature_value is None:
            logger.warning(f"Unknown feature: {feature_key} for tier {user_tier}")
            return False

        # 处理三种权限值
        if feature_value is True:
            return True
        elif feature_value is False:
            return False
        elif feature_value == "trial":
            # 仅在试用期内可用
            return is_trial_active
        else:
            logger.warning(f"Invalid feature value: {feature_value} for {feature_key}")
            return False

    async def get_project_limit(self, user_tier: str) -> int:
        """获取项目数量限制"""
        config = await self.get_tier_config(user_tier)
        return config.get("max_projects", 1)

    async def get_monthly_credits(self, user_tier: str) -> int:
        """获取月度积分额度"""
        config = await self.get_tier_config(user_tier)
        return config.get("monthly_credits", 0)

    async def get_ai_queue_priority(self, user_tier: str) -> str:
        """获取 AI 队列优先级 (low/normal/high)"""
        config = await self.get_tier_config(user_tier)
        return config.get("ai_queue_priority", "low")

    async def get_topup_discount(self, user_tier: str) -> float:
        """获取充值折扣 (1.0 = 无折扣, 0.9 = 9折)"""
        config = await self.get_tier_config(user_tier)
        return config.get("topup_discount", 1.0)

    async def _get_config_value(self, key: str, value_type: type) -> Any:
        """从 ConfigService 获取配置值"""
        value = await self._config_service.get_config(key, use_cache=True)
        if value is None:
            return None

        # 类型转换
        if value_type == int:
            return int(value)
        elif value_type == float:
            return float(value)
        elif value_type == dict:
            import json
            return json.loads(value) if isinstance(value, str) else value
        else:
            return value

    def clear_cache(self):
        """清除缓存 (配置更新后调用)"""
        self._cache.clear()
```

### 3.2 修改现有文件

#### A. domains/creation/service.py

**改动**:
```python
# 删除硬编码
# PROJECT_LIMITS = {"t1": 5, "t2": 50, "t3": 500}  # 删除

# 在 __init__ 中注入 TierPermissionService
def __init__(self, repository, tier_permission_service: TierPermissionService = None):
    self._repository = repository
    self._tier_permission_service = tier_permission_service

# 修改项目创建检查
async def create_project(self, ...):
    # 旧代码: limit = self.PROJECT_LIMITS.get(user_tier, 5)
    # 新代码:
    limit = await self._tier_permission_service.get_project_limit(user_tier)
```

#### B. domains/billing/service.py

**改动**:
```python
# 删除硬编码
# TIER_ALLOWANCES = {"t1": 0, "t2": 500, "t3": 1000}  # 删除
# SIGNUP_BONUS = 50  # 删除

# 修改月度积分发放
async def process_subscription_renewal(self, user_id: str, tier: str):
    # 旧代码: allowance = self.TIER_ALLOWANCES.get(tier, 0)
    # 新代码:
    allowance = await self._tier_permission_service.get_monthly_credits(tier)

# 修改注册赠送
async def grant_signup_bonus(self, user_id: str, ...):
    # 从配置获取
    bonus = await self._config_service.get_config("credits.signup_bonus", use_cache=True)
    bonus_amount = int(bonus) if bonus else 100  # 默认 100
```

#### C. domains/export/export_service.py

**改动**:
```python
# 删除硬编码检查
# if tier.lower() != "t3":  # 删除

# 新代码:
async def export_zip(self, user: dict, ...):
    can_export = await self._tier_permission_service.can_use_feature(
        user_tier=user.get("tier", "t1"),
        feature=FeatureKey.ZIP_EXPORT,
        is_trial_active=self._is_trial_active(user)
    )
    if not can_export:
        raise InsufficientPermissionException(
            "ZIP export requires Pro plan or active trial"
        )
```

#### D. domains/tools/tools_service.py

**改动**:
```python
# 删除硬编码
# if user.get("tier", "t1").lower() != "t3":  # 删除

# 新代码:
async def process_pdf_preview(self, user: dict, ...):
    can_use = await self._tier_permission_service.can_use_feature(
        user_tier=user.get("tier", "t1"),
        feature=FeatureKey.UPLOAD_ADVANCED,
        is_trial_active=self._is_trial_active(user)
    )
    if not can_use:
        raise HTTPException(403, "Upgrade to Pro to use Smart Scan")
```

#### E. domains/shared/access_control.py

**改动**:
```python
# 重写 can_use_ocr() 函数
async def can_use_ocr(user: dict, tier_permission_service: TierPermissionService) -> bool:
    """
    检查用户是否可以使用 OCR 功能

    从配置读取权限，不再硬编码 tier 检查
    """
    user_tier = user.get("tier", "t1")
    is_trial_active = _is_trial_active(user)

    return await tier_permission_service.can_use_feature(
        user_tier=user_tier,
        feature=FeatureKey.AI_FEATURES,
        is_trial_active=is_trial_active
    )

def _is_trial_active(user: dict) -> bool:
    """检查 t1 用户是否在试用期内"""
    if user.get("tier") != "t1":
        return False

    from datetime import datetime, timedelta
    created_at = user.get("created_at")
    if not created_at:
        return False

    # 试用期天数从配置读取 (默认 30 天)
    trial_days = 30  # 可改为从配置读取
    trial_end = created_at + timedelta(days=trial_days)
    return datetime.utcnow() < trial_end
```

#### F. domains/generation/generation_service.py

**改动**:
```python
# 修改优先级获取
async def _get_generation_priority(self, user_tier: str) -> int:
    """
    获取 AI 生成优先级

    Returns:
        0=low, 1=normal, 2=high
    """
    priority_str = await self._tier_permission_service.get_ai_queue_priority(user_tier)
    priority_map = {"low": 0, "normal": 1, "high": 2}
    return priority_map.get(priority_str, 0)

async def _get_queue_priority(self, user_tier: str) -> str:
    """获取任务队列优先级字符串"""
    return await self._tier_permission_service.get_ai_queue_priority(user_tier)
```

#### G. dependencies.py

**改动**:
```python
# 修复硬编码 "pro" 字符串
# 旧代码: if user.get("tier") != "pro":
# 新代码: if user.get("tier") != "t3":

# 或者更好的方式: 使用 TierPermissionService 检查
async def require_pro(
    user: dict = Depends(get_current_user),
    tier_permission_service: TierPermissionService = Depends(get_tier_permission_service)
):
    """Require Pro tier for the endpoint"""
    # 检查是否是 t3 或者在试用期内
    if user.get("tier") == "t3":
        return user

    if user.get("tier") == "t1":
        is_trial = _is_trial_active(user)
        if is_trial:
            return user

    raise MembershipRequiredException("Pro features require Pro plan")
```

---

## 4. 数据库配置初始化

运行以下 SQL 将配置写入 `system_configs` 表：

```sql
-- 参见 docs/shared/TIER-PERMISSIONS.md 中的完整 SQL
-- 包含所有 tier.{tier}.* 配置项
```

---

## 5. 实施步骤

### Phase 1: 基础设施 (预计 4 小时)

1. [ ] 创建 `TierPermissionService` 类
2. [ ] 添加 `FeatureKey` 枚举
3. [ ] 创建依赖注入 `get_tier_permission_service()`
4. [ ] 添加辅助函数 `_is_trial_active()`
5. [ ] 单元测试

### Phase 2: 迁移硬编码 (预计 6 小时)

1. [ ] 迁移 `creation/service.py` - 项目限制
2. [ ] 迁移 `billing/service.py` - 月度积分、注册赠送
3. [ ] 迁移 `export/export_service.py` - 导出权限 (3 处)
4. [ ] 迁移 `tools/tools_service.py` - PDF/OCR 权限
5. [ ] 迁移 `access_control.py` - can_use_ocr()
6. [ ] 迁移 `generation_service.py` - AI 队列优先级
7. [ ] 修复 `dependencies.py` - "pro" → "t3"

### Phase 3: 数据初始化 (预计 2 小时)

1. [ ] 编写 SQL 脚本
2. [ ] 验证现有 system_configs 表结构
3. [ ] 插入初始配置数据
4. [ ] 验证数据正确性

### Phase 4: 集成测试 (预计 4 小时)

1. [ ] 测试 t1 用户 (试用期内/过期)
2. [ ] 测试 t2 用户
3. [ ] 测试 t3 用户
4. [ ] 测试权限边界情况
5. [ ] 测试配置热更新

---

## 6. 验收标准

### 功能验收

- [ ] t1 试用期内可使用所有 "trial" 功能
- [ ] t1 试用期过期后仅能使用 pdf_export
- [ ] t2 用户权限符合 TIER-PERMISSIONS.md
- [ ] t3 用户权限符合 TIER-PERMISSIONS.md
- [ ] Admin 修改配置后立即生效

### 数据验收

- [ ] system_configs 表包含所有 tier.* 配置
- [ ] 配置值与 TIER-PERMISSIONS.md 一致
- [ ] 无硬编码权限检查残留

### 性能验收

- [ ] 权限检查响应 < 50ms (有缓存)
- [ ] 缓存失效后首次查询 < 200ms

---

## 7. 风险与回滚

### 风险

1. **数据库不可用**: 使用 EMERGENCY_FALLBACK 兜底
2. **配置错误**: Admin 审计日志记录所有变更
3. **缓存一致性**: 配置变更后调用 clear_cache()

### 回滚方案

如果新实现出现问题：
1. 恢复 git 提交前的代码
2. 保留 system_configs 数据 (不删除)
3. 硬编码值可作为临时回退

---

## 8. 文件清单

| 文件 | 操作 | 改动量 |
|------|------|--------|
| `domains/identity/tier_permission_service.py` | 新建 | ~200 行 |
| `domains/creation/service.py` | 修改 | ~20 行 |
| `domains/billing/service.py` | 修改 | ~30 行 |
| `domains/export/export_service.py` | 修改 | ~30 行 |
| `domains/tools/tools_service.py` | 修改 | ~20 行 |
| `domains/shared/access_control.py` | 修改 | ~40 行 |
| `domains/generation/generation_service.py` | 修改 | ~20 行 |
| `dependencies.py` | 修改 | ~15 行 |
| `tests/test_tier_permission_service.py` | 新建 | ~150 行 |

---

**END OF DOCUMENT**
