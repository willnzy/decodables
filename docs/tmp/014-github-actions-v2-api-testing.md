# GitHub Actions - v2 API Testing Strategy

> 为 38 个 v2 API 文件配置自动化测试

---

## 当前状态

### ✅ 已有测试 (5 个 API 文件)
- tests/api/test_export_api.py
- tests/api/test_generation_api.py
- tests/api/test_projects_api.py
- tests/api/test_upload_api.py
- tests/api/test_user_api.py

### ⚠️ 缺失测试 (33 个 API 文件)
- 19 个公开 API
- 14 个 Admin API

---

## 推荐方案：CI 驱动测试（95% 场景）

### ✅ 工作流

```
本地开发 → 写测试 → git push → GitHub Actions 运行全部测试 → 查看结果
```

### 本地只在以下情况运行测试（5% 场景）:

1. **快速验证新功能**:
   ```bash
   pytest tests/api/test_new_feature.py -v
   ```

2. **修改核心逻辑前验证**:
   ```bash
   pytest tests/test_payment_service.py tests/test_credits_logic.py -v
   ```

3. **CI 失败后调试**:
   ```bash
   pytest tests/api/test_xxx.py::test_specific -vv --tb=long
   ```

---

## GitHub Actions 配置优化

### 选项 A: 扩展现有 api-tests job（推荐）

**当前配置** (`.github/workflows/test.yml:101-134`):
```yaml
api-tests:
  name: API Tests
  runs-on: ubuntu-latest

  steps:
    - name: Run API tests
      run: |
        pytest tests/api/ \
               -v --tb=short || echo "::warning::Some API tests failed"
```

**优化后**:
```yaml
api-tests:
  name: API Tests (v2)
  runs-on: ubuntu-latest

  steps:
    - name: Run v2 API tests
      run: |
        # Public APIs
        pytest tests/api/ \
               -v --tb=short

        # Admin APIs (如果存在)
        pytest tests/api/admin/ \
               -v --tb=short || echo "::warning::Admin API tests not yet implemented"
      env:
        TESTING: 'true'
        # ... 环境变量
```

### 选项 B: 添加专门的 v2-api-tests job

在 `.github/workflows/test.yml` 中添加新 job:

```yaml
# ============================================
# v2 API Tests (New Architecture)
# ============================================
v2-api-tests:
  name: v2 API Tests (DDD)
  runs-on: ubuntu-latest

  steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        cache: 'pip'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio httpx

    - name: Run v2 API tests
      run: |
        echo "## 🧪 v2 API Test Results" >> $GITHUB_STEP_SUMMARY
        echo "" >> $GITHUB_STEP_SUMMARY

        # Public APIs (24 files)
        echo "### Public APIs (24 files)" >> $GITHUB_STEP_SUMMARY
        pytest tests/api/ \
               --tb=short \
               -v 2>&1 | tee api_test_output.txt

        # Admin APIs (14 files)
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "### Admin APIs (14 files)" >> $GITHUB_STEP_SUMMARY
        pytest tests/api/admin/ \
               --tb=short \
               -v 2>&1 | tee -a api_test_output.txt || echo "⚠️ Admin API tests not yet complete"

        # Application Layer (Handlers)
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "### Application Layer (Handlers)" >> $GITHUB_STEP_SUMMARY
        pytest tests/application/ \
               --tb=short \
               -v 2>&1 | tee -a api_test_output.txt

        # Domain Layer (Aggregates)
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "### Domain Layer (Aggregates)" >> $GITHUB_STEP_SUMMARY
        pytest tests/domains/ \
               --tb=short \
               -v 2>&1 | tee -a api_test_output.txt
      env:
        TESTING: 'true'
        STRIPE_SECRET_KEY: 'sk_test_mock'
        STRIPE_WEBHOOK_SECRET: 'whsec_test_mock'
        OPENAI_API_KEY: 'sk-test-mock-key'
        FAL_KEY: 'test-fal-key'
        DASHSCOPE_API_KEY: 'test-dashscope-key'
        SUPABASE_URL: 'https://mock.supabase.co'
        SUPABASE_KEY: 'mock_supabase_key'
        CLERK_WEBHOOK_SECRET: 'whsec_test_mock'

    - name: Upload test summary
      if: always()
      run: |
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "---" >> $GITHUB_STEP_SUMMARY
        echo "" >> $GITHUB_STEP_SUMMARY
        grep -E "(PASSED|FAILED|ERROR)" api_test_output.txt >> $GITHUB_STEP_SUMMARY || true
```

### 选项 C: 按层级分离测试 job（最细粒度）

```yaml
# API 层测试
api-layer-tests:
  name: API Layer Tests
  runs-on: ubuntu-latest
  steps: [...]

# Application 层测试
application-layer-tests:
  name: Application Layer Tests
  runs-on: ubuntu-latest
  steps: [...]

# Domain 层测试
domain-layer-tests:
  name: Domain Layer Tests
  runs-on: ubuntu-latest
  steps: [...]
```

---

## 测试覆盖率目标

### Phase 2 目标: 80%+ 覆盖率

