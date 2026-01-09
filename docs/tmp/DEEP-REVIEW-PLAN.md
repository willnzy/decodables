# Admin API 深度审查执行计划

## 审查目标

对所有 125 个 Admin API 接口进行逐个、仔细、全面、深入的 review，确保：

1. **代码规范合规性**: 符合项目规范、系统架构、业务逻辑和业界最佳实践
2. **调用链完整性**: 完整审查所有调用链 (API → Handler → Service → Repository)，检查逻辑遗漏或错误
3. **测试覆盖完整性**: 测试覆盖全部业务逻辑，包括边界情况和异常情况
4. **文档同步准确性**: 所有状态和关键记录同步到文档

---

## 审查标准

### 1. 接口层面审查 (API Endpoint)

- [ ] **路由定义正确性**
  - HTTP 方法符合 RESTful 规范
  - 路径参数命名清晰
  - Query 参数有默认值和验证

- [ ] **安全性检查**
  - ✅ Rate limiting (`@limiter.limit()`)
  - ✅ Admin 认证 (`admin: dict = Depends(require_admin)`)
  - ✅ 输入验证 (Pydantic model + Field validation)
  - ✅ 输出清理 (不暴露敏感错误信息)

- [ ] **DDD 架构合规性**
  - API 层只调用 Service/Repository，不直接操作数据库
  - 使用 Domain Entity 而非 dict (如有)
  - 错误处理统一 (HTTPException)

### 2. 调用链审查 (Call Chain)

**标准调用链**: API → Repository → Database

检查点:
- [ ] Repository 方法是否存在
- [ ] 参数传递是否完整
- [ ] 返回值处理是否正确
- [ ] 异常是否正确传播

### 3. Request Model 审查

- [ ] **字段验证完整性**
  - 必填字段 (`...`)
  - 字段长度限制 (`min_length`, `max_length`)
  - 数值范围限制 (`ge`, `le`)
  - 枚举验证 (`@field_validator`)

- [ ] **业务规则正确性**
  - 符合业务逻辑 (如 tier 只能是 free/starter/pro)
  - 边界值合理 (如 max_length=100 对 uid)

### 4. 测试覆盖审查

每个接口必须有以下测试:

- [ ] **基本功能测试**
  - 成功场景 (happy path)
  - 返回值结构正确

- [ ] **认证测试**
  - 未登录返回 401
  - 非 admin 返回 403

- [ ] **输入验证测试**
  - 必填字段缺失
  - 字段长度超限
  - 枚举值非法
  - 数值范围超限

- [ ] **边界情况测试**
  - 空列表
  - 分页边界 (offset=0, limit=max)
  - 极限值 (max_length-1, max_length, max_length+1)

- [ ] **异常情况测试**
  - 数据库错误
  - 第三方服务失败 (Stripe, Supabase)
  - 资源不存在 (404)
  - 权限不足 (403)

### 5. 错误处理审查

- [ ] **错误日志记录**
  - 使用 `logger.error()` 记录详细错误
  - 日志包含足够的上下文信息

- [ ] **错误信息清理**
  - 用户看到的错误信息通用化
  - 不暴露内部实现细节
  - 不暴露敏感信息 (API keys, internal paths)

---

## 审查顺序 (按业务优先级)

### 阶段 1: 核心业务模块 (高风险)

1. **Subscriptions (3个)** - 涉及支付和订阅
2. **AI (9个)** - 涉及积分扣费
3. **Stats (18个)** - 核心数据展示

### 阶段 2: 用户管理模块 (已初步审查)

4. **Users (13个)** - 重新深度审查
5. **Tasks Management (4个)** - 重新深度审查
6. **Health (2个)** - 重新深度审查

### 阶段 3: 配置和管理模块

7. **System (11个)** - 系统配置
8. **Config (9个)** - 配置管理
9. **Experiments (14个)** - Feature flags

### 阶段 4: 数据和通知模块

10. **Events (9个)** - 事件追踪
11. **Logs (4个)** - 日志查询
12. **Metrics (7个)** - 指标统计
13. **Notifications (5个)** - 通知管理
14. **Campaigns (9个)** - 营销活动

### 阶段 5: 内容审核模块

15. **Moderation (10个)** - 内容审核

---

## 审查流程 (每个接口)

### Step 1: 读取源代码

```bash
# 读取 API 文件
Read api/admin/{module}.py

# 读取对应的 Repository (如有)
Read infrastructure/repositories/{module}_repository.py

# 读取对应的 Service (如有)
Read domains/{domain}/{module}_service.py
```

### Step 2: 调用链验证

绘制调用链图:
```
API Endpoint
  ↓ (调用)
Repository Method / Service Method
  ↓ (调用)
Database / External Service
```

检查:
- 方法是否存在
- 参数是否匹配
- 返回值是否正确处理
- 异常是否正确处理

### Step 3: 测试覆盖验证

```bash
# 读取测试文件
Read tests/api/admin/test_{module}.py

# 统计测试用例
grep "async def test_" tests/api/admin/test_{module}.py | wc -l

# 运行测试
pytest tests/api/admin/test_{module}.py -v
```

检查:
- 每个接口是否都有测试
- 是否覆盖所有验证规则
- 是否测试边界情况
- 是否测试异常情况

### Step 4: 发现问题并修复

如果发现问题:
1. 记录问题 (在审查报告中)
2. 修复代码
3. 补充测试
4. 重新运行测试验证

### Step 5: 更新文档

在 `API-REVIEW-ADMIN.md` 中更新:
- 审查状态 (✅ 深度审查完成)
- 发现的问题
- 修复的内容
- 测试覆盖情况

---

## 输出文档

### 1. 审查报告 (每个模块)

文件: `docs/tmp/REVIEW-{MODULE}.md`

内容:
```markdown
# {MODULE} 模块深度审查报告

## 审查信息
- 审查人: Claude Code
- 审查时间: {timestamp}
- 接口数量: {count}

## 调用链分析

### 接口 1: {endpoint}
- 调用链: API → {service/repo} → {db/external}
- 参数验证: ✅ / ⚠️ / ❌
- 错误处理: ✅ / ⚠️ / ❌
- 测试覆盖: {count} tests

### 接口 2: ...

## 发现的问题

| 严重性 | 问题描述 | 影响 | 修复状态 |
|--------|----------|------|----------|
| 🔴 HIGH | ... | ... | ✅ / 🔧 / ❌ |

## 测试覆盖统计

- 总测试数: {total}
- 基本功能: {count}
- 边界测试: {count}
- 异常测试: {count}

## 审查结论

✅ 通过 / ⚠️ 有问题但已修复 / ❌ 有严重问题
```

### 2. 总体进度跟踪

更新 `API-REVIEW-ADMIN.md`:
- 进度百分比
- 审查质量等级 (⭐⭐⭐⭐⭐ 深度审查 vs ⭐⭐⭐ 批量审查)

---

## 时间估算

- 每个接口深度审查: 15-20 分钟
- 总接口数: 125 个
- 预计总时间: 31-42 小时

**分批执行**:
- 每批 10-15 个接口
- 每批约 3-5 小时
- 总共 8-10 批

---

## 开始执行

现在开始第一批: **Subscriptions 模块 (3个接口)** - 最高优先级

下一步: 读取 `api/admin/subscriptions.py` 并开始逐接口审查。
