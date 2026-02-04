# 资产与素材系统设计

> 用户素材资产上传、管理与复用能力说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables/domains/assets/`, `decodables/api/user/user_assets.py`

---

## 背景

- 需要统一用户素材资产的生命周期
- 需要支持上传、管理与复用

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 提供素材上传与管理能力
- 支持素材搜索与复用
- 约束存储与权限边界

## 能力清单

- 素材上传/删除
- 素材列表与筛选
- 素材复用与引用

## 关键流程

- 上传 → 存储 → 列表展示
- 选择素材 → 应用到项目

## 规则与护栏

- 允许类型：jpeg/png/gif/webp/svg/pdf
- 文件大小按 tier 限制（t1=5MB, t2=10MB, t3=20MB）
- URL 导入需 SSRF 防护与长度限制（2048）
- UUID 校验与所有权校验

## 状态与类型

- scope：`all`（跨项目，仅 t3/t4）
- starred：收藏标记（star/unstar）

## 数据结构

- Asset：`id` / `project_id` / `folder_id` / `url` / `mime_type` / `created_at`
- AssetList：`items` / `total` / `offset` / `limit` / `has_more`

## 前端交互要点

- 上传/URL 导入与收藏切换
- 列表支持筛选、分页与回收站恢复
- 资产可移动到文件夹

## 实现边界（现状）

- 跨项目资产仅对高 tier 开放
- 回收站与恢复以 API 返回为准

## 影响范围

- 相关模块：资产与素材
- 相关文档：`docs/v2/10-product/user/editor/create.md`

## 证据与验证

- 关键证据来源：`decodables/domains/assets/`、`decodables/api/user/user_assets.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充资产与素材系统设计细节 | Docs Working Group |
