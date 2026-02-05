# v3 文档结构审计报告

> **审计日期**: 2026-02-05
> **审计范围**: docs/v3/ 全部目录和文档
> **状态**: ✅ 阶段1+2+3 已完成（2026-02-05）

---

## 一、统计概览

| 项目 | 数量 |
|------|------|
| 目录总数 | 74 |
| README 文件 | 67 |
| 其他文档 | 6 |
| v1 文档（参考） | 87 |
| v2 文档（参考） | 159 |

---

## 二、发现的问题

### 🔴 问题 1：缺少索引 README

| 目录 | 问题 | 建议 |
|------|------|------|
| `internal/` | 缺少索引 README | 添加 internal 总览 |
| `public/` | 缺少索引 README | 添加 public 总览 |
| `archive/` | 缺少说明 | 添加归档说明 |

### 🔴 问题 2：模块映射不完整

**后端有 35 个 domain，但 modules/ 只有 9 个模块**

未明确归属的 domain：
| domain | 建议归属模块 |
|--------|--------------|
| `referrals` | billing/ |
| `tools` | editor/ |
| `tag` | marketplace/ |
| `interfaces` | 通用/不需要文档 |
| `logging` | platform/ |
| `tasks` | platform/ |
| `webhooks` | billing/ 或 platform/ |

**建议**：更新 modules/README.md 中的映射表。

### 🔴 问题 3：功能规格文档遗漏

features/README.md 只列出 5 个功能，但实际还有：

| 遗漏功能 | 说明 |
|----------|------|
| `profile.md` | 个人主页功能 |
| `notifications.md` | 通知系统 |
| `search.md` | 搜索功能 |
| `favorites.md` | 收藏功能 |
| `sharing.md` | 分享功能 |
| `templates.md` | 模板系统 |

### 🔴 问题 4：页面文档遗漏

pages/user/README.md 缺少一些页面：

| 遗漏页面 | 对应路由 |
|----------|----------|
| `notifications.md` | `/notifications` |
| `transaction-history.md` | `/transaction-history` |
| `about-us.md` | `/about-us` |
| `contact-us.md` | `/contact-us` |
| `terms.md` | `/terms-of-service` |
| `privacy.md` | `/privacy-policy` |

### 🔴 问题 5：document-planning.md 遗漏

未包含在规划中的文档：

| 位置 | 文档 |
|------|------|
| 04-engineering/modules/ | marketplace/architecture.md |
| 04-engineering/modules/ | dashboard/architecture.md |
| 04-engineering/modules/ | ai/architecture.md |
| 04-engineering/modules/ | platform/architecture.md |
| 04-engineering/modules/ | admin/architecture.md |
| 04-engineering/modules/ | content/architecture.md |
| 04-engineering/api/ | 所有 API 文档 |
| 04-engineering/data/ | 所有数据文档 |
| 03-design/patterns/ | 所有模式文档 |
| 03-design/tokens/spacing.md | 间距系统 |
| 03-design/tokens/shadows.md | 阴影系统 |
| 03-design/components/ | forms.md, modals.md 等 |

### 🟡 问题 6：07-analytics 和 08-operations 内容不一致

这两个 README 已经包含了详细内容大纲，但格式与其他 README 不一致：
- 包含了 `内容大纲` 而不是 `计划文档`
- 内容更详细，但格式不统一

**建议**：保持格式统一，或明确这是"已完成"的 README。

### 🟡 问题 7：entitlement 设计文档整合

v1/shared/entitlement/ 有 28 个文档，但 v3 的 planned/ 目录是空的。

**建议**：
1. 明确 entitlement 重构后是否还需要这些文档
2. 如果需要，创建 planned/ 下的规划清单

### 🟡 问题 8：ADR 模板缺失

document-outlines.md 提到了 ADR 模板，但 templates/ 下没有 `adr-template.md`。

### 🟡 问题 9：v1 重要文档未映射

v1 有一些重要文档未在 v3 中明确映射：

| v1 文档 | 建议 v3 位置 |
|---------|--------------|
| adr/0001-use-ddd-architecture.md | 04-engineering/architecture/decisions/ |
| adr/0002-database-driven-config.md | 04-engineering/architecture/decisions/ |
| shared/self-hosted-auth-design.md | 04-engineering/modules/auth/ 或 decisions/ |
| shared/pricing-system-design.md | 05-business/pricing/ |
| shared/analytics-system-design.md | 07-analytics/ |

### 🟢 问题 10：格式不一致（小问题）

部分 README 的 `计划文档` 表格列不一致：
- 有的有 `同步` 列
- 有的有 `对应路由` 列
- 有的只有 `用途` 和 `状态`

**建议**：统一格式。

---

## 三、遗漏清单总结

### 需要添加的 README

| 路径 | 优先级 |
|------|--------|
| `internal/README.md` | P0 |
| `public/README.md` | P0 |
| `archive/README.md` | P2 |

### 需要更新的 README

| 路径 | 更新内容 | 优先级 |
|------|----------|--------|
| `02-product/features/README.md` | 添加遗漏功能 | P1 |
| `02-product/pages/user/README.md` | 添加遗漏页面 | P1 |
| `04-engineering/modules/README.md` | 完善 domain 映射 | P1 |

### 需要创建的模板

| 路径 | 优先级 |
|------|--------|
| `10-governance/templates/adr-template.md` | P1 |
| `10-governance/templates/module-readme-template.md` | P2 |
| `10-governance/templates/feature-spec-template.md` | P2 |

### 需要更新的规划文档

| 路径 | 更新内容 | 优先级 |
|------|----------|--------|
| `document-planning.md` | 添加遗漏的模块架构文档 | P0 |
| `document-planning.md` | 添加 API 文档规划 | P1 |
| `document-planning.md` | 添加设计系统完整文档 | P1 |

---

## 四、建议的修复顺序

### 阶段 1：结构完善（P0）✅ 已完成

1. ✅ 添加 `internal/README.md` - 已完成
2. ✅ 添加 `public/README.md` - 已完成
3. ✅ 添加 `archive/README.md` - 已完成
4. ✅ 更新 `document-planning.md` 添加遗漏文档 - 已完成

### 阶段 2：内容补全（P1）✅ 已完成

1. ✅ 更新 `02-product/features/README.md` - 已添加 18 个功能
2. ✅ 更新 `02-product/pages/user/README.md` - 已添加 16 个页面
3. ✅ 更新 `04-engineering/modules/README.md` - 已完善 domain 映射表
4. ✅ 创建 `adr-template.md` - 已完成
5. ✅ 创建 `04-engineering/architecture/decisions/` 目录 - 已完成

### 阶段 3：格式统一（P2）✅ 已完成

1. ✅ 统一 07-analytics/README.md 格式 - 已完成
2. ✅ 统一 08-operations/README.md 格式 - 已完成
3. ✅ 创建 module-readme-template.md - 已完成
4. ✅ 创建 feature-spec-template.md - 已完成
5. ✅ 创建 page-design-template.md - 已完成
6. ✅ 创建 api-reference-template.md - 已完成
7. ✅ 创建 faq-template.md - 已完成（原已存在，已更新）
8. ✅ 创建 news-template.md - 已完成（原已存在，已更新）
9. ✅ 更新 templates/README.md - 已完成

---

## 五、审计结论

**整体评估**：v3 文档结构基本完整，主要问题是：
1. 部分索引 README 缺失
2. 功能/页面文档列表不完整
3. 模块映射需要细化
4. document-planning.md 需要扩充

**建议**：按阶段 1 → 阶段 2 → 阶段 3 顺序修复。

---

**END OF AUDIT**
