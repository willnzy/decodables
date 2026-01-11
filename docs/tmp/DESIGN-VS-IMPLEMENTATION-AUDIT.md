# 设计文档与代码实现一致性审计报告

**日期**: 2026-01-06  
**审计范围**: `docs/shared/` 下的设计文档 vs 当前后台代码 (`api/`, `domains/`, `infrastructure/`, `migrations/`)

---

## 1. 审计摘要

| 系统/模块 | 设计文档 | 状态 | 说明 |
| :--- | :--- | :--- | :--- |
| **User ID System** | `USER-ID-SYSTEM.md` | ✅ 一致 | 26位 User Code 生成逻辑完全符合设计。 |
| **Tier Naming** | `TIER-NAMING-SYSTEM.md` | ✅ 一致 | `t1/t2/t3` 系统代码与枚举定义一致。 |
| **Pricing System** | `PRICING-SYSTEM-DESIGN.md` | ⚠️ **存在差异** | 数据库表已创建，但核心计费逻辑目前依赖 `ConfigService` 而非设计中的 `PricingService`。 |
| **Asset Category** | `[重构后]Asset-Category...` | ✅ 数据库一致 | 关键表 `asset_categories` (含 LTREE) 已在迁移脚本中。 |
| **Feature Flags** | `[重构后]Feature-Flag...` | ✅ 一致 | 统一架构的服务层代码与数据库表均已就位。 |
| **Theme System** | `[重构后]Theme-Daily...` | ✅ 数据库一致 | `themes` 相关表结构已在迁移脚本中。 |
| **Onboarding** | `[重构后]Onboarding...` | ✅ 数据库一致 | `onboarding_tours` 等表结构已在迁移脚本中。 |

---

## 2. 详细发现

### 2.1 User ID System (用户标识系统)
*   **设计要求**: 双重 ID 系统，`user_id` (Clerk ID) 用于系统内部，`user_code` (26位，包含日期+时间+毫秒+序号+随机数) 用于管理和对外。
*   **代码实现**: `infrastructure/repositories/user_repository.py` 中的 `generate_user_code` 方法实现了精确的 26 位生成逻辑，格式完全符合文档描述。`create_profile` 方法正确调用了生成器。
*   **结论**: **完全一致**。

### 2.2 Tier Naming System (层级命名系统)
*   **设计要求**: 数据库存储系统代码 `t1`, `t2`, `t3`；显示名称可配置。
*   **代码实现**: `domains/identity/value_objects.py` 定义了 `UserTier` 枚举 (`T1='t1'`, `T2='t2'`, `T3='t3'`)。`BillingService` 中的配额字典也使用了这些键。
*   **结论**: **完全一致**。

### 2.3 Pricing System (定价系统)
*   **设计要求**:
    *   引入 `pricing_plans` 表存储所有定价方案。
    *   使用 `PricingService` 统一管理价格获取、计算和历史记录。
    *   支持 `pricing_history` 和 `user_price_overrides`。
*   **代码实现**:
    *   **数据库**: `migrations/v2/refactored_schema_v2.sql` 中包含了 `CREATE TABLE pricing_plans`，说明数据库层已准备好。
    *   **业务逻辑**: `domains/billing/service.py` 中的 `BillingService` 目前通过 `self._config_service.get_config(config_key)` (即查询 `system_configs` 表) 来获取操作成本 (如 `credits.cost.image_generation`)。
    *   **差异点**: 代码尚未完全迁移到使用 `PricingService` 和 `pricing_plans` 表来驱动业务逻辑。目前的实现是一个过渡状态，使用了 `ConfigService` 作为主要价格源，而非设计文档中描述的专用定价服务。
*   **结论**: **逻辑实现滞后于设计**。虽然基础设施 (DB表) 已存在，但应用层逻辑尚未切换。

### 2.4 Feature Flag & Experiments (特性开关)
*   **设计要求**: 统一 `feature_flags` 表，支持 boolean/multivariate/experiment 类型。
*   **代码实现**:
    *   `core/feature_flag/service.py` 实现了 Facade 模式，结构与设计一致。
    *   数据库迁移文件中包含 `feature_flags` 表定义。
*   **结论**: **一致**。

### 2.5 Asset Category (素材分类)
*   **设计要求**: 使用 `LTREE` 存储分类路径，支持多级分类。
*   **代码实现**: 数据库迁移文件中确认包含 `asset_categories` 表及 `LTREE` 扩展的使用。
*   **结论**: **数据库层一致**。

---

## 3. 建议行动

1.  **完成 Pricing System 迁移**:
    *   实现 `PricingService` 类 (参考 `PRICING-SYSTEM-DESIGN.md` Section 2.3)。
    *   重构 `BillingService`，将 `get_operation_cost` 的实现从 `ConfigService` 切换到 `PricingService`。
    *   确保 `pricing_plans` 表中已填充了初始数据。

2.  **验证业务模块对接**:
    *   确保 `Asset Category` 和 `Theme` 等新系统在应用层代码中也有对应的 Service 实现 (目前主要验证了 Database 层)。
