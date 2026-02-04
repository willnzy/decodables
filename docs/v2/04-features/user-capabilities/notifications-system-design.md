# 通知系统设计

> 用户通知与消息投递能力的系统设计说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables/domains/platform/notifications/`, `decodables/api/user/notifications.py`

---

## 背景

- 需要统一通知模型与投递规则
- 需要明确阅读状态与通知中心行为

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 定义通知类型与优先级
- 提供通知中心与状态管理
- 约束投递频率与去重策略

## 能力清单

- 通知列表与已读管理
- 通知投递与去重
- 通知聚合与过滤

## 关键流程

- 事件触发 → 通知生成 → 投递/展示
- 用户阅读 → 状态更新 → 归档

## 规则与护栏

- 通知类型需白名单控制
- 投递频控与去重策略必须启用
- 通知内容需脱敏与权限校验

## 状态与类型

- 通知状态：`unread` / `read` / `archived`
- 通知类型：`system` / `billing` / `marketing` / `security`

## 数据结构

- Notification：`id` / `user_id` / `type` / `title` / `status` / `created_at`
- NotificationDelivery：`notification_id` / `channel` / `status` / `sent_at`

## 前端交互要点

- 通知中心支持筛选与已读管理
- 未读数量角标与实时更新
- 通知详情跳转与归档

## 实现边界（现状）

- 通知类型与渠道配置以后端枚举为准

## 影响范围

- 相关模块：通知系统
- 相关文档：`docs/v2/10-product/user/dashboard/notifications.md`

## 证据与验证

- 关键证据来源：`decodables/domains/platform/notifications/`、`decodables/api/user/notifications.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充通知系统设计细节 | Docs Working Group |
