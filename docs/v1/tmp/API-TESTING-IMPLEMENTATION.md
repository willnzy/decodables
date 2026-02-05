# API 集成测试实施计划

> 从测试到监控到修复的完整闭环方案

**创建日期**: 2026-01-18
**状态**: 进行中
**当前阶段**: Phase 1 - Step 1

---

## 🔴 核心原则: 黑盒测试

### 绝对禁止

```
❌ 禁止根据现有代码实现来设计测试用例
❌ 禁止因为"代码就是这样写的"而认为测试通过
❌ 禁止迎合后端代码的 bug 来调整测试期望
❌ 禁止跳过"代码不支持"的测试场景
```

### 必须遵守

```
✅ 把 API 当作完全的黑盒
✅ 从业务逻辑和用户视角设计测试用例
✅ 测试用例基于 API 文档/规范，而非代码实现
✅ 发现问题时修复代码，而非修改测试
✅ 边界条件和异常场景必须按业务规则测试
```

### 测试设计思维

**错误示例** (迎合代码):
```python
# ❌ 看了代码发现 title 没有长度限制，所以不测试边界
def test_create_project(self):
    # 代码里没有限制，所以随便传
    response = client.post("/projects", json={"title": "x" * 10000})
    assert response.status_code == 201  # 代码允许，所以期望 201
```

**正确示例** (业务逻辑):
```python
# ✅ 从业务角度: 标题应该有合理的长度限制
def test_create_project_title_too_long(self):
    # 业务规则: 标题最长 200 字符
    response = client.post("/projects", json={"title": "x" * 201})
    # 期望: 超长标题应该被拒绝
    assert response.status_code == 400  # 如果返回 201，说明代码有 bug
```

### 发现问题时的处理流程

```
测试失败
    │
    ├── 测试期望正确 (基于业务规则)
    │   └── → 修复代码，不改测试
    │
    └── 测试期望错误 (误解了业务规则)
        └── → 确认业务规则后修改测试
```

---

## 一、整体流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        完整闭环流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│   │  1.测试  │───▶│  2.监控  │───▶│  3.分析  │───▶│  4.修复  │ │
│   │   执行   │    │   报告   │    │   定位   │    │   验证   │ │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│        │                                               │        │
│        └───────────────── 回归测试 ◀──────────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.1 四个阶段说明

| 阶段 | 输入 | 输出 | 工具 |
|------|------|------|------|
| **测试执行** | 测试用例 | 测试结果 (Pass/Fail) | pytest + httpx |
| **监控报告** | 测试结果 | 问题清单 + 分类 | pytest-html + 自定义报告 |
| **分析定位** | 问题清单 | 根因分析 + 修复方案 | 日志分析 + 代码审查 |
| **修复验证** | 修复代码 | 回归测试通过 | pytest -k "specific_test" |

---

## 二、实施阶段规划

### Phase 1: 基础框架搭建 (当前)

**目标**: 搭建完整的测试 + 监控 + 报告框架

#### Step 1: 核心框架 ✅ 进行中

- [x] 创建目录结构
- [x] 实现 conftest.py (Token 刷新)
- [x] 实现 quick_verify.py (快速验证)
- [ ] 实现 base.py (基础测试类)
- [ ] 实现 helpers/assertions.py (自定义断言)
- [ ] 实现 helpers/security.py (安全测试 payload)

#### Step 2: 监控报告系统

- [ ] 实现 reporters/test_reporter.py (测试报告生成)
- [ ] 实现 reporters/issue_tracker.py (问题追踪)
- [ ] 配置 pytest-html 报告
- [ ] 创建问题模板 (ISSUE_TEMPLATE.md)

#### Step 3: 问题分析工具

- [ ] 实现 analyzers/log_analyzer.py (日志分析)
- [ ] 实现 analyzers/response_differ.py (响应对比)
- [ ] 创建问题分类标准

#### Step 4: 修复验证流程

- [ ] 实现 scripts/fix_and_verify.sh (修复后验证)
- [ ] 创建修复 checklist

### Phase 2: P0 接口测试

**目标**: 覆盖所有 P0 (核心+财务) 接口

