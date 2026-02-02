# 自托管认证系统安全审计报告 (最终版)

**审计日期**: 2026-02-02
**审计范围**: 后端 auth domain + API 路由 + 前端 auth 抽象层/页面/BFF/中间件
**代码总量**: ~6,200 行 (后端 ~3,400 行, 前端 ~2,800 行)
**审计方法**: 三轮逐行人工审查 + 交叉验证

---

## 审计过程说明

本报告经历三轮审计迭代:
- **v1**: 初次全面扫描，发现 59 个问题
- **v2**: 深度逐行审查，修正 C4 误判，精简为 50 个问题
- **v3 (本版)**: 逐条对照代码验证，移除 4 个误报，下调 6 个严重等级，最终确认 **34 个真实问题**

**已移除的误报**:

| 原 ID | 原始结论 | 误报原因 |
|--------|---------|---------|
| C4 (v1) | 注册步骤 2→3 缺少密码学绑定 | `router.py:190-194` 已使用 `create_purpose_token` 创建 JWT，步骤 3 用 `verify_purpose_token` 验证 |
| H2 (v2) | 双密钥轮换过期 token 处理异常 | `jwt.ExpiredSignatureError` 是正确行为 — 过期 token 应被拒绝；`jwt.InvalidSignatureError`（签名不匹配）才会触发旧密钥 fallback |
| M13 (v2) | 登录重定向可被 `javascript:` 绕过 | `router.push()` 是 Next.js 客户端导航，非浏览器跳转，不会执行 `javascript:` URL |
| M14 (v2) | 客户端 JWT 解码未验签名 | 业界标准做法 — 客户端解码仅用于展示，所有授权在服务端完成 |

---

## 总览

| 严重等级 | 后端 | 前端 | 合计 |
|---------|------|------|------|
| **CRITICAL** | 1 | 1 | **2** |
| **HIGH** | 4 | 4 | **8** |
| **MEDIUM** | 8 | 6 | **14** |
| **LOW** | 5 | 5 | **10** |
| **合计** | 18 | 16 | **34** |

---

## CRITICAL 问题 (2 个)

### C1. OTP Hash 比较存在时序攻击 [后端]

- **文件**: `domains/auth/service.py` 行 259, 675, 793
- **验证状态**: ✅ 已确认
- **问题**: OTP hash 比较使用 Python `!=` 而非常量时间比较，攻击者可通过响应时间差异逐字节推断 hash
- **涉及方法**:
  - `verify_registration_otp` (行 259)
  - `verify_authenticated_otp` (行 675)
  - `verify_password_reset_otp` (行 793)
- **风险评估**: 理论风险 — 5 次尝试限制 + 10 分钟 OTP 有效期大幅缩小了利用窗口，但修复成本极低，没有理由不修
- **修复**: 三处 `!=` 替换为 `hmac.compare_digest(input_hash, auth_user.otp_code_hash or "")`

```python
# 修复前
if input_hash != auth_user.otp_code_hash:

# 修复后
import hmac
if not hmac.compare_digest(input_hash, auth_user.otp_code_hash or ""):
```

---

### C2. Cookie path 配置错误导致中间件路由保护完全失效 [前端]

- **文件**: `decodables-fe/app/api/auth/[...action]/route.ts` 行 104, `middleware.ts` 行 77
- **验证状态**: ✅ 已确认 — 实际影响最大的 bug
- **问题**: refresh_token cookie 的 `path: '/api/auth'` 导致浏览器只在 `/api/auth/*` 路径发送此 cookie
- **根因分析**:
  - `route.ts:104`: `res.cookies.set(REFRESH_COOKIE_NAME, ..., { path: '/api/auth' })`
  - `middleware.ts:77`: `req.cookies.has('refresh_token')` — 在 `/dashboard` 等页面路由上**永远为 false**
- **后果**:
  1. 未登录用户可直接访问 `/dashboard` 等受保护页面（不会被重定向到 /login）
  2. 已登录用户访问 `/login` 不会被重定向到 /dashboard
  3. 中间件的 auth 保护形同虚设
- **修复**: `path: '/api/auth'` → `path: '/'`

---

## HIGH 问题 (8 个)

### H1. X-Forwarded-For 可被伪造绕过限流 [后端+前端]

- **文件**: `api/auth/router.py` 行 100-107, `route.ts` 行 65-66
- **验证状态**: ✅ 已确认
- **问题**: 后端盲信 `X-Forwarded-For` 首项，BFF 代理也直接转发该 header
- **影响**: 攻击者可伪造 IP 绕过所有 IP-based 限流

