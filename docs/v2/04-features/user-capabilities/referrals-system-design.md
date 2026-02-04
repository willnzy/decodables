# 推荐与返利系统设计

> 推荐码、归因与返利规则说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables/domains/referrals/`, `decodables/api/user/referrals.py`

---

## 背景

- 需要统一推荐与返利的规则边界
- 需要支持归因与奖励发放

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 规范推荐与归因机制
- 保障奖励规则清晰可追溯
- 约束异常与作弊处理

## 能力清单

- 推荐码生成与分享
- 归因与奖励追踪
- 奖励发放与记录

## 关键流程

- 分享推荐码 → 注册/购买 → 归因 → 发放奖励

## 影响范围

- 相关模块：推荐与返利
- 相关文档：`docs/v2/10-product/user/dashboard/dashboard.md`

## 证据与验证

- 关键证据来源：`decodables/domains/referrals/`、`decodables/api/user/referrals.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
