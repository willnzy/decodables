# docs/main - 主文档目录

**文档总数**: 20 个
**最后整理**: 2026-01-10
**维护**: Make Decodables 后端团队

---

## 📚 文档分类索引

### 1️⃣ 架构与设计规范 (6个) - [architecture/](architecture/)

**用途**: 系统架构设计、开发规范、迁移指南

| 文档 | 版本 | 用途 | 优先级 |
|------|------|------|--------|
| [BACKEND_ARCHITECTURE_GUIDE.md](architecture/BACKEND_ARCHITECTURE_GUIDE.md) | v3.1 | ⭐ **后端架构标准规范** (所有新代码必须遵循) | 🔴 P0 |
| [DDD-Migration-Guide.md](architecture/DDD-Migration-Guide.md) | 1.1.0 | DDD 迁移指南 (v2.x → v3.1) | 🟡 P1 |
| [ARCHITECTURE_CLEANUP_PLAN.md](architecture/ARCHITECTURE_CLEANUP_PLAN.md) | - | 架构清理与优化计划 (健康度 95/100) | 🟢 P2 |
| [RAILWAY_ARCHITECTURE_ANALYSIS.md](architecture/RAILWAY_ARCHITECTURE_ANALYSIS.md) | - | Railway 多服务架构兼容性分析 | 🟢 P2 |
| [SCALING.md](architecture/SCALING.md) | - | 多实例部署扩展指南 | 🟢 P2 |
| [API-HTTP-METHODS-GUIDELINES.md](architecture/API-HTTP-METHODS-GUIDELINES.md) | - | RESTful API 设计规范 - HTTP 方法使用 | 🟡 P1 |

**使用场景**:
- 🆕 新功能开发前必读: `BACKEND_ARCHITECTURE_GUIDE.md`
- 🔄 模块重构: `DDD-Migration-Guide.md`
- 🚀 生产部署: `SCALING.md`, `RAILWAY_ARCHITECTURE_ANALYSIS.md`

---

### 2️⃣ 业务逻辑与 API (3个)

**用途**: 业务规则、API 接口文档、定价系统

| 文档 | 版本 | 用途 | 更新频率 |
|------|------|------|----------|
| [后台业务逻辑说明.md](后台业务逻辑说明.md) | v3.3.0 | ⭐ **完整业务逻辑文档** (Tier/积分/AI 成本) | 🔴 高频更新 |
| [API_REFERENCE.md](API_REFERENCE.md) | v3.24 | API 接口参考文档 (供前端重构参考) | 🟡 中频更新 |
| [PRICING-SYSTEM-DESIGN.md](PRICING-SYSTEM-DESIGN.md) | 1.0.0 | 价格配置系统设计 (Stripe + Config) | 🟢 低频更新 |

**使用场景**:
- 📖 了解业务规则: `后台业务逻辑说明.md`
- 🔌 前端集成: `API_REFERENCE.md`
- 💰 价格调整: `PRICING-SYSTEM-DESIGN.md`

---

### 3️⃣ 质量保障与测试 (4个)

**用途**: 质量评审、测试覆盖、CI/CD 限制

| 文档 | 版本 | 用途 | 状态 |
|------|------|------|------|
| [MODULE-QUALITY-REVIEWS.md](MODULE-QUALITY-REVIEWS.md) | - | ⭐ **模块质量评审汇总** (12 模块 5 星评分) | ✅ 持续更新 |
| [5-STAR-REVIEW-PLAN.md](5-STAR-REVIEW-PLAN.md) | - | 5 星标准 Review 计划 | ✅ 执行中 |
| [TEST_COVERAGE_PLAN.md](TEST_COVERAGE_PLAN.md) | 2.0 | 测试覆盖率提升计划 (DDD 架构) | ✅ 执行中 |
| [CI-TESTING-LIMITATIONS.md](CI-TESTING-LIMITATIONS.md) | - | CI 测试局限性和解决方案 | 📝 参考 |

