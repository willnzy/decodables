# 用户运营系统设计

> 后台用户运营与管理能力的系统设计与边界说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/users/`, `decodables/api/admin/users.py`

---

## 背景

- 管理员需要统一检索与定位用户
- 需要覆盖订阅、积分、项目等核心运营信息

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 提供用户搜索、筛选与详情查看能力
- 支持订阅等级与积分相关的运营操作
- 保留关键操作的可追溯性

## 能力清单

- 用户搜索/筛选/详情
- 订阅等级与折扣管理
- 积分与支付记录查看
- 项目与资产概览/恢复

## 关键流程

- 搜索 → 选择用户 → 查看详情 → 执行运营操作
- 操作完成后反馈结果并记录审计

## 影响范围

- 相关模块：用户运营
- 相关文档：`docs/v2/10-product/admin/admin-dashboard/users.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/admin/users/`、`decodables/api/admin/users.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
