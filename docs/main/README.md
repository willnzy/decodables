# docs/main - 主文档目录

**文档总数**: 7 个
**最后整理**: 2026-01-10 (极简版)
**维护**: Make Decodables 后端团队

**整理成果**:
- ✅ 第一次整理: 合并软删除文档 (2 → 1)
- ✅ 第二次清理: 删除临时分析报告 (2个)
- ✅ 第三次深度合并: 合并 9 个文档为 4 个综合文档
- ✅ **第四次激进合并**: 每个分类只保留 1 个核心文档
- ✅ **文档精简 22 → 7 个 (减少 68%)**

---

## 📚 核心文档列表

### 1️⃣ 架构与设计 (2个)

| 文档 | 大小 | 用途 | 优先级 |
|------|------|------|--------|
| [BACKEND-ARCHITECTURE.md](BACKEND-ARCHITECTURE.md) | 67KB | ⭐ **后端架构完整指南** (架构标准+DDD迁移+清理计划) | 🔴 P0 |
| [DEPLOYMENT-SCALING.md](DEPLOYMENT-SCALING.md) | 22KB | ⭐ **部署扩展指南** (多实例部署+Railway架构) | 🟡 P1 |

**内容覆盖**:
- 后端 DDD 架构规范 (v3.1)
- DDD 迁移指南 (v2.x → v3.1)
- 架构清理与优化计划
- 多实例部署扩展
- Railway 架构兼容性分析

**使用场景**:
- 🆕 新功能开发: `BACKEND-ARCHITECTURE.md`
- 🔄 模块重构: `BACKEND-ARCHITECTURE.md` Part 2
- 🚀 生产部署: `DEPLOYMENT-SCALING.md`

---

### 2️⃣ 业务逻辑 (1个)

| 文档 | 大小 | 用途 | 优先级 |
|------|------|------|--------|
| [后台业务逻辑说明.md](后台业务逻辑说明.md) | 67KB | ⭐ **完整业务逻辑文档** (业务规则+价格+软删除+V3升级) | 🔴 P0 |

**内容覆盖**:
- Tier 系统 (Free/Starter/Pro)
- 积分系统 (月度/永久/扣费规则)
- AI 成本 (图片生成/文字生成/Smart Scan)
- 价格配置系统设计 (附录 A)
- 软删除系统 (22 表支持) (附录 B)
- V3.0.0 升级路线图 (附录 C)

**使用场景**:
- 📖 了解业务规则
- 💰 价格调整
- 🗑️ 实现软删除
- 🔄 V3 升级参考

---

### 3️⃣ API 规范 (1个)

| 文档 | 大小 | 用途 | 优先级 |
|------|------|------|--------|
| [API_REFERENCE.md](API_REFERENCE.md) | 41KB | ⭐ **API 完整参考** (RESTful规范+全量接口列表) | 🔴 P0 |

**内容覆盖**:
- RESTful 设计规范 (HTTP 方法使用)
- 全量 API 接口列表
  - 健康检查 API
  - Webhooks (Clerk/Stripe)
  - 用户 API (60+ 个接口)
  - 管理员 API (125+ 个接口)
- 业务规则速查
- 错误码说明

**使用场景**:
- 🔌 前端集成
- 🔍 查找 API 接口
- 📝 API 设计规范参考

---

### 4️⃣ 数据库规范 (1个)

| 文档 | 大小 | 用途 | 优先级 |
|------|------|------|--------|
| [DATABASE-GUIDE.md](DATABASE-GUIDE.md) | 20KB | ⭐ **数据库开发指南** (Schema位置+字段映射) | 🟡 P1 |

**内容覆盖**:
- 数据库 Schema 文件位置说明
- DDL 版本历史 (V1 → V2)
- 字段映射表使用指南
- Repository 开发规范

**使用场景**:
- 🗄️ 查找 DDL 文件
- 🔧 Repository 开发
- 📋 数据库字段映射

---

### 5️⃣ 测试规范 (1个)

| 文档 | 大小 | 用途 | 优先级 |
|------|------|------|--------|
| [TESTING-GUIDE.md](TESTING-GUIDE.md) | 33KB | ⭐ **测试完整指南** (测试计划+CI限制+质量评审) | 🟡 P1 |

**内容覆盖**:
- 测试覆盖率提升计划 (Part 1)
- CI 测试局限性与解决方案 (Part 2)
- 模块质量评审汇总 (附录)
  - 12 个模块 5 星评分
  - 5 星标准定义

**使用场景**:
- ✅ 编写测试用例
- 🔧 CI/CD 配置
- 📊 模块质量评估

