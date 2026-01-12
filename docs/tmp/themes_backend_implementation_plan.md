# Themes 后端 API 实现计划 (v2.1)

> **版本**: v2.1
> **日期**: 2026-01-12
> **状态**: 规划中
> **前置**: Schema 更新已完成 (commit: a8e6ba8)

---

## I. 当前实现状态分析

### 已实现

| 层级 | 文件 | 功能 |
|------|------|------|
| Repository | `infrastructure/repositories/themes_repository.py` | `list_active_themes()` |
| Service | `domains/themes/themes_service.py` | `get_current_active_theme()` + 日期匹配逻辑 |
| Query Handler | `application/queries/themes.py` | `GetCurrentThemeQuery` / `GetCurrentThemeHandler` |
| User API | `api/user/themes.py` | `GET /themes/current` |

### 缺失功能 (需实现)

| 功能 | 说明 |
|------|------|
| **Admin API** | 完整的 CRUD + 批量生成 + Review + 重新生成 |
| **Repository 扩展** | get_by_id, get_by_date, create, update, list_for_review, 统计方法 |
| **Service 扩展** | create_theme, update_theme, review_theme, regenerate_theme |
| **AI 生成服务** | generate_theme_suggestions (调用 OpenAI) |

---

## II. 实现清单

### Phase 1: Repository 层 (12 个方法)

**文件**: `infrastructure/repositories/themes_repository.py`

| # | 方法名 | 参数 | 返回 | 说明 |
|---|--------|------|------|------|
| 1 | `get_by_id` | theme_id: str | Optional[Dict] | 按 ID 获取 |
| 2 | `get_by_date` | date: date | Optional[Dict] | 按日期获取 |
| 3 | `create` | data: Dict | Dict | 创建主题 |
| 4 | `update` | theme_id: str, data: Dict | Optional[Dict] | 更新主题 |
| 5 | `delete` | theme_id: str | bool | 软删除 |
| 6 | `list_all` | offset, limit, filters | List[Dict] | 列表 + 分页 |
| 7 | `list_for_review` | filters, offset, limit | List[Dict] | 审核列表 |
| 8 | `count_all` | filters | int | 总数统计 |
| 9 | `count_for_review` | filters | int | 审核统计 |
| 10 | `get_existing_dates` | start_date, end_date | Set[date] | 已存在日期 |
| 11 | `get_review_status_stats` | start_date, end_date | Dict | 审核状态统计 |
| 12 | `batch_update_status` | theme_ids, status, admin_id | int | 批量更新状态 |

### Phase 2: Service 层 (8 个方法)

**文件**: `domains/themes/themes_service.py`

| # | 方法名 | 参数 | 返回 | 说明 |
|---|--------|------|------|------|
| 1 | `create_theme` | 多参数 | Dict | 创建主题 |
| 2 | `update_theme` | theme_id, update_data, admin_id | Optional[Dict] | 更新主题 |
| 3 | `delete_theme` | theme_id, admin_id | bool | 删除主题 |
| 4 | `review_theme` | theme_id, action, alternative_id, notes, admin_id | Dict | 审核主题 |
| 5 | `regenerate_theme` | theme_id, reason, admin_id | Dict | 重新生成 |
| 6 | `get_theme_by_id` | theme_id | Optional[Dict] | 获取单个 |
| 7 | `get_theme_by_date` | date | Optional[Dict] | 按日期获取 |
| 8 | `list_themes` | offset, limit, filters | Dict | 列表 + 统计 |

### Phase 3: AI 生成服务 (2 个方法)

**文件**: `shared/ai/theme_generator.py` (新建)

| # | 方法名 | 参数 | 返回 | 说明 |
|---|--------|------|------|------|
| 1 | `generate_theme_suggestions` | target_date: date | Dict | 生成 3 个备选方案 |
| 2 | `_build_generation_prompt` | target_date | str | 构建 Prompt |

### Phase 4: Admin API (12 个端点)

