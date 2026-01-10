# API 文档完善计划 (P3-A)

**日期**: 2026-01-11
**任务**: Phase 4 - Task 8 - 完善 API 文档和注释
**预计工时**: 4 hours
**优先级**: P3 (LOW)

---

## 📋 问题总结

基于代码审查，发现以下文档缺失问题：

### 关键发现

1. **最严重问题**: Admin 端点 (feature_flags, notifications) 仅有 1-2 行文档，无错误码说明
2. **高优先级**: 缺少有效枚举值文档 (tier, operation, event_type, group_by)
3. **中优先级**: Response model 结构未在文档中详细说明
4. **模式问题**: 代码中定义的约束未在 API 文档中体现 (如 MAX_CHAT_IMAGES = 4)
5. **不一致性**: 部分文件 (config.py, metrics.py) 文档较好，其他文件 (feature_flags.py, notifications.py) 文档极简

### 统计数据

- **16 个 Admin API 文件** - 文档质量参差不齐
- **26 个 User API 文件** - OpenAPI 合规性不一致
- **识别出的高优先级端点**: 8 个文件，~30 个端点

---

## 🎯 文档标准

### OpenAPI 完整文档应包含

1. **功能描述** (2-3 句话)
   - 端点用途
   - 主要功能
   - 版本变更说明（如有）

2. **参数说明** (每个参数)
   - 参数用途
   - 有效值/取值范围
   - 格式要求 (日期、枚举等)
   - 默认值和约束

3. **Response Model 示例**
   - 返回字段说明
   - 字段类型和含义
   - 示例值

4. **错误码文档**
   - 400: 参数验证失败 (具体场景)
   - 401: 认证失败
   - 403: 权限不足
   - 404: 资源不存在
   - 409: 冲突 (并发、状态)
   - 500: 内部错误

5. **Security 说明** (如适用)
   - 权限要求
   - Rate limit
   - 数据访问控制

---

## 📝 实施计划

### Phase 1: 高优先级端点 (2h) - Admin API

**目标**: 补全最严重缺失的 Admin API 文档

#### 1.1 Feature Flags API (30 min)
**文件**: `api/admin/feature_flags.py`

**待改进端点**:
- `GET /` (list_flags) - 添加参数说明、错误码
- `POST /` (create_flag) - 添加错误码 (400 key exists, 500)
- `PUT /{key}` (update_flag) - 添加 404 错误说明
- `DELETE /{key}` (delete_flag) - 添加 404、409 错误说明
- `POST /{key}/toggle` (toggle_flag) - 添加错误码

**示例改进**:
```python
# BEFORE
async def create_flag(...):
    """创建Flag"""

# AFTER
async def create_flag(...):
    """Create a new feature flag.

    Creates a feature flag with the specified configuration. Flag keys must be unique.

    Args:
        req: Feature flag configuration
            - key: Unique identifier (alphanumeric + underscore)
            - description: Human-readable description
            - is_enabled: Initial enabled state (default: false)
            - target_users: Optional list of user IDs for targeting
            - percentage: Optional rollout percentage (0-100)

    Returns:
        FeatureFlagResponse: Created flag with metadata
            - id: Flag UUID
            - key: Flag identifier
            - is_enabled: Current state
            - created_at: Creation timestamp

    Raises:
        400: Invalid key format or key already exists
        401: Unauthorized (not admin)
        500: Database error

    Security:
        - Admin role required
        - Rate limit: 30/minute

    Example:
        POST /api/v2/admin/feature-flags
        {
            "key": "new_editor_ui",
            "description": "Enable new editor UI",
            "is_enabled": false,
            "percentage": 10
        }
    """
```

#### 1.2 Notifications API (30 min)
**文件**: `api/admin/notifications.py`

**待改进端点**:
- `POST /broadcast` - 详细文档、错误码
- `POST /notification/send` - 用户不存在 (404) 说明
- `POST /notification/batch` - 批量失败处理说明
- `GET /stats` - 返回字段说明

#### 1.3 Events API (20 min)
**文件**: `api/admin/events.py`

**待改进端点**:
- `GET /events` - 日期格式、错误码
- `GET /events/stats` - group_by 有效值文档

#### 1.4 Users API (20 min)
**文件**: `api/admin/users.py`

**待改进端点**:
- `GET /users` - query 搜索字段说明
- `GET /users/by-tier/{tier}` - tier 有效值文档

#### 1.5 Config API (20 min)
**文件**: `api/admin/config.py`

**待改进端点**:
- `GET /config` - category 有效值、错误码
- `GET /config/{key}` - 404 错误说明

