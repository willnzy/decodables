# 后端API自动化测试文档

## 测试框架

- **pytest**: Python 测试框架
- **pytest-asyncio**: 异步测试支持
- **httpx**: HTTP 客户端（用于 API 测试）

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_tier_logic.py

# 详细输出
pytest -v

# 显示覆盖率
pytest --cov=. --cov-report=html
```

## 测试结构

```
tests/
├── conftest.py              # 测试配置和 fixtures
├── test_tier_logic.py       # 核心业务逻辑测试（无需依赖）
├── test_projects_api.py     # 项目 API 测试
├── test_export_api.py       # 导出 API 测试
├── test_upload_api.py       # 上传 API 测试
└── test_image_generation.py # 图片生成 API 测试
```

## 测试覆盖范围 (PRD v3.2)

### ✅ 已实现的测试

1. **test_tier_logic.py** - 核心业务逻辑测试
   - ✅ 项目数量限制（Free: 1, Starter: 20, Pro: 200）
   - ✅ Free 7天游玩期检查
   - ✅ 权限检查（ZIP导出、个人上传、PDF导出）
   - ✅ AI 模型选择（Free/Starter: flux-schnell, Pro: flux-dev）
   - ✅ 降级逻辑（项目排序和限制）

2. **test_projects_api.py** - 项目 API 测试
   - ✅ 项目创建限制检查
   - ✅ Free 7天游玩期过期检查
   - ✅ 降级后项目编辑限制

3. **test_export_api.py** - 导出 API 测试
   - ✅ ZIP 导出权限（Pro only）
   - ✅ PDF 导出权限（所有 tier）

4. **test_upload_api.py** - 上传 API 测试
   - ✅ 个人上传权限（Pro only）

5. **test_image_generation.py** - 图片生成 API 测试
   - ✅ AI 模型选择（根据 tier）
   - ✅ Credit 不足检查

## 测试最佳实践

1. **Mock 外部依赖**
   - Supabase: 使用 `@patch('db_service.supabase')`
   - Clerk Auth: Mock `get_current_user`
   - 外部 API: Mock HTTP 请求

2. **测试隔离**
   - 每个测试前重置 mock
   - 使用 `pytest.fixture` 管理测试数据

3. **测试命名**
   - 使用描述性的测试名称
   - 遵循 "test_[functionality]_[condition]" 格式

## 注意事项

1. **依赖安装**: 需要安装所有项目依赖才能运行完整测试
2. **环境变量**: 某些测试可能需要环境变量（可以 mock）
3. **数据库**: 使用 mock 避免实际数据库操作

## 快速测试（无需依赖）

运行 `test_tier_logic.py` 可以快速验证核心业务逻辑，无需安装所有依赖：

```bash
pytest tests/test_tier_logic.py -v --ignore=tests/conftest.py
```

