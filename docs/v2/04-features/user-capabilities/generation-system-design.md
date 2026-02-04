# 生成与导出系统设计

> AI 生成与导出能力的系统设计说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables/domains/generation/`, `decodables/domains/export/`

---

## 背景

- 需要统一 AI 生成与导出能力边界
- 需要明确积分扣费与生成成本

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 明确生成能力与输入约束
- 规范导出格式与权限限制
- 约束生成失败与重试策略

## 能力清单

- AI 图片/故事/页面生成
- OCR / Smart Scan
- PDF/ZIP 导出与下载

## 关键流程

- 提交生成请求 → 扣费 → 生成结果 → 存储/引用
- 发起导出 → 生成文件 → 下载/分享

## 影响范围

- 相关模块：生成与导出
- 相关文档：`docs/v2/10-product/user/editor/create.md`

## 证据与验证

- 关键证据来源：`decodables/domains/generation/`、`decodables/domains/export/`、`decodables/api/user/generations.py`、`decodables/api/user/export.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
