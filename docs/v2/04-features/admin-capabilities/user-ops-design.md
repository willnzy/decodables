# 用户运营系统设计

> 后台用户运营与管理能力的系统设计与边界说明。

**状态**: draft  
**版本**: 0.2.0  
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
- 需要对敏感操作提供审计与限流保护

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 提供用户搜索、筛选与详情查看能力
- 支持订阅等级与积分相关的运营操作
- 保留关键操作的可追溯性
- 支持资产/环境/支付维度的诊断视图

## 能力清单

- 用户搜索/筛选/详情
- 订阅等级与折扣管理
- 积分调整与支付记录查看
- 项目与资产概览/恢复
- 会话/设备环境统计
- 运营审计与活动记录

## 关键流程

- 搜索 → 选择用户 → 查看详情 → 执行运营操作
- 操作完成后反馈结果并记录审计

## 规则与护栏

- 统一分页：`offset` + `limit`
- 用户 ID 长度校验（后端限制 100）
- 管理员权限与接口限流
- 限流：读取 30/min；写操作 10/min
- 变更操作需记录审计日志

## 状态与类型

- Tier：`t1` / `t2` / `t3`
- Credits：`monthly` / `permanent`
- 订阅事件：`created` / `upgraded` / `downgraded` / `cancelled` / `renewed`
- 积分事件：`adjusted` / `consumed` / `refunded` / `monthly_reset`
- 设备类型：`desktop` / `tablet` / `mobile`
- 支付状态：`succeeded` / `pending` / `failed` / `refunded`

## 数据结构

- UserSearchResult：`id` / `email` / `name` / `user_code` / `tier` / `credits_monthly` / `credits_permanent`
- UserAudit：`activities` / `subscription_history` / `credit_history`
- UserAssetUsage：`images_count` / `projects_count` / `total_storage_mb`
- UserEnvStats：`last_browser` / `last_os` / `last_login` / `sessions`
- UserProjects：`title` / `status` / `page_count`
- Payments：`amount` / `currency` / `status` / `payment_method`

## 前端交互要点

- 左侧搜索/筛选，右侧详情卡
- 详情中分区展示订阅/积分/项目/支付/环境/审计
- 弹窗操作：积分调整、Tier 变更、退款、取消订阅、降级

## 实现边界（现状）

- 前端搜索参数为 `q/page/page_size`，后端为 `search/offset/limit`
- 前端路径包含 `/users/users/...`（路由前缀叠加）
- `POST /users/{user_id}/tier` 已废弃（410），前端仍保留调用
- 积分调整字段前端 `credit_type`，后端 `bucket`

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
| 2026-02-04 | 0.2.0 | 补充用户运营系统设计细节 | Docs Working Group |
