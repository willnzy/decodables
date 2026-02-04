 # 自建认证系统设计
 
 > 自建认证体系的架构、流程与安全约束。
 
 **状态**: draft  
 **版本**: 0.1.0  
 **版本日期**: 2026-02-04  
 **最后复核**: 2026-02-04  
 **负责人**: Docs Working Group  
 **适用范围**: shared  
 **source_repo**: both  
 **sync_required**: yes  
 **来源/依据**: `decodables-fe/docs/shared/self-hosted-auth-design.md`, `decodables/docs/shared/self-hosted-auth-design.md`
 
 ---
 
## 背景
 
- 问题或机会: 待补充
- 目标与非目标: 待补充
 
## 设计约束（强制）
 
- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致
 
## 结论/规范/方案
 
- 统一认证流程与安全边界
- 明确 Token/Session/OTP 的职责
- 规范安全与审计要求

## 详细说明

- 认证流程: 注册 → 登录 → 刷新 → 退出
- 安全约束: 密钥管理；风险控制与限流

## 影响范围

- 相关模块: 待补充
- 相关文档: 待补充

## 证据与验证

- 关键证据来源：`decodables/domains/auth/`、`decodables-fe/@shared/auth/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
