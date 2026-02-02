# 自托管认证系统深度安全审计报告 v2

**审计日期**: 2026-02-02 (第二轮深度审计)
**审计范围**: 后端 auth domain + API 路由 + 前端 auth 抽象层/页面/BFF/中间件
**代码总量**: ~6,200 行 (后端 ~3,400 行, 前端 ~2,800 行)
**审计方法**: 逐文件人工逐行审查，非自动化扫描

---

## 总览

| 严重等级 | 后端 | 前端 | 合计 |
|---------|------|------|------|
| **CRITICAL** | 4 | 2 | **6** |
| **HIGH** | 7 | 6 | **13** |
| **MEDIUM** | 12 | 8 | **20** |
| **LOW** | 5 | 6 | **11** |
| **合计** | 28 | 22 | **50** |

---

## CRITICAL 问题 (6个)

### C1. OTP 验证存在时序攻击 [后端] ⚠️ 确认
- **文件**: `service.py:259, 675, 793`
- **问题**: OTP hash 比较使用 `!=` (Python `str.__ne__`)，攻击者可通过响应时间差异逐字节推断 hash
- **场景**: `verify_registration_otp`, `verify_authenticated_otp`, `verify_password_reset_otp` 三处均使用 `input_hash != auth_user.otp_code_hash`
- **影响**: 理论上可通过大量请求统计推断 SHA-256 hash 前缀，但 OTP 有效期 10 分钟 + 最多 5 次尝试限制了利用窗口
- **修复**: `import hmac; hmac.compare_digest(input_hash, auth_user.otp_code_hash)`

### C2. JWT Token 中 role/tier 硬编码为 "user"/"t1" [后端] ⚠️ 确认
- **文件**: `service.py:522-523, 1104-1105, 1132-1133`
- **问题**: 所有 access token 都硬编码 `role="user"`, `tier="t1"`，管理员和付费用户的 JWT claims 不反映真实权限
- **影响**: 依赖 JWT claims 做前端权限判断的代码会一直显示 Free Plan，管理员功能无法通过 JWT 判断
- **连锁影响**: 前端 `useUser.ts:41` 会 fallback 到 `payload.tier || 't1'`，如果 useUserStore 数据尚未加载，所有用户都显示为 t1
- **修复**: 签发 token 前从 profile 查询实际 role 和 tier
- **备注**: 代码中有 `# TODO: get from profile` 注释，确认是已知未完成项

### C3. 密码重置 OTP 验证后未清除 [后端] ⚠️ 确认
- **文件**: `service.py:758-811`
- **问题**: `verify_password_reset_otp()` 成功后未调用 `clear_otp()`，但 `verify_authenticated_otp()` (line 690) 有清除
- **差异对比**:
  - `verify_authenticated_otp` (line 690): ✅ 有 `await self._auth_user_repo.clear_otp(user_id)`
  - `verify_password_reset_otp` (line 807-811): ❌ 只返回结果，未清除
- **影响**: 同一 OTP 可在 10 分钟有效期内重复验证，生成多个 otp_verified_token
- **修复**: 在 line 807 前添加 `await self._auth_user_repo.clear_otp(auth_user.id)`

### C4. 注册步骤2返回的 register_token 已有密码学绑定 [后端] ✅ 修正前次判断
- **前次审计**: 认为步骤2→3缺少密码学绑定
- **实际代码**: `router.py:190-194` 使用 `token_service.create_purpose_token(user_id, purpose="register")` 创建 JWT
- **router.py:225-228**: 步骤3用 `verify_purpose_token(token, expected_purpose="register")` 验证
- **结论**: ✅ 已有正确的密码学绑定，前次审计判断有误。**此项从 CRITICAL 降级为已解决**
- **但注意**: `service.py:complete_registration` 的 `user_id` 参数来自 JWT 验证后的值，service 层本身不再做额外验证，这是安全的设计

