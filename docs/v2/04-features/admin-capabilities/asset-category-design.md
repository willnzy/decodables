 # 素材分类系统设计
 
 > 素材分类树、规则与管理流程说明。
 
 **状态**: draft  
 **版本**: 0.1.0  
 **版本日期**: 2026-02-04  
 **最后复核**: 2026-02-04  
 **负责人**: Docs Working Group  
 **适用范围**: shared  
 **source_repo**: both  
 **sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/content/`, `decodables-fe/app/admin/content/_lib/api.ts`, `decodables-fe/app/admin/content/_lib/types.ts`, `decodables/api/admin/asset_categories.py`
 
 ---
 
## 背景

- 需要统一素材分类模型与层级规则
- 明确分类维护流程

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 统一素材分类模型与层级规则
- 约束分类的增删改与层级调整
- 支持前端展示、检索与资源绑定

## 能力清单

- 分类列表/树形结构
- 分类创建/更新/移动/删除
- 分类资源绑定与查询

## 关键流程

- 创建分类 → 写入层级路径 → 展示树
- 调整层级 → 更新路径 → 资源继承/展示
- 删除分类 → 校验子节点 → 级联或拒绝

## 规则与护栏

- slug 仅允许小写字母、数字、`-`、`_`
- asset_type 限定在固定集合
- min_tier 限定 `t1`-`t3`
- 删除支持级联（cascade）与阻断校验

## 分类结构

- 树形层级与路径（path/level）
- 叶子节点与可用性（is_visible/is_featured）
- 展示顺序（display_order）

## 接口清单（Admin）

- `GET /api/v2/admin/asset-categories`
- `GET /api/v2/admin/asset-categories/tree`
- `POST /api/v2/admin/asset-categories`
- `PATCH /api/v2/admin/asset-categories/{slug}`
- `PUT /api/v2/admin/asset-categories/{slug}/move`
- `DELETE /api/v2/admin/asset-categories/{slug}`
- `GET /api/v2/admin/asset-categories/{slug}/resources`

## 影响范围

- 相关模块：素材分类系统
- 相关文档：`docs/v2/05-api/admin-endpoints.md`、`docs/v2/04-features/admin-capabilities/asset-category-design.md`

## 证据与验证

- 关键证据来源：`decodables/api/admin/asset_categories.py`、`decodables/domains/assets/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