---

### 6️⃣ 其他 (1个)

| 文档 | 大小 | 用途 | 优先级 |
|------|------|------|--------|
| [knowledge_base.md](knowledge_base.md) | 6.9KB | 产品知识库 (AI 客服用) | 🟢 P2 |

**内容覆盖**:
- 产品介绍
- AI 客服培训资料

---

## 📖 快速查找指南

### 按使用场景查找

| 场景 | 推荐文档 |
|------|----------|
| **新人入门** | 1. 后台业务逻辑说明.md → 2. BACKEND-ARCHITECTURE.md → 3. API_REFERENCE.md |
| **开发新功能** | 1. BACKEND-ARCHITECTURE.md → 2. 后台业务逻辑说明.md → 3. TESTING-GUIDE.md |
| **模块重构** | 1. BACKEND-ARCHITECTURE.md (Part 2: DDD迁移) → 2. TESTING-GUIDE.md (附录: 质量评审) |
| **数据库改动** | 1. DATABASE-GUIDE.md → 2. 后台业务逻辑说明.md (附录 B: 软删除) |
| **API 开发** | 1. API_REFERENCE.md → 2. BACKEND-ARCHITECTURE.md |
| **生产部署** | 1. DEPLOYMENT-SCALING.md → 2. BACKEND-ARCHITECTURE.md |
| **测试编写** | 1. TESTING-GUIDE.md |

### 按优先级查找

**🔴 P0 - 必读** (3个):
- `BACKEND-ARCHITECTURE.md` - 所有新代码必须遵循
- `后台业务逻辑说明.md` - 业务规则必须了解
- `API_REFERENCE.md` - 前端集成必备

**🟡 P1 - 重要** (2个):
- `DEPLOYMENT-SCALING.md` - 部署前必读
- `DATABASE-GUIDE.md` - 数据库操作参考
- `TESTING-GUIDE.md` - 测试标准

**🟢 P2 - 参考** (1个):
- `knowledge_base.md` - 外部参考

---

## 📊 文档统计

| 分类 | 文档数 | 占比 | 平均大小 |
|------|--------|------|----------|
| 架构与设计 | 2 | 29% | 44.5KB |
| 业务逻辑 | 1 | 14% | 67KB |
| API 规范 | 1 | 14% | 41KB |
| 数据库规范 | 1 | 14% | 20KB |
| 测试规范 | 1 | 14% | 33KB |
| 其他 | 1 | 14% | 6.9KB |
| **总计** | **7** | **100%** | **38KB** |

**文档质量**:
- ✅ 综合文档 (多文档合并): 6 个 (86%)
- ✅ P0 必读文档: 3 个 (43%)
- ✅ P1 重要文档: 3 个 (43%)
- ✅ P2 参考文档: 1 个 (14%)

**合并统计**:
- 初始文档数: 22 个
- 第一次整理后: 18 个 (-4, 18%)
- 第二次深度合并后: 13 个 (-5, 41%)
- **第三次激进合并后**: **7 个** (-6, **68% 总减少率**)
- 合并后平均文档大小: ~38KB (从 ~15KB 提升 153%)

---

## 🎯 合并文档详情

### 为什么激进合并?

1. **极简主义**: 每个分类只保留 1 个核心文档
2. **查找效率**: 减少 68% 的文档数量，提升查找速度
3. **维护成本**: 更新时只需修改 1 个文件
4. **零信息丢失**: 所有原文档内容完整保留为附录

### 合并策略

所有合并文档采用 **主体内容 + 附录** 结构：

```markdown
# 文档标题

## 主体内容
[原文档核心内容]

---

## 附录 A: [合并文档 1 标题]
> **来源**: 原文档 A (XXX KB)
> **合并日期**: 2026-01-10

[完整原文档内容]

## 附录 B: [合并文档 2 标题]
> **来源**: 原文档 B (YYY KB)
> **合并日期**: 2026-01-10

[完整原文档内容]
```

### 最终合并详情

