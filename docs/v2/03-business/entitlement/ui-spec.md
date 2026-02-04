# 权限 UI 交互规范

> 权限锁定、试用提示与配额交互规范。

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Frontend Team  
**适用范围**: shared  
**source_repo**: frontend  
**sync_required**: yes

---

## 背景

- 需要统一权限状态与交互规范
- 明确锁定/试用/配额交互模式

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 状态映射

- `full`: 正常显示
- `trial`: 试用期标识 + 提示
- `locked`: 锁定 + 升级弹窗

## 交互规范

| 场景 | 交互 |
|------|------|
| 功能锁定 | 锁图标 + Upgrade Modal |
| 配额耗尽 | 按钮置灰 + Tooltip |
| 试用期结束 | Banner + 只读模式 |

## 影响范围

- 相关模块：权限 UI
- 相关文档：`docs/v2/03-business/entitlement/system-design.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/`、`decodables-fe/@shared/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐模板 | Docs Working Group |
