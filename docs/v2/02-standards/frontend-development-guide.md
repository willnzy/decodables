# 前端开发规范（摘要版）

**状态**: needs-review  
**版本**: 2.7.0  
**版本日期**: 2026-01-19  
**最后复核**: 2026-02-04  
**负责人**: Frontend Team  
**适用范围**: frontend  
**source_repo**: frontend  
**sync_required**: no

---

## 背景

- 问题或机会: 前端规范分散，执行标准不一致
- 目标与非目标: 目标是统一技术栈与工程规范；非目标是替代业务设计

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- 新代码必须使用 `.ts/.tsx`
- 状态管理使用 Zustand 拆分式 Store
- Mobile-first：默认移动端样式，`md/` 以上增强
- 错误处理统一进入 errorLogger

## 详细说明

### 技术栈

- Next.js 16.1.1 (App Router)
- React 19.2.3
- TypeScript 5.x
- Zustand 5.0.9
- Tailwind CSS 4
- Fabric.js 5.3.0

### 核心规则

- 认证门控: 使用 AuthGate 模式，确保 Hook 顺序与权限校验一致

## 影响范围

- 相关模块: 前端工程化与 UI
- 相关文档: `docs/v2/02-standards/responsive-design-guide.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/`、`decodables-fe/@business/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 2.7.0 | 结构对齐与信息补齐 | Docs Working Group |
