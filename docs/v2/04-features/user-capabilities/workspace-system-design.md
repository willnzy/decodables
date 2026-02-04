# Workspace 系统设计

> Workspace、成员与邀请机制的系统设计说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables/domains/workspace/`, `decodables/api/user/workspaces.py`

---

## 背景

- 需要统一 Workspace 与成员模型
- 需要明确邀请与权限边界

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 定义 Workspace 与成员关系
- 明确邀请、加入与移除流程
- 约束权限与角色控制

## 能力清单

- Workspace 创建与管理
- 成员邀请/加入/移除
- 角色与权限控制

## 关键流程

- 创建 Workspace → 邀请成员 → 成员加入
- 更新角色 → 权限生效 → 审计记录

## 规则与护栏

- Workspace name 长度 1-100，description ≤ 500
- 个人 Workspace 默认存在且不可删除（Phase 1）
- 创建团队 Workspace 受 tier 配额限制
- 邀请有效期 7 天，过期自动失效

## 状态与类型

- Workspace：`is_default` / `is_personal` / `is_active`
- Member role：`owner` / `member`
- Invitation status：`pending` / `accepted` / `declined` / `expired`

## 数据结构

- Workspace：`id` / `name` / `owner_id` / `is_default` / `is_personal`
- WorkspaceMember：`workspace_id` / `user_id` / `role` / `is_active`
- WorkspaceInvitation：`invited_email` / `role` / `status` / `expires_at`

## 前端交互要点

- 默认 Workspace 自动加载与切换入口
- 成员邀请与角色调整需二次确认
- 超配额创建提示与升级引导

## 实现边界（现状）

- Phase 1：仅个人 Workspace；团队 Workspace 为 Phase 2+
- Pro 用户最多 10 个 Workspace，Free/Starter 不可新增

## 影响范围

- 相关模块：Workspace
- 相关文档：`docs/v2/10-product/user/dashboard/dashboard.md`

## 证据与验证

- 关键证据来源：`decodables/domains/workspace/`、`decodables/api/user/workspaces.py`、`decodables/api/user/workspace_members.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充 Workspace 系统设计细节 | Docs Working Group |
