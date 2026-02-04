# 日志标准（摘要版）

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-01-13  
**最后复核**: 2026-02-04  
**负责人**: Backend Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 原则

- 结构化日志
- 关键操作需审计记录
- 不记录敏感明文

## 背景

- 需要统一日志规范与审计原则
- 明确敏感数据处理要求

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 影响范围

- 相关模块：日志与审计
- 相关文档：`docs/v2/02-standards/logging-standard.md`

## 证据与验证

- 关键证据来源：`decodables/docs/shared/message-logging-standard.md`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐模板 | Docs Working Group |
