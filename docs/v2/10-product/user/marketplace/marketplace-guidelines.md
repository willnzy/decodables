# Marketplace Guidelines 体验

> Marketplace Guidelines 页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/marketplace-guidelines/`

---

## 背景

- 问题或机会: 需要统一对外发布与审核的内容规范
- 目标与非目标: 目标是展示发布准则；非目标是审核后台

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 服务端渲染 + ISR（1h）+ CMS 兜底
- 必须遵循的规则: 按区块导航锚点组织内容

## 详细说明

- 页面结构与关键区域:
  - Hero + 更新时间
  - 快速导航（锚点）
  - 发布资格/内容要求/违规与申诉
  - 联系方式区块
- 关键用户路径与状态:
  - 从 CMS 拉取页面数据
  - 更新日期由 updated_at 生成
  - 页面内容分段滚动阅读
- PC/Mobile 差异: 无特定差异，布局自适配

## 影响范围

- 相关模块: user-experience/marketplace
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/marketplace-guidelines/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
