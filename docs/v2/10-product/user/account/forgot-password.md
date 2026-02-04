# 忘记密码页面体验

> 忘记密码页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/(auth)/forgot-password/`

---

## 背景

- 问题或机会: 提供安全的密码找回入口，避免邮箱枚举风险
- 目标与非目标: 目标是完成 OTP 验证后重置密码；非目标是在此页面完成登录

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 三步 OTP 流程（Email → OTP → 新密码）
- 必须遵循的规则: 发送 OTP 始终返回成功提示；OTP 60 秒倒计时重发

## 详细说明

- 页面结构与关键区域:
  - Step 1: 输入邮箱 + 发送验证码按钮
  - Step 2: OTP 输入框 + 重发按钮/倒计时
  - Step 3: 新密码与确认密码 + 密码强度提示
  - 成功态: 重置成功提示，自动跳转登录
- 关键用户路径与状态:
  - Step 1 → Step 2: `sendOtp('forgot_password')`，无论成功与否均进入 OTP
  - Step 2 → Step 3: `verifyOtp` 返回 `otp_verified_token`
  - Step 3 → Success: `forgotPasswordReset` 成功后 2 秒跳转 `/login`
- 异常与提示:
  - OTP 过期/无效/尝试过多统一提示并重置 OTP
  - 新密码校验失败或确认不一致时阻止提交
  - 令牌过期要求重新开始流程
- PC/Mobile 差异: 统一组件布局，暂未拆分移动端

## 影响范围

- 相关模块: user-experience/account
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/(auth)/forgot-password/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
