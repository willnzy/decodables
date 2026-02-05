# 数据分析

> **说明**: 定义核心指标和数据追踪规范

---

## 目录结构

```
07-analytics/
├── README.md              # 本文件
├── metrics.md             # 核心指标定义
├── tracking.md            # 埋点规范
├── dashboards.md          # 看板说明
└── insights-template.md   # 分析报告模板
```

---

## 文档说明

| 文档 | 说明 |
|------|------|
| `metrics.md` | 核心指标：北极星指标、关键漏斗、健康指标 |
| `tracking.md` | 埋点规范：事件命名、属性定义、实施指南 |
| `dashboards.md` | 看板说明：产品看板、增长看板、运营看板 |
| `insights-template.md` | 分析报告模板：周报、月报、专题分析 |

---

## 核心指标框架

### 北极星指标

| 指标 | 定义 | 计算方式 |
|------|------|----------|
| WAU | 周活跃用户 | 7 天内有编辑行为的用户数 |
| 付费转化率 | 免费 → 付费比例 | 新增付费 / 7 天前注册用户 |

### 关键漏斗

```
注册 → 首次编辑 → 首次导出 → 7 日回访 → 付费
```

### 健康指标

| 类别 | 指标 |
|------|------|
| 获客 | DAU, WAU, 新注册 |
| 活跃 | 编辑次数, 导出次数, 会话时长 |
| 留存 | D1, D7, D30 留存 |
| 变现 | MRR, ARPU, 付费率 |

---

## tracking.md 内容大纲

```markdown
## 事件命名规范
- 格式：{module}_{action}_{object}
- 示例：editor_create_project, billing_upgrade_plan

## 通用属性
- user_id, session_id, timestamp
- platform, device, browser

## 页面浏览
- page_view: page_name, referrer

## 编辑器事件
- editor_open, editor_save, editor_export
- element_add, element_delete, element_edit

## 付费事件
- checkout_start, checkout_complete
- subscription_upgrade, subscription_cancel
```

---

## 与其他目录的关系

| 目录 | 关系 |
|------|------|
| `06-growth/` | 增长策略的效果度量 |
| `04-engineering/development/` | 埋点实现规范 |