---

### Phase 2: 中优先级端点 (1.5h) - User API

**目标**: 补全常用 User API 文档

#### 2.1 Support API (30 min)
**文件**: `api/user/support.py`

**待改进端点**:
- `POST /ticket` - Response 结构、错误码、约束说明
- `POST /chat` - MAX_CHAT_IMAGES、MAX_CONVERSATION_HISTORY 约束文档
- `POST /contact` - 错误码
- `POST /feedback` - 错误码

#### 2.2 Billing API (20 min)
**文件**: `api/user/billing.py`

**待改进端点**:
- `GET /transactions` - tx_type 有效值、日期格式
- `GET /can-afford` - operation 有效值列表

#### 2.3 Tasks API (20 min)
**文件**: `api/user/tasks.py`

**待改进端点**:
- `GET /{task_id}` - 错误码 (404, 401)
- `POST /{task_id}/cancel` - 错误码 (400, 409)

#### 2.4 Generations API (20 min)
**文件**: `api/user/generations.py`

**待改进端点**:
- `GET /history` - favorites_only 参数说明
- `PATCH /{id}` - 错误码

#### 2.5 Resources API (20 min)
**文件**: `api/user/resources.py`

**待改进端点**:
- `GET /stickers` - Response 结构详细说明
- `GET /backgrounds` - Response 结构详细说明

---

### Phase 3: 通用改进 (30 min)

#### 3.1 创建文档模板
**文件**: `docs/API-Documentation-Template.md`

**内容**: 标准 OpenAPI 文档格式模板

#### 3.2 更新贡献指南
**文件**: 更新 `docs/` 中的开发规范

**添加**: API 文档编写规范章节

---

## ✅ 验证标准

### 文档完整性检查

每个端点必须包含：
- [ ] 功能描述 (≥2 句话)
- [ ] 所有参数说明 (包括可选参数)
- [ ] 枚举值列表 (如适用)
- [ ] Response model 字段说明
- [ ] 至少 3 个错误码 (400, 401, 500)
- [ ] Security 说明 (权限、Rate limit)
- [ ] 示例 (复杂端点)

### 质量标准

- ✅ 文档使用英文 (与代码一致)
- ✅ 参数约束在文档中体现
- ✅ 错误场景具体化 (不只是 "400: Bad Request")
- ✅ 代码中定义的常量在文档中说明

---

## 📊 预期成果

### 改进端点统计

| 模块 | 端点数 | 改进项 |
|------|--------|--------|
| Admin - Feature Flags | 5 | 错误码、参数、示例 |
| Admin - Notifications | 4 | 完整文档、错误码 |
| Admin - Events | 2 | 枚举值、错误码 |
| Admin - Users | 2 | 参数说明、枚举值 |
| Admin - Config | 2 | 错误码、category 值 |
| User - Support | 4 | Response、约束、错误码 |
| User - Billing | 2 | 枚举值、格式说明 |
| User - Tasks | 2 | 错误码 |
| User - Generations | 2 | 参数说明、错误码 |
| User - Resources | 2 | Response 结构 |
| **总计** | **27** | **全面改进** |

### 质量提升

- ✅ 从 "最小文档" 升级到 "完整 OpenAPI 文档"
- ✅ 前端开发者可直接根据文档调用 API
- ✅ 错误处理更清晰
- ✅ 减少沟通成本

---

## 🚀 执行顺序

```
1. Phase 1.1: Feature Flags API (30 min)
2. Phase 1.2: Notifications API (30 min)
3. Phase 1.3: Events API (20 min)
4. Phase 1.4: Users API (20 min)
5. Phase 1.5: Config API (20 min)
   └─ Commit: docs(admin): improve Admin API documentation (Phase 1)

6. Phase 2.1: Support API (30 min)
7. Phase 2.2: Billing API (20 min)
8. Phase 2.3: Tasks API (20 min)
9. Phase 2.4: Generations API (20 min)
10. Phase 2.5: Resources API (20 min)
    └─ Commit: docs(user): improve User API documentation (Phase 2)

11. Phase 3: 创建模板和更新规范 (30 min)
    └─ Commit: docs: add API documentation template and guidelines
```

---

## 📌 注意事项

1. **不改变功能**: 只改文档字符串，不修改业务逻辑
2. **保持一致性**: 使用统一的文档风格
3. **验证准确性**: 文档内容必须与代码实现一致
4. **测试无影响**: 文档改动不应影响测试

---

**计划状态**: ✅ Ready for Implementation
**预计总时间**: 4 hours
**优先级**: P3 (LOW)