**使用场景**:
- 📊 模块质量评估: `MODULE-QUALITY-REVIEWS.md`
- ✅ 编写测试: `TEST_COVERAGE_PLAN.md`
- 🔍 质量评审: `5-STAR-REVIEW-PLAN.md`

---

### 4️⃣ 功能系统文档 (4个)

**用途**: 专项功能系统的完整设计与实现

| 文档 | 版本 | 用途 | 状态 |
|------|------|------|------|
| [SOFT-DELETE-SYSTEM.md](SOFT-DELETE-SYSTEM.md) | v3.0 | ⭐ **软删除系统完整文档** (22 表支持) | ✅ 生产就绪 |
| [SOFT-DELETE-HISTORY.md](SOFT-DELETE-HISTORY.md) | - | 软删除系统实施历史 (5 commits) | 📝 历史记录 |
| [V3-UPGRADE-ROADMAP.md](V3-UPGRADE-ROADMAP.md) | - | V3.0.0 升级路线图 (8 模块已完成) | ✅ 全部完成 |
| [FIELD-MAPPINGS-USAGE-GUIDE.md](FIELD-MAPPINGS-USAGE-GUIDE.md) | 1.0.0 | 字段映射表使用指南 | 📝 工具文档 |

**使用场景**:
- 🗑️ 实现软删除: `SOFT-DELETE-SYSTEM.md`
- 🔄 V3 升级: `V3-UPGRADE-ROADMAP.md` (已完成)
- 🔧 Repository 开发: `FIELD-MAPPINGS-USAGE-GUIDE.md`

---

### 5️⃣ 数据库与基础设施 (2个)

**用途**: 数据库 Schema、DDL 管理

| 文档 | 版本 | 用途 | 状态 |
|------|------|------|------|
| [DATABASE-SCHEMA-LOCATION.md](DATABASE-SCHEMA-LOCATION.md) | - | 数据库 Schema 文件位置说明 (V1→V2) | 📝 迁移说明 |
| [knowledge_base.md](knowledge_base.md) | - | 产品知识库 (AI 客服用) | 📝 外部参考 |

**使用场景**:
- 🗄️ 查找 DDL 文件: `DATABASE-SCHEMA-LOCATION.md`
- 🤖 AI 客服培训: `knowledge_base.md`

---

## 📖 快速查找指南

### 按使用场景查找

| 场景 | 推荐文档 |
|------|----------|
| **新人入门** | 1. 后台业务逻辑说明.md → 2. BACKEND_ARCHITECTURE_GUIDE.md → 3. API_REFERENCE.md |
| **开发新功能** | 1. BACKEND_ARCHITECTURE_GUIDE.md → 2. 后台业务逻辑说明.md → 3. TEST_COVERAGE_PLAN.md |
| **模块重构** | 1. DDD-Migration-Guide.md → 2. MODULE-QUALITY-REVIEWS.md → 3. 5-STAR-REVIEW-PLAN.md |
| **数据库改动** | 1. DATABASE-SCHEMA-LOCATION.md → 2. SOFT-DELETE-SYSTEM.md |
| **API 设计** | 1. API-HTTP-METHODS-GUIDELINES.md → 2. API_REFERENCE.md → 3. BACKEND_ARCHITECTURE_GUIDE.md |
| **生产部署** | 1. SCALING.md → 2. RAILWAY_ARCHITECTURE_ANALYSIS.md → 3. BACKEND_ARCHITECTURE_GUIDE.md |

### 按优先级查找

**🔴 P0 - 必读**:
- `BACKEND_ARCHITECTURE_GUIDE.md` - 所有新代码必须遵循
- `后台业务逻辑说明.md` - 业务规则必须了解
- `MODULE-QUALITY-REVIEWS.md` - 代码质量标准

**🟡 P1 - 重要**:
- `DDD-Migration-Guide.md` - 重构时必读
- `API_REFERENCE.md` - 前端集成参考
- `TEST_COVERAGE_PLAN.md` - 测试标准