### C5. BFF 代理无 action 白名单 [前端] ⚠️ 确认
- **文件**: `app/api/auth/[...action]/route.ts:33,56`
- **问题**: `actionParts.join('/')` 直接拼接到 `${BACKEND_URL}/api/v2/auth/${action}`，无白名单校验
- **攻击向量**: 请求 `/api/auth/../users/admin` 可能路径遍历到其他后端端点
- **实际影响评估**: 取决于后端路由配置；`..` 在 URL path 中通常被 HTTP 框架标准化，但仍应防御
- **修复**: 添加 action 白名单:
  ```typescript
  const ALLOWED_ACTIONS = new Set([
    'login', 'refresh', 'logout', 'logout-all',
    'register/send-otp', 'register/verify-otp', 'register/complete',
    'otp/send', 'otp/verify',
    'forgot-password/reset', 'change-password', 'delete-account',
  ])
  if (!ALLOWED_ACTIONS.has(action)) {
    return NextResponse.json({ detail: 'Unknown action' }, { status: 404 })
  }
  ```

### C6. BroadcastChannel 明文广播 access token [前端] ⚠️ 确认
- **文件**: `tokenManager.ts:120-128, 227, 324-331`
- **问题**: 跨 tab 同步时 `broadcast({ type: 'token_refreshed', token: newToken })` 广播完整 JWT
- **攻击面**: 同源恶意脚本/浏览器扩展可监听 BroadcastChannel 获取 token
- **localStorage fallback** (line 329): 更严重，token 被写入 `localStorage`，持久化存储
- **修复方案**: 改为广播 "需要刷新" 信号 `{ type: 'token_refreshed' }`，接收方自行调用 refresh 获取新 token

---

## HIGH 问题 (13个)

### H1. 注册流程存在邮箱枚举 [后端] ⚠️ 确认
- **文件**: `service.py:164-167`
- **问题**: 邮箱已注册时 raise `EmailAlreadyExistsException`，409 响应暴露邮箱注册状态
- **对比**: 密码重置流程 (line 701-756) 正确使用了统一响应 "If an account exists..."
- **影响**: 攻击者可批量探测哪些邮箱已注册
- **修复**: 注册也返回统一响应（但需前端配合处理）

### H2. Token 双密钥轮换: 过期 token 直接抛异常 [后端] ⚠️ 确认
- **文件**: `token_service.py:200-201`
- **问题**: `_decode_jwt` 中 `jwt.ExpiredSignatureError` 直接 `raise TokenExpiredException()` 而非 return None
- **影响**: 旧密钥签发的**过期** token 在密钥轮换时无法 fallback 到旧密钥验证（因为第一次尝试新密钥就抛出过期异常了）
- **场景**: 用户有旧密钥签发的 token → 管理员轮换密钥 → token 过期 → 新密钥验证失败抛 ExpiredSignatureError → 旧密钥 fallback 不执行
- **修复**: 过期错误也应 return None，让 fallback 尝试旧密钥

### H3. 一次性邮箱黑名单太小 [后端] 确认但降级
- **文件**: `service.py:65-73`
- **问题**: 仅 ~28 个域名
- **降级理由**: 这是辅助防护，不是安全关键。可后续接入第三方 API 增强

### H4. Session 限制的 TOCTOU 竞态 [后端] ⚠️ 确认
- **文件**: `service.py:1141-1148`
- **问题**: `count_active_by_user` → `revoke_oldest_by_user` 不是原子操作
- **影响**: 并发登录时可能超出 10 个 session 限制

### H5. Logout 端点无需 access token 认证 [后端] ⚠️ 确认
- **文件**: `router.py:332-339`
- **问题**: `logout` 端点只需 `refresh_token`，不要求 `Authorization: Bearer` 头
- **影响**: 获得 refresh_token 的攻击者可以撤销会话（但 refresh_token 存在 httpOnly cookie 中，实际利用需要先窃取 cookie）
- **评估**: 实际风险较低，因为 refresh_token 是 httpOnly cookie

### H6. 部分端点缺少限流 [后端] ⚠️ 确认
- **文件**: `router.py:332,519,529,542`
- **缺少 @limiter.limit 的端点**:
  - `POST /auth/logout` (line 332) — 无限流
  - `POST /auth/logout-all` (line 519) — 无限流
  - `GET /auth/sessions` (line 529) — 无限流
  - `DELETE /auth/sessions/{id}` (line 542) — 无限流
- **影响**: 认证端点可被频繁调用，虽然需要 JWT 认证，但仍可被 DoS

