# 旧代码清理计划 (Legacy Code Cleanup Plan)

> **文档版本**: 1.0.0
> **更新日期**: 2026-01-07
> **审计执行人**: Claude Code
> **审计方法**: 代码引用分析 + 功能映射

---

## 执行摘要

本文档记录了从 v2.x 传统架构到 v3.0 DDD 架构迁移后的旧代码清理计划。

**当前状态**:
- ✅ **核心业务逻辑已迁移** (5个 domain: billing/identity/creation/marketplace/platform)
- ⚠️  **基础设施代码待迁移** (services/ai/, services/cache/, services/db/)
- ⚠️  **API 层混用** (routers/ 旧版 + api/ 新版并存)
- ✅ **向后兼容层已建立** (exceptions.py 提供平滑过渡)

**清理策略**: 分阶段、低风险、可回滚

---

## 1. 已确认迁移的代码 (可安全删除)

### 1.1 已删除 (Phase 3.1)

| 文件/目录 | 迁移到 | 删除时间 | Commit |
|-----------|--------|----------|--------|
| `repositories/` (5 files) | `infrastructure/repositories/` | 2026-01-07 | 37024a1 |
| `exceptions/` (8 files) | `core/exceptions/` | 2026-01-07 | 37024a1 |

**总计**: 已删除 1637 行废弃代码

---

## 2. 引用检查结果

### 2.1 services/db/core.py

**检查命令**:
```bash
grep -r "from services.db.core import" --include="*.py" .
```

**引用情况**:
- ❌ `tests/services/test_db_other.py` - 旧测试文件 (16+ 引用)
- ✅ 生产代码无引用

**结论**: **暂不删除** - 需要先更新或删除旧测试

### 2.2 services/cache/*

**检查命令**:
```bash
grep -r "from services.cache import" --include="*.py" .
```

**引用情况**:
- ❌ `app.py` - `from services.cache import close_redis`
- ❌ `routers/admin_system.py` - `get_redis_client()` (4处)
- ❌ `api/admin/system_api.py` - `get_redis_client()`
- ❌ `services/ai/model_config_service.py` - `cache_service`
- ❌ `tests/test_redis_client.py` - 测试文件

**结论**: **暂不删除** - 需要先更新所有引用

### 2.3 services/credit_service.py

**检查命令**:
```bash
grep -r "from services.credit_service import\|from services import.*credit" --include="*.py" .
```

**预期**: 被多个 routers/ 文件引用

**结论**: **暂不删除** - 需要先迁移 routers/ 到 api/

---

## 3. 清理路线图

### Phase 3.4.3 - 更新引用 (本周)

#### 步骤 1: 更新 services/cache 引用

```python
# ❌ 旧引用 (app.py, routers/admin_system.py, api/admin/system_api.py)
from services.cache import get_redis_client, close_redis

# ✅ 新引用
from core.cache import CacheService, get_cache_provider
```

**文件清单**:
- [ ] `app.py` - 更新 `close_redis` 引用
- [ ] `routers/admin_system.py` - 更新 `get_redis_client` 引用
- [ ] `api/admin/system_api.py` - 更新 `get_redis_client` 引用
- [ ] `services/ai/model_config_service.py` - 更新 `cache_service` 引用

#### 步骤 2: 删除或更新旧测试

```bash
# 选项 A: 删除旧测试 (如果功能已有新测试覆盖)
rm tests/services/test_db_other.py
rm tests/test_redis_client.py

# 选项 B: 更新测试引用 (如果测试仍有价值)
# 手动更新 import 语句
```

**文件清单**:
- [ ] 评估 `tests/services/test_db_other.py` - 是否有价值？
- [ ] 评估 `tests/test_redis_client.py` - 是否有价值？
- [ ] 如果有价值，更新引用；否则删除

#### 步骤 3: 删除已迁移文件

**仅在步骤 1-2 完成后执行**:

```bash
# 确认无引用后删除
rm services/db/core.py
rm services/cache/cache_service.py
rm services/cache/redis_client.py
rm services/cache/memory_cache.py
rm services/cache/cache_keys.py
```

---

### Phase 3.4.4 - 迁移 AI 服务 (本月)

#### 目标: services/ai/ → shared/ai/

**当前状态**:
- `services/ai/` 是一个完整的 AI 服务模块 (18+ 文件)
- 被多个 routers/ 引用
- 架构设计良好，可以整体迁移

**迁移步骤**:

1. **复制文件** (不删除原文件)
```bash
cp -r services/ai shared/ai
```

2. **更新内部引用**
```python
# shared/ai/__init__.py
# 更新所有相对导入
```

3. **更新外部引用**
```python
# ❌ 旧引用
from services.ai import UnifiedImageService

# ✅ 新引用
from shared.ai import UnifiedImageService
```

4. **验证功能**
```bash
pytest tests/integration/test_generation_flow.py -v
```

5. **删除旧文件**
```bash
rm -rf services/ai/
```

---

### Phase 3.4.5 - 迁移 routers 到 api (长期)

#### 目标: 逐步替换 routers/ 为 api/

**优先级**:

