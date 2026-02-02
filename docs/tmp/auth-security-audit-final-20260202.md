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
- **v3 (本版)**: 逐条对照代码验证，移除 5 个误报，下调 6 个严重等级，确认 **33 个真实问题**
- **方法论交叉**: 对照 23 维度审计方法论，新增 5 个问题 (S1-S5)
- **全系统交叉**: 对照 704-finding 全系统审计，新增 4 个问题 (T1-T4)
- **最终确认**: **42 个真实问题**

**已移除的误报**:

| 原 ID | 原始结论 | 误报原因 |
|--------|---------|---------|
| C4 (v1) | 注册步骤 2→3 缺少密码学绑定 | `router.py:190-194` 已使用 `create_purpose_token` 创建 JWT，步骤 3 用 `verify_purpose_token` 验证 |
| H2 (v2) | 双密钥轮换过期 token 处理异常 | `jwt.ExpiredSignatureError` 是正确行为 — 过期 token 应被拒绝；`jwt.InvalidSignatureError`（签名不匹配）才会触发旧密钥 fallback |
| M13 (v2) | 登录重定向可被 `javascript:` 绕过 | `router.push()` 是 Next.js 客户端导航，非浏览器跳转，不会执行 `javascript:` URL |
| M14 (v2) | 客户端 JWT 解码未验签名 | 业界标准做法 — 客户端解码仅用于展示，所有授权在服务端完成 |
| M3 (v3) | 账号锁定无自动解锁机制 | `auth_user.py:201-202` 已有 `locked_until = now + LOCKOUT_DURATION_MINUTES(30)`，`is_locked` 属性 (行 173-177) 基于时间自动解锁 |

---

## 总览

| 严重等级 | 后端 | 前端 | 跨层 | 合计 |
|---------|------|------|------|------|
| **CRITICAL** | 1 | 1 | 0 | **2** |
| **HIGH** | 6 | 3 | 1 | **10** |
| **MEDIUM** | 11 | 4 | 0 | **15** |
| **LOW** | 9 | 6 | 0 | **15** |
| **合计** | 27 | 14 | 1 | **42** |

> 含原始 33 个 (v3) + 方法论交叉 5 个 (S1-S5) + 全系统交叉 4 个 (T1-T4)

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