- [ ] billing/test_credits.py
- [ ] billing/test_transactions.py
- [ ] payment/test_checkout.py
- [ ] projects/test_crud.py
- [ ] generate/test_images.py
- [ ] marketplace/test_purchase.py

### Phase 3: 监控与持续改进

**目标**: 建立持续监控机制

- [ ] CI/CD 集成
- [ ] 定时任务 (每日运行)
- [ ] 告警机制 (Slack/Email)
- [ ] 周报生成

---

## 三、详细实施步骤

### Step 1: 核心框架 (当前执行)

#### 1.1 需要创建的文件

```
tests/integration/staging/
├── base.py                    # 基础测试类
├── constants.py               # 常量定义
├── helpers/
│   ├── __init__.py
│   ├── assertions.py          # 自定义断言
│   ├── security.py            # 安全测试 payload
│   └── cleanup.py             # 数据清理
├── reporters/
│   ├── __init__.py
│   ├── test_reporter.py       # 测试报告
│   └── issue_tracker.py       # 问题追踪
└── analyzers/
    ├── __init__.py
    ├── log_analyzer.py        # 日志分析
    └── response_differ.py     # 响应对比
```

#### 1.2 执行顺序

```
1. base.py + constants.py     → 测试基础设施
2. helpers/*                  → 辅助工具
3. reporters/*                → 监控报告
4. analyzers/*                → 问题分析
5. 运行验证                    → 确认框架工作
```

---

## 四、监控报告系统设计

### 4.1 测试结果报告

每次测试运行后生成结构化报告:

```json
{
  "run_id": "20260118_034500",
  "timestamp": "2026-01-18T03:45:00Z",
  "environment": "staging",
  "summary": {
    "total": 100,
    "passed": 95,
    "failed": 4,
    "skipped": 1,
    "duration_seconds": 120
  },
  "failures": [
    {
      "test_id": "test_billing_credits::test_get_credits_success",
      "endpoint": "GET /api/v2/user/billing/credits",
      "expected": 200,
      "actual": 500,
      "error_message": "Internal server error",
      "response_body": "{...}",
      "category": "server_error",
      "priority": "P0",
      "first_seen": "2026-01-18T03:45:00Z",
      "occurrence_count": 1
    }
  ],
  "issues_created": ["ISSUE-001", "ISSUE-002"]
}
```

### 4.2 问题分类标准

| 分类 | 状态码 | 优先级 | 自动处理 |
|------|--------|--------|----------|
| **server_error** | 5xx | P0 | 立即告警 |
| **auth_failure** | 401/403 | P0 | 检查 token |
| **validation_error** | 400/422 | P1 | 记录日志 |
| **not_found** | 404 | P1 | 检查资源 |
| **rate_limit** | 429 | P2 | 等待重试 |
| **timeout** | - | P1 | 增加超时 |
| **schema_mismatch** | 200 但格式错 | P1 | 记录详情 |

### 4.3 问题追踪格式

```markdown
# ISSUE-001: GET /api/v2/user/resources 返回 500

## 基本信息
- **发现时间**: 2026-01-18 03:44:25
- **测试用例**: test_resources.py::test_list_resources
- **优先级**: P0 (server_error)
- **状态**: 待修复

## 问题描述
调用 GET /api/v2/user/resources 接口返回 500 Internal Server Error

## 请求信息
- **URL**: https://decodables-staging.up.railway.app/api/v2/user/resources
- **Method**: GET
- **Headers**: Authorization: Bearer ***
- **Params**: limit=5

## 响应信息
- **Status Code**: 500
- **Response Body**:
```json
{
  "code": "server_error",
  "message": "Internal server error. Please try again later.",
  "request_id": "1597d66f-0e45-48c2-94d6-b0dabfb67a3f"
}
```

## 根因分析
(待分析)

## 修复方案
(待确定)

## 修复验证
- [ ] 本地测试通过
- [ ] Staging 测试通过
- [ ] 相关测试用例通过
```

---

## 五、问题分析与修复流程

### 5.1 分析流程

```
发现问题
    │
    ▼
┌───────────────┐
│ 1. 查看响应体  │ ← 获取 error code, message, request_id
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ 2. 查询日志    │ ← 使用 request_id 在 Railway 日志中搜索
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ 3. 定位代码    │ ← 根据 endpoint 找到对应的 router/service
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ 4. 复现问题    │ ← 本地环境复现
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ 5. 编写修复    │ ← 修改代码
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ 6. 验证修复    │ ← 运行相关测试
└───────────────┘
```

