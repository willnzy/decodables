# 后端命名规范（摘要版）

**状态**: needs-review  
**版本**: 1.0.0  
**版本日期**: 2026-01-16  
**最后复核**: 2026-02-04  
**负责人**: Backend Team  
**适用范围**: backend  
**source_repo**: backend  
**sync_required**: no

---

## 背景

- 问题或机会: 待补充
- 目标与非目标: 待补充

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- service / repository / router 分层命名
- 领域对象使用 `Entity` 后缀
- 查询分页使用 `offset + limit`

## 详细说明

- service / repository / router 分层命名
- 领域对象使用 `Entity` 后缀
- 查询分页使用 `offset + limit`

## 影响范围

- 相关模块: 后端领域与应用层
- 相关文档: `docs/v2/01-architecture/backend-architecture.md`

## 证据与验证

- 关键证据来源：`decodables/domains/`、`decodables/api/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐与信息补齐 | Docs Working Group |
