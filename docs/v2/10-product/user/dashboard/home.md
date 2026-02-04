# 首页体验

> 首页页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/page.tsx`

---

## 背景

- 问题或机会: 提供品牌与价值主张入口，承接新用户转化
- 目标与非目标: 目标是展示产品价值与引导注册/登录；非目标是进行编辑与创作

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: Landing 页面为营销入口，内容由客户端组件承载
- 必须遵循的规则: 保持 SEO 元数据与 FAQ 结构化数据

## 详细说明

- 页面结构与关键区域:
  - 服务端注入 SEO metadata + FAQ JSON-LD
  - 客户端组件 `LandingPageClient` 承载主要内容区块
- 关键用户路径与状态:
  - 入口 CTA 引导注册/登录/开始创建（由客户端组件实现）
  - FAQ 结构化数据覆盖常见问题
- PC/Mobile 差异: 由客户端组件负责响应式布局

## 影响范围

- 相关模块: user-experience/dashboard
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/page.tsx`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