### 5.2 修复验证 Checklist

```markdown
## 修复验证 Checklist

### 代码修改
- [ ] 修改的文件: _______________
- [ ] 修改行数: _______________
- [ ] 是否需要数据库变更: Yes / No
- [ ] 是否需要配置变更: Yes / No

### 本地验证
- [ ] 单元测试通过: `pytest tests/unit/xxx -v`
- [ ] 相关集成测试通过: `pytest tests/integration/staging/xxx -v`
- [ ] 手动测试通过

### 部署验证
- [ ] 代码已推送: `git push`
- [ ] Staging 部署成功
- [ ] Staging 测试通过: `python quick_verify.py --all`
- [ ] 原问题测试通过

### 回归验证
- [ ] P0 测试全部通过: `pytest -m p0`
- [ ] 无新增失败
```

---

## 六、当前待执行任务

### 立即执行: Step 1 - 核心框架

按以下顺序创建文件:

#### Task 1.1: 创建 base.py
```
文件: tests/integration/staging/base.py
内容: 基础测试类 + 通用断言 + 标准测试模式
```

#### Task 1.2: 创建 constants.py
```
文件: tests/integration/staging/constants.py
内容: URL、状态码、错误消息常量
```

#### Task 1.3: 创建 helpers/
```
文件:
- helpers/__init__.py
- helpers/assertions.py (自定义断言)
- helpers/security.py (安全测试 payload)
- helpers/cleanup.py (数据清理)
```

#### Task 1.4: 创建 reporters/
```
文件:
- reporters/__init__.py
- reporters/test_reporter.py (测试报告生成器)
- reporters/issue_tracker.py (问题追踪器)
```

#### Task 1.5: 创建第一个完整测试模块
```
文件: billing/test_credits.py
内容: GET /api/v2/user/billing/credits 的完整测试
```

#### Task 1.6: 运行验证
```bash
# 验证框架工作
pytest tests/integration/staging/billing/test_credits.py -v --html=report.html
```

---

## 七、执行记录

### 2026-01-18 执行记录

| 时间 | 任务 | 状态 | 备注 |
|------|------|------|------|
| 03:40 | 创建 quick_verify.py | ✅ 完成 | |
| 03:44 | 运行首次测试 | ✅ 完成 | 发现 /resources 500 错误 |
| 03:50 | 创建测试方案文档 | ✅ 完成 | API-TESTING-PLAN.md |
| 04:00 | 创建实施文档 | ✅ 完成 | 本文档 |
| 04:05 | Task 1.1 base.py | ✅ 完成 | 基础测试类 + 通用断言 |
| 04:05 | Task 1.2 constants.py | ✅ 完成 | 端点/状态码/常量定义 |
| 04:05 | Task 1.3 helpers/* | ✅ 完成 | assertions.py, security.py, cleanup.py |
| 04:05 | Task 1.4 reporters/* | ✅ 完成 | test_reporter.py, issue_tracker.py |
| 04:10 | Task 1.5 billing/test_credits.py | ✅ 完成 | 20 个黑盒测试用例 |
| 04:15 | Task 1.6 运行验证 | ✅ 完成 | 20 passed in 15s |

### 已发现问题

| ID | 接口 | 状态码 | 优先级 | 状态 |
|----|------|--------|--------|------|
| ISSUE-001 | GET /api/v2/user/resources | 500 | P0 | ⏳ 分析中 |

---

## 八、下一步行动

**Phase 1 Step 1 完成 ✅**

**已完成**:
1. ✅ 所有 Task 1.x 文件创建完成
2. ✅ `pytest tests/integration/staging/billing/test_credits.py -v` 通过 (20/20)
3. ✅ conftest.py 配置完善 (auth_client, anon_client, 自定义标记)

**下一步**:
1. 分析并修复 ISSUE-001 (/resources 500 错误)
2. 继续 Phase 2: P0 接口测试 (projects, generate, payment 等)

---

**文档版本**: v1.1
**最后更新**: 2026-01-18 04:15
