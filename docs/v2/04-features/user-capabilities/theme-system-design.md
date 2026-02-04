 # 主题系统设计
 
 > 主题体系的结构、规则与展示策略说明。
 
 **状态**: draft  
 **版本**: 0.1.0  
 **版本日期**: 2026-02-04  
 **最后复核**: 2026-02-04  
 **负责人**: Docs Working Group  
 **适用范围**: shared  
 **source_repo**: both  
 **sync_required**: yes  
**来源/依据**: `decodables/api/user/themes.py`, `decodables/domains/themes/`, `decodables-fe/lib/useThemeStore.ts`
 
 ---
 
## 背景

- 需要统一节日/每日主题的获取、展示与配置
- 需要将主题配置转化为前端可用的视觉变量

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 定义主题数据结构与展示规范
- 明确主题匹配规则与优先级策略
- 支持审核与再生成流程

## 能力清单

- 获取当前主题（按日期匹配）
- 主题配置下发与前端渲染
- 主题审核、切换与再生成

## 关键流程

- 后端匹配当前主题 → 前端拉取 → 注入 CSS 变量 → 渲染 Banner/装饰
- 管理端生成/审核主题 → 发布 → 用户端生效

## 规则与状态

- 日期规则：`fixed`（固定日期范围）/ `dynamic`（动态节日规则）
- 匹配策略：按优先级倒序匹配第一个命中主题
- Review 状态：`pending` / `auto_approved` / `reviewed` / `rejected`
- 用户端接口限流：`60/minute`

## 数据结构

- `theme_config`
  - `colors`（主题色）
  - `decorations`（snowflakes/hearts/confetti 等）
  - `badge`（Banner 文案）
  - `banner_style`（solid/striped/gradient）

## 接口清单

- `GET /api/v2/user/themes/current`

## 前端渲染要点

- `HolidayProvider` 负责拉取主题与注入 CSS 变量
- `HolidayBanner` 读取 `badge` 与 `banner_style`
- `useThemeStore` 管理主题状态与渲染配置

## 影响范围

- 相关模块：主题系统
- 相关文档：`docs/v2/10-product/admin/content-management/themes.md`

## 证据与验证

- 关键证据来源：`decodables/api/user/themes.py`、`decodables/domains/themes/`
- 前端证据：`decodables-fe/lib/useThemeStore.ts`、`decodables-fe/components/holiday/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
