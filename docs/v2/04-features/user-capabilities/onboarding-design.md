 # Onboarding 系统设计
 
 > 新手引导流程与体验策略说明。
 
 **状态**: draft  
 **版本**: 0.1.0  
 **版本日期**: 2026-02-04  
 **最后复核**: 2026-02-04  
 **负责人**: Docs Working Group  
 **适用范围**: shared  
 **source_repo**: both  
 **sync_required**: yes  
 **来源/依据**: `decodables-fe/docs/shared/onboarding-design.md`, `decodables/docs/shared/onboarding-design.md`
 
 ---
 
## 背景

- 需要统一新手引导策略与触发规则
- 明确关键路径完成标准

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标
 
 - 提升新手完成关键路径的成功率
 - 统一引导阶段与触发条件
 - 约束打扰频率与跳过策略
 
## 引导阶段
 
 - 注册 → 初次创建 → 首次导出
 
## 触发规则
 
 - 首次事件触发
 - 任务完成状态

## 影响范围

- 相关模块：Onboarding
- 相关文档：`docs/v2/04-features/user-capabilities/onboarding-design.md`

## 证据与验证

- 关键证据来源：`decodables/api/user/onboarding.py`、`decodables-fe/app/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