**🟢 P2 - 参考**:
- `SOFT-DELETE-SYSTEM.md` - 删除功能参考
- `SCALING.md` - 扩展性参考
- `CI-TESTING-LIMITATIONS.md` - 测试局限性

---

## 🔄 文档维护规则

### 更新频率

| 频率 | 文档 | 触发条件 |
|------|------|----------|
| **每次发布** | 后台业务逻辑说明.md, API_REFERENCE.md | 业务规则变更、API 变更 |
| **每月** | MODULE-QUALITY-REVIEWS.md | 完成新模块评审 |
| **按需** | BACKEND_ARCHITECTURE_GUIDE.md | 架构标准变更 |
| **一次性** | SOFT-DELETE-HISTORY.md, V3-UPGRADE-ROADMAP.md | 项目完成后归档 |

### 文档状态标识

| 标识 | 含义 | 示例 |
|------|------|------|
| ✅ 生产就绪 | 已完成且在生产环境使用 | SOFT-DELETE-SYSTEM.md |
| 📝 执行中 | 正在执行或持续更新 | TEST_COVERAGE_PLAN.md |
| 📚 标准规范 | 长期有效的标准文档 | BACKEND_ARCHITECTURE_GUIDE.md |
| 📖 历史记录 | 已完成项目的历史记录 | SOFT-DELETE-HISTORY.md |

### 过期文档处理

**原则**: docs/main/ 只保留**长期有效**的文档

**过期标准**:
- ❌ 临时执行计划 → 移到 docs/tmp/
- ❌ 一次性任务记录 → 提取关键结论后归档
- ❌ 过时的技术方案 → 删除或更新

**归档流程**:
```
1. 识别过期文档
2. 提取关键结论到相关标准文档
3. 移动到 docs/archive/ (如需保留)
4. 或直接删除 (临时文档)
```

---

## 📊 文档统计

| 分类 | 文档数 | 占比 |
|------|--------|------|
| 架构与设计规范 | 6 | 30% |
| 业务逻辑与 API | 3 | 15% |
| 质量保障与测试 | 4 | 20% |
| 功能系统文档 | 4 | 20% |
| 数据库与基础设施 | 2 | 10% |
| **总计** | **20** | **100%** |

**文档质量**:
- ✅ 标准规范文档: 6 个 (30%)
- ✅ 生产就绪文档: 5 个 (25%)
- 📝 执行中文档: 3 个 (15%)
- 📖 历史记录文档: 2 个 (10%)
- 📚 参考文档: 4 个 (20%)

---

## 🎯 下一步优化建议

### 短期 (1-2 周)

1. **创建子目录分类** (可选):
   ```
   docs/main/
   ├── architecture/      # 架构与设计
   ├── business/          # 业务逻辑
   ├── quality/           # 质量保障
   ├── systems/           # 功能系统
   └── infrastructure/    # 基础设施
   ```

2. **更新过时内容**:
   - ✅ V3-UPGRADE-ROADMAP.md - 标记为"已完成"状态
   - ⚠️ API_REFERENCE.md - 检查是否与最新代码同步

3. **补充缺失文档**:
   - 📝 创建 `DEPLOYMENT-GUIDE.md` (部署流程)
   - 📝 创建 `TROUBLESHOOTING.md` (常见问题排查)

### 中期 (1 个月)

1. **文档自动化**:
   - API_REFERENCE.md 自动生成 (OpenAPI/Swagger)
   - 测试覆盖率自动更新

2. **质量检查**:
   - 定期检查文档与代码同步性
   - 删除不再使用的文档

---

## 🔗 相关文档目录

- [docs/tmp/](../tmp/) - 临时文档、待执行任务
- [docs/shared/](../shared/) - 前后端共用文档
- [.claude/guides/](../../../.claude/guides/) - 开发指南和最佳实践

---

**Last Updated**: 2026-01-10
**Total Documents**: 20
**Status**: 🟢 已分类整理

📚 **所有核心文档已完整归类，方便快速查找！**
