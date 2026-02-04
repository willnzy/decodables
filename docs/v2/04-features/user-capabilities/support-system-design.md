# 支持与反馈系统设计

> 用户支持入口、工单与反馈流程说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables/domains/support/`, `decodables/api/user/support.py`

---

## 背景

- 需要统一用户支持入口与处理流程
- 需要明确访客与登录用户的提交路径

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 提供统一的支持请求入口
- 支持工单/反馈的状态追踪
- 降低支持响应时间与丢单风险

## 能力清单

- 支持入口与表单提交
- 工单创建与状态管理
- 反馈与问题分类

## 关键流程

- 提交支持请求 → 创建工单 → 回复与关闭
- 访客提交 → 公开入口 → 后台处理

## 规则与护栏

- 访客提交需限频与验证码
- 工单需保留状态与时间线
- 敏感信息需脱敏与权限控制

## 状态与类型

- 工单状态：`open` / `pending` / `resolved` / `closed`
- 反馈类型：`bug` / `billing` / `account` / `other`

## 数据结构

- Ticket：`id` / `user_id` / `status` / `category` / `created_at`
- TicketMessage：`ticket_id` / `sender` / `content` / `created_at`

## 前端交互要点

- 访客与登录用户入口分流
- 提交后状态提示与工单列表回显
- 回复通知与未读提示

## 实现边界（现状）

- 工单状态与分类以后端枚举为准

## 影响范围

- 相关模块：支持与反馈
- 相关文档：`docs/v2/10-product/user/dashboard/contact-us.md`

## 证据与验证

- 关键证据来源：`decodables/domains/support/`、`decodables/api/user/support.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充支持与反馈系统设计细节 | Docs Working Group |
