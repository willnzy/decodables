# 模板系统设计

> 模板管理、使用与分发机制说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables/domains/templates/`, `decodables/api/user/templates.py`

---

## 背景

- 需要统一模板的使用与权限边界
- 需要支持模板复用与分发

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 提供模板浏览与使用能力
- 规范模板分发与授权
- 约束模板变更与版本管理

## 能力清单

- 模板列表与筛选
- 模板引用与应用
- 模板授权与可见性

## 关键流程

- 选择模板 → 创建项目 → 二次编辑
- 权限校验 → 可用性提示

## 规则与护栏

- 模板可见性与授权校验（按 API 返回）
- 访问频控与分页查询
- 模板引用需校验来源与权限

## 状态与类型

- 可见性：public/private（以 API 字段为准）
- 模板状态：active/archived（以 API 字段为准）

## 数据结构

- Template：`id` / `name` / `preview` / `category` / `visibility`
- TemplateList：`items` / `total` / `offset` / `limit`

## 前端交互要点

- 列表筛选与预览
- 一键使用模板创建项目
- 无权限模板提示与升级引导

## 实现边界（现状）

- 具体可见性/状态枚举以 API 返回为准

## 影响范围

- 相关模块：模板系统
- 相关文档：`docs/v2/10-product/user/editor/create.md`

## 证据与验证

- 关键证据来源：`decodables/domains/templates/`、`decodables/api/user/templates.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充模板系统设计细节 | Docs Working Group |