## MEDIUM 问题 (13 个)

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
])
if (!ALLOWED_ACTIONS.has(action)) {
  return NextResponse.json({ detail: 'Unknown action' }, { status: 404 })
}
```

> 注意: BFF 当前只 export `POST` handler。后端的 `GET /sessions` 和 `DELETE /sessions/{id}` 端点目前不经过 BFF 代理。实现 session 管理 UI 时需要添加对应的 GET/DELETE handler 并扩展白名单。

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

### M3. Refresh token 存储为 SHA-256 hash [后端]

- **文件**: `domains/auth/token_service.py` `hash_token` 方法
- **验证状态**: ✅ 已确认 — 设计备注
- **问题**: SHA-256 是快速哈希，数据库泄露后 token 理论上可被暴力破解
- **缓解**: Refresh token 为 256-bit 随机值（URL-safe），暴力破解不可行
- **修复**: 低优先级。如需纵深防御可考虑 bcrypt/Argon2 哈希

---

### M4. 限流配置泄露在 429 响应中 [后端]

- **文件**: `infrastructure/rate_limiter.py` 行 135, 159
- **验证状态**: ✅ 已确认
- **问题**: `detail=f"Rate limit exceeded. Please try again later. (Limit: {limit_string})"` 暴露精确限流配置
- **修复**: 移除 `(Limit: {limit_string})` 后缀

---

### M5. Session 刷新无 IP/设备绑定验证 [后端]

- **文件**: `domains/auth/service.py` refresh 流程
- **验证状态**: ✅ 已确认 — 设计限制
- **问题**: Session 存储 `device_name` 和 `ip_address` 但刷新时不验证，被盗的 refresh token cookie 可从任何网络/设备使用
- **修复**: 可选的 IP/设备指纹验证，可配置严格程度

---

### M6. 注册流程邮箱枚举 [后端]

- **文件**: `domains/auth/service.py` `send_registration_otp` 行 164-167
- **验证状态**: ✅ 已确认 — 有意设计
- **问题**: 已注册邮箱会返回 `EmailAlreadyExistsException` (409)，暴露邮箱注册状态
- **对比**: 密码重置流程正确使用了统一响应 "If an account exists..."
- **评估**: 注册流程固有需要告知用户邮箱是否已被占用，可接受

---

### M7. 日志中明文记录用户邮箱 (PII) [后端]

- **文件**: `domains/auth/service.py` 行 204, 636, 722, 754
- **验证状态**: ✅ 已确认
- **问题**: 多处 `logger.info(f"... {email} ...")` 明文记录完整邮箱
- **修复**: 邮箱脱敏处理，如 `u***@example.com`

---

### M8. BFF 日志泄露后端错误详情 [前端]

- **文件**: `route.ts` 行 76
- **验证状态**: ✅ 已确认
- **问题**: `console.error(\`[BFF Auth] Failed to reach backend: ${error}\`)` 可能在生产日志中暴露完整错误堆栈
- **修复**: 仅记录 `error.message` 或脱敏版本

---

### M9. 邮箱正则不强制 TLD [后端]

- **文件**: `domains/auth/value_objects.py` 行 30-34
- **验证状态**: ✅ 已确认，但已被 API 层缓解
- **问题**: Domain 层的 Email 值对象正则不强制 TLD (`user@a` 可通过)
- **缓解**: 所有 API 端点使用 Pydantic `EmailStr`（校验 TLD），数据到达 domain 层之前已被过滤
- **修复**: 低优先级。可在 Email 值对象中增加 TLD 检查做纵深防御

---

### M10. 无 Content-Security-Policy 头 [前端]

- **文件**: Next.js 配置
- **验证状态**: ✅ 已确认
- **问题**: 未设置 CSP 头限制脚本来源，XSS 防护仅依赖 React 内置转义
- **修复**: 通过 `next.config.js` 或 middleware 添加 CSP 头

---

### M11. ChangePasswordRequest.current_password 无 max_length [后端]

- **文件**: `api/auth/schemas.py` 行 117
- **验证状态**: ✅ 已确认
- **问题**: 与 H5 同类型 Argon2 DoS 风险，但需要认证
- **修复**: `current_password: str = Field(..., min_length=1, max_length=128)`

---

### M12. session_limit_exceeded 未加入常量 [后端]

- **文件**: `domains/auth/constants.py` `VALID_REVOKE_REASONS`, `session.py` 行 176
- **验证状态**: ✅ 已确认
- **问题**: `session_limit_exceeded` 作为 revoke reason 使用但未在 `VALID_REVOKE_REASONS` 中定义，导致硬编码特判
- **修复**: 添加到 `VALID_REVOKE_REASONS`

---

### M13. email_service.py 同步调用阻塞事件循环 [后端]

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

### L7. config.py 启动校验泄露密钥长度 [后端]

- **文件**: `config.py` 行 97-98
- **问题**: `raise ValueError(f"AUTH_JWT_SECRET too short: {len(AUTH_JWT_SECRET)} chars")` — ValueError 消息泄露实际密钥长度
- **修复**: 改为 `"AUTH_JWT_SECRET too short, minimum 43 chars required"`

### L8. 注册赠送积分非幂等 [后端]

- **文件**: `api/auth/router.py` 行 250 → `service.py` `complete_registration`
- **问题**: 理论上使用同一 purpose token 重复调用可能双倍赠送积分
- **缓解**: `service.py:320` 检查 `auth_user.is_registered` 阻止重复完成，RPC 为原子操作。风险极低

### L9. useResendCountdown 重复代码 + 未清理 interval [前端]

- **文件**: `register/page.tsx`, `forgot-password/page.tsx`
- **问题**: 相同的 `useResendCountdown` hook 重复定义两次；组件卸载时未清理 interval
- **修复**: 抽取为共享 hook，添加 cleanup

### L10. 跨 tab 刷新竞态条件 [前端]

- **文件**: `decodables-fe/lib/auth/tokenManager.ts` 行 ~199
- **问题**: `_pendingBroadcastResolver` (行 199) 与 `refreshPromise` 生命周期不完全同步
- **缓解**: Grace period 可缓解多余 refresh 请求触发 reuse detection

---

## 优先修复计划

### Phase 1 — 立即修复 (CRITICAL + 快速修复)

| # | ID | 问题 | 工作量 | 修复方案 |
|---|-----|------|--------|---------|
| 1 | **C2** | Cookie path 导致中间件失效 | 1 行 | `path: '/api/auth'` → `path: '/'` |
| 2 | **C1** | OTP 时序攻击 | 3 行 | `!=` → `hmac.compare_digest()` |
| 3 | **H5** | LoginRequest.password 无 max_length | 1 行 | 加 `max_length=128` |
| 4 | **M11** | current_password 无 max_length | 1 行 | 加 `max_length=128` |

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
| 12 | **T1** | JWT 缺少 iss/aud 验证 | 签发/验证添加 issuer + audience |
| 13 | **T2** | Sentry 未脱敏登录密码 | `_sanitize_sentry_event` 增加 body 脱敏 |

### Phase 3 — 加固 (MEDIUM + LOW)

| # | ID | 问题 |
|---|-----|------|
| 14 | **M1** | BFF 添加 action 白名单 |
| 15 | **M2** | verify_password_reset_otp 后 clear_otp |
| 16 | **M4** | 429 响应移除限流配置 |
| 17 | **M7** | 日志 PII 脱敏 |
| 18 | **M10** | 添加 CSP 头 |
| 19 | **M13** | email_service 异步改造 |
| 20 | **T3** | api_logs/error_logs 请求体脱敏 |
| 21 | **S1** | tokenManager 事件监听器清理 |
| 22 | **L4** | dependencies.py 错误信息脱敏 |
| 23 | **T4** | dependencies.py 异常静默吞没 |
| 24 | **S2-S4** | interval 泄漏 / AbortController / ErrorBoundary |
| 25 | **S5** | Repository 多记录检测 |
| 26 | 其余 | 逐步修复 |

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
5. **Schema 校验缺口**: 部分密码字段缺少 max_length (H5, M11)

### 总体评价

认证系统在架构设计上是健全的。CRITICAL 问题是实现层面的 bug（cookie path 配置、时序比较），而非架构缺陷。优先修复项多为 1 行代码改动但影响显著。建议按 Phase 1 → 2 → 3 顺序逐步修复。

---

## 方法论交叉审计补充 (2026-02-02)

> 参照 `decodables-fe/docs/tmp/20260130-audit-methodology.md` v3.2 的审计维度和检查清单，对本报告进行交叉验证。
> 认证/权限审计必选维度: 1-7, 5(重点), 12, 13, 19; 可选维度: 8-11; 专项 checklist: 4.1, 4.4, 5.4

### 维度覆盖分析

| 维度 | 名称 | 报告覆盖 | 备注 |
|------|------|---------|------|
| 1 | 代码错误 & 潜在 Bug | ✅ | C1, C2, M2, M12 |
| 2 | 逻辑缺失 / 逻辑错误 | ✅ | H2, H6, L2, L8 |
| 3 | 性能问题 | ⚠️ 补充 | M13 涵盖，新增发现见下 |
| 4 | 系统稳定性 / 可靠性 | ⚠️ 补充 | L6, L10 涵盖，新增内存泄漏见下 |
| 5 | 安全漏洞 | ✅ 重点 | C1, H1, H3, H5, H7, H8, M1, M4, M10 等 |
| 6 | 业界最佳实践 (DDD/架构) | ✅ | M3 (hash), M9 (邮箱), M12 (常量) |
| 7 | 代码复杂度 | ✅ | L9 (重复代码) |
| 8 | 前后端 API 契约 | ✅ | C2 (cookie path), M1 (BFF 白名单) |
| 9 | 竞态条件 | ✅ | L6, L10 |
| 10 | 内存泄漏 / 资源清理 | ⚠️ **新增** | 原报告未覆盖，见下 |
| 11 | TypeScript 类型安全 | ✅ | 未发现显著问题 |
| 12 | 后端服务层缺口 | ✅ | 架构评估已涵盖 |
| 13 | 其他 | ✅ | L2, L5, L7 |
| 19 | 启动校验 / 运行时配置 | ✅ | L5, L7; config.py 启动校验已确认完备 |

### 补充发现 (方法论交叉审计新增)

以下问题由方法论 checklist 交叉审计发现，原三轮审计未覆盖:

#### S1. tokenManager.ts 事件监听器未清理 [前端] — MEDIUM (维度 10)

- **文件**: `decodables-fe/lib/auth/tokenManager.ts` 行 275-285
- **问题**: `window.addEventListener('storage', ...)` 在 `initCrossTabSync()` 中注册但无对应的 `removeEventListener`
- **影响**: TokenManager 重建时会注册重复监听器；页面生命周期结束时监听器不被回收
- **同时**: BroadcastChannel (行 269-272) 未在清理时调用 `channel.close()`
- **修复**: 添加 `cleanup()` 方法，在 AuthProvider unmount 时调用

#### S2. register/page.tsx useResendCountdown interval 泄漏 [前端] — LOW (维度 10)

- **文件**: `decodables-fe/app/(auth)/register/page.tsx` 行 48-64
- **问题**: `setInterval` 存储在 `timerRef.current`，但仅在 countdown 到 0 时内部清理；若组件 unmount 时 countdown 未到 0，interval 继续运行
- **缓解**: L9 已指出此 hook 重复定义的问题，修复时一并添加 `useEffect` cleanup
- **修复**: 添加 `useEffect(() => () => clearInterval(timerRef.current), [])`

#### S3. tokenManager.ts 缺少 AbortController [前端] — LOW (维度 4)

- **文件**: `decodables-fe/lib/auth/tokenManager.ts` 行 205
- **问题**: `fetch()` 调用无 AbortController，token 刷新请求无法在页面卸载/导航时取消
- **缓解**: 单次 refresh 请求很短（<1s），实际影响小
- **修复**: 在 `cleanup()` 中 abort 进行中的请求

#### S4. 登录/注册页面缺少 ErrorBoundary [前端] — LOW (维度 4)

- **文件**: `login/page.tsx`, `register/page.tsx`
- **问题**: auth 页面未被 ErrorBoundary 包裹，未捕获的渲染错误将导致整个页面白屏
- **修复**: 在 `(auth)/layout.tsx` 添加 ErrorBoundary 包裹

#### S5. Repository 层未检测多记录返回 [后端] — LOW (维度 1)

- **文件**: `infrastructure/repositories/auth_user_repository.py`
- **问题**: `.maybe_single()` 查询和 RPC 结果仅检查 `len(result.data) == 0`（未找到），不检测 `len(result.data) > 1`（多记录异常）
- **缓解**: email 字段有唯一索引，正常情况不会出现多记录
- **修复**: 添加 `if len(result.data) > 1: raise RuntimeError("Multiple records")` 做纵深防御

### Checklist 交叉验证

#### 4.1 API 安全与设计

| 检查项 | 状态 | 备注 |
|--------|------|------|
| BOLA/IDOR | ✅ | auth 端点通过 JWT sub 验证身份，无 IDOR 风险 |
| Broken Authentication | ✅ | 报告已全面覆盖 (C1, C2, H5-H7) |
| Excessive Data Exposure | ✅ | 响应只返回必要字段 (UserInfo schema 限制) |
| Rate Limiting | ✅ | H4 已指出遗漏端点 |
| Mass Assignment | ✅ | Pydantic 白名单模型，无过度赋值风险 |
| CORS 配置 | ✅ 通过 | 已确认: 显式来源白名单、credentials 启用、header 限制 |
| 错误响应格式 | ✅ | 统一 ErrorResponse schema |
| HTTP 方法语义 | ✅ | POST 用于认证操作，语义正确 |

#### 4.4 数据安全与隐私

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 密码/token 不在日志中暴露 | ⚠️ | M7 已覆盖 PII 日志问题 |
| 前端不在 localStorage 存敏感信息 | ⚠️ | H7 已覆盖 |
| 所有通信强制 HTTPS | ✅ | Vercel/Railway 默认 HTTPS |
| Webhook 签名验证 | N/A | auth 系统不涉及 Webhook |

#### 5.4 认证专项 (自托管替代 Clerk)

| 检查项 | 状态 | 备注 |
|--------|------|------|
| Token 过期/刷新/吊销 | ✅ | 完整的 refresh + rotation + reuse detection |
| 多 Tab 共享认证 | ⚠️ | L10 已覆盖竞态，S1 补充监听器泄漏 |
| 认证中间件覆盖率 | ⚠️ | C2 已覆盖 cookie path 使中间件失效 |
| JWT metadata 同步 | ⚠️ | H2 已覆盖 role/tier 硬编码 |

#### 3.9 可观测性检查

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 所有路由有 logger | ✅ | router.py 各端点有日志 |
| 错误用 logger.error | ✅ | 通过 |
| 错误日志含上下文 | ⚠️ | M7 指出 PII 未脱敏 |
| 结构化安全审计日志 | ❌ | L3 已覆盖 |
| 前端调试 console.log | ✅ | 登录/注册页面无 console.log 残留 |

#### 3.7 输入校验检查

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 前后端校验规则一致 | ⚠️ | 后端 `EmailStr` + domain 层 Email VO，前端 HTML5 type=email；M9 指出 domain 层较宽松 |
| 错误消息格式统一 | ✅ | 统一 ErrorResponse 格式 |

### 报告结构对照方法论要求

| 方法论要求 | 报告状态 | 备注 |
|-----------|---------|------|
| 按维度分布统计 | ❌ 未包含 | 报告按严重等级分类，未按维度统计 |
| 根因归纳 (RC) | ❌ 未包含 | 42 个问题未做 RC 归纳 |
| TOP 20 排序 | ✅ 包含 | 优先修复计划已按 Phase 排序 |
| 正面模式识别 | ✅ 包含 | 架构评估-优点部分 |

### 更新后统计

| 严重等级 | 后端 | 前端 | 跨层 | 合计 |
|---------|------|------|------|------|
| **CRITICAL** | 1 | 1 | 0 | **2** |
| **HIGH** | 4 | 3 | 1 | **8** |
| **MEDIUM** | 10 | 4 | 0 | **14** |
| **LOW** | 8 | 6 | 0 | **14** |
| **合计** | 23 | 14 | 1 | **38** |

> 方法论交叉审计新增 5 个问题: S1 (MEDIUM 前端), S2-S4 (LOW×3 前端), S5 (LOW 后端)。
> 总数从 33 → 38 (本轮新增以前端资源清理和防御性编程为主)。

---

## 全系统审计交叉验证 (2026-02-02)

> 参照 `decodables-fe/docs/tmp/audit-sessions/` 目录下的全系统审计 (704 findings, v3.8)，
> 提取与认证系统直接相关的发现，与本报告交叉验证。

### 全系统审计中的 auth 相关发现

以下为全系统审计 (2026-02-01, R1-R6 + 补充审计) 中涉及认证模块的问题，与本报告对照:

| 全系统 ID | 级别 | 描述 | 本报告覆盖 | 备注 |
|-----------|------|------|-----------|------|
| **S0-07** | HIGH | JWT 验证缺少 issuer (iss) 验证 — `dependencies.py:85-147` | ❌ **遗漏** | 新增 T1，见下 |
| **STAB-03** | HIGH | ~~Clerk JWT 验证无超时~~ | N/A | 全系统审计基于 Clerk 架构，自托管后不适用 — dependencies.py 已重写为本地 JWT 验证 |
| **LOG-01** | HIGH | JWT 验证中 user_id/email 明文日志 — `dependencies.py:174-234` | ⚠️ 部分覆盖 | M7 覆盖了 service.py 中的 PII，未覆盖 dependencies.py。但 dependencies.py 已随自托管重写，需确认当前代码 |
| **LOG-02** | HIGH | Sentry 事件未脱敏 request/response body — `app.py:65-85` | ❌ **遗漏** | 新增 T2，见下 |
| **LOG-03** | HIGH | api_logs/error_logs 表存储完整请求体含密码 | ❌ **遗漏** | 新增 T3，见下 |
| **STAB-05** | MED | bare `except: pass` 在 `dependencies.py:241-242` | ❌ **遗漏** | 新增 T4，见下 |
| **S0-08** | MED | 日志中泄露敏感信息 context 未脱敏 — `dependencies.py` | ⚠️ | M7 + L4 部分覆盖 |
| **XS-12** | MED | Clerk Webhook 竞态 session.created 先于 user.created | N/A | 自托管后无 Clerk Webhook |
| **S13-08** | MED | CSRF 保护不完整 | ✅ | H3 已覆盖 |

### 补充发现 (全系统审计交叉验证新增)

#### T1. JWT 缺少 iss/aud 验证 [后端] — HIGH (维度 5)

- **文件**: `domains/auth/token_service.py` (全文件)
- **来源**: 全系统审计 S0-07
- **问题**: `create_access_token` / `verify_access_token` / `create_purpose_token` / `verify_purpose_token` 均不设置和验证 `iss` (issuer) 和 `aud` (audience) 声明
- **影响**:
  - 如果攻击者获取了 JWT 密钥（或存在其他使用同一密钥的服务），可伪造 token
  - 不同环境 (staging/production) 的 token 可能互用
  - Purpose token 和 access token 之间已通过 `type` 字段区分，但缺少标准 JWT 声明
- **修复**: 签发时添加 `iss="make-decodables"`, `aud="make-decodables-api"`，验证时传入 `issuer` 和 `audience` 参数给 `jwt.decode()`

#### T2. Sentry 未脱敏 request body (含登录密码) [后端] — HIGH (维度 5)

- **文件**: `app.py` 行 64 `_sanitize_sentry_event()`
- **来源**: 全系统审计 LOG-02
- **问题**: Sentry `before_send` 钩子的 `_sanitize_sentry_event()` 只脱敏了 headers 和 query_string，**未处理 request body**
- **影响**: `/auth/login` 请求的 `{ email, password }` 会原样上传到 Sentry。密码明文泄漏到第三方服务
- **修复**: 在 `_sanitize_sentry_event` 中增加 request body 脱敏，按敏感字段名列表 (`password`, `token`, `secret`, `otp_code`) 替换值为 `[REDACTED]`

#### T3. api_logs/error_logs 表存储完整请求体 [后端] — MEDIUM (维度 5)

- **文件**: `migrations/v2/03_infrastructure.sql` 行 147, 182
- **来源**: 全系统审计 LOG-03
- **问题**: `api_logs` 和 `error_logs` 表的 `request_body JSONB` 字段存储完整请求内容。如果 auth 端点的请求被记录，密码/OTP/token 会明文入库
- **缓解**: 需确认 auth 路由是否实际写入这两张表（如果 API 日志中间件排除了 /auth 路径则风险降低）
- **修复**: 入库前对敏感字段脱敏，或在中间件层排除 auth 端点

#### T4. dependencies.py 异常静默吞没 [后端] — LOW (维度 4)

- **文件**: `dependencies.py` 行 254-256
- **来源**: 全系统审计 STAB-05
- **问题**: `except (ValueError, Exception): pass` 静默吞没所有异常，workspace 验证失败时无任何日志
- **修复**: 至少添加 `logger.warning()` 记录

### 不适用项说明

以下全系统审计发现基于 **Clerk 认证架构**，自托管后已不再适用:

| 全系统 ID | 描述 | 不适用原因 |
|-----------|------|-----------|
| STAB-03 | Clerk JWT 验证无超时 | 自托管后 JWT 验证为本地计算，无外部调用 |
| XS-12 | Clerk Webhook 竞态 | 自托管后无 Clerk Webhook |
| S2-06 | get_client_flags auth 不一致 | 与 Clerk session 相关 |

### 更新后最终统计

| 严重等级 | 后端 | 前端 | 跨层 | 合计 |
|---------|------|------|------|------|
| **CRITICAL** | 1 | 1 | 0 | **2** |
| **HIGH** | 6 | 3 | 1 | **10** |
| **MEDIUM** | 11 | 4 | 0 | **15** |
| **LOW** | 9 | 6 | 0 | **15** |
| **合计** | 27 | 14 | 1 | **42** |

> 全系统审计交叉验证新增 4 个问题: T1 (HIGH 后端), T2 (HIGH 后端), T3 (MEDIUM 后端), T4 (LOW 后端)。
> 总数从 38 → 42。
>
> **累计审计轮次**: 原始三轮 (v1/v2/v3) + 方法论交叉 + 全系统交叉 + 代码复验 = 6 轮验证。
