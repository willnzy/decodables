# 权限矩阵附录

> 权限矩阵可视化汇总表（摘要版）。

**状态**: active  
**版本**: 1.3.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Product Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 背景

- 需要提供权限矩阵的可视化摘要
- 支持审阅与快速对照

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 符号说明

| 符号 | 含义 |
|:----:|------|
| ✅ | 完全可用 |
| ❌ | 不可用 |
| N/A | 不适用 |
| 可配置 | 后台可配置 |

---

## 汇总矩阵（摘要）

- 资源配额 × Tier
- 文件夹权限 × Tier
- 自定义素材权限 × Tier
- 项目操作权限 × Tier
- 分享权限 × Tier
- Workspace 权限等级 × 操作

## 影响范围

- 相关模块：权限矩阵摘要
- 相关文档：`docs/v2/03-business/entitlement/permission-matrix.md`

## 证据与验证

- 关键证据来源：`decodables/docs/shared/entitlement/permission-matrix-appendix.md`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.3.0 | 结构对齐模板 | Docs Working Group |
*** End Patch}]}Commentary to=functions.ApplyPatch code