```python
# 后端 — 盲信首项
def _get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()  # 攻击者可控
```

- **修复**: 使用 Railway/Vercel 提供的真实客户端 IP header，或配置 trusted proxy hops

---

### H2. JWT Token 中 role/tier 硬编码为 "user"/"t1" [后端]

- **文件**: `domains/auth/service.py` 行 522-523, 1104-1105, 1132-1133
- **验证状态**: ✅ 已确认，但影响有限
- **问题**: 所有 access token 硬编码 `role="user"`, `tier="t1"`（代码中有 `# TODO: get from profile` 注释）
- **实际影响**: **后端无任何授权决策依赖 JWT 的 role/tier** — `dependencies.py` 和 `get_current_auth_user_id()` 仅使用 `payload.sub` (user_id)。前端 `useUser.ts` 会 fallback 到 `useUserStore` 数据（来自 `/user/me`），JWT 中的值仅作为加载前的临时 fallback
- **为何 HIGH 而非 CRITICAL**: 不影响后端权限判断，仅影响前端在 `/user/me` 加载前的短暂展示

```python
access_token = self._token_svc.create_access_token(
    user_id=user.id, email=user.email,
    role="user",   # TODO: get from profile  ← 硬编码
    tier="t1",     # TODO: get from profile  ← 硬编码
)
```

- **修复**: 签发 token 前从用户 profile 查询实际 role 和 tier

---

### H3. BFF 代理无 CSRF 保护 [前端]

- **文件**: `decodables-fe/app/api/auth/[...action]/route.ts` 行 28-115
- **验证状态**: ✅ 已确认
- **问题**: 无 CSRF token、无 Origin 头验证、无 custom header 要求
- **缓解因素**: `sameSite: 'lax'` cookie 阻止了跨站 `<form>` POST，但不防御同站子域攻击
- **修复**: 添加 Origin 头校验或要求自定义 header (如 `X-Requested-With: XMLHttpRequest`)

---

### H4. Logout/sessions 端点缺少限流 [后端]

- **文件**: `api/auth/router.py` 行 332, 519, 529, 542
- **验证状态**: ✅ 已确认
- **问题**: 以下端点均无 `@limiter.limit()`:
  - `POST /auth/logout` (行 332)
  - `POST /auth/logout-all` (行 519)
  - `GET /auth/sessions` (行 529)
  - `DELETE /auth/sessions/{id}` (行 542)
- **修复**: 补充限流装饰器

---

### H5. LoginRequest.password 无 max_length [后端]

