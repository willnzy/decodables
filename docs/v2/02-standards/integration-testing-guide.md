# 前端集成测试指南（摘要版）

**状态**: needs-review  
**版本**: 1.0.0  
**版本日期**: 2026-01-11  
**最后复核**: 2026-02-04  
**负责人**: Frontend Team  
**适用范围**: frontend  
**source_repo**: frontend  
**sync_required**: no

---

## 背景

- 问题或机会: 集成测试覆盖不一致，关键路径缺少稳定回归
- 目标与非目标: 目标是统一关键路径与集成测试清单；非目标是替代单元测试

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- 覆盖范围: 关键路径（登录、创建、导出、购买）
- 跨模块集成: Workspace/Marketplace/Editor
- 工具与策略: React Testing Library；Playwright（E2E）

## 详细说明

- 关键路径清单: 登录/注册、编辑器创建与保存、导出、购买与交易记录
- 跨模块集成清单: Workspace 与 Project、Marketplace 与 Assets、Editor 与 Export
- 测试环境与数据准备: 预置测试账号、种子数据与稳定的测试环境配置

## 影响范围

- 相关模块: 前端测试与质量保障
- 相关文档: `docs/v2/02-standards/frontend-development-guide.md`

## 证据与验证

- 关键证据来源：`decodables-fe/tests/`、`decodables-fe/app/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐与信息补齐 | Docs Working Group |