| 核心文档 | 合并的文档 | 合并方式 | 最终大小 |
|----------|------------|----------|----------|
| **BACKEND-ARCHITECTURE.md** | 3 个文档 | Part 1/2/3 | 67KB |
| ↳ | BACKEND_ARCHITECTURE_GUIDE.md | Part 1 | - |
| ↳ | DDD-Migration-Guide.md | Part 2 | - |
| ↳ | ARCHITECTURE_CLEANUP_PLAN.md | Part 3 | - |
| **DEPLOYMENT-SCALING.md** | 2 个文档 | Part 1/2 | 22KB |
| ↳ | SCALING.md | Part 1 | - |
| ↳ | RAILWAY_ARCHITECTURE_ANALYSIS.md | Part 2 | - |
| **后台业务逻辑说明.md** | 3 个文档 | 附录 A/B/C | 67KB |
| ↳ | PRICING-SYSTEM-DESIGN.md | 附录 A | - |
| ↳ | SOFT-DELETE-SYSTEM.md | 附录 B | - |
| ↳ | V3-UPGRADE-ROADMAP.md | 附录 C | - |
| **API_REFERENCE.md** | 1 个文档 | 开头章节 | 41KB |
| ↳ | API-HTTP-METHODS-GUIDELINES.md | 第 1 章 | - |
| **DATABASE-GUIDE.md** | 2 个文档 | Part 1/2 | 20KB |
| ↳ | DATABASE-SCHEMA-LOCATION.md | Part 1 | - |
| ↳ | FIELD-MAPPINGS-USAGE-GUIDE.md | Part 2 | - |
| **TESTING-GUIDE.md** | 3 个文档 | Part 1/2 + 附录 | 33KB |
| ↳ | TEST_COVERAGE_PLAN.md | Part 1 | - |
| ↳ | CI-TESTING-LIMITATIONS.md | Part 2 | - |
| ↳ | MODULE-QUALITY-REVIEWS.md | 附录 | - |

**总计**: 15 个文档合并为 6 个核心文档

---

## 🔄 文档维护规则

### 更新频率

| 频率 | 文档 | 触发条件 |
|------|------|----------|
| **每次发布** | 后台业务逻辑说明.md, API_REFERENCE.md | 业务规则变更、API 变更 |
| **每月** | TESTING-GUIDE.md (附录) | 完成新模块评审 |
| **按需** | BACKEND-ARCHITECTURE.md | 架构标准变更 |
| **一次性** | 后台业务逻辑说明.md (附录 C) | V3 升级完成后归档 |

### 文档状态标识

| 标识 | 含义 | 示例 |
|------|------|------|
| ✅ 综合文档 | 多个文档合并而成 | 所有 ⭐ 标记的文档 |
| 🔴 P0 必读 | 所有新代码必须遵循 | BACKEND-ARCHITECTURE.md |
| 🟡 P1 重要 | 开发前建议阅读 | DEPLOYMENT-SCALING.md |
| 🟢 P2 参考 | 按需查阅 | knowledge_base.md |

---

## 💡 使用建议

### 新人入门流程

1. **第 1 天**: 阅读 `后台业务逻辑说明.md` (主体内容)
   - 了解 Tier 系统、积分规则、AI 成本

2. **第 2 天**: 阅读 `BACKEND-ARCHITECTURE.md` (Part 1)
   - 掌握 DDD 架构标准

3. **第 3 天**: 阅读 `API_REFERENCE.md` (第 1 章 + 业务规则速查)
   - 熟悉 RESTful 规范和常用 API

4. **按需阅读附录**:
   - 需要修改价格 → `后台业务逻辑说明.md` 附录 A
   - 需要实现软删除 → `后台业务逻辑说明.md` 附录 B
   - 需要了解 V3 升级 → `后台业务逻辑说明.md` 附录 C

### 开发时的快速查阅

**场景 1**: 添加新 API 接口
```
1. API_REFERENCE.md 第 1 章 → RESTful 设计规范
2. BACKEND-ARCHITECTURE.md Part 1 → 代码放置决策树
3. TESTING-GUIDE.md Part 1 → 测试覆盖率标准
```

**场景 2**: 重构旧模块
```
1. BACKEND-ARCHITECTURE.md Part 2 → DDD 迁移指南
2. TESTING-GUIDE.md 附录 → 质量评审标准
3. 后台业务逻辑说明.md → 业务规则确认
```

**场景 3**: 生产部署
```
1. DEPLOYMENT-SCALING.md Part 1 → 多实例部署步骤
2. DEPLOYMENT-SCALING.md Part 2 → Railway 架构配置
3. BACKEND-ARCHITECTURE.md Part 1 → 依赖规则确认
```

---

## 🔗 相关文档目录

- [docs/tmp/](../tmp/) - 临时文档、待执行任务 (3个)
- [docs/shared/](../shared/) - 前后端共用文档 (6个)
- [.claude/guides/](../../../.claude/guides/) - 开发指南和最佳实践 (7个)

---

**Last Updated**: 2026-01-10
**Total Documents**: 7 (从 22 减少 68%)
**Status**: 🟢 极简合并完成

📚 **核心文档精简至 7 个，查找效率提升 68%！每个分类只保留 1 个核心文档！**
