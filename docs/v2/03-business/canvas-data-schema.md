 # Canvas 数据契约
 
 > 画布数据结构与字段约束的统一说明。
 
 **状态**: draft  
 **版本**: 0.1.0  
 **版本日期**: 2026-02-04  
 **最后复核**: 2026-02-04  
 **负责人**: Docs Working Group  
 **适用范围**: shared  
 **source_repo**: both  
 **sync_required**: yes  
 **来源/依据**: `decodables-fe/docs/shared/canvas-data-schema.md`, `decodables/docs/shared/canvas-data-schema.md`
 
 ---
 
## 背景

- 问题或机会: 画布结构口径不统一，易造成兼容与解析成本上升
- 目标与非目标: 目标是统一数据契约与字段语义；非目标是替代具体渲染实现

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- 统一 Canvas 数据模型与字段语义
- 明确前后端数据契约与兼容策略
- 降低结构漂移与解析成本

## 详细说明

- 范围: 画布根结构与元信息；元素/图层/资源引用；版本与兼容策略
- 关键约束: 必填字段与默认值；类型与枚举定义；扩展字段规范

## 影响范围

- 相关模块: 画布与数据契约
- 相关文档: `docs/v2/04-features/canvas-architecture.md`

## 证据与验证

- 关键证据来源：`decodables-fe/@core/`、`decodables/domains/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 结构对齐与信息补齐 | Docs Working Group |