### H7. X-Forwarded-For 可被伪造 [后端] ⚠️ 确认
- **文件**: `router.py:100-107`
- **问题**: `forwarded.split(",")[0].strip()` 盲信 X-Forwarded-For 首项
- **影响**: 未经反代清洗时，客户端可伪造 IP 绕过 IP-based 限流
- **前端也转发**: `route.ts:65` BFF 代理也直接转发 X-Forwarded-For

### H8. Purpose token 不支持双密钥轮换 [后端] ⚠️ 确认
- **文件**: `token_service.py:324-342`
- **问题**: `verify_purpose_token` 只用当前密钥 `self._jwt_secret` 验证，没有 fallback 到 `_jwt_secret_old`
- **影响**: JWT 密钥轮换时，进行中的注册/重置流程的 purpose token 会立即失效

### H9. localStorage fallback 持久存储 token [前端] ⚠️ 确认
- **文件**: `tokenManager.ts:329`
- **问题**: BroadcastChannel 不可用时 `localStorage.setItem(AUTH_SYNC_STORAGE_KEY, JSON.stringify(message))` 写入包含 token 的消息
- **影响**: token 被持久化存储，违背 "内存存储" 的安全设计，且 **永不清理**
- **修复**: 要么不在 localStorage 存 token（只存信号），要么写入后立即 removeItem

### H10. Cookie path=/api/auth 导致中间件路由保护完全失效 [前端] ⚠️ 确认 — 最严重的前端问题
- **文件**: `route.ts:104`, `middleware.ts:77`
- **详细分析**:
  - `route.ts:104`: `res.cookies.set(REFRESH_COOKIE_NAME, ..., { path: '/api/auth' })`
  - `middleware.ts:77`: `req.cookies.has('refresh_token')` — middleware 运行在所有页面路由上
  - cookie path 限制为 `/api/auth`，浏览器**不会**在 `/dashboard` 等页面路由中发送此 cookie
  - 因此 `req.cookies.has('refresh_token')` 在所有非 `/api/auth/*` 的路由上**永远为 false**
- **后果**:
  1. 未登录用户可直接访问 `/dashboard` 等受保护页面（不会被重定向到 /login）
  2. 已登录用户访问 `/login` 不会被重定向到 /dashboard
  3. 中间件的 auth 路由保护形同虚设
- **修复**: 将 cookie path 改为 `/`

### H11. BFF 代理无 CSRF 保护 [前端] ⚠️ 确认
- **文件**: `route.ts:28-115`
- **问题**: 无 CSRF token、无 Origin 头验证、无 custom header 要求
- **评估**: `sameSite: 'lax'` cookie 提供了对 GET 请求的保护，但 POST 请求（所有 auth 操作）在某些跨站场景下仍可能被触发
- **修复**: 添加 Origin 头验证或要求自定义 header (如 `X-Requested-With`)

### H12. NEXT_PUBLIC_ 环境变量暴露后端 URL [前端]
- **文件**: `server.ts:15`, `route.ts:16`
- **问题**: `NEXT_PUBLIC_API_BASE_URL` 使用 NEXT_PUBLIC_ 前缀，值会被打包到客户端 JS bundle
- **影响**: 后端内部 URL 暴露给前端，攻击者可直接绕过 BFF 代理访问后端
- **修复**: 改为 `API_BASE_URL`（不带 NEXT_PUBLIC_ 前缀）

### H13. 跨 tab 刷新竞态条件 [前端] ⚠️ 确认
- **文件**: `tokenManager.ts:165-197`
- **问题**: `_pendingBroadcastResolver` 生命周期与 `refreshPromise` 不完全同步
- **场景**: Tab A 开始 refresh → 等待 300ms → Tab B broadcast 新 token → resolver 触发 → 但 Tab A 的 doRefresh 可能已经发出请求
- **影响**: 多余的 refresh 请求可能触发 reuse detection（虽然有 grace period 缓解）

---

## MEDIUM 问题 (20个)

### 后端 (12个)

