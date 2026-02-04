# 设计系统规范（摘要版）

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-01-13  
**最后复核**: 2026-02-04  
**负责人**: Design + Frontend  
**适用范围**: frontend  
**source_repo**: frontend  
**sync_required**: no

---

## 背景

- 问题或机会: 设计规范分散，组件样式与交互缺少统一口径
- 目标与非目标: 目标是统一视觉与交互规范；非目标是替代业务流程设计

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- 组件可复用
- 语义化颜色
- 一致的交互反馈

## 详细说明

- 组件体系: Button / Card / Badge / Modal
- 视觉与交互规范: 颜色、间距、排版与状态反馈保持一致

## 影响范围

- 相关模块: 前端 UI 组件库
- 相关文档: `docs/v2/02-standards/ui-navigation-design.md`

## 证据与验证

- 关键证据来源：`decodables-fe/@core/`、`decodables-fe/app/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐与信息补齐 | Docs Working Group |
