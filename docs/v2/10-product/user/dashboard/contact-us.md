# 联系我们页面体验

> 联系我们页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/contact-us/`

---

## 背景

- 问题或机会: 需要统一的对外联系入口，支持访客与已登录用户
- 目标与非目标: 目标是提交咨询/支持请求；非目标是即时聊天系统

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 统一表单 + 多渠道入口；提交状态与错误处理
- 必须遵循的规则: 已登录走支持工单接口，访客走公开联系接口

## 详细说明

- 页面结构与关键区域:
  - Hero 介绍区
  - 联系方式卡片（Email / WhatsApp / Help Center）
  - 表单区（姓名/邮箱/角色/主题/内容）
  - 提交成功状态
  - FAQ 列表
- 关键用户路径与状态:
  - 组装 fullMessage（含 subject 与用户类型）
  - 已登录：获取 token → submitSupportTicket
  - 未登录：submitContactForm
  - 提交成功显示确认态；失败提示配置错误文案
- PC/Mobile 差异: 网格在 md 断点切换为双栏

## 影响范围

- 相关模块: user-experience/dashboard
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/contact-us/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