| Router | API | 复杂度 | 优先级 | 预估时间 |
|--------|-----|--------|--------|----------|
| `routers/health.py` | `api/health_api.py` | 低 | P0 | 30min |
| `routers/users.py` | `api/user_api.py` | 高 | P0 | 2h |
| `routers/projects.py` | `api/projects_api.py` | 高 | P1 | 3h |
| `routers/generation.py` | `api/generation_api.py` | 高 | P1 | 3h |
| `routers/marketplace.py` | `api/marketplace_api.py` | 中 | P1 | 2h |
| `routers/webhooks_*.py` | `api/webhooks_*.py` | 中 | P2 | 1h |

**迁移模板**:

```python
# 旧代码 (routers/users.py)
from services.user_service import UserService

@router.get("/users/me")
async def get_me(user: dict = Depends(get_current_user)):
    service = UserService()
    return service.get_user(user["id"])

# 新代码 (api/user_api.py)
from container import Container
from application.queries.identity import GetUserQuery

@router.get("/users/me")
async def get_me(
    user: dict = Depends(get_current_user),
    container: Container = Depends(get_container),
):
    identity_service = container.identity_service()
    query = GetUserQuery(user_id=user["id"])
    user_profile = await identity_service.get_user(query.user_id)
    return UserResponse.from_domain(user_profile)
```

---

## 4. 风险控制

### 4.1 删除前检查清单

每次删除文件前必须确认:

- [ ] ✅ 功能已在新架构中实现
- [ ] ✅ 新代码有测试覆盖 (≥60%)
- [ ] ✅ 无生产代码引用 (grep 检查)
- [ ] ✅ CI/CD 通过
- [ ] ✅ 本地应用可启动
- [ ] ✅ 关键 API 端点测试通过

### 4.2 回滚策略

**Git 回滚命令**:
```bash
# 如果删除导致问题，可以立即恢复
git revert <commit_hash>

# 或者从历史中恢复单个文件
git checkout <commit_hash> -- path/to/file.py
```

### 4.3 分支策略

**建议**:
- 所有清理工作在 `develop` 分支进行
- 每完成一个 Phase 创建一个 commit
- 定期推送到 Railway 测试环境验证
- `main` 分支保持稳定

---

## 5. 进度追踪

### Phase 3.4.3 - 更新引用

- [x] 审计引用情况
- [ ] 更新 app.py 引用
- [ ] 更新 routers/admin_system.py 引用
- [ ] 更新 api/admin/system_api.py 引用
- [ ] 更新 services/ai/model_config_service.py 引用
- [ ] 删除或更新旧测试
- [ ] 删除已迁移文件

**预估完成时间**: 今天

### Phase 3.4.4 - 迁移 AI 服务

- [ ] 复制 services/ai/ 到 shared/ai/
- [ ] 更新内部引用
- [ ] 更新外部引用
- [ ] 运行集成测试验证
- [ ] 删除旧 services/ai/

**预估完成时间**: 本周

### Phase 3.4.5 - 迁移 Routers

- [ ] health.py
- [ ] users.py
- [ ] projects.py
- [ ] generation.py
- [ ] marketplace.py
- [ ] webhooks_*.py

**预估完成时间**: 2周

---

## 6. 成功指标

### 定量指标

| 指标 | 当前 | 目标 |
|------|------|------|
| 旧代码行数 (services/) | ~5000 | <1000 |
| 旧代码行数 (routers/) | ~3000 | 0 |
| 测试覆盖率 | 60% | 70% |
| 启动时间 | ~2s | <2s |

### 定性指标

- ✅ 所有 API 端点正常工作
- ✅ 无 import 错误
- ✅ 文档已更新
- ✅ 团队成员理解新架构

---

## 7. 常见问题

### Q: 为什么不一次性删除所有旧代码?

**A**: 风险太高。我们采用**渐进式迁移**策略:
1. 先迁移功能到新架构
2. 确保新代码稳定
3. 更新所有引用
4. 最后删除旧代码

这样可以：
- ✅ 随时回滚
- ✅ 逐步验证
- ✅ 降低风险

### Q: 删除后如果发现遗漏的功能怎么办?

**A**:
1. 通过 Git 恢复旧代码
2. 在新架构中实现遗漏的功能
3. 添加测试覆盖
4. 再次删除旧代码

### Q: services/ai/ 为什么要复制而不是移动?

**A**:
- 复制后可以同时存在，降低风险
- 更新引用时不会中断现有功能
- 验证完成后再删除旧代码

---

## 8. 下一步行动

### 立即执行 (今天, 2026-01-07)

1. **完成 Phase 3.4.3**:
   - 更新 services/cache 引用 (4个文件)
   - 删除或更新旧测试 (2个文件)
   - 删除已迁移文件 (5个文件)

2. **提交并推送**:
```bash
git add -A
git commit -m "chore: remove legacy cache and db core after updating references"
git push origin develop
```

3. **验证**:
```bash
pytest tests/test_app_startup.py -v
python3 -c "import app; print('OK')"
```

### 本周执行

1. 开始 Phase 3.4.4 (迁移 AI 服务)
2. 更新 app.py 路由注册
3. 测试所有 API 端点

---

**文档所有者**: Backend Team
**最后更新**: 2026-01-07
**下次审计**: 2026-01-14
