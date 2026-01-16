# 文档命名规范 (Documentation Naming Conventions)

**版本**: v1.0
**更新日期**: 2026-01-11
**适用范围**: `decodables/docs/` 所有文档

---

## 📋 目录

1. [核心规则](#核心规则)
2. [命名格式](#命名格式)
3. [文档类型后缀](#文档类型后缀)
4. [状态前缀](#状态前缀)
5. [示例对照表](#示例对照表)
6. [特殊规则](#特殊规则)

---

## 核心规则

### 1. 统一使用 **小写 + 连字符 (kebab-case)**

```
✅ 正确: api-reference.md
✅ 正确: backend-architecture.md
✅ 正确: user-id-system.md

❌ 错误: API_REFERENCE.md (大写 + 下划线)
❌ 错误: Canvas-Data-Schema.md (驼峰)
❌ 错误: knowledge_base.md (小写 + 下划线)
```

**例外**: `README.md` 全大写（业界惯例）

---

### 2. 统一使用 **英文命名**

```
✅ 正确: backend-business-logic.md
❌ 错误: 后台业务逻辑说明.md
```

**原因**:
- 跨平台兼容性（Windows/Linux/macOS）
- 避免编码问题
- 便于命令行操作
- 国际化团队协作

---

### 3. 统一使用 **连字符 `-`** 分隔单词

```
✅ 正确: asset-category-design.md
❌ 错误: asset_category_design.md (下划线)
❌ 错误: AssetCategoryDesign.md (驼峰)
```

---

### 4. 状态前缀使用 **方括号 `[status]`**

```
✅ 正确: [archived]old-design.md
✅ 正确: [wip]refactoring-plan.md
✅ 正确: [draft]new-feature.md

❌ 错误: [重构后]Asset-Category-System-Design.md (中文前缀)
❌ 错误: WIP-refactoring-plan.md (无方括号)
```

---

## 命名格式

### 标准格式

```
{prefix}-{module}-{type}.md
```

**组成部分**:

| 部分 | 必选 | 说明 | 示例 |
|------|------|------|------|
| `prefix` | 可选 | 状态前缀（方括号） | `[archived]`, `[wip]`, `[draft]` |
| `module` | 必选 | 模块/功能名称 | `api`, `database`, `asset-category` |
| `type` | 必选 | 文档类型 | `reference`, `guide`, `design` |

**示例**:

```
api-reference.md                    # 无前缀，正式文档
backend-architecture.md             # 无前缀，正式文档
[archived]api-db-audit-2026-01-10.md # 有前缀，已归档
[wip]admin-api-review.md            # 有前缀，进行中
```

---

## 文档类型后缀

| 类型 | 后缀 | 说明 | 示例 |
|------|------|------|------|
| **指南** | `-guide.md` | 操作指南、开发指南 | `database-guide.md`, `testing-guide.md` |
| **参考** | `-reference.md` | API 参考、规范参考 | `api-reference.md` |
| **设计** | `-design.md` | 系统设计、架构设计 | `asset-category-design.md`, `pricing-system-design.md` |
| **系统** | `-system.md` | 系统性文档、规范 | `tier-naming-system.md`, `user-id-system.md` |
| **架构** | `-architecture.md` | 架构文档 | `backend-architecture.md` |
| **提案** | `-proposal.md` | 方案、提案 | `architecture-proposal.md` |
| **审计** | `-audit.md` | 审计报告 | `api-db-audit.md` |
| **报告** | `-report.md` | 分析报告、进度报告 | `backend-analysis.md`, `fix-progress.md` |
| **计划** | `-plan.md` | 实施计划、路线图 | `refactoring-plan.md`, `implementation-plan.md` |
| **评审** | `-review.md` | 代码评审、API 评审 | `admin-api-review.md`, `user-api-review.md` |
| **逻辑** | `-logic.md` | 业务逻辑说明 | `backend-business-logic.md` |
| **扩展** | `-scaling.md` | 扩展、部署 | `deployment-scaling.md` |
| **知识库** | `-base.md` | 知识库、FAQ | `knowledge-base.md` |
| **模式** | `-schema.md` | 数据结构、Schema | `canvas-data-schema.md` |

---

## 状态前缀

| 前缀 | 含义 | 使用场景 | 示例 |
|------|------|----------|------|
| `[archived]` | 已归档 | 历史文档，不再维护，保留备查 | `[archived]api-db-audit-2026-01-10.md` |
| `[wip]` | 进行中 | 正在编写或实施，未完成 | `[wip]admin-api-review.md` |
| `[draft]` | 草稿 | 设计中，未定稿，待讨论 | `[draft]onboarding-design.md` |
| `[deprecated]` | 已废弃 | 已被新版本替代，不再使用 | `[deprecated]v1-api.md` |
| **无前缀** | 正式文档 | 已完成，正在使用，长期维护 | `api-reference.md` |

**使用建议**:

- **main/** - 极少使用前缀（都是正式文档）
- **shared/** - 极少使用前缀（都是正式规范）
- **tmp/** - 大量使用前缀（区分状态）

---

## 示例对照表

### main/ 目录（后端专用）

| 旧名称 | 新名称 | 类型 |
|--------|--------|------|
| `API_REFERENCE.md` | `api-reference.md` | 参考文档 |
| `ARCHITECTURE-PROPOSAL.md` | `architecture-proposal.md` | 提案 |
| `BACKEND-ARCHITECTURE.md` | `backend-architecture.md` | 架构 |
| `DATABASE-GUIDE.md` | `database-guide.md` | 指南 |
| `DEPLOYMENT-SCALING.md` | `deployment-scaling.md` | 扩展 |
| `TESTING-GUIDE.md` | `testing-guide.md` | 指南 |
| `knowledge_base.md` | `knowledge-base.md` | 知识库 |
| `后台业务逻辑说明.md` | `backend-business-logic.md` | 逻辑 |
| `README.md` | `README.md` | ✅ 不变 |

### shared/ 目录（前后端共用）

| 旧名称 | 新名称 | 类型 |
|--------|--------|------|
| `Canvas-Data-Schema.md` | `canvas-data-schema.md` | 模式 |
| `PRICING-SYSTEM-DESIGN.md` | `pricing-system-design.md` | 设计 |
| `TIER-NAMING-SYSTEM.md` | `tier-naming-system.md` | 系统 |
| `USER-ID-SYSTEM.md` | `user-id-system.md` | 系统 |
| `[重构后]Asset-Category-System-Design.md` | `asset-category-design.md` | 设计 |
| `[重构后]Feature-Flag-Experiments-Unified-Design.md` | `feature-flag-design.md` | 设计 |
| `README.md` | `README.md` | ✅ 不变 |

### tmp/ 目录（临时文档）

| 旧名称 | 新名称 | 类型 + 状态 |
|--------|--------|-------------|
| `API-DB-Consistency-Audit-MASTER.md` | `[archived]api-db-audit-2026-01-10.md` | 审计 + 归档 |
| `API-DB-Fix-Progress.md` | `[archived]api-db-fix-progress-2026-01-10.md` | 报告 + 归档 |
| `API-REVIEW-ADMIN.md` | `[wip]admin-api-review.md` | 评审 + 进行中 |
| `API-REVIEW-USER.md` | `[wip]user-api-review.md` | 评审 + 进行中 |
| `COMPREHENSIVE-BACKEND-ANALYSIS-2026-01-11.md` | `[archived]backend-analysis-2026-01-11.md` | 报告 + 归档 |
| `[重构后]Onboarding-System-Design.md` | `[draft]onboarding-design.md` | 设计 + 草稿 |
| `[重构后]Project-Implementation-Plan.md` | `[wip]refactoring-plan.md` | 计划 + 进行中 |
| `[重构后]Theme-Daily-Doodle-Design.md` | `[draft]theme-system-design.md` | 设计 + 草稿 |
| `README.md` | `README.md` | ✅ 不变 |

---

## 特殊规则

### 1. 日期后缀

**临时文档**（如审计报告、分析报告）建议添加日期后缀：

```
[archived]api-db-audit-2026-01-10.md
[archived]backend-analysis-2026-01-11.md
```

**格式**: `YYYY-MM-DD`

**用途**: 区分同一类型的多个历史报告

---

### 2. README.md 例外

`README.md` 保持全大写，不遵循 kebab-case 规则。

**原因**: 业界惯例，所有主流平台都识别 `README.md`

---

### 3. 简化冗余词汇

去除不必要的冗余词汇：

```
✅ 简化前: Feature-Flag-Experiments-Unified-Design.md
✅ 简化后: feature-flag-design.md

✅ 简化前: System-Resources-API-Reference.md
✅ 简化后: system-resources-reference.md
```

**原则**:
- `design` 已表明是设计文档，无需 `unified`、`system` 等修饰词
- 保持简洁，易于输入和记忆

---

### 4. 中文翻译对照

| 中文 | 英文 |
|------|------|
| 后台业务逻辑说明 | backend-business-logic |
| 重构后 | 无（用状态前缀替代，如 `[wip]`） |
| 系统资源 | system-resources |
| 素材分类 | asset-category |
| 定价系统 | pricing-system |
| 会员层级 | tier-naming |
| 用户标识符 | user-id |
| 画布数据 | canvas-data |
| 功能开关 | feature-flag |
| 新手引导 | onboarding |
| 主题系统 | theme-system |

---

## 检查清单

在提交新文档前，请确认：

- [ ] 文件名全部小写
- [ ] 单词之间使用连字符 `-`
- [ ] 使用英文命名（非中文）
- [ ] 包含明确的类型后缀（`-guide.md`, `-design.md` 等）
- [ ] 临时文档使用状态前缀（`[archived]`, `[wip]`, `[draft]`）
- [ ] 已归档文档包含日期（如 `2026-01-10`）
- [ ] `README.md` 保持大写

---

## 维护规则

### 新增文档

1. 确定文档类型 → 选择后缀
2. 确定文档状态 → 选择前缀（可选）
3. 使用 kebab-case 格式
4. 更新对应目录的 `README.md`

### 修改现有文档

如果现有文档不符合规范：

1. 先重命名文件
2. 更新所有引用该文档的链接
3. Git commit 说明重命名原因

---

## 工具脚本（可选）

```bash
# 检查文档命名是否符合规范
find docs/ -name "*.md" ! -name "README.md" | while read file; do
  basename=$(basename "$file")
  if [[ ! "$basename" =~ ^(\[.*\]-)?[a-z0-9-]+\.md$ ]]; then
    echo "❌ 不符合规范: $file"
  fi
done
```

---

**文档版本**: v1.0
**最后更新**: 2026-01-11
**维护者**: Make Decodables 开发团队

📚 **统一命名规范，提升文档可维护性！**
