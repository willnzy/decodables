# 邮箱验证页面体验

> 邮箱验证页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/(auth)/verify-email/`

---

## 背景

- 问题或机会: 兼容历史验证链接，统一引导到注册 OTP 流程
- 目标与非目标: 目标是无感跳转到注册；非目标是继续旧验证流程

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 页面仅做重定向，不承载验证逻辑
- 必须遵循的规则: 进入即 `replace('/register')`

## 详细说明

- 页面结构与关键区域:
  - 中心提示 “Redirecting...”
- 关键用户路径与状态:
  - `useEffect` 触发路由替换到 `/register`
- PC/Mobile 差异: 无

## 影响范围

- 相关模块: user-experience/account
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/(auth)/verify-email/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
