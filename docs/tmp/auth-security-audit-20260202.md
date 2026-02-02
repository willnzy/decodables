# 自托管认证系统完整安全审计报告

**审计日期**: 2026-02-02
**审计范围**: 后端 auth domain + API 路由 + 前端 auth 抽象层/页面/BFF/中间件
**代码总量**: ~6,200 行 (后端 ~3,400 行, 前端 ~2,800 行)

---

## 总览

| 严重等级 | 后端 | 前端 | 合计 |
|---------|------|------|------|
| **CRITICAL** | 4 | 2 | **6** |
| **HIGH** | 8 | 5 | **13** |
| **MEDIUM** | 15 | 10 | **25** |
| **LOW** | 7 | 8 | **15** |
| **合计** | 34 | 25 | **59** |

---

## CRITICAL 问题 (6个)

### C1. OTP 验证存在时序攻击 [后端]
- **文件**: `service.py:259, 675, 793`
- **问题**: OTP hash 比较使用 `!=` 而非常量时间比较，攻击者可通过响应时间差异推断 hash 前缀
- **修复**: 使用 `hmac.compare_digest(input_hash, auth_user.otp_code_hash)`

### C2. JWT Token 中 role/tier 硬编码 [后端]
- **文件**: `service.py:522-523, 1104-1105, 1132-1133`
- **问题**: 所有 access token 都硬编码 `role="user"`, `tier="t1"`，管理员和付费用户的 JWT 不反映真实权限
- **修复**: 签发 token 前从 profile 查询实际 role 和 tier

### C3. 密码重置 OTP 验证后未清除 [后端]
- **文件**: `service.py:758-811`
- **问题**: `verify_password_reset_otp()` 成功后未调用 `clear_otp()`，同一 OTP 可在有效期内重复验证生成多个 token
- **修复**: 成功验证后添加 `await self._auth_user_repo.clear_otp(auth_user.id)`

### C4. 注册步骤2→3缺少密码学绑定 [后端]
- **文件**: `service.py:274-279, 316-321`
- **问题**: 步骤2返回明文 `user_id`，步骤3仅检查 `is_registered`，攻击者猜到 UUID 即可劫持注册
- **修复**: 步骤2应返回 purpose JWT（`create_purpose_token(user_id, "register")`），步骤3验证此 token
- **备注**: router.py 已使用 `register_token`，但 service 层的 `complete_registration` 直接接受 `user_id` 参数，需核实调用链

### C5. BFF 代理无 action 白名单 [前端]
- **文件**: `app/api/auth/[...action]/route.ts:56`
- **问题**: URL action 参数直接拼接到后端 URL，可能被路径遍历攻击访问非预期端点
- **修复**: 添加允许的 action 白名单 (如 `["register/send-otp", "login", "refresh", ...]`)

### C6. BroadcastChannel 明文广播 access token [前端]
- **文件**: `tokenManager.ts:120-128`
- **问题**: 跨 tab 同步时广播完整 JWT，同源恶意脚本/扩展可监听获取
- **修复**: 改为广播 "需要刷新" 信号而非 token 本身

---

## HIGH 问题 (13个)

### H1. 注册流程存在邮箱枚举 [后端]
- **文件**: `service.py:164-167`
- **问题**: 邮箱已注册时返回 `EmailAlreadyExistsException`，暴露邮箱注册状态
- **修复**: 改为统一返回（如密码重置流程的处理方式）

### H2. Token 双密钥轮换异常处理不一致 [后端]
- **文件**: `token_service.py:193-203`
- **问题**: `_decode_jwt` 对过期 token 直接抛异常而非返回 None，导致旧密钥签发的过期 token 无法走 fallback 路径

### H3. 一次性邮箱黑名单太小 [后端]
- **文件**: `service.py:65-73`
- **问题**: 仅 ~28 个域名，实际一次性邮箱服务有上万个

### H4. Session 限制存在 TOCTOU 竞态 [后端]
- **文件**: `service.py:1141-1148`
- **问题**: count→revoke 不是原子操作，并发登录可超出 session 限制

### H5. Logout 端点无需认证 [后端]
- **文件**: `router.py:332-339`
- **问题**: 任何获得 refresh_token 的人都可以撤销会话，无需提供 access token

### H6. Logout/sessions 端点缺少限流 [后端]
- **文件**: `router.py:332, 519, 529, 542`
- **问题**: logout, logout-all, sessions 列表, session 撤销均无 `@limiter.limit()`

### H7. X-Forwarded-For 可被伪造绕过限流 [后端]
- **文件**: `router.py:100-107`
- **问题**: 盲信 X-Forwarded-For 首项，未经反代清洗

### H8. Purpose token 不支持双密钥轮换 [后端]
- **文件**: `token_service.py:324-342`
- **问题**: `verify_purpose_token` 只验证当前密钥，密钥轮换时进行中的注册/重置流程会中断

### H9. localStorage fallback 持久存储 token [前端]
- **文件**: `tokenManager.ts:327-330`
- **问题**: BroadcastChannel 不可用时 token 写入 localStorage 且永不清理，违背 "内存存储" 的安全设计

