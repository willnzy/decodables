# 主题管理页面体验

> 主题管理页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/themes/`

---

## 背景

- 问题或机会: 需要集中管理每日主题与审核流程
- 目标与非目标: 目标是主题管理；非目标是普通用户浏览

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 日历/列表/审核三种视图切换
- 必须遵循的规则: 视图与筛选通过 URL 参数驱动

## 详细说明

- 页面结构与关键区域:
  - Header + 统计卡片
  - Tabs（calendar/list/review）
  - 主题编辑/详情/批量生成/审核弹窗
- 管理路径与状态:
  - URL 控制 view/category/status/search
  - Calendar 点击日期/主题进入详情或编辑
  - Approve/Reject/Regenerate 操作更新列表
- PC/Mobile 差异: 无特定差异，布局自适配

## 影响范围

- 相关模块: admin-experience/content-management
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/admin/themes/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
