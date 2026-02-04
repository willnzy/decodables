# 注册页面体验

> 注册页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/(auth)/register/`

---

## 背景

- 问题或机会: 提供安全的注册与恢复已删除账号入口
- 目标与非目标: 目标是完成 OTP 验证并自动登录；非目标是直接登录既有账号

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 三步注册流程 + 可选账号恢复分支
- 必须遵循的规则: OTP 60 秒倒计时重发；密码强度校验；自动登录

## 详细说明

- 页面结构与关键区域:
  - Step 1: 输入邮箱 + 发送验证码
  - Step 1b: 账号恢复选择（如存在可恢复账号）
  - Step 2: OTP 输入 + 重发按钮/倒计时
  - Step 3: Display Name（可选）+ 密码/确认密码 + 强度提示
- 关键用户路径与状态:
  - `registerSendOtp(email)` 返回 `has_restorable_account` 时进入恢复选择
  - OTP 校验成功返回 `register_token`
  - `registerComplete` 成功后设置 token 并跳转 `/dashboard`
- 异常与提示:
  - `EMAIL_ALREADY_EXISTS` 提示去登录
  - OTP 过期/无效/尝试过多提示并重置
  - `TOKEN_EXPIRED` 需重新开始注册
- PC/Mobile 差异: 统一组件布局，暂未拆分移动端

## 影响范围

- 相关模块: user-experience/account
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/(auth)/register/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
