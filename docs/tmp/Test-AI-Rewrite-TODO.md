# test_ai.py 测试重写 TODO

**日期**: 2026-01-11
**优先级**: P2 (MEDIUM)
**预计工时**: 3-4 hours

---

## 📋 问题描述

`tests/api/admin/test_ai.py` 包含 21 个失败的测试用例,主要问题:

1. **Mock 了不存在的函数**: `api.admin.ai.get_database_client`
2. **Mock 路径不正确**: 应该 mock `domains.stats` 中的实际函数
3. **Repository mock 过时**: 使用了 `SupabaseAdminStatsRepository` 的过时模式
4. **认证 mock 无效**: `@patch('api.admin.ai.require_admin')` 在 TestClient 中不生效

---

## ❌ 当前状态

**测试结果**: 21 failed, 16 passed

**失败原因分类**:

| 类型 | 数量 | 示例测试 |
|------|------|----------|
| Mock 不存在的函数 | 11 | `test_insights_success_all_type` |
| 认证 mock 无效 (401) | 6 | `test_insights_rejects_invalid_type` |
| 模块找不到 | 4 | `test_generate_report_success_comprehensive` |

---

## ✅ 修复方案

### 1. 集成测试改为真实数据库

**当前问题**: 过度使用 mock,导致测试不稳定

**解决方案**: 使用测试数据库 + fixtures

```python
@pytest.fixture
async def test_db():
    """Create test database connection."""
    # Use test Supabase instance or SQLite
    pass

class TestInsightsSuccess:
    @pytest.mark.asyncio
    async def test_insights_success_all_type(self, test_db, override_get_current_user):
        """Real integration test with test database."""
        # Insert test data
        # Call actual endpoint
        # Verify result
        pass
```

### 2. 使用 pytest override 处理认证

**当前问题**: `@patch('api.admin.ai.require_admin')` 不生效

**解决方案**: FastAPI dependency override

```python
@pytest.fixture
def override_require_admin(app):
    """Override admin authentication for testing."""
    async def mock_admin():
        return {"id": "admin123", "role": "admin"}

    app.dependency_overrides[require_admin] = mock_admin
    yield
    app.dependency_overrides.clear()

class TestInsightsSuccess:
    def test_insights_success(self, client, override_require_admin):
        """Test with overridden auth."""
        response = client.get("/api/v2/admin/ai/insights")
        assert response.status_code == 200
```

### 3. Mock `domains.stats` 函数 (单元测试)

**当前问题**: Mock 路径错误

**解决方案**: 正确的 mock 路径

```python
class TestInsightsUnitTests:
    @patch('domains.stats.get_ai_insights')
    def test_insights_calls_domain_service(self, mock_insights, client, override_require_admin):
        """Unit test: verify endpoint calls domain service."""
        mock_insights.return_value = [{"category": "growth"}]

        response = client.get("/api/v2/admin/ai/insights")

        assert response.status_code == 200
        mock_insights.assert_called_once_with("all")
```

---

## 📝 重写计划

### Phase 1: 修复认证 (1h)

**目标**: 所有测试能正确处理 admin 认证

**任务**:
1. 创建 `override_require_admin` fixture
2. 更新所有测试使用 fixture 替代 `@patch`
3. 验证认证测试通过

**影响**: 27 个测试

---

### Phase 2: 重写集成测试 (1.5h)

**目标**: 使用真实数据库替代过度 mock

**任务**:
1. 创建 test database fixture
2. 重写 Success 测试类 (4个类)
   - `TestInsightsSuccess`
   - `TestRecommendationsSuccess`
   - `TestBehaviorAnalysisSuccess`
   - `TestGenerateReportSuccess`
3. 使用真实数据 + 真实查询

**影响**: 8 个测试

---

### Phase 3: 修复参数验证测试 (0.5h)

**目标**: 参数验证测试返回正确的 400 错误

**任务**:
1. 确保 auth override 生效
2. 验证参数验证逻辑
3. 更新断言匹配实际错误消息

**影响**: 6 个测试

---

### Phase 4: 修复异常处理测试 (1h)

**目标**: 异常处理测试正确 mock 和验证

**任务**:
1. Mock `domains.stats` 函数抛出异常
2. 验证 500 错误和错误消息
3. 测试各种异常场景

**影响**: 4 个测试

---

## 🎯 预期结果

**测试覆盖**:
- ✅ 37 tests passing (currently 16)
- ✅ 0 failures (currently 21)
- ✅ Proper integration + unit test mix
- ✅ Stable and maintainable tests

**质量提升**:
- ✅ 真实数据库测试 (集成测试)
- ✅ 正确的 mock 策略 (单元测试)
- ✅ FastAPI 最佳实践 (dependency override)
- ✅ 清晰的测试分层

---

## 📌 依赖

**工具**:
- pytest-asyncio
- pytest fixtures
- FastAPI TestClient
- Supabase test instance (或 SQLite)

**文档参考**:
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [FastAPI Dependency Override](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)

---

## 🚧 暂时的解决方案

**当前状态**: 测试部分失败,但不影响核心功能

**原因**: 这些测试本来就有问题 (mock 了不存在的函数)

**影响**:
- ✅ 认证测试通过 (16/37)
- ✅ 单元测试通过 (参数验证,常量检查)
- ❌ 集成测试失败 (需要重写)

**风险**:
- 🟡 MEDIUM - 缺少集成测试覆盖
- 🟢 LOW - 核心功能已在其他测试覆盖

---

**下一步**:
1. 优先完成 Phase 4 其他任务
2. 将测试重写加入 Phase 5 或单独 sprint
3. 时间允许时再处理测试重写

**Commit**: `8f2cf90` - fix(tests): remove invalid mocks from test_ai.py