| ID | 文件 | 问题 |
|----|------|------|
| M1 | `email_service.py:50` | `resend.api_key = resend_api_key` 全局设置，多实例时会冲突 |
| M2 | `email_service.py:117` | async 方法内同步调用 `resend.Emails.send()`，阻塞事件循环 |
| M3 | `session.py:176` | `reason != "session_limit_exceeded"` 硬编码特判，但 `REVOKE_REASON_SESSION_LIMIT` 常量值就是这个字符串 — 应直接加入 `VALID_REVOKE_REASONS` |
| M4 | `service.py:316-321` | `complete_registration` 只检查 `is_registered`，未验证 OTP 已通过（依赖 router 层用 purpose_token 保护） |
| M5 | `service.py:829-832` | `reset_password` 未验证当前 OTP purpose 是否为 forgot_password（依赖 router 层 purpose_token） |
| M6 | `value_objects.py:30-33` | 邮箱正则不强制 TLD (`user@a` 可通过)，缺少 `\.[a-zA-Z]{2,}$` |
| M7 | `service.py:270,685,803` | `from .constants import OTP_MAX_ATTEMPTS` 在函数内部重复 lazy import，应移至文件顶部 |
| M8 | `service.py:204,636,722,754` | 日志中明文记录用户邮箱 (PII 泄露风险) |
| M9 | `service.py:994` | 删除账号后 `logger.info(f"Account deleted for user {user_id}")` 记录 user_id (GDPR 问题) |
| M10 | `schemas.py:54` | `LoginRequest.password` 无 `max_length`，可发送超长密码触发 argon2 计算导致 DoS |
| M11 | `rate_limiter.py:131,155` | 字符串匹配异常类型 `"RateLimitExceeded" in str(type(e))` 非常脆弱 |
| M12 | `rate_limiter.py:134,159` | 限流配置 (`Limit: {limit_string}`) 泄露在 429 错误响应中 |

### 前端 (8个)

| ID | 文件 | 问题 |
|----|------|------|
| M13 | `login/page.tsx:41-48` | 重定向 URL 校验可被协议相对 URL 绕过 (`/\evil.com` → `/` 开头且不含 `//` 但仍可能被浏览器解析为跨域) |
| M14 | `authStore.ts:18-27` | 客户端解码 JWT 未验签名 (`atob(parts[1])`)，恶意 token 可伪造 userId |
| M15 | `PasswordStrengthIndicator.tsx` | 密码不要求特殊字符（与后端 `value_objects.py` 一致，非 bug 但可改进） |
| M16 | `login/page.tsx:68-92` | 登录页无 429 限流响应处理，被限流后只显示通用错误 |
| M17 | `register/page.tsx + forgot-password/page.tsx` | `useResendCountdown` 完全相同的 hook 重复定义了两次 |
| M18 | `register/page.tsx + forgot-password/page.tsx` | `useResendCountdown` 组件卸载时未清理 interval (`timerRef.current`) |
| M19 | `AuthProvider.tsx:61-64` | 无全局 auth loading 态，render children immediately 会导致 FOUC (Flash of Unauthenticated Content) |
| M20 | `tokenManager.ts:339-341` | SSR export `null as unknown as TokenManager` 可产生运行时 null 引用错误 |

---

## LOW 问题 (11个)

### 后端 (5个)

| ID | 文件 | 问题 |
|----|------|------|
| L1 | `constants.py:37-46` | 常用密码黑名单只有 ~40 个，应扩展或使用 `zxcvbn` 库 |
| L2 | `constants.py:126-132` | `VALID_REVOKE_REASONS` 缺少 `session_limit_exceeded` (在 Session.revoke 中需要硬编码特判) |
| L3 | `router.py:346-389` | `/otp/send` 端点混合公开/认证模型：`forgot_password` 公开，`change_password`/`delete_account` 需认证，但公共端口相同 |
| L4 | `__init__.py` | auth 模块端点文档列表可能过时 |
| L5 | `email_service.py:160-189` | 邮件模板内联 HTML，建议抽取为模板文件 |

### 前端 (6个)

| ID | 文件 | 问题 |
|----|------|------|
| L6 | `OtpInput.tsx` | OTP 输入框无 `aria-label`，无障碍不友好 |
| L7 | `register/page.tsx:432-543` | 注册步骤3缺少返回上一步按钮 |
| L8 | `forgot-password/page.tsx:185-187` | 成功后 `setTimeout(() => router.push('/login'), 2000)` — 组件卸载后可能仍执行 |
| L9 | `useUser.ts:43` | `emailVerified: true` 硬编码，应从 /user/me 响应获取 |
| L10 | `server.ts:35` | 请求后端 URL 路径是 `/api/v2/auth/refresh`，与 BFF 代理的 `/api/v2/auth/{action}` 一致，但需确认后端实际挂载路径 |
| L11 | `authApi.ts:53-57` | `authFetch` 所有请求都用 POST 方法，包括逻辑上应该是 GET 的 sessions 列表 |

