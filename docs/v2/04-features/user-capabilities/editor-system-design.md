# 编辑器系统设计

> 画布编辑器能力边界与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/create/`, `decodables/domains/creation/`

---

## 背景

- 需要统一编辑器能力范围与调用边界
- 明确画布、素材、AI 能力的协作关系

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 定义编辑器核心能力与扩展能力
- 明确加载流程与权限限制
- 约束导入/导出/生成的行为规则

## 能力清单

- 画布与页面管理
- 媒体与素材管理
- AI 生成与批量生成
- 导入/导出与历史记录

## 关键流程

- 进入编辑器 → 鉴权 → 初始化数据 → 渲染画布
- 编辑 → 保存 → 导出/发布

## 影响范围

- 相关模块：编辑器
- 相关文档：`docs/v2/10-product/user/editor/create.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/create/`、`decodables/domains/creation/`、`decodables/api/user/projects.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
