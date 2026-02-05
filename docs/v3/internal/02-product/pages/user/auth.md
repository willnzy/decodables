# 认证相关页面

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **对应代码**: `decodables-fe/app/(auth)/`

---

## 概述

用户认证相关的所有页面，包括登录、注册、密码重置等。

---

## 页面列表

### 登录页 (`/login`)
- 代码路径: `app/(auth)/login/page.tsx`
- 功能: 邮箱密码登录、OTP 登录

### 注册页 (`/register`)
- 代码路径: `app/(auth)/register/page.tsx`
- 功能: 新用户注册、邮箱验证

### 忘记密码 (`/forgot-password`)
- 代码路径: `app/(auth)/forgot-password/page.tsx`
- 功能: 发送密码重置邮件

### 重置密码 (`/reset-password`)
- 代码路径: `app/(auth)/reset-password/page.tsx`
- 功能: 设置新密码

### 邮箱验证 (`/verify-email`)
- 代码路径: `app/(auth)/verify-email/page.tsx`
- 功能: 验证邮箱地址

---

## 相关文档

- [认证模块技术设计](../../../04-engineering/modules/auth/)
- [用户体系](../../../05-business/user-system.md)