---

## 与 v1 审计对比变更

| 前次 ID | 状态 | 说明 |
|---------|------|------|
| C4 (注册缺密码学绑定) | ✅ **降级/移除** | 实际代码已有 purpose JWT 绑定，前次判断有误 |
| H2 (过期 token 处理) | 保持 HIGH | 确认问题存在 |
| H3 (黑名单太小) | 降级 LOW | 辅助防护，非安全关键 |
| 其他所有问题 | 保持 | 逐行审查确认问题存在 |

**新增发现**:
- 无（本轮为更深入验证，主要修正了 C4 的误判）

---

## 优先修复建议（更新版）

### 第一优先级（立即修复 — 5 个最关键修复）

| 序号 | ID | 问题 | 修复工作量 | 修复方案 |
|------|-----|------|----------|---------|
| 1 | C1 | OTP 时序攻击 | 极小 | 3 处 `!=` → `hmac.compare_digest()` |
| 2 | C3 | 密码重置 OTP 未清除 | 极小 | 加 1 行 `clear_otp()` |
| 3 | C5 | BFF 无白名单 | 小 | 加 action 白名单集合 |
| 4 | H10 | Cookie path 导致中间件失效 | 极小 | `path: '/api/auth'` → `path: '/'` |
| 5 | M10 | LoginRequest.password 无 max_length | 极小 | 加 `max_length=128` |

### 第二优先级（本周修复 — 7 个）

| 序号 | ID | 问题 | 修复方案 |
|------|-----|------|---------|
| 6 | C2 | role/tier 硬编码 | 查询 profile 后签发 token |
| 7 | C6 | 广播 token | 改为信号模式 |
| 8 | H9 | localStorage token | 只存信号或写入后立即删除 |
| 9 | H2 | 过期 token 双密钥 | ExpiredSignatureError → return None |
| 10 | H8 | Purpose token 无双密钥 | 加 fallback 到旧密钥 |
| 11 | H11 | CSRF 保护 | 添加 Origin 头校验 |
| 12 | H12 | NEXT_PUBLIC 暴露后端 URL | 改为非 NEXT_PUBLIC 环境变量 |

### 第三优先级（后续迭代）

| 序号 | ID | 问题 |
|------|-----|------|
| 13 | H1 | 邮箱枚举 → 统一注册响应 |
| 14 | H6 | 补充端点限流 |
| 15 | M2 | Resend SDK 同步调用 → run_in_threadpool |
| 16 | M3+L2 | session_limit_exceeded 加入 VALID_REVOKE_REASONS |
| 17 | M6 | 邮箱正则强制 TLD |
| 18 | M8 | 日志 PII 脱敏 |
| 19 | M13 | 重定向 URL 校验增强 |
| 20 | M14 | 客户端 JWT 解码增加基础校验 |
| 21 | M17+M18 | useResendCountdown 提取为共享 hook + 清理 interval |
| 22 | 其余 LOW | 逐步修复 |

---

## 架构层面观察

### 正面评价
1. **目的明确的 token 设计**: register_token 和 otp_verified_token 使用 purpose JWT，多步流程之间有密码学绑定
2. **Token 族谱 reuse detection**: Session 的 family-based 检测设计合理，带 grace period
3. **Password 使用 argon2id**: 符合 OWASP 2024 推荐
4. **BFF 代理模式**: refresh_token 不暴露给客户端 JS（虽然 cookie path 配置有误）
5. **密码重置防枚举**: forgot-password 流程正确使用统一响应
6. **Access token 内存存储**: 不持久化到 localStorage（主路径正确）
7. **OTP 冷却 + 尝试限制**: 60 秒冷却 + 5 次最大尝试

### 需要注意的设计点
1. **service.py:complete_registration** 不验证 OTP 状态 — 依赖 router 层的 purpose_token 保护。这是有意的分层设计（service 层信任 router 已验证），但如果 service 被其他入口调用需要注意
2. **reset_password** 同样依赖 router 层的 purpose_token 保护，service 层不再验证 OTP
3. **双密钥轮换** 只实现了 access_token，purpose_token 和 OTP hash 没有双密钥支持