- **文件**: `api/auth/schemas.py` 行 54
- **验证状态**: ✅ 已确认
- **问题**: `LoginRequest.password: str` 无 `max_length`，可发送 1MB+ 密码触发 argon2id 计算导致 DoS
- **对比**: `CompleteRegistrationRequest` (行 42) 正确设置了 `max_length=128`

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str  # ← 无 max_length
```

- **修复**: `password: str = Field(..., min_length=1, max_length=128)`

---

### H6. Purpose token 不支持双密钥轮换 [后端]

- **文件**: `domains/auth/token_service.py` 行 324-334
- **验证状态**: ✅ 已确认
- **问题**: `verify_purpose_token` 只用当前密钥验证，没有 fallback 到 `_jwt_secret_old`
- **影响**: JWT 密钥轮换时，进行中的注册/密码重置流程的 purpose token 会立即失效
- **对比**: `verify_access_token` 和 `_decode_jwt` 已支持双密钥 fallback
- **修复**: 添加类似 `_decode_jwt` 的旧密钥 fallback 逻辑

---

### H7. localStorage fallback 持久存储 token [前端]

- **文件**: `decodables-fe/lib/auth/tokenManager.ts` 行 329
- **验证状态**: ✅ 已确认
- **问题**: BroadcastChannel 不可用时，跨 tab 同步 fallback 到 localStorage，明文持久存储 access token
- **澄清**: BroadcastChannel 本身是同源限制的（v2 的 C6 高估了风险），**真正的问题是 localStorage fallback**:
  - token 以明文持久存储，可在浏览器重启后存活
  - 写入后**永不清理**
  - XSS 可直接读取

```typescript
// 问题代码
localStorage.setItem(AUTH_SYNC_STORAGE_KEY, JSON.stringify(message))
// message = { type, token, timestamp } — token 明文
```

- **修复**: 改为只广播信号（不含 token），或写入后立即 `removeItem`

---

### H8. 服务端代码使用 NEXT_PUBLIC_ 环境变量 [前端]

- **文件**: `decodables-fe/lib/auth/server.ts`, `route.ts` 行 16
- **验证状态**: ✅ 已确认
- **问题**: `NEXT_PUBLIC_API_BASE_URL` 使用 `NEXT_PUBLIC_` 前缀，值会被打包到客户端 JS bundle
- **影响**: 后端内部 URL 暴露，攻击者可绕过 BFF 代理直接访问后端
- **修复**: 服务端代码改用 `API_BASE_URL`（不带 `NEXT_PUBLIC_` 前缀）

---

## MEDIUM 问题 (14 个)

### M1. BFF 代理无 action 白名单 [前端]

- **文件**: `route.ts` 行 33, 56
- **验证状态**: ✅ 已确认，但风险低于初始评估
- **问题**: `actionParts.join('/')` 直接拼接到后端 URL，无白名单
- **为何 MEDIUM**: Next.js 标准化路径（阻止 `../` 遍历），FastAPI 只响应已定义路由，但仍允许探测 `/api/v2/auth/*` 下的任意路径
- **修复**: 添加 `ALLOWED_ACTIONS` 白名单

```typescript
const ALLOWED_ACTIONS = new Set([
  'login', 'refresh', 'logout', 'logout-all',
  'register/send-otp', 'register/verify-otp', 'register/complete',
  'otp/send', 'otp/verify',
  'forgot-password/reset', 'change-password', 'delete-account',
  'sessions',
])
if (!ALLOWED_ACTIONS.has(action)) {
  return NextResponse.json({ detail: 'Unknown action' }, { status: 404 })
}
```

---

### M2. 密码重置 OTP 验证后未清除 [后端]

- **文件**: `domains/auth/service.py` 行 807-811
- **验证状态**: ✅ 已确认，但窗口很窄
- **问题**: `verify_password_reset_otp()` 成功后未调用 `clear_otp()`
- **对比**: `verify_authenticated_otp()` (行 690) **有** `clear_otp()`
- **缓解**: `reset_password` → `update_password` (仓库层 `auth_user_repository.py:296-315`) **会**清除 OTP 字段
- **窗口**: 仅在 verify 和 reset 两次调用之间，同一 OTP 可被重复验证获取多个 `otp_verified_token`（每个 10 分钟有效期，绑定 purpose）
- **修复**: 在 `verify_password_reset_otp` 成功后添加 `await self._auth_user_repo.clear_otp(auth_user.id)`

---

### M3. 账号锁定无自动解锁机制 [后端]

- **文件**: `domains/auth/service.py`, `domains/auth/auth_user.py`
- **验证状态**: ✅ 已确认
- **问题**: 达到 `LOGIN_MAX_FAILED_ATTEMPTS` (10) 后账号永久锁定，无 TTL 自动解锁
- **修复**: 添加 `locked_until` 时间戳，可配置解锁时长（如 30 分钟）

---

### M4. Refresh token 存储为 SHA-256 hash [后端]

- **文件**: `domains/auth/token_service.py` `hash_token` 方法
- **验证状态**: ✅ 已确认 — 设计备注
- **问题**: SHA-256 是快速哈希，数据库泄露后 token 理论上可被暴力破解
- **缓解**: Refresh token 为 256-bit 随机值（URL-safe），暴力破解不可行
- **修复**: 低优先级。如需纵深防御可考虑 bcrypt/Argon2 哈希

---

### M5. 限流配置泄露在 429 响应中 [后端]

- **文件**: `infrastructure/rate_limiter.py` 行 135, 159
- **验证状态**: ✅ 已确认
- **问题**: `detail=f"Rate limit exceeded. Please try again later. (Limit: {limit_string})"` 暴露精确限流配置
- **修复**: 移除 `(Limit: {limit_string})` 后缀

---

### M6. Session 刷新无 IP/设备绑定验证 [后端]

- **文件**: `domains/auth/service.py` refresh 流程
- **验证状态**: ✅ 已确认 — 设计限制
- **问题**: Session 存储 `device_name` 和 `ip_address` 但刷新时不验证，被盗的 refresh token cookie 可从任何网络/设备使用
- **修复**: 可选的 IP/设备指纹验证，可配置严格程度

---

### M7. 注册流程邮箱枚举 [后端]

- **文件**: `domains/auth/service.py` `send_registration_otp` 行 164-167
- **验证状态**: ✅ 已确认 — 有意设计
- **问题**: 已注册邮箱会返回 `EmailAlreadyExistsException` (409)，暴露邮箱注册状态
- **对比**: 密码重置流程正确使用了统一响应 "If an account exists..."
- **评估**: 注册流程固有需要告知用户邮箱是否已被占用，可接受

---

### M8. 日志中明文记录用户邮箱 (PII) [后端]

- **文件**: `domains/auth/service.py` 行 204, 636, 722, 754
- **验证状态**: ✅ 已确认
- **问题**: 多处 `logger.info(f"... {email} ...")` 明文记录完整邮箱
- **修复**: 邮箱脱敏处理，如 `u***@example.com`

---

### M9. BFF 日志泄露后端错误详情 [前端]

- **文件**: `route.ts` 行 76
- **验证状态**: ✅ 已确认
- **问题**: `console.error(\`[BFF Auth] Failed to reach backend: ${error}\`)` 可能在生产日志中暴露完整错误堆栈
- **修复**: 仅记录 `error.message` 或脱敏版本

---

### M10. 邮箱正则不强制 TLD [后端]

- **文件**: `domains/auth/value_objects.py` 行 30-33
- **验证状态**: ✅ 已确认，但已被 API 层缓解
- **问题**: Domain 层的 Email 值对象正则不强制 TLD (`user@a` 可通过)
- **缓解**: 所有 API 端点使用 Pydantic `EmailStr`（校验 TLD），数据到达 domain 层之前已被过滤
- **修复**: 低优先级。可在 Email 值对象中增加 TLD 检查做纵深防御

---

### M11. 无 Content-Security-Policy 头 [前端]

- **文件**: Next.js 配置
- **验证状态**: ✅ 已确认
- **问题**: 未设置 CSP 头限制脚本来源，XSS 防护仅依赖 React 内置转义
- **修复**: 通过 `next.config.js` 或 middleware 添加 CSP 头

---

### M12. ChangePasswordRequest.current_password 无 max_length [后端]

- **文件**: `api/auth/schemas.py` 行 117
- **验证状态**: ✅ 已确认
- **问题**: 与 H5 同类型 Argon2 DoS 风险，但需要认证
- **修复**: `current_password: str = Field(..., min_length=1, max_length=128)`

---

### M13. session_limit_exceeded 未加入常量 [后端]

- **文件**: `domains/auth/constants.py` `VALID_REVOKE_REASONS`, `session.py` 行 176
- **验证状态**: ✅ 已确认
- **问题**: `session_limit_exceeded` 作为 revoke reason 使用但未在 `VALID_REVOKE_REASONS` 中定义，导致硬编码特判
- **修复**: 添加到 `VALID_REVOKE_REASONS`

---

### M14. email_service.py 同步调用阻塞事件循环 [后端]

- **文件**: `domains/auth/email_service.py` 行 ~117
- **验证状态**: ✅ 已确认
- **问题**: async 方法内同步调用 `resend.Emails.send()`，阻塞事件循环
- **修复**: 使用 `run_in_threadpool` 包装同步调用

---

## LOW 问题 (10 个)

### L1. Access token 15 分钟有效期 [后端]

- **文件**: `domains/auth/constants.py`
- **评估**: 信息性 — 15 分钟是业界标准

### L2. emailVerified 硬编码为 true [前端]

- **文件**: `decodables-fe/lib/auth/useUser.ts` 行 43
- **问题**: `emailVerified: true` 硬编码，应从 `/user/me` 获取实际验证状态

### L3. 无结构化安全事件审计日志 [后端]

- **问题**: 登录失败、密码变更、账号删除等安全事件未记录到专用审计表

### L4. dependencies.py 错误信息泄露 [后端]

- **文件**: `dependencies.py` 行 64
- **问题**: `raise UnauthorizedException(message=f"Invalid token: {e.message}")` 可能泄露内部细节（如 "Invalid token purpose", "Malformed token payload"）
- **修复**: 使用通用消息 `"Invalid token"`

### L5. container.py JWT 密钥空字符串 fallback [后端]

- **文件**: `container.py` 行 306
- **问题**: `getattr(config, 'AUTH_JWT_SECRET', None) or ''` 空字符串 fallback
- **缓解**: `config.py:validate_secrets_at_startup()` 验证 JWT 密钥长度 ≥ 43 字符，生产环境不会触发

### L6. Session TOCTOU 竞态 [后端]

- **文件**: `domains/auth/service.py` session 创建
- **问题**: Session 限制的 check-then-act 非原子操作，可能多 1-2 个 session
- **评估**: 良性竞态，不构成安全问题

### L7. config.py 日志泄露密钥长度 [后端]

- **文件**: `config.py` 行 96-98
- **问题**: `f"AUTH_JWT_SECRET too short: {len(AUTH_JWT_SECRET)} chars"` 泄露实际长度
- **修复**: 改为 `"AUTH_JWT_SECRET too short, minimum 43 chars required"`

### L8. 注册赠送积分非幂等 [后端]

- **文件**: `api/auth/router.py` 行 250 → `service.py` `complete_registration`
- **问题**: 理论上注册重复完成可能双倍赠送积分
- **缓解**: purpose token 实际为一次性使用，风险极低

### L9. useResendCountdown 重复代码 + 未清理 interval [前端]

- **文件**: `register/page.tsx`, `forgot-password/page.tsx`
- **问题**: 相同的 `useResendCountdown` hook 重复定义两次；组件卸载时未清理 interval
- **修复**: 抽取为共享 hook，添加 cleanup

### L10. 跨 tab 刷新竞态条件 [前端]

- **文件**: `decodables-fe/lib/auth/tokenManager.ts` 行 165-197
- **问题**: `_pendingBroadcastResolver` 与 `refreshPromise` 生命周期不完全同步
- **缓解**: Grace period 可缓解多余 refresh 请求触发 reuse detection

---

## 优先修复计划

### Phase 1 — 立即修复 (CRITICAL + 快速修复)

| # | ID | 问题 | 工作量 | 修复方案 |
|---|-----|------|--------|---------|
| 1 | **C2** | Cookie path 导致中间件失效 | 1 行 | `path: '/api/auth'` → `path: '/'` |
| 2 | **C1** | OTP 时序攻击 | 3 行 | `!=` → `hmac.compare_digest()` |
| 3 | **H5** | LoginRequest.password 无 max_length | 1 行 | 加 `max_length=128` |
| 4 | **M12** | current_password 无 max_length | 1 行 | 加 `max_length=128` |

### Phase 2 — 重要修复 (HIGH)

| # | ID | 问题 | 修复方案 |
|---|-----|------|---------|
| 5 | **H1** | X-Forwarded-For 可伪造 | 使用平台原生客户端 IP header |
| 6 | **H2** | role/tier 硬编码 | 签发 token 前查询 profile |
| 7 | **H3** | 无 CSRF 保护 | 添加 Origin 校验或 custom header |
| 8 | **H4** | Logout/sessions 无限流 | 补充 `@limiter.limit()` |
| 9 | **H6** | Purpose token 无双密钥 | 添加旧密钥 fallback |
| 10 | **H7** | localStorage token 泄露 | 广播信号而非 token / 写入后删除 |
| 11 | **H8** | NEXT_PUBLIC 暴露后端 URL | 改为 `API_BASE_URL` |

### Phase 3 — 加固 (MEDIUM + LOW)

| # | ID | 问题 |
|---|-----|------|
| 12 | **M1** | BFF 添加 action 白名单 |
| 13 | **M2** | verify_password_reset_otp 后 clear_otp |
| 14 | **M3** | 账号锁定添加自动解锁 |
| 15 | **M5** | 429 响应移除限流配置 |
| 16 | **M8** | 日志 PII 脱敏 |
| 17 | **M11** | 添加 CSP 头 |
| 18 | **M14** | email_service 异步改造 |
| 19 | **L4** | dependencies.py 错误信息脱敏 |
| 20 | 其余 | 逐步修复 |

---

## 架构评估

### 优点

1. **DDD 分层架构**: domain/service/repository 职责清晰
2. **Purpose token 设计**: register_token 和 otp_verified_token 使用 purpose JWT 绑定多步流程，设计合理
3. **密码安全**: Argon2id 哈希，符合 OWASP 2024 推荐
4. **Token 族谱 reuse detection**: family-based 检测 + grace period，设计成熟
5. **密码重置防枚举**: forgot-password 流程正确使用统一响应
6. **Access token 内存存储**: 主路径不持久化到 localStorage
7. **OTP 安全**: 60 秒冷却 + 5 次最大尝试 + 10 分钟有效期
8. **BFF 代理**: 正确剥离 refresh_token 不暴露给客户端 JS
9. **Rate limiting**: 所有敏感端点有限流（logout/sessions 除外）

### 需要改进

1. **Cookie path 配置错误**: 使中间件完全失效 (C2)
2. **无 CSRF 保护**: BFF 代理缺少 CSRF 防御 (H3)
3. **X-Forwarded-For 信任模型**: 不适合公网服务 (H1)
4. **localStorage fallback**: 违背内存存储安全设计 (H7)
5. **Schema 校验缺口**: 部分密码字段缺少 max_length (H5, M12)

### 总体评价

认证系统在架构设计上是健全的。CRITICAL 问题是实现层面的 bug（cookie path 配置、时序比较），而非架构缺陷。优先修复项多为 1 行代码改动但影响显著。建议按 Phase 1 → 2 → 3 顺序逐步修复。
