# API HTTP Methods Optimization Plan

> 根据 API-METHODS-AUDIT.md 审查结果制定的优化计划

## 优化原则

1. **向后兼容**: 保留旧端点，添加新端点作为推荐方式
2. **前端影响**: 需要同步更新前端调用
3. **文档同步**: 更新 API 文档和注释

---

## 需要优化的端点

### 1. export_api.py

**当前**:
```python
POST /api/v2/export/zip
Body: {"project_id": "...", "items": [...]}
```

**优化后**:
```python
GET /api/v2/export/projects/{project_id}/zip?items=page1,page2
```

**原因**: 导出是幂等操作，应使用 GET。items 可作为查询参数传递。

**兼容性**: 保留 POST 端点，标记为 deprecated

---

###2. generations_api.py

#### 2.1 Favorite 操作

**当前**:
```python
POST /api/v2/generations/{generation_id}/favorite
```

**优化后**:
```python
PATCH /api/v2/generations/{generation_id}
Body: {"favorite": true/false}
```

**原因**: 修改资源的某个属性，应使用 PATCH

**兼容性**: 保留 POST 端点，标记为 deprecated

#### 2.2 批量删除

**当前**:
```python
DELETE /api/v2/generations/batch
Body: {"generation_ids": [...]}
```

**优化后**:
```python
POST /api/v2/generations/batch-delete
Body: {"generation_ids": [...]}
```

**原因**: 批量操作不是标准 REST 资源操作，应使用 POST + 动词

**兼容性**: 保留 DELETE 端点，标记为 deprecated

---

### 3. admin/ai_api.py

**当前**:
```python
PUT /api/v2/admin/ai/providers/toggle
Body: {"provider": "openai", "enabled": true}
```

**优化后**:
```python
PATCH /api/v2/admin/ai/providers/{provider}
Body: {"enabled": true}
```

**原因**: 部分更新资源状态，应使用 PATCH

**兼容性**: 保留 PUT 端点，标记为 deprecated

---

### 4. admin/config_api.py

**当前**:
```python
POST /api/v2/admin/config/rate-limits/update
Body: {...}
```

**优化后**:
```python
PUT /api/v2/admin/config/rate-limits
Body: {...}
```

**原因**: 更新资源应使用 PUT，不需要 `/update` 后缀

**兼容性**: 保留 POST 端点，标记为 deprecated

---

### 5. admin/events_api.py

**当前**:
```python
GET /api/v2/admin/events/
```

**优化后**:
```python
# 路径已经是 /events，无需改动
# 但需要检查 router prefix 设置
```

**原因**: 路径应该明确，不应该为空

**兼容性**: 无需兼容处理

---

### 6. admin/users_api.py

**当前**:
```python
PUT /api/v2/admin/users/{user_id}/tier
Body: {"tier": "pro"}
```

**优化后**:
```python
PATCH /api/v2/admin/users/{user_id}
Body: {"tier": "pro"}
```

**原因**: 部分更新用户资源，应使用 PATCH

**兼容性**: 保留 PUT 端点，标记为 deprecated

---

## 实施计划

### 阶段 1: 添加新端点 (保持兼容)

1. 在各个文件中添加新的优化端点
2. 在旧端点添加 `deprecated=True` 标记
3. 在旧端点文档中添加 deprecation 警告

### 阶段 2: 更新文档

1. 更新 API 文档中的端点说明
2. 在 `API-HTTP-METHODS-GUIDELINES.md` 中添加这些案例

### 阶段 3: 前端迁移

1. 通知前端团队 API 变更
2. 前端逐步迁移到新端点
3. 监控旧端点使用情况

### 阶段 4: 废弃旧端点 (3 个月后)

1. 在旧端点返回警告 header: `Deprecation: true`
2. 记录使用旧端点的日志
3. 6 个月后完全移除旧端点

---

## 前端需要更新的调用

| 旧调用 | 新调用 | 文件位置 (估计) |
|-------|-------|----------------|
| `POST /export/zip` | `GET /export/projects/{id}/zip` | Export 相关组件 |
| `POST /generations/{id}/favorite` | `PATCH /generations/{id}` | Generations 列表 |
| `DELETE /generations/batch` | `POST /generations/batch-delete` | Generations 批量操作 |
| `PUT /admin/ai/providers/toggle` | `PATCH /admin/ai/providers/{provider}` | Admin AI 设置 |
| `POST /admin/config/rate-limits/update` | `PUT /admin/config/rate-limits` | Admin 配置 |
| `PUT /admin/users/{id}/tier` | `PATCH /admin/users/{id}` | Admin 用户管理 |

---

## 当前决策

**由于这些优化会影响前端调用，建议:**

1. 先不修改现有端点 (避免破坏性变更)
2. 将优化方案记录在此文档中
3. 在下一个大版本 (v3) 中统一调整
4. 或与前端协商后统一迁移

**如果立即实施，请确保:**
- 前端同步更新所有调用
- 充分测试确保无遗漏
- 提前通知相关团队
