# 资源与系统素材设计

> 系统资源库与内置素材能力说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables/domains/resources/`, `decodables/api/user/resources.py`

---

## 背景

- 需要统一系统资源与内置素材的边界
- 需要区分用户素材与平台资源

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 定义系统资源类型与范围
- 规范资源加载与授权
- 约束资源更新与缓存

## 能力清单

- 系统资源列表
- 资源检索与筛选
- 资源授权与引用

## 关键流程

- 资源加载 → 授权校验 → 展示与使用

## 规则与护栏

- 资源类型需白名单控制
- 资源下载/引用需权限校验
- 资源缓存需遵循更新策略

## 状态与类型

- 资源状态：`active` / `archived`
- 资源类型：`theme` / `asset` / `template` / `font`

## 数据结构

- ResourceItem：`id` / `type` / `name` / `url` / `status`
- ResourceList：`items` / `total` / `offset` / `limit`

## 前端交互要点

- 资源库筛选与搜索
- 资源预览与一键引用
- 空态与加载状态提示

## 实现边界（现状）

- 资源类型与权限以后端枚举为准

## 影响范围

- 相关模块：资源库
- 相关文档：`docs/v2/10-product/user/editor/create.md`

## 证据与验证

- 关键证据来源：`decodables/domains/resources/`、`decodables/api/user/resources.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充资源与系统素材设计细节 | Docs Working Group |