| 层级 | 当前 | 目标 | 优先级 |
|------|------|------|--------|
| **API 层** | ~13% (5/38) | 80%+ (31+/38) | 🔴 高 |
| **Application 层** | ~50% (2/4估计) | 90%+ | 🟠 中 |
| **Domain 层** | ~60% (3/5估计) | 90%+ | 🟠 中 |
| **Services 层** | ~60% (已有) | 70%+ | 🟡 低 |

### 具体任务

**Week 1 (12h)**: API 层测试
- [ ] 补充 19 个公开 API 测试
- [ ] 补充 14 个 Admin API 测试

**Week 2 (8h)**: Application + Domain 层测试
- [ ] 补充 Application 层缺失测试
- [ ] 补充 Domain 层缺失测试

**Week 3 (4h)**: 边缘用例 + 集成测试
- [ ] 并发场景测试
- [ ] Webhook 幂等性测试
- [ ] 端到端流程测试

---

## 本地测试命令速查

### 快速验证（单个文件）
```bash
# 测试单个 API 文件
pytest tests/api/test_billing_api.py -v

# 测试单个函数
pytest tests/api/test_billing_api.py::test_deduct_credits -v

# 显示详细错误
pytest tests/api/test_billing_api.py -vv --tb=long
```

### 分层测试
```bash
# 只测试 API 层
pytest tests/api/ -v

# 只测试 Application 层
pytest tests/application/ -v

# 只测试 Domain 层
pytest tests/domains/ -v

# 测试 v2 架构全部
pytest tests/api/ tests/application/ tests/domains/ -v
```

### 覆盖率检查
```bash
# 查看 API 层覆盖率
pytest tests/api/ --cov=api --cov-report=term-missing

# 查看全部覆盖率
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

### CI 失败后调试
```bash
# 1. 查看 GitHub Actions 日志，找到失败的测试
# 2. 本地运行该测试
pytest tests/api/test_xxx.py::test_failed_function -vv

# 3. 进入 pdb 调试
pytest tests/api/test_xxx.py::test_failed_function --pdb
```

---

## 最佳实践

### ✅ DO (推荐)

1. **依赖 CI 运行全部测试**:
   - 每次 push 自动运行
   - 环境一致，结果可靠
   - 无需本地配置环境

2. **本地只运行正在开发的测试**:
   - 快速反馈
   - 节省时间
   - 避免本地环境问题

3. **使用 GitHub Actions Summary**:
   - 查看测试结果摘要
   - 无需下载日志

4. **失败时才本地调试**:
   - 使用 `-vv --tb=long` 查看详细错误
   - 使用 `--pdb` 进入调试器

### ❌ DON'T (不推荐)

1. ❌ 不要在本地运行全部测试:
   - 耗时长（可能 10+ 分钟）
   - 环境差异可能导致误报
   - CI 已经会运行

2. ❌ 不要在 commit 前运行所有测试:
   - 影响开发效率
   - CI 会自动运行
   - 只需确保新写的测试通过

3. ❌ 不要跳过写测试:
   - 代码改动 = 业务代码 + 测试代码
   - 测试是文档的一部分

---

## Phase 2 执行计划

### Week 1: API 层测试 (12h)

**任务**:
1. 为 33 个缺失的 API 创建测试文件
2. 每个 API 至少测试:
   - ✅ 正常流程（200/201 响应）
   - ✅ 认证失败（401）
   - ✅ 参数验证（422）
   - ✅ 权限检查（403，仅 Admin API）

**工作流**:
```bash
# 1. 创建测试文件
touch tests/api/test_billing_api.py

# 2. 写测试
vim tests/api/test_billing_api.py

# 3. 本地验证
pytest tests/api/test_billing_api.py -v

# 4. 提交并触发 CI
git add tests/api/test_billing_api.py
git commit -m "test(api): add billing API tests"
git push origin develop

# 5. 查看 GitHub Actions 结果
```

**预期成果**:
- ✅ 38 个 API 测试文件全部创建
- ✅ GitHub Actions 中 api-tests job 通过率 > 95%
- ✅ API 层覆盖率 > 80%

---

## 监控与优化

### 查看 CI 测试历史
1. 访问 GitHub 仓库
2. Actions → Backend Tests
3. 查看最近 10 次运行记录
4. 分析失败原因

### 优化测试速度
- ✅ 使用 `pytest-xdist` 并行测试（已配置）
- ✅ 使用 mock 避免真实 API 调用（已配置）
- ✅ 缓存 pip 依赖（已配置）

---

## 总结

### ✅ 推荐：95% 依赖 CI

**本地**: 只运行正在开发的测试
```bash
pytest tests/api/test_new_feature.py -v
```

**CI**: 自动运行全部测试
```yaml
# 每次 push 自动触发
pytest tests/ --cov=. --cov-report=xml
```

### ❌ 不推荐：本地运行全部测试

理由:
- ⏱️ 耗时长（10+ 分钟）
- 🔧 环境配置复杂
- ⚠️ 可能与 CI 结果不一致
- 🚀 CI 更快（并行执行）

---

**下一步**: 是否需要我帮你创建缺失的 33 个 API 测试文件？

命令: `开始创建 v2 API 测试` 或 `Start creating v2 API tests`
