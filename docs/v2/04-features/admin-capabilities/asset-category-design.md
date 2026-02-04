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
 **来源/依据**: `decodables-fe/docs/shared/asset-category-design.md`, `decodables/docs/shared/asset-category-design.md`
 
 ---
 
## 背景

- 需要统一素材分类模型与层级规则
- 明确分类维护流程

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标
 
 - 统一素材分类模型与层级规则
 - 约束分类增删改流程
 - 支持前端展示与检索
 
## 分类结构
 
 - 树形层级与编号策略
 - 叶子节点与可用性规则
 
## 维护流程
 
 - 创建 → 审核 → 发布 → 调整

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
