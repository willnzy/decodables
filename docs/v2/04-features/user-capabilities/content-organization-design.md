# 内容组织系统设计

> 文件夹、回收站与内容恢复机制说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables/domains/folder/`, `decodables/api/user/folders.py`

---

## 背景

- 需要统一内容组织与分类方式
- 需要提供安全的删除与恢复机制

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 支持文件夹层级与组织能力
- 支持回收站与恢复流程
- 约束删除与恢复的权限规则

## 能力清单

- 文件夹创建/移动/删除
- 回收站与恢复
- 组织视图与筛选

## 关键流程

- 创建文件夹 → 归档内容 → 删除/恢复
- 回收站清理 → 不可恢复

## 规则与护栏

- folder_type 仅允许 `project` / `asset`
- 文件夹名称 1-100 字符，颜色限定 8 色
- 删除为软删除，需二次确认
- 需要 workspace 访问权限校验

## 状态与类型

- FolderType：`project` / `asset`
- FolderColor：`slate` / `red` / `orange` / `amber` / `emerald` / `cyan` / `blue` / `violet`

## 数据结构

- Folder：`workspace_id` / `folder_type` / `name` / `color` / `item_count`
- FolderCounts：`bought_count` / `selling_count` / `preview_items`

## 前端交互要点

- 列表支持拖拽排序与颜色选择
- 回收站视图支持批量清理
- Folder 与内容筛选联动

## 实现边界（现状）

- 文件夹仅支持 project/asset 两类，未开放自定义类型
- 回收站恢复与永久删除策略以内置规则为准

## 影响范围

- 相关模块：内容组织
- 相关文档：`docs/v2/10-product/user/dashboard/dashboard.md`

## 证据与验证

- 关键证据来源：`decodables/domains/folder/`、`decodables/api/user/folders.py`、`decodables-fe/app/dashboard/_components/sections/TrashSection.tsx`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充内容组织系统设计细节 | Docs Working Group |