**文件**: `api/admin/themes.py` (新建)

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 1 | GET | `/themes` | 列表 (分页 + 筛选) |
| 2 | GET | `/themes/{id}` | 获取详情 |
| 3 | POST | `/themes` | 手动创建 |
| 4 | PUT | `/themes/{id}` | 更新 |
| 5 | DELETE | `/themes/{id}` | 删除 |
| 6 | POST | `/themes/batch-generate` | 批量生成 |
| 7 | GET | `/themes/generation-status` | 生成状态 |
| 8 | GET | `/themes/calendar` | 日历视图 |
| 9 | POST | `/themes/{id}/review` | 审核 |
| 10 | POST | `/themes/{id}/regenerate` | 重新生成 |
| 11 | GET | `/themes/{id}/history` | 历史记录 |
| 12 | POST | `/themes/review/batch-approve` | 批量审核 |

---

## III. 文件结构

```
domains/themes/
├── __init__.py                   # 导出
├── constants.py                  # 常量定义 (新建)
├── entity.py                     # ThemeEntity (新建)
├── repository.py                 # Repository 接口 (新建)
├── themes_service.py             # Service (升级)
└── date_matcher.py               # 日期匹配器 (拆分)

infrastructure/repositories/
└── themes_repository.py          # Repository 实现 (升级)

shared/ai/
└── theme_generator.py            # AI 生成服务 (新建)

api/admin/
├── themes.py                     # Admin API (新建)
└── themes_models.py              # Request/Response Models (新建)

application/queries/
└── themes.py                     # Query Handlers (升级)
```

---

## IV. 常量定义

**文件**: `domains/themes/constants.py`

```python
# 主题分类
THEME_CATEGORIES = ["holiday", "memorial", "historical", "notable", "campaign", "special"]

# 审核状态
REVIEW_STATUSES = ["pending", "auto_approved", "reviewed", "rejected"]

# 主题状态
THEME_STATUSES = ["draft", "active", "archived"]

# 分页默认值
DEFAULT_LIMIT = 50
MAX_LIMIT = 200

# 批量生成限制
MAX_BATCH_DAYS = 365
DEFAULT_BATCH_DAYS = 300

# 字段长度限制
NAME_MIN_LENGTH = 1
NAME_MAX_LENGTH = 100
SLOGAN_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 1000
```

---

## V. 执行顺序

```
Step 1: 创建常量文件 domains/themes/constants.py
Step 2: 升级 Repository (添加 12 个方法)
Step 3: 升级 Service (添加 8 个方法)
Step 4: 创建 AI 生成服务 shared/ai/theme_generator.py
Step 5: 创建 Admin API models api/admin/themes_models.py
Step 6: 创建 Admin API api/admin/themes.py
Step 7: 注册路由到 api/admin/__init__.py
Step 8: 更新 container.py 依赖注入
Step 9: 运行测试
Step 10: Git commit + push
```

---

## VI. 依赖关系

```
api/admin/themes.py
    ↓ depends on
domains/themes/themes_service.py
    ↓ depends on
infrastructure/repositories/themes_repository.py
    ↓ depends on
core/database.py (Supabase client)

shared/ai/theme_generator.py
    ↓ depends on
shared/ai/openai_client.py (existing)
```

---

## VII. 验收标准

| 功能 | 验收标准 |
|------|----------|
| Admin 列表 | 分页、筛选 (category, status, review_status, date range) |
| 创建主题 | 手动创建，字段验证通过 |
| 批量生成 | 一次生成 300 天主题，每天 3 个备选方案 |
| AI 默认选择 | 自动选择 ai_recommended_id，状态为 auto_approved |
| Review 工作流 | approve/reject/switch 状态流转正确 |
| 重新生成 | 保留历史记录，regenerate_count 递增 |
| 批量审核 | 一次审核多个主题 |

---

## VIII. 风险点

| 风险 | 缓解措施 |
|------|----------|
| AI 生成耗时 | 批量生成使用后台任务，返回 task_id |
| AI 生成失败 | 记录失败日期，支持重试 |
| 并发冲突 | 使用数据库事务 + 乐观锁 |

---

**最后更新**: 2026-01-12
