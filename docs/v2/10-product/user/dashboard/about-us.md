# 关于我们页面体验

> 关于我们页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/about-us/`

---

## 背景

- 问题或机会: 需要一页集中介绍团队与使命，增强品牌信任
- 目标与非目标: 目标是展示团队/故事/价值观；非目标是业务功能教学

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 服务端拉取内容 + fallback 数据；注入 AboutPage/Person Schema
- 必须遵循的规则: extra_data 需通过 type guard 校验后使用

## 详细说明

- 页面结构与关键区域:
  - Hero + Brand 信息
  - Our Story（故事/使命/产品特性）
  - Who We Are（地点/团队优势）
  - Team Members（成员信息）
  - Values（价值观）
  - CTA（联系与试用）
- 关键用户路径与状态:
  - 服务端获取 About 数据
  - 若 API 不可用则使用 fallbackData
  - 生成 schemaData 注入页面
- PC/Mobile 差异: 由栅格与断点类控制

## 影响范围

- 相关模块: user-experience/dashboard
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/about-us/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