### H10. Cookie path=/api/auth 导致中间件路由保护失效 [前端]
- **文件**: `route.ts:104`, `middleware.ts:77`
- **问题**: refresh_token cookie path 限制为 `/api/auth`，中间件在页面路由上检查此 cookie 永远为 false
- **影响**: 未登录用户可直接访问 /dashboard 等受保护页面；已登录用户不会被重定向离开 /login
- **修复**: 将 cookie path 改为 `/` 或中间件采用其他检测机制

### H11. BFF 代理无 CSRF 保护 [前端]
- **文件**: `route.ts:28-115`
- **问题**: 无 CSRF token 或 Origin 头验证，sameSite:lax 仅提供有限保护

### H12. 服务端代码使用 NEXT_PUBLIC_ 环境变量 [前端]
- **文件**: `server.ts:15`, `route.ts:16`
- **问题**: 后端 URL 使用 `NEXT_PUBLIC_API_BASE_URL`，暴露在客户端 JS bundle 中

### H13. 跨 tab 刷新存在竞态条件 [前端]
- **文件**: `tokenManager.ts:165-197`
- **问题**: broadcast resolver 生命周期与 refresh promise 协调不当

---

## MEDIUM 问题 (25个)

| ID | 位置 | 文件 | 问题描述 |
|----|------|------|---------|
| M1 | 后端 | email_service.py:50 | resend.api_key 全局设置，多实例冲突 |
| M2 | 后端 | email_service.py:117 | 异步方法内同步调用 resend SDK，阻塞事件循环 |
| M3 | 后端 | session.py:176 | session_limit_exceeded 硬编码特判，未加入 VALID_REVOKE_REASONS |
| M4 | 后端 | service.py:319-321 | complete_registration 未验证 OTP 已通过 |
| M5 | 后端 | service.py:829-832 | reset_password 未验证 forgot_password OTP purpose |
| M6 | 后端 | value_objects.py:30-33 | 邮箱正则不强制 TLD（`user@a` 可通过） |
| M7 | 后端 | service.py:270,685,803 | OTP_MAX_ATTEMPTS 重复 lazy import |
| M8 | 后端 | service.py:204,636,722,754 | 日志中明文记录用户邮箱（PII 泄露） |
| M9 | 后端 | service.py:994 | 删除账号后日志记录 user_id（GDPR 问题） |
| M10 | 后端 | schemas.py:54 | LoginRequest.password 无 max_length（argon2 DoS） |
| M11 | 后端 | schemas.py:117 | current_password 无 max_length |
| M12 | 后端 | router.py:346-389 | /otp/send 混合认证模型 |
| M13 | 后端 | __init__.py:1-18 | 端点文档过时 |
| M14 | 后端 | rate_limiter.py:131,155 | 字符串匹配异常类型，脆弱 |
| M15 | 后端 | rate_limiter.py:134,159 | 限流配置泄露在错误响应中 |
| M16 | 前端 | login/page.tsx:41-48 | 重定向 URL 校验可被协议相对URL绕过 |
| M17 | 前端 | authStore.ts:18-27 | 客户端解码 JWT 未验签名 |
| M18 | 前端 | PasswordStrengthIndicator.tsx | 密码不要求特殊字符 |
| M19 | 前端 | login/page.tsx:68-92 | 登录页无 429 限流响应处理 |
| M20 | 前端 | register+forgot-password | useResendCountdown 重复代码 |
| M21 | 前端 | register+forgot-password | useResendCountdown 卸载时未清理 interval |
| M22 | 前端 | AuthProvider.tsx:61-64 | 无全局 auth loading 态，存在 FOUC |
| M23 | 前端 | register/page.tsx:432-543 | 注册步骤3无返回按钮 |
| M24 | 前端 | OtpInput.tsx:151-174 | OTP 输入无 aria-label |
| M25 | 前端 | tokenManager.ts:339-341 | SSR null 导出可产生无意义错误 |

---

## 优先修复建议

### 第一优先级（立即修复）
1. **C1** OTP 时序攻击 → `hmac.compare_digest`
2. **C3** 密码重置 OTP 未清除 → 添加 `clear_otp`
3. **C5** BFF 无白名单 → 添加 action allowlist
4. **H10** Cookie path 导致中间件失效 → 改 cookie path 为 `/`

### 第二优先级（本周修复）
5. **C2** role/tier 硬编码 → 查询 profile 后签发 token
6. **C6** 广播 token → 改为信号模式
7. **H9** localStorage token → 清理或移除 fallback
8. **H11** CSRF 保护 → 添加 Origin 头校验
9. **M10/M11** password max_length → schemas 添加 `max_length=128`

### 第三优先级（后续迭代）
10. **H1** 邮箱枚举 → 统一注册响应
11. **H6** 端点限流 → 补充 @limiter.limit
12. **M8** 日志 PII → 邮箱脱敏
13. **其余 MEDIUM/LOW** 逐步修复
