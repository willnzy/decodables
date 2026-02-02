# 自建认证系统 - 完整技术方案

> **状态**: ✅ 技术方案已确认（不涉及代码实施）
> **目标**: 完全移除 Clerk 依赖，自建 Email+Password+OTP 认证系统，架构预留 OAuth 扩展能力
> **确认日期**: 2026-02-02

---

## 一、已确认决策汇总

| 决策项 | 选择 | 理由 | 状态 |
|--------|------|------|------|
| 登录方式 | 邮箱+密码（架构预留 OAuth） | 用户需求，先核心后扩展 | ✅ 已确认 |
| 验证方式 | Email OTP 6位验证码 | 比 Magic Link 更适合移动端，无跨设备问题，用户熟悉度高（Canva 模式） | ✅ 已确认 |
| OTP 适用场景 | 注册验证、修改密码、删除账户、忘记密码 | 关键操作需二次验证，登录只需密码 | ✅ 已确认 |
| 用户 ID | UUID v4 | 业界标准，无第三方依赖 | ✅ 已确认 |
| 邮件服务 | Resend | 现代 API，开发体验好 | ✅ 已确认 |
| 数据迁移 | 全新开始 | 项目未上线，无真实用户 | ✅ 已确认 |
| 表结构 | auth_users 与 profiles 分表 | 认证凭据与业务数据职责分离，符合 DDD | ✅ 已确认 |
| 注册流程 | 邮箱 → OTP 验证 → 设密码 + 昵称 → 完成 | 先验证邮箱可达（OTP），再设密码，Canva 模式 | ✅ 已确认 |
| Token 存储 | 方案 B：Next.js API Route 代理（BFF 模式） | 支持多环境（localhost/Preview/Staging/Production），无需配域名 | ✅ 已确认 |
| JWT 算法 | HS256（对称密钥） | 单后端自签自验，性能好，配置简单 | ✅ 已确认 |
| 密码哈希 | argon2id | OWASP 2024 首推，新项目最优方案 | ✅ 已确认 |

---

## 二、技术决策详情

### 决策 1：Token 存储策略

#### ✅ 最终选择：方案 B — Next.js API Route 代理（BFF 模式）

```
浏览器 → Next.js /api/auth/* (Vercel) → Railway 后端 /auth/*
         ↑ cookie 设在前端域上                ↑ 后端返回 JSON，不设 cookie

Access Token: 返回给前端存内存 (Zustand)
Refresh Token: Next.js Route 设为 httpOnly cookie (前端域)
```

#### 选择理由

1. **多环境兼容**：我们的前端域名需要支持 4 种环境：
   - `localhost:3000`（本地开发）
   - `*.vercel.app`（Vercel Preview，每次部署域名随机）
   - `staging.makedecodables.com`（Staging）
   - `app.makedecodables.com`（Production）

   方案 A（同域 Cookie）需要前后端共享父域，无法兼容 localhost 和 Vercel Preview 的随机域名。
   方案 B 的 cookie 始终设在前端自己的域上，天然兼容所有环境。

2. **域名可能变更**：项目域名后续可能更换，方案 B 不依赖特定域名配置。

3. **安全性等同方案 A**：Refresh Token 同样存储为 httpOnly cookie，JS 无法读取，防 XSS。

4. **业界标准**：NextAuth.js (Auth.js)、Supabase Auth、Lucia Auth、T3 Stack 等 Next.js 生态主流方案都采用此模式。NextAuth.js npm 周下载量 100 万+。

#### 已知取舍

| 维度 | 评估 | 缓解方案 |
|------|------|----------|
| **性能** | 多一跳 +20-80ms | 仅影响 auth 请求（登录/刷新/登出），普通 API 直连后端 |
| **稳定性** | 多一个故障点 | Vercel 宕机 = 整站不可用，auth 不是额外风险 |
| **调试** | 三层排查 | 统一 request ID 串联全链路 |
| **代码量** | ~80 行代理代码 | 逻辑极简，只做转发 + cookie 管理 |

#### 淘汰方案

| 方案 | 淘汰原因 |
|------|----------|
| **方案 A**（同域 Cookie） | 无法兼容 localhost 和 Vercel Preview 随机域名；域名变更时需要重新配置 |
| **方案 C**（localStorage） | Refresh Token 存 localStorage 可被 XSS 读取，系统涉及支付，安全风险不可接受 |

---

### 决策 2：JWT 签名算法

#### ✅ 最终选择：HS256（对称密钥）

```
签名: HMAC-SHA256(header + payload, SECRET_KEY)
验证: 用同一个 SECRET_KEY 重新计算签名并比对
```

#### 选择理由

1. **架构匹配**：当前是单后端架构，签发和验证都在同一个 FastAPI 进程，不需要公钥分发。
2. **性能优势**：签名/验证速度是 RS256 的 10 倍（~0.01ms vs ~1ms），每个请求都要验证 JWT。
3. **配置简单**：只需 1 个环境变量 `AUTH_JWT_SECRET`，无需生成 RSA 密钥对。
4. **迁移成本低**：如果未来拆微服务需要 RS256，只需修改 `TokenService` 内部实现，对外接口不变。

#### 与 Clerk 的对比

Clerk 使用 RS256 是因为 Clerk 作为第三方签发 JWT，你的后端用公钥验证——这是第三方认证的标准做法。
自建后签发和验证在同一个服务，RS256 的"公私钥分离"优势不再适用，HS256 更合适。

#### 淘汰方案

| 方案 | 淘汰原因 |
|------|----------|
| **RS256** | 对当前单后端架构过度设计，配置复杂，性能开销大，未来需要时可低成本迁移 |

---

### 决策 3：密码哈希算法

#### ✅ 最终选择：argon2id

```
特点: 内存硬函数（Memory-Hard），GPU/ASIC 难以加速暴力破解
默认参数: memory=65536KB, iterations=3, parallelism=4
输出: $argon2id$v=19$m=65536,t=3,p=4$salt$hash
Python库: argon2-cffi

参数调优（Phase 1 实施时执行）:
- 在 Railway 实例上运行 argon2-cffi benchmark（argon2.PasswordHasher 自带 profile）
- 目标: 单次 hash 耗时 0.5-1 秒（太快不够安全，太慢影响登录体验）
- 当前默认参数适用于 2GB RAM，Railway 实例 RAM 不同需调整

参数梯度表（根据 Railway 实例内存选择）:
- ≥ 2GB RAM → memory=65536KB, iterations=3, parallelism=4（默认，最优安全性）
- 1GB RAM   → memory=32768KB, iterations=4, parallelism=4（降内存，增迭代补偿）
- 512MB RAM → memory=19456KB, iterations=4, parallelism=4（OWASP 低内存推荐配置）
- 实现方式: constants.py 中定义 ARGON2_MEMORY_COST/ARGON2_TIME_COST/ARGON2_PARALLELISM
  通过环境变量 AUTH_ARGON2_MEMORY_KB 覆盖，默认 65536
- 启动时自动检测: 如果 hash 一次耗时 > 2 秒，输出警告日志建议降低 memory 参数
- 启动时自动检测: 如果 hash 一次耗时 < 0.3 秒，输出警告日志建议提高 memory 参数
```

#### 选择理由

1. **OWASP 2024 首推**：Password Hashing Competition (PHC) 2015 冠军，OWASP 推荐级别最高。
2. **抗 GPU 攻击最强**：内存硬函数，GPU 并行暴力破解无优势（需要大量内存）。
3. **全新项目**：没有历史包袱，直接用最优方案，无需兼容旧哈希格式。
4. **业界趋势**：1Password、Bitwarden 等密码管理器使用 argon2id。

#### 与 Clerk 的对比

Clerk 使用 bcrypt（历史原因，2017 年之前 argon2 生态不够成熟）。Clerk 官方文档也建议新系统考虑 argon2id。

#### 淘汰方案

| 方案 | 淘汰原因 |
|------|----------|
| **bcrypt** | 安全性足够但非最优，计算密集但不是内存硬，GPU 有一定暴力破解优势 |
| **scrypt** | 也是内存硬但不如 argon2id，Web 生态采用度低，Python 接口不如 argon2-cffi 友好 |

---

## 三、Clerk 引用完整清单（全量审计）

### 3.1 前端文件清单

#### A. 根级集成（必须重构）

| 文件 | Clerk 用法 | 替换方案 |
|------|-----------|---------|
| `app/layout.tsx` | `<ClerkProvider>` 包裹整个应用 | → `<AuthProvider>` |
| `middleware.ts` | `clerkMiddleware()` | → 自定义路由保护 middleware |
| `components/GlobalProviders.tsx` | `useAuth()`, `useUser()`, getToken, signOut, Clerk fallback | → 完全重写 auth 初始化逻辑 |
| `hooks/useClerkWithTimeout.ts` | Clerk CDN 超时 fallback | → **删除**（不再需要） |
| `package.json` | `@clerk/nextjs: ^6.36.5` | → **移除依赖** |
| `.env.local` | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` | → **移除**，替换为自建 auth 变量 |

#### B. Clerk UI 组件使用（需重写为自定义组件）

| 文件 | Clerk 组件 | 替换方案 |
|------|-----------|---------|
| `components/common/Navbar.tsx` | `<SignedIn>`, `<SignedOut>`, `<SignInButton>`, `<UserButton>`, `<ClerkLoading>`, `<ClerkLoaded>` | → 条件渲染 + `<UserMenu>` 自定义组件 |
| `components/common/BottomNavbar.tsx` | Clerk auth 状态 | → `useAuth()` from `@/lib/auth` |
| `components/common/MobileMenu.tsx` | `useUser()`, `useClerk()` (signOut), `<SignedIn>`, `<SignedOut>`, `<SignInButton>` | → `useAuth()` + `useUser()` from `@/lib/auth` |
| `components/common/FloatingCTA.tsx` | Clerk auth 状态 | → `useAuth()` from `@/lib/auth` |
| `components/common/PlanButton.tsx` | Clerk auth 状态 | → `useAuth()` from `@/lib/auth` |
| `app/dashboard/_components/DashboardAuthGate.tsx` | `<SignIn>` 内嵌登录 | → 跳转到 `/login` |
| `app/create/page.tsx` | `<SignIn>` 内嵌登录 | → 跳转到 `/login` |
| `app/account/page.tsx` (原 `app/profile/page.tsx`) | `useUser()`, `useAuth()`, `useClerk()` (openUserProfile, signOut), `<SignIn>` | → `useAuth()` + `useUser()` from `@/lib/auth` + 统一 Account 页面 |
| `app/transaction-history/page.tsx` | `useAuth()`, `<SignIn>` 内嵌登录 | → `useAuth()` from `@/lib/auth` + 跳转到 `/login` |
| `app/_components/landing/pricing/SubscriptionPlans.tsx` | `useClerkWithTimeout()` (间接使用 `useAuth()`) | → `useAuth()` from `@/lib/auth`（删除 timeout 包装） |
| `components/common/ClerkBillingPage.tsx` | Clerk 专用计费页 | → **删除或重写** |
| `components/common/ClerkTransactionHistory.tsx` | Clerk 专用交易记录 | → **删除或重写** |

#### C. API 调用层（需改 token 来源）

| 文件 | Clerk 用法 | 替换方案 |
|------|-----------|---------|
| `hooks/useApiCall.ts` | `getToken()` from `useAuth()` | → import 改为 `@/lib/auth` + 将 `/sign-in` 跳转改为 `/login` |
| `services/api.ts` | token refresh 回调 (Clerk getToken) | → 自建 token refresh |

#### D. 业务 Hooks（需改 import 路径）

| 文件 | Clerk 用法 |
|------|-----------|
| `hooks/useCredits.ts` | `useAuth()` 获取 token |
| `app/create/_hooks/ai/useAIGeneration.ts` | `useAuth()` 获取 token |
| `app/create/_hooks/ai/useAIPageGeneration.ts` | `useAuth()` 获取 token |
| `app/create/_hooks/editor/useEditorExport.ts` | `useAuth()` 获取 token |
| `app/marketplace/_hooks/usePurchase.ts` | `useAuth()` 获取 token |

#### E. 页面组件（需改 import 路径）

| 文件 | Clerk 用法 |
|------|-----------|
| `app/dashboard/_components/DashboardContent.tsx` | `useUser()` 获取 clerkUser 对象 → 改为 `useUser()` from `@/lib/auth` |
| `app/admin/page.tsx` | `useAuth()` 验证管理员 |
| `app/marketplace/page.tsx` | `useAuth()` 用户状态 |
| `app/notifications/page.tsx` | `useAuth()` 用户状态 |
| `app/contact-us/page.tsx` | `useAuth()` 用户上下文 |
| `app/_components/landing/CTAButton.tsx` | Clerk auth 跳转 |
| `app/_components/landing/LandingPageClient.tsx` | Clerk auth 条件渲染 |
| `app/_components/landing/pricing/CreditsTierCard.tsx` | Clerk auth 升级流程 |
| `app/_components/landing/hero/PromptInput.tsx` | Clerk auth 状态 |

#### F. 弹窗/对话框组件（需改 import 路径）

| 文件 | Clerk 用法 |
|------|-----------|
| `components/OutOfCreditsModal.tsx` | `useAuth()` 状态 |
| `components/UpgradeModal.tsx` | `useAuth()` 升级跳转 |
| `components/CreateProjectModal.tsx` | `useAuth()` 状态 |
| `app/dashboard/_components/modals/PublishAssetDialog.tsx` | `getToken()` API 调用 |
| `app/create/_components/scan/SmartScanDialog.tsx` | `useAuth()` 状态 |
| `components/common/FeedbackDialog.tsx` | Clerk 用户上下文 |

#### G. 支持组件

| 文件 | Clerk 用法 |
|------|-----------|
| `components/common/support/ContactForm.tsx` | Clerk user ID |
| `components/common/support/AIChat.tsx` | Clerk auth |

#### H. 测试文件（需更新 mock）

| 文件 | 变更 |
|------|------|
| `__tests__/components/Navbar.test.jsx` | 更新 Clerk mock → auth mock |
| `__tests__/components/BottomNavbar.test.tsx` | 更新 Clerk mock → auth mock |
| `jest.setup.js` | 移除 Clerk mocking，添加自建 auth mock |
| `app/create/__tests__/hooks/useProjectTitle.test.ts` | 更新 auth mock |

#### I. 文档文件（需更新描述）

- `docs/tmp/20260131-account-system-audit-report.md`
- `docs/tmp/20260131-account-system-fix-plan.md`
- `docs/main/frontend-development-guide.md`
- `docs/main/integration-testing-guide.md`

---

### 3.2 后端文件清单

#### A. 核心认证模块（必须重构）

| 文件 | Clerk 用法 | 替换方案 |
|------|-----------|---------|
| `dependencies.py` | Clerk RS256 JWT 验证、CLERK_PEM_PUBLIC_KEY、azp 验证、JIT 用户创建 | → 自签 HS256 JWT 验证，移除 JIT |
| `config.py` | `CLERK_PEM_PUBLIC_KEY`, `CLERK_FRONTEND_API`, `CLERK_ALLOWED_ORIGINS`, `CLERK_WEBHOOK_SECRET` | → 替换为 `AUTH_JWT_SECRET` 等 |
| `container.py` | `get_clerk_webhook_service()` | → 移除，新增 `get_auth_service()` 等 |

#### B. Webhook 模块（完全删除）

| 文件 | 操作 |
|------|------|
| `domains/webhooks/clerk_webhook_service.py` | **删除整个文件** |
| `api/user/webhooks.py` | 移除 Clerk webhook 路由（保留 Stripe webhook） |

#### C. 数据库 Schema

| 文件 | 变更 |
|------|------|
| `migrations/v2/01_core_business.sql` | `profiles.id` TEXT → UUID，32 个外键同步 |
| `migrations/v2/02_platform_services.sql` | 16 个引用 profiles(id) 的外键 → UUID |
| `migrations/v2/03_infrastructure.sql` | 删除 `clerk_webhook_events` 表，8 个外键 → UUID |

#### D. 依赖

| 文件 | 变更 |
|------|------|
| `requirements.txt` | 移除 `svix`，新增 `argon2-cffi`（resend 已安装，保留） |

#### E. 身份验证相关

| 文件 | Clerk 用法 |
|------|-----------|
| `core/auth/jwt_utils.py` | JWT 解码（支持 Clerk 格式） |
| `core/auth/context.py` | Auth context（Clerk token 生成） |

#### F. 测试文件（需重写）

| 文件 | 变更 |
|------|------|
| `tests/integration/staging/conftest.py` | Clerk test token → 自签 test token |
| `tests/integration/staging/test_users.py` | Clerk 用户创建测试 → 注册 API 测试 |
| `tests/integration/staging/webhooks/test_webhooks.py` | Clerk webhook 测试 → **删除** |
| `tests/integration/staging/get_test_token.py` | Clerk token 生成 → 自签 token 生成 |
| `tests/api/user/test_webhooks.py` | Clerk webhook 测试 → 移除 Clerk 部分 |
| `tests/conftest.py` | Clerk test setup → 自建 auth setup |

#### G. 文档文件（需更新）

- `docs/main/api-reference.md`
- `docs/shared/user-api-review.md`
- `docs/main/backend-business-logic.md`
- `docs/main/backend-architecture.md`
- `docs/main/database-guide.md`

---

### 3.3 环境变量 & 基础设施

| 位置 | 变更 |
|------|------|
| Vercel 环境变量 | 移除 `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` |
| Railway 环境变量 | 移除 4 个 `CLERK_*` 变量，新增 `AUTH_JWT_SECRET` 等 |
| `.env.local` (前端) | 移除 2 个 Clerk 变量 |
| `.env` (后端) | 移除 4 个 Clerk 变量，新增自建 auth 变量 |

---

### 3.4 影响统计

| 类别 | 文件数 |
|------|--------|
| 前端 - 需重写逻辑 | ~10 个 |
| 前端 - 需改 import | ~30 个 |
| 前端 - 需删除 | ~3 个 |
| 前端 - 测试更新 | ~4 个 |
| 前端 - 文档更新 | ~4 个 |
| 后端 - 需重写 | ~3 个 |
| 后端 - 需删除 | ~2 个 |
| 后端 - Schema 修改 | 3 个（涉及 56 个外键引用） |
| 后端 - 测试更新 | ~6 个 |
| 后端 - 文档更新 | ~5 个 |
| **总计** | **~70 个文件** |

### 数据库外键统计
- `profiles.id` 当前为 TEXT 类型（存 Clerk 格式 `user_2abc...`）
- `01_core_business.sql`: 32 个外键引用 `profiles(id)`
- `02_platform_services.sql`: 16 个外键引用 `profiles(id)`
- `03_infrastructure.sql`: 8 个外键引用 `profiles(id)`
- **总计 56 个外键**需同步变更为 UUID 类型

---

## 四、数据库 Schema 设计

### 4.1 新增表：`auth_users`（认证凭据，与 profiles 分离）

```
auth_users
├── id                          UUID PK (DEFAULT uuid_generate_v4())
├── email                       TEXT UNIQUE NOT NULL
├── password_hash               TEXT (argon2id，注册完成后才有值，OTP 验证阶段为 NULL)
├── email_verified              BOOLEAN DEFAULT FALSE
├── email_verified_at           TIMESTAMPTZ
├── otp_code_hash               TEXT (SHA-256 哈希，不存明文)
├── otp_purpose                 TEXT CHECK (otp_purpose IN ('register', 'change_password', 'delete_account', 'forgot_password'))
├── otp_expires_at              TIMESTAMPTZ
├── otp_attempts                INTEGER DEFAULT 0 (防暴力猜测，最多 5 次)
├── password_changed_at         TIMESTAMPTZ
├── failed_login_attempts       INTEGER DEFAULT 0
├── locked_until                TIMESTAMPTZ
├── last_login_at               TIMESTAMPTZ
├── last_login_ip               INET
├── is_active                   BOOLEAN DEFAULT TRUE
├── created_at                  TIMESTAMPTZ
└── updated_at                  TIMESTAMPTZ
```

**设计要点**：
- `auth_users.id` 与 `profiles.id` 使用**同一个 UUID**（注册完成后同时创建 profiles）
- 认证数据（密码、OTP）与业务数据（tier、credits）分离
- `password_hash` 可为 NULL：注册流程分为 OTP 验证 → 设密码两步，OTP 验证阶段 password_hash 尚未设置
- CHECK 约束：`CHECK (email = LOWER(email))`（邮箱统一小写，详见 7.4）
- **OTP 统一字段设计**：所有场景（注册、修改密码、删除账户、忘记密码）共用同一组 OTP 字段，通过 `otp_purpose` 区分用途
- **单用户单活跃 OTP 约束**：由于所有场景共用同一组字段，同一用户同一时间只能有一个活跃 OTP。新发送 OTP 会覆盖旧的（otp_code_hash、otp_purpose、otp_expires_at 全部更新，otp_attempts 重置为 0）。这在实际场景中不构成问题：pending 用户（注册中）不会触发修改密码/删除账户 OTP；已注册用户同时发起修改密码和删除账户的概率极低，且后发的 OTP 覆盖前一个是合理行为
- **OTP 安全存储**：`otp_code_hash` 存储的是 **SHA-256 哈希值**，不存明文。邮件发给用户的是 6 位数字明文，后端校验时 `SHA256(user_input) == db_hash`（与 refresh_token_hash 保持一致的安全策略）
- **OTP 防暴力破解**：`otp_attempts` 记录当前 OTP 的尝试次数，达到 5 次后该 OTP 自动失效，需重新发送
- 部分索引：`WHERE otp_code_hash IS NOT NULL`（只索引有 OTP 的行）

### 4.2 新增表：`auth_sessions`（Refresh Token 存储 + 轮换检测）

```
auth_sessions
├── id                UUID PK
├── user_id           UUID FK → auth_users(id) ON DELETE CASCADE
├── family_id         UUID (轮换链标识，同一链共享 family_id)
├── refresh_token_hash TEXT UNIQUE (SHA-256，不存明文)
├── user_agent        TEXT
├── ip_address        INET
├── device_name       TEXT (从 user_agent 解析，用于展示)
├── is_revoked        BOOLEAN DEFAULT FALSE
├── revoked_at        TIMESTAMPTZ
├── revoke_reason     TEXT CHECK (revoke_reason IN ('logout','rotation','security','admin','account_deleted'))
├── expires_at        TIMESTAMPTZ NOT NULL
├── last_used_at      TIMESTAMPTZ
└── created_at        TIMESTAMPTZ
```

**设计要点**：
- Refresh Token 轮换：每次 refresh 时旧 token 作废、颁发新 token，共享 `family_id`
- 重用检测：已作废的 token 再次被使用 → 该 family 全部 token 作废（可能被盗）
- 支持多设备：用户可查看/踢出所有登录设备
- **IP 地址获取**：Railway 部署在反向代理后面，需从 `X-Forwarded-For` header 获取真实客户端 IP。FastAPI 中通过 `request.headers.get("X-Forwarded-For", "").split(",")[0].strip()` 取第一个 IP（最接近客户端的）。如果 header 不存在，fallback 到 `request.client.host`。同样适用于 `auth_users.last_login_ip` 和限流 Key 中的 IP
- **并发宽限期**：被作废的 token 如果在作废后 `REFRESH_REUSE_GRACE_PERIOD_S`（默认 1 秒）内再次被使用（`now() - revoked_at < grace_period`），视为并发请求而非重用攻击，允许通过并颁发新 token（共享同一 `family_id`）。这与前端 `CROSS_TAB_REFRESH_DELAY_MS=300ms` 配合，解决多标签页同时 refresh 的竞态问题
  - 宽限期为**可配置常量**（`constants.py` 中 `REFRESH_REUSE_GRACE_PERIOD_S = 1`，可通过环境变量 `AUTH_REFRESH_GRACE_PERIOD_S` 覆盖）
  - 选择 1 秒而非 2 秒的理由：BFF 代理 + 后端验证通常 < 200ms，1 秒已覆盖 5 倍延迟；2 秒窗口过长，在极端场景下（旧 token 被盗）给攻击者提供了不必要的利用空间
  - 如果生产环境发现多标签竞态误判（1 秒内两个标签的 refresh 未完成），可调大到 1.5 秒，但不建议超过 2 秒

### 4.3 新增表：`auth_oauth_accounts`（预留 OAuth 扩展）

```
auth_oauth_accounts
├── id                    UUID PK
├── user_id               UUID FK → auth_users(id) ON DELETE CASCADE
├── provider              TEXT NOT NULL ('google'/'github'/'apple')
├── provider_user_id      TEXT NOT NULL
├── provider_email        TEXT
├── access_token_encrypted  TEXT
├── refresh_token_encrypted TEXT
├── token_expires_at      TIMESTAMPTZ
├── provider_data         JSONB DEFAULT '{}'
├── created_at            TIMESTAMPTZ
└── updated_at            TIMESTAMPTZ

UNIQUE (provider, provider_user_id)  -- 每个第三方账号只能绑一个用户
UNIQUE (user_id, provider)           -- 每个用户每个平台只能绑一个
```

### 4.4 修改：`profiles` 表变更

```
profiles.id: TEXT → UUID

影响范围：56 个外键需要同步变更为 UUID 类型
操作方式：直接修改 3 个主 schema 文件（项目未上线，无数据迁移）
修改顺序：01_core_business.sql → 02_platform_services.sql → 03_infrastructure.sql（外键依赖顺序）

新增字段：
- email_hash    TEXT    (SHA-256 hash of email，账户删除时写入，用于去重分析和 GDPR 合规准备)

新增部分唯一索引：
- CREATE UNIQUE INDEX idx_profiles_email_unique ON profiles(email) WHERE is_deleted = false;
  (活跃用户邮箱唯一，软删除记录不受约束，允许同一邮箱的多条历史记录并存)
```

### 4.5 修改：`profiles.created_by` CHECK 约束

```
当前: CHECK (created_by IN ('webhook', 'jit', 'legacy', 'manual'))
改为: CHECK (created_by IN ('register', 'admin', 'legacy', 'oauth'))

理由: 移除 Clerk 后不再有 webhook/jit 创建路径
- register: 用户通过 /auth/register 自主注册
- admin: 管理员后台创建
- legacy: 历史兼容（保留）
- oauth: 预留未来 OAuth 第三方登录创建
```

### 4.6 修改：`admin_operations.operation_type` CHECK 约束

```
移除不再适用的枚举值：
- webhook_user_create → 改为 auth_user_register
- webhook_tier_update → 保留（Stripe webhook 仍可触发 tier 变更）
```

### 4.7 处理现有 RPC 函数

| RPC 函数 | 操作 | 说明 |
|----------|------|------|
| `generate_user_code()` | ✅ **保留** | 注册时仍需生成 26 位 user_code |
| `create_user_idempotent()` | 🔄 **重写** → `create_auth_user_with_profile()` | 原函数为 Webhook+JIT 并发设计，新函数为注册时原子创建 auth_users + profiles |
| `get_user_creation_stats()` | 🔄 **更新** | 适配新的 source 枚举（`register`/`admin`/`oauth`） |

**新 RPC 函数 `create_auth_user_with_profile()` 职责**：
```
输入: p_email, p_password_hash, p_display_name, p_signup_bonus
操作:
  1. 生成 UUID (uuid_generate_v4())
  2. INSERT INTO auth_users (id, email, password_hash, email_verified=true, ...)
  3. INSERT INTO profiles (id, email, user_code, credits_permanent, created_by='register', ...)
  4. 两个 INSERT 在同一事务中，保证原子性
返回: auth_user + profile 完整数据

注意: 此函数在注册第三步（OTP 验证通过 + 设完密码后）调用。
调用时 email 已经通过 OTP 验证，所以 email_verified=true。

幂等性保护（防止 register_token 重复使用）:
- RPC 内部在 INSERT auth_users 前检查: 如果该 user_id 的 auth_users 记录已存在
  且 password_hash IS NOT NULL（即已完成注册），直接返回错误（不重复创建）
- 此检查确保: 即使攻击者在 15 分钟有效期内重复调用 /auth/register/complete，
  第二次调用会被 RPC 拒绝
- SQL 实现: 在 INSERT 前加 IF EXISTS (SELECT 1 FROM auth_users WHERE id = p_user_id AND password_hash IS NOT NULL) THEN RAISE EXCEPTION 'already_registered';
```

**新 RPC 函数 `create_pending_auth_user()` 职责**：
```
输入: p_email, p_otp_code_hash, p_otp_expires_at
操作（PL/pgSQL 函数，非裸 SQL）:
  1. SELECT 查询 auth_users WHERE email = p_email
  2. 如果不存在 → INSERT 新记录（生成 UUID，password_hash=NULL, email_verified=false）→ 返回新 ID
  3. 如果存在且 email_verified = false AND password_hash IS NULL（pending 用户）
     → UPDATE 覆盖 otp_code_hash, otp_purpose, otp_expires_at, otp_attempts=0 → 返回已有 ID
  4. 如果存在且已完成注册（password_hash IS NOT NULL 或 email_verified = true）
     → 不做任何操作 → 返回 NULL
  5. 仅操作 auth_users，不创建 profiles（注册未完成）
返回: auth_user.id（INSERT 时返回新 ID，UPDATE 时返回已有 ID，已注册时返回 NULL）

⚠️ 为什么不用 ON CONFLICT DO UPDATE ... WHERE：
PostgreSQL 的 ON CONFLICT DO UPDATE SET ... WHERE 当 WHERE 条件不满足时，
既不执行 UPDATE 也不执行 INSERT，而是抛出 unique_violation 异常（非静默跳过）。
ON CONFLICT DO NOTHING 虽然静默，但无法区分"INSERT 成功"和"冲突被忽略"。
因此使用 PL/pgSQL 先 SELECT 判断再 INSERT/UPDATE，行为明确可控。

SQL 伪代码:
  CREATE OR REPLACE FUNCTION create_pending_auth_user(
    p_email TEXT, p_otp_code_hash TEXT, p_otp_expires_at TIMESTAMPTZ
  ) RETURNS UUID AS $$
  DECLARE
    v_user_id UUID;
    v_existing RECORD;
  BEGIN
    SELECT id, email_verified, password_hash INTO v_existing
    FROM auth_users WHERE email = LOWER(p_email) FOR UPDATE;

    IF NOT FOUND THEN
      v_user_id := uuid_generate_v4();
      INSERT INTO auth_users (id, email, otp_code_hash, otp_purpose, otp_expires_at, password_hash, email_verified)
      VALUES (v_user_id, LOWER(p_email), p_otp_code_hash, 'register', p_otp_expires_at, NULL, false);
      RETURN v_user_id;
    ELSIF v_existing.email_verified = false AND v_existing.password_hash IS NULL THEN
      UPDATE auth_users SET
        otp_code_hash = p_otp_code_hash, otp_purpose = 'register',
        otp_expires_at = p_otp_expires_at, otp_attempts = 0, updated_at = now()
      WHERE id = v_existing.id;
      RETURN v_existing.id;
    ELSE
      RETURN NULL;  -- 已注册用户，不操作
    END IF;
  END;
  $$ LANGUAGE plpgsql;

注意: 注册第一步（发送 OTP）时调用。
- SELECT ... FOR UPDATE 防止并发竞态（两个请求同时注册同一邮箱）
- 返回 NULL 表示该邮箱已注册完成 → 后端仍返回统一响应"验证码已发送"（防枚举），但不实际发送 OTP
```

#### RPC 2: `restore_auth_user_with_profile()`

账户恢复专用 RPC——在 30 天恢复期内，用户选择"恢复账号"时调用。复用旧 profiles UUID 作为新 auth_users.id，并将 profiles 记录恢复为活跃状态。

```sql
CREATE OR REPLACE FUNCTION restore_auth_user_with_profile(
  p_old_profile_id  UUID,       -- 待恢复的 profiles.id（软删除状态）
  p_email           TEXT,
  p_password_hash   TEXT,
  p_display_name    TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
  v_profile RECORD;
  v_restored_name TEXT;
BEGIN
  -- 1. 查询可恢复的 profiles 记录（FOR UPDATE 防并发）
  SELECT id, email, display_name, deleted_at, is_deleted
    INTO v_profile
    FROM profiles
   WHERE id = p_old_profile_id
     AND is_deleted = true
     AND deleted_at > now() - INTERVAL '30 days'
     FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'RESTORE_NOT_FOUND: profile % not found or not restorable', p_old_profile_id;
  END IF;

  -- 2. 确认邮箱匹配（防止篡改）
  IF v_profile.email <> p_email THEN
    RAISE EXCEPTION 'RESTORE_EMAIL_MISMATCH: email does not match profile record';
  END IF;

  -- 3. 创建新的 auth_users 记录（复用旧 UUID）
  INSERT INTO auth_users (id, email, password_hash, email_verified)
  VALUES (p_old_profile_id, p_email, p_password_hash, true);

  -- 4. 恢复 profiles 记录
  v_restored_name := COALESCE(p_display_name, v_profile.display_name);
  -- 如果 display_name 已被 30 天定时任务脱敏为 'Deleted User'，使用传入的新名称
  IF v_restored_name = 'Deleted User' THEN
    v_restored_name := COALESCE(p_display_name, 'User');
  END IF;

  UPDATE profiles SET
    is_deleted = false,
    deleted_at = NULL,
    display_name = v_restored_name,
    updated_at = now()
  WHERE id = p_old_profile_id;

  -- 5. 记录恢复事件
  INSERT INTO user_creation_logs (user_id, action, details)
  VALUES (p_old_profile_id, 'account_restored', jsonb_build_object(
    'restored_at', now(),
    'original_deleted_at', v_profile.deleted_at
  ));

  RETURN p_old_profile_id;
END;
$$ LANGUAGE plpgsql;

注意: 注册第三步（complete）且 restore_account=true 时调用。
- 复用旧 profiles.id 作为 auth_users.id，保持所有关联数据（projects、assets 等）的 owner_id 不变
- email_verified 直接设为 true（用户已通过 OTP 验证邮箱归属）
- 如果 display_name 已被 30 天脱敏任务改为 'Deleted User'，优先使用用户新输入的名称
- 恢复后 email_hash 字段保留（不清除），不影响业务逻辑
- RAISE EXCEPTION 抛出的错误由后端 RegistrationService 捕获并转为 HTTP 错误响应
```

### 4.8 处理相关表

| 表 | 操作 | 说明 |
|----|------|------|
| `clerk_webhook_events` | ❌ **删除** | Clerk 专用，不再需要 |
| `user_creation_logs` | 🔄 **保留并更新** | 更新 action 枚举值，继续用于审计注册事件 |
| `system_error_logs` | 🔄 **保留** | 更新 operation 字段的注释引用 |

### 4.9 RLS 策略（Row Level Security）

所有 auth 表必须启用 RLS，防止 Supabase anon key 泄露时数据裸奔。

```
auth_users:
├── ALTER TABLE auth_users ENABLE ROW LEVEL SECURITY;
├── Policy: service_role_full_access
│   → USING (true) WITH CHECK (true)
│   → TO service_role
├── 无 authenticated 用户策略（前端永远不直连此表，所有操作通过后端 API）
└── 理由: 存储密码哈希和 OTP 哈希，安全等级最高

auth_sessions:
├── ALTER TABLE auth_sessions ENABLE ROW LEVEL SECURITY;
├── Policy: service_role_full_access
│   → USING (true) WITH CHECK (true)
│   → TO service_role
├── 无 authenticated 用户策略（会话管理通过后端 API /auth/sessions）
└── 理由: 存储 refresh_token_hash，不允许客户端直接查询

auth_oauth_accounts:
├── ALTER TABLE auth_oauth_accounts ENABLE ROW LEVEL SECURITY;
├── Policy: service_role_full_access
│   → USING (true) WITH CHECK (true)
│   → TO service_role
└── 理由: 存储加密的 OAuth token，不允许客户端直接查询
```

**重要**：后端通过 `SUPABASE_KEY`（service_role key）操作这些表，RLS 对 service_role 透明。

---

## 五、后端架构设计

### 5.1 新增 Auth Domain

```
decodables/domains/auth/
├── __init__.py
├── aggregates/
│   ├── auth_user.py              # AuthUser 聚合根
│   └── session.py                # Session 实体
├── value_objects.py              # Password, Email, Token 值对象
├── repository.py                 # IAuthUserRepository, ISessionRepository 接口（见下方方法签名）
├── registration_service.py       # 注册流程编排（send_otp → verify_otp → complete）
├── session_service.py            # 会话管理（login → refresh → logout → device management）
├── account_service.py            # 账户操作（change_password → forgot_password → delete_account）
├── token_service.py              # JWT 签发/验证 (Access + Refresh)
├── otp_service.py                # OTP 生成/验证/发送邮件 (通过 Resend)
├── password_service.py           # 密码哈希 (argon2id) + 强度校验
└── constants.py                  # Token 有效期、锁定阈值等常量
```

**Service 拆分说明**（原 `service.py` 拆分为 3 个 Service）：

将原始的单一 `AuthService`（12 个核心方法，预估 500+ 行）拆分为 3 个职责清晰的 Service：

| Service | 方法 | 预估行数 | 职责 |
|---------|------|----------|------|
| `RegistrationService` | `send_otp()`, `verify_otp()`, `complete()` | ~150 行 | 注册三步流程 + 一次性邮箱检测 |
| `SessionService` | `login()`, `refresh_token()`, `logout()`, `logout_all()`, `get_sessions()`, `revoke_session()` | ~200 行 | 登录/登出/Token 刷新/多设备管理 |
| `AccountService` | `send_otp()`, `verify_otp()`, `change_password()`, `forgot_password_reset()`, `delete_account()` | ~200 行 | 密码操作/账户注销（复用 OTPService） |

**依赖关系**：
```
RegistrationService → OTPService + PasswordService + TokenService + IAuthUserRepository + ISessionRepository
SessionService      → TokenService + PasswordService + IAuthUserRepository + ISessionRepository
AccountService      → OTPService + PasswordService + TokenService + IAuthUserRepository + ISessionRepository
```

**API Router 调用方式**：
```python
# api/auth/router.py 直接调用对应 Service，无需薄编排层
@router.post("/register/send-otp")
async def register_send_otp(req, registration_service = Depends(get_registration_service)):
    return await registration_service.send_otp(req.email)

@router.post("/login")
async def login(req, session_service = Depends(get_session_service)):
    return await session_service.login(req.email, req.password)

@router.post("/change-password")
async def change_password(req, account_service = Depends(get_account_service)):
    return await account_service.change_password(req.otp_verified_token, req.current_password, req.new_password)
```

**Repository 接口方法签名**：

```
IAuthUserRepository:
├── get_by_id(user_id: UUID) → AuthUser | None
├── get_by_email(email: str) → AuthUser | None
├── create_pending(email: str, otp_hash: str, expires_at: datetime) → UUID  # 注册第一步：创建待验证用户（RPC create_pending_auth_user）
├── create_with_profile(auth_user: AuthUser) → AuthUser                      # 注册第三步：完善信息后原子创建（RPC create_auth_user_with_profile）
├── update_password(user_id: UUID, password_hash: str) → None
├── update_email_verified(user_id: UUID, verified: bool) → None
├── update_login_attempt(user_id: UUID, failed_attempts: int, locked_until: datetime | None) → None
├── set_otp(user_id: UUID, otp_hash: str, purpose: str, expires_at: datetime) → None
├── increment_otp_attempts(user_id: UUID) → int       # 返回当前尝试次数
├── clear_otp(user_id: UUID) → None
├── delete(user_id: UUID) → None                       # 硬删除 auth_users
└── record_login(user_id: UUID, ip: str, timestamp: datetime) → None

ISessionRepository:
├── create(session: Session) → Session
├── get_by_token_hash(token_hash: str) → Session | None
├── get_active_by_user(user_id: UUID) → List[Session]     # "活跃"定义: is_revoked = false AND expires_at > now()
├── count_active_by_user(user_id: UUID) → int              # 同上，用于并发会话限制检查
├── revoke(session_id: UUID, reason: str) → None
├── revoke_family(family_id: UUID, reason: str) → None
├── revoke_all_by_user(user_id: UUID, reason: str) → None
├── revoke_oldest_by_user(user_id: UUID, reason: str) → None  # 踢出最旧会话
└── update_last_used(session_id: UUID) → None
```

### 5.2 核心服务职责

**RegistrationService（注册流程）**：
| 方法 | 职责 |
|------|------|
| `send_otp(email)` | 校验邮箱 → 一次性邮箱检测 → 检查是否已注册 → 生成 6 位 OTP → 哈希存储 → 异步发 OTP 邮件（无论邮箱是否存在都返回成功，防枚举） |
| `verify_otp(email, otp_code)` | 校验 OTP（哈希比对 + 过期检查 + 尝试次数检查）→ 标记 email_verified → 返回临时注册 token（用于下一步设密码） |
| `complete(register_token, password, display_name)` | 校验临时注册 token → 幂等性检查 → 哈希密码 → **原子创建** auth_users + profiles（RPC `create_auth_user_with_profile()`）→ 创建 session → 返回 tokens |

**SessionService（会话管理）**：
| 方法 | 职责 |
|------|------|
| `login(email, password)` | 查用户 → 检查锁定 → 验证密码 → 记录登录 → 创建 session → 返回 tokens |
| `refresh_token(refresh_token, rotate)` | 查 session → 检查过期/作废 → 轮换（废旧发新）或仅验证（rotate=false）→ 重用检测（并发宽限期）→ 返回新 tokens |
| `logout(refresh_token)` | 作废当前 session |
| `logout_all(user_id)` | 作废用户所有 sessions |
| `get_sessions(user_id)` | 列出用户所有活跃 sessions（多设备管理） |
| `revoke_session(session_id)` | 踢出指定设备 |

**AccountService（账户操作）**：
| 方法 | 职责 |
|------|------|
| `send_otp(user_id_or_email, purpose)` | 通用 OTP 发送：校验用户存在 → 生成 6 位 OTP → 哈希存储 → 异步发邮件（用于修改密码/删除账户/忘记密码） |
| `verify_otp(user_id_or_email, otp_code, purpose)` | 通用 OTP 验证：哈希比对 + 过期 + 尝试次数 → 返回 otp_verified_token（JWT） |
| `forgot_password_reset(otp_verified_token, new_password)` | 校验 OTP 已验证 → 更新密码 → 作废所有 sessions |
| `change_password(otp_verified_token, current_password, new_password)` | 校验 OTP 已验证 → 验证旧密码 → 更新密码 → 可选作废其他 sessions |
| `delete_account(otp_verified_token)` | 校验 OTP 已验证 → 取消 Stripe 订阅 → 作废 sessions → 软删除 profiles → 硬删除 auth_users → 异步匿名化内容（详见 7.3） |

**TokenService（JWT 管理）**：
- Access Token: HS256 签名，15 分钟有效期
  - Payload: `{ sub, email, role, tier, type: "access", iat, exp }`
- Refresh Token: 不透明 UUID，SHA-256 哈希后存储，7 天有效期
  - 客户端持有明文，服务端只存哈希

**PasswordService（密码安全）**：
- argon2id 哈希（OWASP 推荐）
- 强度校验：≥8 字符、大小写+数字、不在常见密码列表中
- 时间安全比较（argon2-cffi 内置）

### 5.3 API 端点设计

```
decodables/api/auth/
├── __init__.py
├── router.py                # FastAPI Router
└── schemas.py               # Pydantic Request/Response 模型
```

| Method | Path | 说明 | 限流 | 需认证 |
|--------|------|------|------|--------|
| POST | `/auth/register/send-otp` | 注册第一步：发送 OTP 到邮箱 | 5/hour/IP, 3/hour/email | 否 |
| POST | `/auth/register/verify-otp` | 注册第二步：验证 OTP | 10/hour/IP | 否 |
| POST | `/auth/register/complete` | 注册第三步：设密码+昵称，完成注册 | 5/hour/IP | 否（需临时注册 token） |
| POST | `/auth/login` | 登录（邮箱+密码） | 10/min/IP | 否 |
| POST | `/auth/refresh` | 刷新 Access Token | 30/min/token | Refresh Token |
| POST | `/auth/logout` | 登出当前设备 | — | Refresh Token |
| POST | `/auth/logout-all` | 登出所有设备 | — | Access Token |
| POST | `/auth/otp/send` | 通用 OTP 发送（修改密码/删除账户/忘记密码） | 3/hour/email | 忘记密码: 否; 其他: Access Token |
| POST | `/auth/otp/verify` | 通用 OTP 验证 | 10/hour/IP | 同上 |
| POST | `/auth/forgot-password/reset` | 忘记密码：OTP 验证后重置密码 | 5/hour/IP | 否（需 OTP 验证 token） |
| POST | `/auth/change-password` | 修改密码（已登录，需先 OTP 验证） | 5/hour/user | Access Token + OTP 验证 token |
| GET | `/auth/sessions` | 查看活跃设备 | — | Access Token |
| DELETE | `/auth/sessions/{id}` | 踢出指定设备 | — | Access Token |
| POST | `/auth/delete-account` | 注销账户（需先 OTP 验证） | 1/hour/user | Access Token + OTP 验证 token |

**核心端点 Request/Response Schema**：

```
=== 注册流程（三步） ===

POST /auth/register/send-otp
  Request:  { email: string }
  Response: { success: true, message: "验证码已发送到您的邮箱", has_restorable_account?: boolean }
            // 无论邮箱是否已注册，统一响应防枚举（始终返回 success: true）
            // has_restorable_account: 仅当存在 30 天内的可恢复账户时为 true，否则为 false
            // ⚠️ 已知取舍：此字段暴露邮箱是否有已删除账户（邮箱枚举风险），
            //    已通过 IP 限流（5/hour/IP + 3/hour/email）缓解，详见 7.3 邮箱复用
  Errors:   429 (限流)

POST /auth/register/verify-otp
  Request:  { email: string, otp_code: string }
  Response: { success: true, register_token: string }  // 临时注册 token（15分钟有效，JWT，用于下一步）
  Errors:   400 { error: "invalid_otp" | "otp_expired" | "too_many_attempts" }

POST /auth/register/complete
  Request:  { register_token: string, password: string, display_name?: string, restore_account?: boolean }
  Response: { access_token: string, refresh_token: string, user: { id: UUID, email: string, display_name: string } }
  Note:     refresh_token 由 BFF 代理截获设为 httpOnly cookie，不返回给前端 JS
            restore_account=true 时调用 restore_auth_user_with_profile() RPC（复用旧 UUID，恢复 profiles）
            restore_account=false 或未传时调用 create_auth_user_with_profile() RPC（全新 UUID）
  Errors:   400 { error: "invalid_register_token" | "weak_password" | "restore_not_found" | "restore_expired" } / 409 (邮箱已完成注册)

=== 登录 ===

POST /auth/login
  Request:  { email: string, password: string }
  Response: { access_token: string, refresh_token: string, user: { id: UUID, email: string, tier: string, role: string } }
  Note:     refresh_token 由 BFF 代理截获设为 httpOnly cookie，不返回给前端 JS
  Errors:   401 { error: "invalid_credentials" } / 403 { error: "account_locked", retry_after: number }

=== Token 管理 ===

POST /auth/refresh
  Request:  { refresh_token: string, rotate?: boolean }  // rotate 默认 true
  Response: { access_token: string, refresh_token?: string }  // rotate=false 时不返回 refresh_token
  Errors:   401 { error: "token_expired" | "token_revoked" | "reuse_detected" }

POST /auth/logout
  Request:  { refresh_token: string }
  Response: { success: true }

=== 通用 OTP（修改密码/删除账户/忘记密码）===

POST /auth/otp/send
  Request:  { purpose: "change_password" | "delete_account" | "forgot_password", email?: string }
  Response: { success: true, message: "验证码已发送到您的邮箱" }  // 统一响应，防枚举
  Note:
    - purpose="forgot_password" 时：不需要 Access Token，必须传 email（因为用户未登录）
    - purpose="change_password" | "delete_account" 时：需要 Access Token，email 从 JWT 中提取（忽略请求体中的 email，防止向他人邮箱发 OTP）

POST /auth/otp/verify
  Request:  { purpose: string, otp_code: string, email?: string }
  Response: { success: true, otp_verified_token: string }  // 临时验证 token（10分钟有效，JWT，用于后续操作）
  Note:     email 参数规则同 /auth/otp/send（forgot_password 需传，其他从 JWT 提取）
  Errors:   400 { error: "invalid_otp" | "otp_expired" | "too_many_attempts" }

=== 密码操作 ===

POST /auth/forgot-password/reset
  Request:  { otp_verified_token: string, new_password: string }
  Response: { success: true }
  Errors:   400 { error: "invalid_token" | "token_expired" | "weak_password" }
  Note:     重置成功后所有 sessions 自动作废

POST /auth/change-password
  Request:  { otp_verified_token: string, current_password: string, new_password: string }
  Response: { success: true }
  Errors:   400 { error: "invalid_token" | "wrong_password" | "weak_password" }

=== 设备管理 ===

GET /auth/sessions
  Response: { sessions: [{ id: UUID, device_name: string, ip_address: string, last_used_at: string, is_current: boolean }] }

DELETE /auth/sessions/{id}
  Response: { success: true }

POST /auth/delete-account
  Request:  { otp_verified_token: string }
  Response: { success: true }
  Errors:   400 { error: "invalid_token" | "token_expired" }

统一错误响应格式：
{ error: string, message?: string, details?: object }
→ error: 机器可读的错误码（如 "invalid_credentials"）
→ message: 人类可读的错误描述（可选，前端可 i18n 覆盖）
→ details: 额外信息（可选，如 retry_after、validation_errors）
```

### 5.3.1 限流实现方案

```
实现选型: SlowAPI (基于 limits 库) + 内存后端

理由:
- 当前 Railway 部署为单实例，内存后端足够
- SlowAPI 是 FastAPI 生态标准限流方案（已有 RATE_LIMIT_* 配置在 config.py）
- 未来如需多实例部署，可切换为 Redis 后端（仅改配置，不改代码）

限流 Key 设计:
- /auth/login:              IP + email（防止同 IP 不同账号暴力破解）
- /auth/register/send-otp:  IP + email（防止同 IP 批量注册 + 同邮箱频繁发送）
- /auth/register/verify-otp: IP（防止暴力猜测 OTP）
- /auth/refresh:            Refresh Token hash（防止单 token 滥用）
- /auth/otp/send:           email（防止对同一邮箱频繁发送 OTP）
- /auth/otp/verify:         IP（防止暴力猜测 OTP）

OTP 重发冷却时间（后端校验，防绕过前端 60 秒倒计时）:
- 每次发送 OTP 时记录 otp_expires_at（生成时间可从中推算）
- 如果距离上次 OTP 发送 < 60 秒，返回 429 { error: "otp_cooldown", retry_after: seconds_remaining }
- 实现方式: 在 OTPService.send_otp() 中检查 auth_users.otp_expires_at 是否在 (now() - 有效期 + 60秒) 之后
  即: 如果 otp_expires_at > now() - 有效期 + 60s，说明距上次发送不到 60 秒
- 这是在 SlowAPI 小时级限流（3/hour）之外的额外保护层

锁定机制 (auth_users.failed_login_attempts):
- 每次密码错误: failed_login_attempts += 1
- 达到 5 次: locked_until = now() + 30min
- 成功登录: failed_login_attempts = 0, locked_until = NULL
- 锁定期间的登录尝试: 不计数（防止攻击者通过锁定期间尝试来延长锁定）
- 锁定状态下返回: 403 { error: "account_locked", retry_after: seconds_remaining }

响应头 (便于前端展示):
- X-RateLimit-Limit: 10
- X-RateLimit-Remaining: 7
- X-RateLimit-Reset: 1706889600 (Unix timestamp)
```

### 5.3.2 OTP 安全规范

```
OTP 验证码（统一规范，所有场景通用）:
├── 格式: 6 位纯数字（000000-999999）
├── 生成: secrets.randbelow(1000000)，用 zfill(6) 补齐前导零
├── 存储: SHA-256 哈希后存入 auth_users.otp_code_hash（不存明文）
├── 有效期: 10 分钟
├── 一次性使用: 验证成功后立即清除（otp_code_hash=NULL, otp_purpose=NULL, otp_attempts=0）
├── 重发机制: 重发时生成新 OTP，旧 OTP hash 立即覆盖，attempts 重置为 0
├── 最大尝试次数: 5 次（otp_attempts >= 5 后该 OTP 自动失效，需重新发送）
├── 邮件内容: "您的验证码是: 123456，10 分钟内有效。"
└── 后端校验: SHA256(user_input) == db_hash AND 未过期 AND otp_attempts < 5 AND purpose 匹配

临时 Token（OTP 验证后颁发，用于后续操作）:

注册临时 Token (register_token):
├── 格式: JWT (HS256)，payload: { sub: email, user_id: UUID, purpose: "register", exp: now()+15min }
├── 有效期: 15 分钟（给用户足够时间填写密码和昵称）
├── 一次性使用: 注册完成后该 email 的 auth_user 已有 password_hash，token 自然失效
├── 用途: 注册第三步（/auth/register/complete）时携带，证明该 email 已通过 OTP 验证
├── user_id: pending auth_user 的 UUID，complete 时验证 email + user_id 双重匹配
└── 不存储在数据库中，后端直接验证 JWT 签名和过期时间

OTP 验证 Token (otp_verified_token):
├── 格式: JWT (HS256)，payload: { sub: user_id, purpose: string, exp: now()+10min }
├── 有效期: 10 分钟
├── 用途: 修改密码、删除账户、忘记密码重置 的后续操作携带
├── 后端校验: 验证 JWT 签名 + 过期 + purpose 匹配当前操作
└── 不存储在数据库中，后端直接验证 JWT 签名和过期时间

安全理由:
- OTP 哈希存储: 数据库被攻破后无法反推 OTP 明文
- 临时 Token 用 JWT: 无状态验证，无需额外数据库查询，且自带过期机制
- 两步验证分离: OTP 验证和实际操作是分开的 API 调用，攻击者即使绕过前端也需要有效的临时 Token
- register_token 增强: payload 包含 auth_user_id（pending 用户 UUID），complete 时验证 email + id 双重匹配

时序攻击防护（防止通过响应时间推断邮箱是否存在）:
├── OTP 发送（register/send-otp, otp/send）统一异步处理：
│   1. 后端收到请求后立即返回统一响应（不等待邮件发送完成）
│   2. 邮件发送放入后台任务（或 asyncio.create_task）
│   3. 如果邮箱不存在，仍然执行相同的数据库查询路径，只是不创建 OTP / 不发邮件
│   4. 响应时间固定 ~50-100ms（仅数据库查询），不因是否发邮件而波动
├── 或者：固定最小响应时间
│   1. 记录请求开始时间
│   2. 处理完成后，如果耗时 < 500ms，sleep 到 500ms
│   3. 确保所有响应时间一致
└── 推荐方案: 异步发送邮件（更自然，不人为延迟用户体验）

OTP 清理:
├── 验证成功后立即清除 otp_code_hash/otp_purpose/otp_expires_at/otp_attempts
├── 不需要定期清理任务（过期 OTP 在下次发送时会被覆盖）
└── 部分索引: WHERE otp_code_hash IS NOT NULL
```

### 5.4 修改现有模块

**`dependencies.py`**（核心改造，详细清单）：
- 替换 Clerk RS256 JWT 验证 → 自签 HS256 JWT 验证（调用 `TokenService.verify_access_token()`）
- 移除 JIT 用户创建逻辑（~130 行代码：重试机制、Sentry 捕获、UserProfile.create_new、TierService signup bonus 等）
- 移除 `user_id.startswith("user_")` 格式校验（Clerk 格式不再适用，如需要可改为 UUID 格式验证）
- 移除 `_get_allowed_origins()` 函数和 `azp` 验证逻辑（Clerk 特有）
- 移除 `import asyncio` 和 `asyncio.sleep(0.1)` 重试逻辑（JIT 专用）
- `get_current_user()` 签名不变（`authorization: str = Header(None)` → 返回 `UserProfile`），下游代码无需改动
- `optional_user()` / `get_current_user_optional`：内部调用 `get_current_user()`，自动适配，无需单独修改
- `require_admin()`、`require_member()`、`require_pro()`：依赖 `get_current_user()` 返回的 `UserProfile`，自动适配
- `get_current_user_with_workspace()`：依赖 `get_current_user()`，自动适配
  - 注意：`workspaces.owner_id` 外键也需改为 UUID（已包含在 56 个外键变更中）

**`config.py`**：
- 移除：`CLERK_WEBHOOK_SECRET`, `CLERK_PEM_PUBLIC_KEY`, `CLERK_FRONTEND_API`, `CLERK_ALLOWED_ORIGINS`
- 移除：`TEST_JWT_PUBLIC_KEY` 相关逻辑（HS256 测试直接用 `AUTH_JWT_SECRET` 签发，不需要单独测试密钥）
- 新增：`AUTH_JWT_SECRET`, `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES`, `AUTH_REFRESH_TOKEN_EXPIRE_DAYS` 等
- 更新 `REQUIRED_ENV_VARS`：新增 `AUTH_JWT_SECRET`
- 更新 `RECOMMENDED_ENV_VARS`：移除 `CLERK_WEBHOOK_SECRET`、`CLERK_PEM_PUBLIC_KEY`，保留 `STRIPE_*`、`RESEND_API_KEY`
- 新增 `validate_secrets_at_startup()` 强化校验：`AUTH_JWT_SECRET` 长度必须 ≥ 43 字符（256-bit = 32 bytes → base64 ≈ 43 chars），不满足则 raise 启动失败（防止开发者误设弱密钥如 "123456"）

**`container.py`**：
- 注册新服务：`get_registration_service()`, `get_session_service()`, `get_account_service()`, `get_token_service()`, `get_password_service()`, `get_otp_service()` 等
- 移除：`get_clerk_webhook_service()`
- 遵循现有的 async factory 懒加载模式

### 5.5 删除模块

- `domains/webhooks/clerk_webhook_service.py`（整个文件）
- Clerk webhook 路由
- `svix` 依赖

### 5.6 新增依赖

- `argon2-cffi` — 密码哈希
- `resend` — 邮件发送（**已安装**，复用现有配置：`RESEND_API_KEY`、`SUPPORT_EMAIL_FROM`）
- 移除 `svix`

### 5.7 邮件发送前置条件

```
域名配置（Phase 1 开始前必须完成）：
- makedecodables.com 已配置 Resend 的 SPF 记录
- makedecodables.com 已配置 Resend 的 DKIM 记录
- 建议配置 DMARC 策略（v=DMARC1; p=none; 开始观察模式）
- 在 Resend Dashboard 验证域名所有权

发送测试清单（Phase 1 完成后验证）：
- 发送到 Gmail → 检查是否进垃圾箱
- 发送到 Outlook → 检查是否进垃圾箱
- 检查移动端邮件显示效果（OTP 数字清晰可辨）
- 检查 OTP 邮件是否被手机系统自动识别（iOS/Android OTP 自动填充）
```

### 5.8 OTP 邮件模板设计

```
发件人: Make Decodables <noreply@makedecodables.com>
（使用 RESEND_API_KEY + 已验证的 makedecodables.com 域名）

4 种邮件模板（根据 otp_purpose 区分）:

1. purpose = "register"
   Subject: "Your verification code: 123456"
   Body:
   - Make Decodables Logo
   - "Welcome! Please verify your email"
   - OTP 大字体居中显示: "123456"（方便手机自动识别）
   - "This code expires in 10 minutes."
   - "If you didn't create an account, you can safely ignore this email."
   - Footer: © Make Decodables

2. purpose = "forgot_password"
   Subject: "Password reset code: 123456"
   Body:
   - "We received a password reset request for your account."
   - OTP: "123456"
   - "This code expires in 10 minutes."
   - "If you didn't request this, your account is safe. No action needed."

3. purpose = "change_password"
   Subject: "Password change verification: 123456"
   Body:
   - "You requested to change your password."
   - OTP: "123456"
   - "This code expires in 10 minutes."
   - "If you didn't make this request, please secure your account immediately."

4. purpose = "delete_account"
   Subject: "Account deletion verification: 123456"
   Body:
   - "You requested to delete your account."
   - OTP: "123456"
   - "⚠️ This action is irreversible."
   - "This code expires in 10 minutes."
   - "If you didn't make this request, please secure your account immediately."

HTML 模板规范:
- 响应式设计（移动端优先）
- OTP 数字使用等宽字体，字号 32px+，方便阅读和自动识别
- 品牌色彩与 Design System 一致
- 纯文本版本作为 fallback（Resend 支持 text + html 双版本）
- 多语言: MVP 阶段仅英文，未来可通过用户 locale 设置扩展
```

---

## 六、前端架构设计

### 6.1 Auth 抽象层（核心，实现可替换）

```
decodables-fe/lib/auth/
├── index.ts              # 统一导出
├── AuthProvider.tsx       # React Context Provider（替换 ClerkProvider）
├── useAuth.ts            # useAuth() hook（同名替换 Clerk 的）
├── useUser.ts            # useUser() hook（同名替换 Clerk 的）
├── authApi.ts            # 调用后端 /auth/* 端点
├── tokenManager.ts       # Token 存储、自动刷新、拦截器
└── types.ts              # AuthState, AuthUser 等类型
```

**关键设计**：新 `useAuth()` 暴露与 Clerk 相同的接口，最小化下游改动。

**useAuth() 完整 TypeScript 接口定义**：

```typescript
// lib/auth/types.ts

interface UseAuthReturn {
  // === 与 Clerk 相同的字段（下游代码零改动）===
  isSignedIn: boolean           // 用户是否已登录
  isLoaded: boolean             // Auth 是否初始化完成
  userId: string | null         // UUID（Clerk 时为 "user_2abc..."）
  getToken: () => Promise<string | null>  // 返回 Access Token
  signOut: () => Promise<void>            // 登出

  // === 新增字段 ===
  signIn: (email: string, password: string) => Promise<void>
  // 注册不在 useAuth 中（多步流程由注册页面自行管理）

  // === OTP 相关 ===
  sendOtp: (email: string, purpose: OtpPurpose) => Promise<void>
  verifyOtp: (email: string, otpCode: string, purpose: OtpPurpose) => Promise<string>  // 返回 otp_verified_token
}

type OtpPurpose = 'register' | 'change_password' | 'delete_account' | 'forgot_password'

// 审计结论：当前代码库中所有 getToken() 调用都不传参数（无 skipCache/template），
// 所有 signOut() 调用也不传参数（无 redirectUrl/sessionId），
// 因此简化签名完全兼容。
```

**useUser() 完整 TypeScript 接口定义**：

```typescript
// lib/auth/types.ts

interface AuthUser {
  id: string                    // UUID
  email: string                 // 用户邮箱
  displayName: string | null    // 显示名称
  imageUrl: string | null       // 头像 URL（Gravatar 或上传）
  tier: string                  // 't1' | 't2' | 't3'
  role: string                  // 'user' | 'admin'
  emailVerified: boolean        // 邮箱是否已验证
}

interface UseUserReturn {
  user: AuthUser | null         // 用户信息（未登录为 null）
  isLoaded: boolean             // 是否加载完成
}
```

**useUser() 和 useClerk() 替换策略**：

当前代码库中只有 2 个文件使用 `useUser()` 和 `useClerk()`（`MobileMenu.tsx` 和 `profile/page.tsx`），用法较简单：

```
Clerk useUser() 当前用法 → 替换方案:
├── user.primaryEmailAddress  → useUser().user.email（来自 /user/me 或 JWT payload）
├── user.firstName            → useUser().user.displayName（来自 profiles 表）
├── user.imageUrl             → useUser().user.imageUrl（Gravatar 或上传头像）
├── user.publicMetadata.tier  → useUser().user.tier（来自 Zustand store，/user/me 更新）
├── isSignedIn                → useAuth().isSignedIn（同之前）

Clerk useClerk() 当前用法 → 替换方案:
├── signOut()                 → useAuth().signOut()（合并到 useAuth）
├── openUserProfile()         → router.push('/account')（自定义设置页替代 Clerk 弹窗）

数据来源：
- AuthProvider 初始化时调用 /user/me → 写入 Zustand store
- useUser() 从 Zustand store 读取（不直接请求后端）
- 这与当前 GlobalProviders.tsx 的模式一致（fetchUserData → set Zustand）
```

**AuthProvider 初始化流程**（替代 Clerk Fallback 机制）：

当前 `GlobalProviders.tsx` 在 `/user/me` API 失败时，使用 `clerkUser.publicMetadata.tier` 作为 fallback。新系统不再有 Clerk 数据源，替代方案如下：

```
AuthProvider 启动流程：
1. 检查内存中是否有 Access Token → 有则跳到步骤 3
2. 没有 → 调用 /api/auth/refresh（BFF 代理，自动携带 httpOnly cookie）
   → 成功：获取新 Access Token，存入内存
   → 失败：用户未登录，isSignedIn = false，流程结束
3. 有 Access Token → 调用 /user/me 获取用户完整数据
   → 成功：写入 Zustand store（tier, credits, role 等）
   → 失败：使用 JWT payload 中的 tier/role 作为 fallback
     （Access Token payload 包含 { sub, email, role, tier }，可 decode 后使用）
4. 标记 isLoaded = true

优势：JWT payload 本身就有 tier/role，比 Clerk publicMetadata fallback 更可靠
```

### 6.2 Token 存储策略

```
                    ┌──────────────┐
                    │   Browser    │
                    ├──────────────┤
Access Token  ───→  │   内存(Zustand) │  ← 不存 localStorage，防 XSS
                    ├──────────────┤
Refresh Token ───→  │ httpOnly Cookie│  ← 由 Next.js API Route 代理设置
                    └──────────────┘

流程：
1. 登录 → 前端调用 /api/auth/login (Next.js API Route)
2. Next.js Route 转发到 Railway 后端 /auth/login
3. 后端返回 { access_token, refresh_token }
4. Next.js Route 将 refresh_token 设为 httpOnly cookie，access_token 返回给客户端
5. 客户端将 access_token 存入内存

为什么不直接用后端设 cookie？
→ 前端 (Vercel) 和后端 (Railway) 不同域，httpOnly cookie 的跨域设置复杂
→ Next.js API Route 代理是业界常用方案，cookie 设在前端域上

Access Token 存储细节（Zustand）：
- 存储位置：Zustand store（非 persist，纯内存）
- 与现有 store 的关系：新建 lib/auth/authStore.ts（独立于 useUserStore）
  → authStore: { accessToken, isSignedIn, isLoaded }（auth 状态）
  → useUserStore: { tier, credits, role, ... }（业务数据，已有）
- tokenManager.ts 内部使用 authStore 读写 token
- useAuth() hook 从 authStore 读取状态
```

**Next.js API Route 代理（BFF）**：
```
decodables-fe/app/api/auth/[...action]/route.ts
→ 代理所有 /auth/* 请求到后端
→ 管理 httpOnly cookie 的设置/清除

实现逻辑伪代码：

async function handler(req: NextRequest, { params }: { params: { action: string[] } }) {
  const action = params.action.join('/')  // e.g. "login", "refresh", "logout"
  const body = await req.json().catch(() => ({}))

  // 1. refresh/logout 需要从 cookie 中取 refresh_token 注入 body
  if (action === 'refresh' || action === 'logout') {
    const refreshToken = req.cookies.get('refresh_token')?.value
    if (!refreshToken) return NextResponse.json({ error: 'no_session' }, { status: 401 })
    body.refresh_token = refreshToken
  }

  // 2. 透传 Access Token（已登录端点需要）
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const authHeader = req.headers.get('Authorization')
  if (authHeader) headers['Authorization'] = authHeader

  // 3. 转发到后端
  const backendRes = await fetch(`${BACKEND_URL}/auth/${action}`, {
    method: req.method,  // 支持 POST/GET/DELETE
    headers,
    body: ['GET', 'DELETE'].includes(req.method) ? undefined : JSON.stringify(body),
  })
  const data = await backendRes.json()

  // 3. 处理响应
  const res = NextResponse.json(
    { access_token: data.access_token, user: data.user },
    { status: backendRes.status }
  )

  // 4. 设置/清除 httpOnly cookie
  // 注意: refresh 端点的 rotate 参数决定是否返回新 refresh_token:
  // - BFF 代理调用(默认 rotate=true): 后端返回新 refresh_token → 更新 cookie
  // - SSR 服务端调用(rotate=false): 后端不返回 refresh_token → 不更新 cookie
  // 因此这里只需检查 data.refresh_token 是否存在即可正确处理两种场景
  if (data.refresh_token) {
    // login/register/refresh(rotate=true) → 设置新 cookie
    res.cookies.set('refresh_token', data.refresh_token, {
      httpOnly: true, secure: true, sameSite: 'lax',
      path: '/api/auth', maxAge: 7 * 24 * 60 * 60,
    })
  }
  if (action === 'logout' || action === 'logout-all' || action === 'delete-account') {
    // 登出/注销 → 清除 cookie
    res.cookies.delete('refresh_token')
  }

  return res
}

路由映射（~80 行代码）：
export { handler as POST, handler as GET, handler as DELETE }

⚠️ BFF 代理维护策略:
- 当前 14 个 auth 端点共用一个 catch-all handler，通过 action 字符串分支处理
- 核心分支逻辑仅 3 类: (1) 需要注入 cookie 的: refresh/logout
  (2) 需要设置 cookie 的: login/register/complete/refresh
  (3) 需要清除 cookie 的: logout/logout-all/delete-account
- 如果未来 auth 端点超过 20 个，或出现复杂的端点特有逻辑，考虑拆分为:
  app/api/auth/login/route.ts, app/api/auth/register/[step]/route.ts 等独立文件
- 当前阶段保持 catch-all 即可，逻辑足够简单（3 类分支 + 透传）

POST:
- /api/auth/login                → {BACKEND}/auth/login
- /api/auth/register/send-otp   → {BACKEND}/auth/register/send-otp
- /api/auth/register/verify-otp → {BACKEND}/auth/register/verify-otp
- /api/auth/register/complete   → {BACKEND}/auth/register/complete
- /api/auth/refresh              → {BACKEND}/auth/refresh  (注入 cookie 中的 refresh_token)
- /api/auth/logout               → {BACKEND}/auth/logout   (注入 cookie 中的 refresh_token)
- /api/auth/logout-all           → {BACKEND}/auth/logout-all (透传 Authorization header)
- /api/auth/otp/send            → {BACKEND}/auth/otp/send  (透传 Authorization header)
- /api/auth/otp/verify          → {BACKEND}/auth/otp/verify (透传 Authorization header)
- /api/auth/*                    → {BACKEND}/auth/*  (其余端点透传)
GET:
- /api/auth/sessions             → {BACKEND}/auth/sessions  (透传 Authorization header)
DELETE:
- /api/auth/sessions/{id}        → {BACKEND}/auth/sessions/{id} (透传 Authorization header)
```

**httpOnly Cookie 安全属性**：
```
name:     "refresh_token"
httpOnly: true                    # JS 无法读取，防 XSS
secure:   true                    # 仅 HTTPS（localhost 开发时自动豁免）
sameSite: "lax"                   # 防 CSRF，同时允许导航跳转携带 cookie
path:     "/api/auth"             # 仅 auth 相关路由可访问，缩小攻击面
maxAge:   7 * 24 * 60 * 60       # 7 天（与 Refresh Token 有效期一致）
```

**与现有 USE_PROXY 模式的关系**：
```
现有 api.ts 有 NEXT_PUBLIC_USE_API_PROXY 模式（开发调试用途）。
BFF auth 代理与 USE_PROXY 是不同机制，互不冲突：

- /api/auth/* → BFF 代理（管理 httpOnly cookie，所有环境启用）
- 其他 API  → 直连后端（带 Bearer Access Token，不走 BFF）

Phase 5 迁移时需确认：USE_PROXY 模式下的 API 调用也正确携带 Bearer token

USE_PROXY 模式迁移细节（Step 5.5 实施时处理）:

1. 当前 USE_PROXY 行为:
   - USE_PROXY=true 时，非 auth API 请求走 Next.js /api/proxy/* 转发到后端
   - USE_PROXY=false 时，非 auth API 请求直连后端（带 Bearer token）
   - 当前 token 来源: api.ts 中通过 getToken 回调从 Clerk useAuth().getToken 获取

2. 迁移后行为:
   - Auth 请求（/api/auth/*）: 始终走 BFF 代理，管理 httpOnly cookie（不受 USE_PROXY 影响）
   - 非 auth 请求: token 来源改为 tokenManager.getValidToken()
     - USE_PROXY=true:  请求 → Next.js proxy → 后端（proxy 需透传 Authorization header）
     - USE_PROXY=false: 请求 → 直连后端（带 Bearer token）
   - 关键修改点: api.ts 中初始化 ApiClient 时，不再传 getToken 回调，
     改为在请求拦截器中调用 tokenManager.getValidToken() 注入 Bearer header

3. 验证要点:
   - USE_PROXY=true 时: 确认 Next.js proxy 中间层透传 Authorization header 到后端
   - USE_PROXY=false 时: 确认 api.ts 请求拦截器正确注入 Bearer token
   - 两种模式下 401 → refresh → 重试 的链路都正确
```

### 6.2.1 Token 生命周期管理（tokenManager.ts 核心逻辑）

**自动刷新策略：主动 + 被动双保险**

```
                        Access Token 15 分钟生命周期
|━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━|━━━━|
0min                                           14min  15min
                                                 ↑      ↑
                                          主动刷新区  过期

主动刷新（优先）：
- tokenManager 在 Access Token 签发时启动定时器
- 到期前 60 秒（第 14 分钟）自动触发 /api/auth/refresh
- 用户无感知，API 调用不中断

被动刷新（兜底）：
- API 返回 401 → 触发 refresh → 重发原请求
- 覆盖主动刷新失败、页面休眠恢复等边界场景
```

**API 请求队列（防止 refresh 期间请求失败）**

```typescript
// tokenManager.ts 核心逻辑伪代码

class TokenManager {
  private refreshPromise: Promise<string> | null = null
  private accessToken: string | null = null

  async getValidToken(): Promise<string> {
    // 1. 已有正在进行的 refresh → 等待它完成（请求去重）
    if (this.refreshPromise) {
      return await this.refreshPromise
    }

    // 2. Token 即将过期（< 60s）或已过期 → 发起 refresh
    if (this.isTokenExpiring()) {
      this.refreshPromise = this.doRefresh()
      try {
        const newToken = await this.refreshPromise
        return newToken
      } finally {
        this.refreshPromise = null
      }
    }

    // 3. Token 有效 → 直接返回
    return this.accessToken!
  }

  private isTokenExpiring(): boolean {
    // 解码 JWT 检查 exp，剩余 < 60s 视为即将过期
    const payload = decodeJwtPayload(this.accessToken)
    return payload.exp * 1000 - Date.now() < 60_000
  }

  private async doRefresh(): Promise<string> {
    const res = await fetch('/api/auth/refresh', { method: 'POST' })
    // BFF 代理自动携带 httpOnly cookie
    if (!res.ok) throw new SessionExpiredError()
    const { access_token } = await res.json()
    this.setToken(access_token)
    // 通过 BroadcastChannel 通知其他标签页
    this.channel.postMessage({ type: 'token_refreshed', token: access_token })
    return access_token
  }
}

// SessionExpiredError 处理链:
// 1. TokenManager.doRefresh() 抛出 SessionExpiredError
// 2. api.ts 拦截器捕获 → 不再重试（区别于普通 401）
// 3. 清除 Zustand auth 状态（accessToken = null, isSignedIn = false）
// 4. 清除 useUserStore 业务数据（tier = null, credits = null, role = null 等）
//    → 防止在 /login 页面或下一次登录时残留上一个用户的数据
// 5. 重置所有 loading/modal 状态（防止 token null 时 UI 卡死）
// 6. router.push('/login?redirect=' + currentPath)
// 7. BroadcastChannel 广播 user_logged_out → 其他标签同步登出
```

**跨标签 Token 同步（BroadcastChannel）**

```
BroadcastChannel 消息类型:

1. token_refreshed:  某标签刷新了 token → 其他标签更新内存中的 token
2. user_logged_out:  某标签登出 → 其他标签清除状态并跳转 /login
3. user_logged_in:   某标签登录 → 其他标签（如停留在 /login 页）刷新状态

⚠️ 只广播 access_token，绝不广播 refresh_token
（refresh_token 仅存在于 httpOnly cookie 中，JS 不可读取也不应传播）

跨标签 Refresh 竞态解决:
- Tab A 和 Tab B 同时检测到 token 过期
- Tab A 先发起 refresh → refreshPromise 不为 null
- Tab A refresh 成功 → 广播新 access_token
- Tab B 收到广播 → 直接使用新 token，取消自己的 refresh
- 如果 Tab B 已经发起了 refresh（Tab A 广播前）：
  → 后端 Refresh Token 轮换：Tab A 的旧 refresh token 已作废
  → Tab B 的 refresh 用的是同一个 cookie → BFF 代理发的是同一个旧 token → 可能触发重用检测
  → 解决方案：Tab B 发起 refresh 前先等 CROSS_TAB_REFRESH_DELAY_MS（默认 300ms），
    期间监听广播。收到则取消 refresh，未收到则继续发起。
  → 该延迟值可通过常量配置，选择 300ms 是因为 BFF 代理 + 后端验证通常 < 200ms

Fallback（BroadcastChannel 不可用时）:
- Safari < 15.4、所有 IE、部分 WebView 不支持 BroadcastChannel
- Fallback: 使用 localStorage 'storage' 事件
  → Tab A: localStorage.setItem('auth_sync', JSON.stringify({ type, token, timestamp }))
  → Tab B: window.addEventListener('storage', handler) 监听变化
- 检测: if (typeof BroadcastChannel !== 'undefined') 使用 BC，否则 fallback
- storage 事件的限制：同一 tab 内不触发（只在其他 tab 触发），与 BC 行为一致
```

**页面刷新（F5）处理**

```
用户按 F5：
1. Zustand 内存清空（accessToken = null）
2. httpOnly cookie 保留（refresh_token 不受影响）
3. Next.js 重新渲染 → AuthProvider 挂载
4. AuthProvider useEffect 检测到 accessToken 为 null
5. 调用 /api/auth/refresh（cookie 自动携带）
6. 获取新 accessToken → 存入 Zustand → isLoaded = true

用户体验：
- 整个过程 < 200ms（BFF 代理 + 后端验证）
- isLoaded = false 期间显示 Skeleton 加载态
- 不会出现"未登录"闪烁（Skeleton → 已登录状态）
```

### 6.3 新增认证页面

```
decodables-fe/app/(auth)/
├── layout.tsx              # 居中卡片布局（品牌 Logo + 白色卡片 + 背景色）
├── login/page.tsx          # 登录表单（邮箱 + 密码）
├── register/page.tsx       # 注册表单（多步：邮箱 → OTP → 密码+昵称）
└── forgot-password/page.tsx # 忘记密码（多步：邮箱 → OTP → 新密码）
```

**页面 UI 设计**：

```
(auth)/layout.tsx — 共享布局：
- 居中卡片布局：max-w-md mx-auto，白色卡片 + 阴影
- 顶部：品牌 Logo（链接到首页）
- 底部：返回首页 / 帮助链接
- 背景：与 Design System 一致的渐变背景

login/page.tsx — 登录页（单步）：
- 标题："Sign in to your account"
- 字段：Email + Password
- 按钮："Sign In"（loading 状态）
- 链接："Forgot password?" → /forgot-password
- 链接："Don't have an account? Sign up" → /register
- 错误处理：401 → "Invalid email or password" / 403 → "Account locked, try again in X minutes"

register/page.tsx — 注册页（三步 + 可选恢复步骤，同一页面内切换）：
  Step 1 — 输入邮箱：
  - 标题："Create your account"
  - 字段：Email
  - 按钮："Send Verification Code"（loading 状态）
  - 提交后调用 POST /auth/register/send-otp
  - 链接："Already have an account? Sign in" → /login
  - 如果响应 has_restorable_account=true → 进入 Step 1b（恢复选择）
  - 如果 has_restorable_account=false → 直接进入 Step 2

  Step 1b — 账户恢复选择（仅当 has_restorable_account=true 时显示）：
  - 标题："Welcome back!"
  - 提示文字："We found a previously deleted account associated with this email."
  - 单选选项：
    ○ "Restore my previous account" — 恢复旧账户（保留历史数据）
    ○ "Create a brand new account" — 全新开始（旧账户将无法再恢复）
  - 字段：6 位 OTP 输入框（需验证邮箱归属后才能执行恢复/创建）
  - 按钮："Continue"（loading 状态）
  - 链接："Use a different email" → 返回 Step 1
  - 提交后调用 POST /auth/register/verify-otp → 获取 register_token
  - 前端保存用户选择（restore_account: boolean），传入 Step 3 的 complete 请求

  Step 2 — 输入 OTP（非恢复流程走此步骤）：
  - 标题："Enter verification code"
  - 提示文字："We sent a 6-digit code to xxx@xxx.com"
  - 字段：6 位 OTP 输入框（每位一个输入框，自动跳转，支持粘贴）
  - 按钮："Verify"（loading 状态）
  - 链接："Didn't receive the code? Resend"（60 秒倒计时后可重发）
  - 链接："Use a different email" → 返回 Step 1
  - 提交后调用 POST /auth/register/verify-otp → 获取 register_token
  - 错误处理：400 → "Invalid code" / "Code expired, please resend"

  Step 3 — 设置密码和昵称：
  - 标题："Set up your account"（恢复流程时为 "Restore your account"）
  - 字段：Display Name（可选）+ Password + Confirm Password
  - 密码强度指示器（实时校验：≥8字符、大小写+数字）
  - 按钮："Create Account" / "Restore Account"（根据 restore_account 动态切换，loading 状态）
  - 提交后调用 POST /auth/register/complete（携带 register_token + restore_account）
  - 注册/恢复成功 → 自动登录 → 跳转 /dashboard

forgot-password/page.tsx — 忘记密码（三步流程，同一页面内切换）：
  Step 1 — 输入邮箱：
  - 标题："Reset your password"
  - 字段：Email
  - 按钮："Send Verification Code"
  - 提交后调用 POST /auth/otp/send { purpose: "forgot_password" }
  - 提交后始终进入 Step 2（防枚举，即使邮箱不存在也不提示）

  Step 2 — 输入 OTP：
  - 标题："Enter verification code"
  - 提示文字："If this email is registered, we sent a 6-digit code"
  - 字段：6 位 OTP 输入框
  - 链接："Resend code"（60 秒倒计时）
  - 提交后调用 POST /auth/otp/verify { purpose: "forgot_password" } → 获取 otp_verified_token

  Step 3 — 设置新密码：
  - 标题："Set new password"
  - 字段：New Password + Confirm Password
  - 按钮："Reset Password"
  - 提交后调用 POST /auth/forgot-password/reset（携带 otp_verified_token）
  - 成功 → "Password reset successfully" + 自动跳转 /login
```

**OTP 输入组件（复用组件）**：
```
components/auth/OtpInput.tsx — 6 位 OTP 输入框：
- 6 个独立 input 框，每个限制 1 位数字
- 输入后自动聚焦下一个框
- 支持粘贴完整 6 位验证码（自动分发到各框）
- 支持退格删除（自动回到上一个框）
- 支持 autocomplete="one-time-code"（iOS/Android 自动填充 OTP）
- 失败时清空并聚焦第一个框
- 可复用于注册和忘记密码页面
```

**修改密码 UI（在 /account 页面内）**：
```
入口：/account 页面 → "Security" 区域 → "Change Password"
实现方式：内嵌在 Account 页面中（不是独立页面）

UI 流程：
1. 显示 "Change Password" 卡片，按钮 "Change Password"
2. 点击后展开表单：
   Step 1: 点击 "Send Verification Code" → 调用 POST /auth/otp/send { purpose: "change_password" }
   Step 2: OTP 输入框（复用 OtpInput 组件）→ 调用 POST /auth/otp/verify → 获取 otp_verified_token
   Step 3: 输入 Current Password + New Password + Confirm Password
           → 调用 POST /auth/change-password（携带 otp_verified_token）
3. 成功 → 显示 "Password changed successfully" + 折叠表单
4. 取消 → 折叠表单
```

**删除账户 UI（在 /account 页面内）**：
```
入口：/account 页面 → "Danger Zone" 区域（红色边框卡片）
实现方式：使用 ResponsiveModal（桌面 Dialog / 移动 Sheet）

UI 流程：
1. 点击 "Delete Account" 按钮（红色）→ 弹出确认对话框
2. 对话框内容：
   - 警告图标 + "This action cannot be undone"
   - 说明文字：列出删除后果（项目、积分、订阅将被删除）
   - 勾选框："I understand this action is irreversible"
   - 勾选后激活 "Send Verification Code" 按钮
3. Step 1: 点击 "Send Verification Code" → 发送 OTP
4. Step 2: 对话框内输入 OTP（复用 OtpInput 组件）→ 验证 → 获取 otp_verified_token
5. Step 3: 显示 "Delete My Account" 最终确认按钮（红色）
   → 调用 POST /auth/delete-account（携带 otp_verified_token）
6. 成功 → 清除登录状态 → 跳转首页 + "Account deleted" 提示
7. 错误处理：
   - 500 (Stripe 取消订阅失败) → "Account deletion failed. Please try again later or contact support."
   - 400 (invalid_token/token_expired) → "Verification expired. Please restart the deletion process."
   - 网络错误 → "Unable to connect. Please check your connection and try again."
```

**设备管理 UI（在 /account 页面内）**：
```
入口：/account 页面 → "Security" 区域 → "Active Sessions"

UI 设计：
- 卡片列表，每个卡片显示一个活跃设备：
  - 设备图标（桌面/手机/平板，根据 user_agent 判断）
  - 设备名称（如 "Chrome on macOS"）
  - IP 地址（部分遮蔽：192.168.*.*)
  - 最后活跃时间（如 "2 minutes ago"）
  - 当前设备标记：绿色 "Current" badge
  - 非当前设备：显示 "Revoke" 按钮
- 底部 "Sign out all other devices" 按钮
- 踢出设备确认：简单的二次确认对话框

API 调用：
- 加载：GET /auth/sessions
- 踢出设备：DELETE /auth/sessions/{id}
- 全部登出：POST /auth/logout-all
```

**UserMenu 组件（替换 Clerk UserButton）**：
```
components/common/UserMenu.tsx — 头像下拉菜单（极简 4 项）：

设计理念：
- 参考 Canva/Notion 的极简风格
- Dashboard/Marketplace 已在主导航中展示，不重复
- 下拉菜单只放"非导航"的账户操作项
- Profile/Settings 统一为 "Account" 一个入口

触发器：
- 用户头像（圆形，36px，9x9 Tailwind）
- 头像来源：Gravatar（根据 email MD5 生成 URL）+ 本地首字母默认头像
  - Gravatar URL: `https://www.gravatar.com/avatar/${md5(email.trim().toLowerCase())}?d=404&s=80`
  - 使用 `?d=404` 而非 `?d=initials`：Gravatar 的 initials 服务不稳定，部分邮箱返回空白
  - Fallback 策略：前端 `<img>` 的 `onError` 回调中切换为本地首字母头像
  - 本地首字母头像实现：`<div>` + CSS（bg-indigo-100 text-indigo-700，文字居中显示首字母大写）
  - 未来扩展：用户上传自定义头像（存 Supabase Storage）
  - MVP 阶段使用 Gravatar（d=404）+ 本地首字母即可

下拉菜单项（共 4 项）：
┌─────────────────────────────┐
│ 👤 DisplayName              │  ← 用户信息区（顶部）
│    user@email.com           │
├─────────────────────────────┤
│ 🔧 Account       → /account│  ← 统一的账户管理入口
│ 📋 Transactions   → /txn   │
│ 💳 Buy Credits    → /dash?c│
├─────────────────────────────┤
│ 🚪 Sign Out                │  ← 红色文字，独立区域
└─────────────────────────────┘

具体说明：
1. 用户信息区（顶部，不可点击）：
   - 显示名称 + email（truncate 处理长文本）
   - 无 tier badge（简化信息密度）
2. "Account" → /account
   - 图标：User (lucide)
   - 统一入口：包含 Profile 信息、安全设置、偏好等
3. "Transactions" → /transaction-history
   - 图标：History (lucide)
4. "Buy Credits" → /dashboard?tab=credits
   - 图标：CreditCard (lucide)
5. 分隔线
6. "Sign Out" → signOut()
   - 图标：LogOut (lucide)
   - 文字颜色：rose-600，hover: rose-50 背景

移动端：
- 不使用下拉菜单，UserMenu 只在 sm: 以上显示
- 移动端通过 BottomNavbar "Account" tab 进入 /account 页面
- MobileMenu 底部有 Sign Out 按钮
```

**Account 页面（统一的账户管理页面）**：

```
路由：/account
命名决策：统一使用 "Account"（参考 Canva/Notion 模式）
- 不再区分 "Profile" 和 "Settings"
- PC 和 Mobile 共用同一路由 /account
- BottomNavbar 的 "Profile" tab 改为 "Account"

文件结构：
decodables-fe/app/account/
├── page.tsx                # Account 主页面（响应式，PC/Mobile 共用）
└── _components/
    ├── AccountSidebar.tsx   # PC 侧边栏导航（仅 lg: 以上显示）
    ├── ProfileSection.tsx   # 个人信息区域
    ├── SecuritySection.tsx  # 安全设置（修改密码 + 设备管理）
    ├── CreditsSection.tsx   # 积分与订阅（复用 CreditsCard + SubscriptionCard）
    └── DangerZoneSection.tsx # 危险区域（删除账户）

组件复用：
- CreditsCard → 从 components/profile/CreditsCard.tsx 复用
- SubscriptionCard → 从 components/profile/SubscriptionCard.tsx 复用
- UserIdCard → 从 components/profile/UserIdCard.tsx 复用
- OtpInput → 从 components/auth/OtpInput.tsx 复用（修改密码 + 删除账户）
```

```
PC 布局（lg: 以上，≥1024px）：

┌─────────────────────────────────────────────────────┐
│ Navbar                                              │
├──────────────┬──────────────────────────────────────┤
│  Sidebar     │  Content Area                        │
│              │                                      │
│  ◉ Profile   │  [根据 sidebar 选中项切换内容]         │
│  ○ Security  │                                      │
│  ○ Credits   │  Profile 区域（默认）：                │
│  ○ Danger    │  - 头像 + 显示名称 + 邮箱             │
│              │  - User ID（复用 UserIdCard）          │
│              │  - 编辑 Display Name 表单              │
│              │                                      │
│              │  Security 区域：                      │
│              │  - Change Password（OTP 三步流程）     │
│              │  - Active Sessions（设备列表）         │
│              │                                      │
│              │  Credits & Subscription 区域：         │
│              │  - CreditsCard（余额 + 购买）          │
│              │  - SubscriptionCard（当前计划）         │
│              │                                      │
│              │  Danger Zone：                        │
│              │  - Delete Account（OTP 确认）          │
│              │                                      │
├──────────────┴──────────────────────────────────────┤
│ Footer (optional)                                   │
└─────────────────────────────────────────────────────┘

PC 实现细节：
- 整体布局：max-w-4xl mx-auto，左侧 sidebar 200px + 右侧 content flex-1
- Sidebar：sticky top-[calc(44px+64px+16px)]（Banner + Navbar 高度 + 间距）
  - 导航项：Profile / Security / Credits & Subscription / Danger Zone
  - 选中态：左侧 2px indigo border + bg-indigo-50 + text-indigo-600
  - 非选中：text-slate-600 hover:bg-slate-50
  - 使用 scrollIntoView + IntersectionObserver 实现 scroll spy
  - 或使用 tab 切换模式（URL hash: /account#security）
- Content：单页滚动模式（所有区域在同一页面上下排列）
  - 每个区域用 <section id="profile|security|credits|danger"> 标记
  - 区域间用 border-b border-slate-200 分隔
```

```
Mobile 布局（< lg，即 < 1024px）：

┌─────────────────────────┐
│ Navbar                  │
├─────────────────────────┤
│                         │
│  [头像]                  │
│  DisplayName            │
│  user@email.com         │
│  [Tier Badge]           │
│                         │
│  ┌───────────────────┐  │
│  │ User ID: 26...    │  │  ← UserIdCard
│  └───────────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │ Credits: 150      │  │  ← CreditsCard
│  │ Monthly / Perm    │  │
│  │ [Buy Credits]     │  │
│  └───────────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │ Starter Plan      │  │  ← SubscriptionCard
│  │ [Manage/Upgrade]  │  │
│  └───────────────────┘  │
│                         │
│  Quick Actions:         │
│  ├─ Transaction History │  ← 打开 TransactionSheet
│  ├─ Account Settings    │  ← 打开 SecuritySheet (含密码+设备)
│  ├─ Notifications       │  ← 打开 NotificationsSheet
│  ├─ Language & Theme    │  ← 打开 PreferencesSheet
│  └─ Help & Support      │  ← 跳转 /manual
│                         │
│  [Sign Out]             │
│                         │
│  Version 1.0.0          │
│                         │
├─────────────────────────┤
│ BottomNavbar            │
│ Home|Dash|Create|Mkt|Acct│
└─────────────────────────┘

Mobile 实现细节：
- 沿用当前 /profile 页面的 iOS Settings 风格布局
- ProfileHeader → UserIdCard → CreditsCard → SubscriptionCard → QuickActionsList → SignOutButton
- Quick Actions 使用 drill-down 模式（点击打开 Bottom Sheet）
- "Account Settings" Quick Action 打开包含密码修改 + 设备管理的 Sheet
- 不需要 sidebar（移动端空间有限，使用 sheet drill-down 更自然）
```

```
BottomNavbar 更新：
- 当前: { id: 'profile', label: 'Profile', href: '/profile', icon: User }
- 改为: { id: 'account', label: 'Account', href: '/account', icon: User }

MobileMenu 更新：
- 底部用户区域保持不变（Credits + User Info + Sign Out）
- 无需新增 Account 入口（BottomNavbar 已有）

Navbar UserMenu（PC）更新：
- 移除 Profile、Dashboard、Marketplace、Settings 4 个冗余项
- 保留 Account（新）、Transactions、Buy Credits、Sign Out（共 4 项）
- Copy User ID 功能移入 Account 页面的 UserIdCard
```

```
路由迁移对照表：

| 旧路由 | 新路由 | 说明 |
|--------|--------|------|
| /profile | /account | 统一命名 |
| /profile/settings | /account | 设置功能内嵌在 Account 页面中 |
| BottomNavbar "Profile" | BottomNavbar "Account" | tab 名称更新 |
| UserMenu "Settings" | UserMenu "Account" | 菜单项更新 |
| UserMenu "Profile" | (移除) | 合并到 Account |

openUserProfile() 替换：
- 旧：router.push('/profile/settings')
- 新：router.push('/account')
```

**登录后重定向机制**：
```
/login?redirect=/dashboard?showCreate=true

login/page.tsx 实现：
1. 从 searchParams 读取 redirect 参数
2. 登录成功后跳转到 redirect URL
3. 无 redirect 参数时默认跳转 /dashboard
4. 安全校验：redirect 必须是站内相对路径（以 / 开头，不含 //）
   防止 Open Redirect 攻击（如 redirect=https://evil.com）
```

### 6.4 Clerk 组件替换映射

| Clerk 组件 | 替换为 | 位置 |
|-----------|--------|------|
| `<ClerkProvider>` | `<AuthProvider>` | `layout.tsx` |
| `clerkMiddleware()` | 自定义 middleware | `middleware.ts` |
| `<SignIn>` | `<LoginForm>` / 跳转到 `/login` | 3 个 AuthGate 位置 |
| `<UserButton>` | `<UserMenu>` (极简 4 项：Account/Transactions/Buy Credits/Sign Out) | Navbar |
| `<SignedIn>` | `{isSignedIn && ...}` | Navbar |
| `<SignedOut>` | `{!isSignedIn && ...}` | Navbar |
| `<SignInButton>` | `<Link href="/login">` | Navbar |
| `<SignInButton forceRedirectUrl="...">` | `<Link href="/login?redirect=...">` | Navbar（需 login 页支持 redirect 参数） |
| `<ClerkLoading>` | `{!isLoaded && <Skeleton>}` | Navbar |
| `<ClerkLoaded>` | `{isLoaded && ...}` | Navbar |
| `ClerkBillingPage` import | **移除**（Navbar 不再需要引用） | Navbar |
| `ClerkTransactionHistory` import | **移除**（Navbar 不再需要引用） | Navbar |
| `useClerkWithTimeout` | 删除（不再需要 CDN 超时） | hooks/ |

### 6.5 前端文件迁移策略

**~30 个文件只需改 import 路径**：
```typescript
// 改前:
import { useAuth } from "@clerk/nextjs";

// 改后:
import { useAuth } from "@/lib/auth";
```

因为新 `useAuth()` 接口与 Clerk 的一致，绝大多数文件只需换 import，逻辑不变。

**需要改逻辑的特殊文件**（共 5 个，需逐一分析重构）：

1. **`GlobalProviders.tsx`**（389 行，最复杂）：
   - 移除：`useAuth()` / `useUser()` from `@clerk/nextjs`
   - 移除：Clerk CDN 超时 fallback 逻辑（`useClerkWithTimeout`、`isEffectivelyLoaded`、`timedOut`）
   - 移除：`clerkUser.publicMetadata.tier` 作为 fallback 数据源
   - 保留：`fetchUserData()`（调用 /user/me 获取用户数据 → 写入 Zustand store）
   - 保留：`BroadcastChannel` 跨标签同步逻辑（改为新消息格式）
   - 重构后：GlobalProviders 不再负责 auth 初始化（由 AuthProvider 负责），只负责 Zustand store 同步
   - 注意：这个文件可能在 Phase 5 完全重写为更简单的版本（~100 行），因为大部分逻辑转移到 AuthProvider

2. **`Navbar.tsx`** — 替换 Clerk UI 组件为自定义组件（`<UserMenu>` 等）

3. **`DashboardAuthGate.tsx`** — 替换 `<SignIn>` 为 `redirect('/login')`

4. **`services/api.ts`**（751 行）：
   - 移除：`getToken` 回调（当前从 Clerk `useAuth().getToken` 传入）
   - 改为：从 `tokenManager.getValidToken()` 获取 token
   - 保留：401 重试逻辑（改为调用 tokenManager.doRefresh()）
   - 保留：`USE_PROXY` 模式兼容

5. **`app/transaction-history/page.tsx`** — 替换 `useAuth()` import + `<SignIn>` 为跳转

### 6.6 Middleware 替换

```
当前 middleware.ts 仅一行：export default clerkMiddleware()
替换为自定义路由保护 middleware，~40 行代码。

判断方式: 检查 refresh_token httpOnly cookie 是否存在
（注意：middleware 无法验证 token 有效性，只检查是否存在。
  真正的验证在后端 get_current_user()，middleware 只做粗粒度保护）

路由分类：

公开路由（PUBLIC_ROUTES）— 无需登录：
  /, /pricing, /marketplace, /marketplace/*, /articles, /articles/*,
  /manual, /manual/*, /contact-us, /api/*

认证页路由（AUTH_ROUTES）— 已登录用户重定向到 /dashboard：
  /login, /register, /forgot-password

保护路由（其余所有）— 未登录重定向到 /login：
  /dashboard, /dashboard/*, /create, /create/*, /account, /account/*,
  /admin, /admin/*, /notifications, /transaction-history

实现伪代码：

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl
  const hasRefreshToken = req.cookies.has('refresh_token')

  // 1. 公开路由 → 放行
  if (isPublicRoute(pathname)) return NextResponse.next()

  // 2. 认证页 + 已登录 → 跳转 dashboard
  if (isAuthRoute(pathname) && hasRefreshToken) {
    return NextResponse.redirect(new URL('/dashboard', req.url))
  }

  // 3. 保护路由 + 未登录 → 跳转 login（带 redirect）
  if (!hasRefreshToken) {
    const loginUrl = new URL('/login', req.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  // 排除: _next (框架资源), static (静态文件), favicon.ico, 所有含 . 的路径(静态文件如 .css/.js/.png)
  // 注意: 含 . 的路径被排除意味着 /api/auth/register.json 等路径不会经过 middleware
  // 这对当前项目无影响（API 路径不含扩展名），但新增路由时需注意此约束
  matcher: ['/((?!_next|static|favicon.ico|.*\\..*).*)'],
}
```

### 6.7 Server Components / SSR Token 注入

Next.js App Router 中 Server Components 是默认模式，但无法使用 useAuth() hook 或 Zustand。需要专门的服务端 Token 获取机制。

```
方案：lib/auth/server.ts — 服务端 Token 工具函数

import { cookies } from 'next/headers'

export async function getServerAccessToken(): Promise<string | null> {
  const cookieStore = await cookies()
  const refreshToken = cookieStore.get('refresh_token')?.value
  if (!refreshToken) return null

  // 直接调用后端 /auth/refresh（不走 BFF 代理，因为已在服务端）
  const res = await fetch(`${BACKEND_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!res.ok) return null
  const { access_token } = await res.json()
  return access_token
}

使用场景:
// app/dashboard/page.tsx (Server Component)
export default async function DashboardPage() {
  const token = await getServerAccessToken()
  if (!token) redirect('/login')

  const projects = await fetch(`${BACKEND_URL}/projects`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(r => r.json())

  return <ProjectList projects={projects} />
}
```

```
⚠️ SSR 与 Refresh Token 轮换的冲突及解决方案：

问题：/auth/refresh 设计为轮换式（废旧发新）。SSR 调用 refresh 后：
- 旧 refresh token 作废，颁发新 token
- 但 SSR 无法将新 refresh token 写回客户端 httpOnly cookie
- 客户端下次用旧 cookie 中的 token → 触发重用检测 → 用户被踢出

✅ 确定方案：/auth/refresh 增加 rotate 参数

POST /auth/refresh
Body: { refresh_token, rotate?: boolean }  // 默认 rotate=true

- 客户端 BFF 代理调用：rotate=true（默认值，正常轮换，BFF 更新 cookie）
- SSR 服务端调用：rotate=false（不轮换，只返回新 access_token，旧 refresh_token 不作废）

后端实现：
- rotate=true：废旧 refresh token，颁发新 refresh token + access token
- rotate=false：验证 refresh token 有效性，仅颁发新 access token，不修改 session

安全性：rotate=false 不降低安全性，因为：
1. SSR 在服务端执行，refresh_token 不暴露给客户端 JS
2. 不触发轮换 = 不产生新 session，只验证现有 session 仍有效
3. 等价于用 refresh_token 做一次"验证读取"操作

注意事项：
1. Server Component 中获取的 token 不会存入客户端 Zustand（仅本次 SSR 使用）
2. 客户端 hydration 后，AuthProvider 会独立获取 token（通过 /api/auth/refresh，rotate=true）
3. 大多数页面用 Client Component 即可，SSR 仅用于 SEO 关键页面（如 /marketplace）

⚠️ SSR 缓存策略（防止 refresh token 被高频验证）：
- SSR 使用 rotate=false，不会轮换 refresh token，但每次 SSR 请求都会验证一次 refresh token
- 如果爬虫或高流量场景频繁触发 SSR，同一个 refresh token 会被反复验证，
  延长了 refresh token 被盗后的有效窗口（因为没有轮换，盗用者可以持续使用）
- 缓解方案:
  1. SSR 页面启用 Next.js ISR (Incremental Static Regeneration):
     export const revalidate = 60  // 60 秒缓存，避免每个请求都触发 SSR
  2. 需要实时数据的 SSR 页面: 使用 React.cache() 包装 getServerAccessToken()，
     确保同一个 SSR 请求内只调用一次（已在 Step 3.9 实现）
  3. 不需要认证的 SEO 页面（如 /marketplace 公开列表）: 直接 SSG 或 ISR，不调用 getServerAccessToken()
  4. 需要认证的 SSR 页面（如 /dashboard SSR 预加载）: 评估是否真的需要 SSR，
     大多数情况 CSR + loading skeleton 即可满足用户体验
```

---

## 七、安全设计

| 安全措施 | 实现方式 |
|---------|---------|
| 密码存储 | argon2id（OWASP 推荐） |
| OTP 安全 | 6 位数字 + SHA-256 哈希存储 + 10 分钟有效期 + 最多 5 次尝试 |
| OTP 操作隔离 | OTP 验证后颁发临时 JWT Token，后续操作需携带该 Token（防 CSRF、防重放） |
| XSS 防护 | Access Token 仅存内存，Refresh Token 为 httpOnly cookie |
| CSRF 防护 | API 使用 Bearer Token 认证（非 cookie 认证），天然防 CSRF |
| 暴力破解 | 密码: 5 次失败锁定 30 分钟; OTP: 5 次失败自动失效 + API 限流 |
| Token 泄露 | Refresh Token 轮换 + 重用检测（作废整个 family） |
| 邮箱枚举 | 注册/密码重置/OTP 发送对不存在的邮箱也返回成功 |
| 时间安全 | argon2-cffi 内置时间安全比较 |
| 跨标签同步 | BroadcastChannel 登出同步（现有逻辑保留） |
| 会话管理 | 用户可查看/踢出所有设备 |
| Open Redirect 防护 | `/login?redirect=` 参数仅允许站内相对路径（以 `/` 开头，不含 `//`） |

### 7.1 JWT Payload 中 tier 的同步延迟说明

Access Token payload 包含 `{ sub, email, role, tier }`，但 tier 变更后已签发的 token 不会自动更新。

```
策略：
- Access Token 中的 tier 仅用于前端 fallback 展示（/user/me 失败时的临时数据）
- 后端权限检查始终从数据库读取最新 tier（get_current_user() → 查 profiles 表）
- 前端升级/降级后立即调用 /user/me 刷新 Zustand store，不依赖 JWT 中的旧值
- 最坏情况：15 分钟内前端 fallback 展示旧 tier（仅显示，不影响实际权限）
- 这与 Clerk 现有行为一致（Clerk token 的 metadata 也有同步延迟）
```

### 7.2 邮箱验证时机

```
OTP 模式下的邮箱验证：
- 注册第二步就完成了邮箱验证（通过 OTP 证明邮箱可达）
- 注册完成后 email_verified = true（注册流程保证）
- 因此 email_verified=false 只存在于注册中途放弃的 pending 用户
- 不存在"已注册但邮箱未验证"的用户（与旧方案不同）

require_verified_email 依赖仍然保留：
- 作为防御层：理论上所有完成注册的用户 email_verified=true
- 保护 OAuth 注册场景（未来扩展，OAuth 用户可能需要额外验证邮箱）
- 防止数据库直接操作创建的异常用户

注册中途放弃的 pending 用户清理（确定方案）：
- **主动覆盖（实时生效）**：`create_pending_auth_user()` RPC 使用 PL/pgSQL `SELECT ... FOR UPDATE` + `IF/ELSIF` 模式（详见 4.7 节），当 pending 用户（`email_verified=false AND password_hash IS NULL`）再次注册时直接覆盖 OTP 信息，不阻塞新用户
- **定期清理（兜底）**：每天凌晨执行一次清理任务，删除 `auth_users` 中满足以下条件的记录：
  - `password_hash IS NULL`（未完成注册）
  - `email_verified = false`（未验证邮箱）
  - `created_at < now() - interval '24 hours'`（超过 24 小时）
- **实现方式**：Phase 1 中使用 pg_cron 或后端定时任务（FastAPI startup event + asyncio.create_task 定时循环）
- **SQL 示例**：`DELETE FROM auth_users WHERE password_hash IS NULL AND email_verified = false AND created_at < now() - interval '24 hours'`
- **不影响正常用户**：已完成注册的用户 `password_hash IS NOT NULL AND email_verified = true`，不会被清理
- **日志记录**：清理时记录删除数量到 `system_error_logs`（operation='auth_pending_cleanup'），便于监控异常注册量

过期 auth_sessions 清理（与 pending 用户清理放在同一个定时任务中）：
- **清理条件**：`is_revoked = true AND revoked_at < now() - interval '30 days'`（已作废超过 30 天）
  OR `expires_at < now() - interval '30 days'`（过期超过 30 天且未被主动作废）
- **SQL 示例**：`DELETE FROM auth_sessions WHERE (is_revoked = true AND revoked_at < now() - interval '30 days') OR (expires_at < now() - interval '30 days')`
- **理由**：已作废/过期的 session 记录无业务价值，持续累积会影响表大小和索引性能
- **保留 30 天**：便于安全审计（如发现异常登录时回溯设备信息）
- **日志记录**：清理时记录删除数量到 `system_error_logs`（operation='auth_session_cleanup'）
```

### 7.3 账户删除 / 注销

用户可以主动注销账户，需要安全流程和数据处理策略。

**注销流程**：
```
前端：
1. 用户在 /account 页面点击 "删除账户"
2. 弹出确认对话框：勾选 "我理解此操作不可逆" + 点击 "发送验证码"
3. 调用 POST /auth/otp/send { purpose: "delete_account" } → 发送 OTP 到用户邮箱
4. 用户输入 6 位 OTP → 调用 POST /auth/otp/verify { purpose: "delete_account" } → 获取 otp_verified_token
5. 确认删除 → 调用 POST /auth/delete-account { otp_verified_token }

后端 AuthService.delete_account():
1. 验证 otp_verified_token（JWT 签名 + purpose="delete_account" + 未过期）
2. 取消 Stripe 订阅（如果有活跃订阅）
   → 失败则中止整个流程，返回 500（不能在订阅未取消时删除账户）
3. 作废所有 auth_sessions（revoke_reason='account_deleted'）
4. 软删除 profiles 记录（is_deleted=true, deleted_at=now()）
5. 删除 auth_users 记录（CASCADE 自动清除 auth_sessions 残留）
6. 返回 200
7. 异步任务（不阻塞响应）：匿名化用户内容（projects owner_id → 'deleted_user' UUID）
   → 通过后台任务队列处理，避免大量 UPDATE 导致请求超时
```

**数据处理策略**：
```
立即删除（不可逆）：
- auth_users 记录（密码、验证 token 等凭据数据）
- auth_sessions 所有会话（ON DELETE CASCADE）

永久软删除（不清理）：
- profiles 记录（is_deleted=true, deleted_at=now()）
  永久保留，用于数据分析、用户行为洞察、用户召回等运营场景
  30 天内可通过重新注册恢复（restore_account=true）
  30 天后不可恢复，但记录永久保留在数据库中
  ⚠️ 不设定期清理任务，profiles 软删除记录永不硬删除
- 删除时立即生成 email_hash：profiles.email_hash = SHA-256(email)
  用于 GDPR 合规准备（将来需要时可清除 email 原始值，仅保留 hash 用于去重分析）
- 30 天后 PII 部分脱敏（定时任务）：
  - profiles.display_name → 'Deleted User'（原始值不可恢复）
  - profiles.email → 保留原始值（用于用户召回、管理员搜索）
  - profiles.email_hash → 保留（删除时已生成）
  - profiles.user_code → 保留（系统生成编号，非 PII）
  - profiles.tier / credits_* / created_at / deleted_at → 保留（分析用）
  - ⚠️ 如果将来需要 GDPR 全面合规，只需一条 SQL 将已脱敏记录的 email 置 NULL，
    email_hash 仍可用于去重和行为分析

保留不匿名化：
- projects/assets：owner_id 保持原 UUID 关联
  便于恢复账户时重建关联，也便于数据分析追溯用户创作历史
  已购买者继续通过 marketplace_listings 访问资产（不受影响）
- payment_records：保留交易记录（法律要求保留 7 年）
  owner_id 保持关联，便于用户召回时展示历史交易

立即清除：
- Stripe: 调用 Stripe API 取消订阅、删除 customer（或标记不活跃）
- Resend: 移除邮件列表（如有）
```

**新增 API 端点**：
```
POST /auth/delete-account    需要 OTP 验证（otp_verified_token）   Access Token
```

**邮箱复用**：
- 账户删除后，该邮箱可以重新注册（因为 auth_users 已硬删除）
- **profiles 表唯一约束处理**：profiles.email 需使用**部分唯一索引**，排除软删除记录：
  - `CREATE UNIQUE INDEX idx_profiles_email_unique ON profiles(email) WHERE is_deleted = false;`
  - 确保同一邮箱在活跃用户中唯一，但允许软删除记录与新记录并存
  - profiles 软删除记录永久保留，不会被清理（用于数据分析和用户召回）
  - 同一邮箱可能存在多条软删除 profiles 记录（用户多次注册→删除→再注册→再删除），这是正常的
- **已知取舍 — 邮箱枚举风险**：
  - send-otp 响应包含 `has_restorable_account` 字段，攻击者可通过批量调用探测哪些邮箱曾注册过
  - 泄露的信息仅限"该邮箱曾注册且删除过"（非当前活跃账户），信息敏感度较低
  - 有 IP 限流保护（5/hour/IP + 3/hour/email），批量探测成本高
  - 权衡结论：接受此风险，换取更好的用户恢复体验（尽早告知用户有可恢复账户）

- **30 天恢复期内**，注册第一步（`/auth/register/send-otp`）行为：
  1. 后端检测 profiles 中是否存在同 email 的可恢复记录（`is_deleted=true AND deleted_at > now() - interval '30 days'`）
     - 多条软删除记录时取最近的：`ORDER BY deleted_at DESC LIMIT 1`
  2. 响应：`{ success: true, has_restorable_account: true/false }`
     - 无论邮箱是否存在都发送 OTP（防部分枚举：不区分"邮箱不存在"和"邮箱存在但无可恢复账户"）
     - `has_restorable_account=true` 仅当 30 天内有软删除 profiles 记录
  3. 前端收到 `has_restorable_account=true` 后，在 OTP 输入步骤之前展示选择 UI：
     ```
     ┌────────────────────────────────────────┐
     │ We found a previously deleted account  │
     │ associated with this email.            │
     │                                        │
     │ ○ Restore my previous account          │
     │   (recover credits, projects, etc.)    │
     │ ○ Create a new account                 │
     │                                        │
     │ Enter the verification code sent to    │
     │ your email to continue.                │
     │                                        │
     │ [OTP Input: _ _ _ _ _ _]               │
     │                                        │
     │ [Continue]                              │
     └────────────────────────────────────────┘
     ```
  4. 用户选择后进入第二步 verify-otp（验证邮箱归属），通过后获取 register_token
  5. 第三步 complete 携带 `restore_account` 参数：
     - `restore_account=true`：调用 `restore_auth_user_with_profile()` RPC
       → 复用旧 profiles 的 UUID 创建新 auth_users
       → 恢复 profiles（`is_deleted=false, deleted_at=NULL`）
       → projects/assets 的 owner_id 天然匹配（UUID 不变）
       → 重置密码（用户在 complete 步骤设置新密码）
       → 积分保留（credits_monthly 重置为 0，credits_permanent 保留原值）
     - `restore_account=false`（默认）：调用 `create_auth_user_with_profile()` RPC
       → 创建全新 auth_users + profiles（新 UUID）
       → 旧 profiles 保持软删除状态永久保留

- **30 天后**，同一邮箱重新注册时：
  - send-otp 返回 `has_restorable_account=false`（旧 profiles 的 `deleted_at` 已超过 30 天）
  - 正常创建全新 auth_users + profiles（新 UUID）
  - 旧 profiles 永久保留在数据库中（`is_deleted=true`），仅供后台数据分析使用

### 7.4 邮箱规范化

```
问题：User@Example.com 和 user@example.com 是否视为同一用户？
答案：是。必须统一处理。

规则：
1. 注册/登录时统一转为小写：email = email.strip().lower()
2. 数据库层面：
   - auth_users.email 存储小写
   - 添加 CHECK 约束：CHECK (email = LOWER(email))
   - 唯一索引已有：UNIQUE (email)
3. 查询时统一：WHERE email = LOWER($1)

注意：
- RFC 5321 规定邮箱 local-part (@ 前面) 理论上区分大小写
- 但实际上几乎所有邮箱服务商都不区分
- 业界标准做法（Auth.js、Supabase Auth、Firebase）都做小写化
```

### 7.5 垃圾注册防护（OTP 增强）

```
OTP 本身就是强力的垃圾注册防护：
- 必须验证邮箱可达（OTP 发到真实邮箱）
- 一次性邮箱虽然能收 OTP，但有黑名单检测
- 每个邮箱每小时只能发 3 次 OTP

多层防护（由轻到重）：

Layer 1 — 邮箱格式校验（后端 Pydantic 验证）：
- RFC 5322 格式校验
- 拒绝明显无效格式

Layer 2 — 一次性邮箱检测：
- 维护黑名单列表（mailinator.com, tempmail.io, guerrillamail.com 等）
- 开源库：disposable-email-domains（Python: disposable-email-domains）
- 注册时检查 email 域名是否在黑名单中
- 返回通用错误："注册失败，请使用有效邮箱"（不暴露具体原因，防枚举）

Layer 3 — IP 限流（已有，5/hour/IP）

Layer 4 — CAPTCHA（推荐 Phase 2 后添加，非 MVP 必需）：
- 候选方案：Cloudflare Turnstile（免费、隐私友好）
- 触发时机：同一 IP 注册 > 2 次/天时出现
- 前端：<Turnstile> 组件在注册表单底部
- 后端：验证 Turnstile token
- 暂不实施，作为后续增强项
```

### 7.6 JWT 密钥轮换策略

```
场景：AUTH_JWT_SECRET 需要更换（泄露、定期轮换等）

策略：双密钥过渡期（Graceful Rotation）

1. 在环境变量新增 AUTH_JWT_SECRET_OLD（可选）
2. TokenService 签发新 token 用 AUTH_JWT_SECRET（新密钥）
3. TokenService 验证 token 时：
   - 先用 AUTH_JWT_SECRET 验证
   - 失败 → 用 AUTH_JWT_SECRET_OLD 验证（过渡期兼容）
   - 两个都失败 → 401
4. 过渡期 = 1 个 Access Token 生命周期（15 分钟）
   15 分钟后所有旧 token 自然过期
5. 确认无旧 token 后，移除 AUTH_JWT_SECRET_OLD

操作步骤：
1. 设置 AUTH_JWT_SECRET_OLD = 当前密钥
2. 设置 AUTH_JWT_SECRET = 新密钥
3. 重启服务
4. 等待 15 分钟
5. 移除 AUTH_JWT_SECRET_OLD
6. 重启服务

新增环境变量：
AUTH_JWT_SECRET_OLD    # 旧密钥（仅轮换期间配置，平时不设）
```

### 7.7 并发会话限制

```
策略：每用户最多 10 个活跃会话

理由：
- 防止凭据泄露后无限制创建会话
- 10 个足够覆盖正常使用（手机、平板、电脑、公司电脑等）
- 超过上限时自动踢出最旧的会话

实现：
- AuthService.login() 创建新 session 前检查活跃 session 数
- 如果 >= 10：自动 revoke 最旧的 session（last_used_at 最早的）
- 不阻止登录，只清理最旧会话

用户感知：
- /auth/sessions 接口已有，用户可以管理设备
- 被踢出的旧设备下次请求会 401 → 正常登出流程
```

### 7.8 email_verified 校验点

```
OTP 注册模式下：
- 所有完成注册的用户 email_verified = true（注册流程保证）
- require_verified_email 作为防御层保留，但正常流程不会触发

后端校验位置（集中式，非分散到每个 API）：

方案：新增 FastAPI 依赖 require_verified_email()

async def require_verified_email(user = Depends(get_current_user)):
    if not user.email_verified:
        raise EmailNotVerifiedException()
    return user

使用方式：
@router.post("/ai/generate")
async def generate_image(user = Depends(require_verified_email)):
    ...  # 只有已验证邮箱的用户才能执行

需要 require_verified_email 的 API：
- POST /ai/generate（AI 生图）
- POST /ai/generate-page（AI 生 Page）
- POST /ocr/*（OCR 识别）
- POST /projects（创建项目）
- POST /billing/checkout（购买积分/订阅）
- POST /marketplace/purchase（购买素材）

不需要验证的 API（require_member 或 get_current_user 即可）：
- GET /user/me（获取用户信息）
- GET /projects（查看项目列表）
- GET /marketplace/*（浏览市场）
- PUT /user/preferences（更新偏好设置）
```

---

## 八、实施阶段划分

### 总览

| 阶段 | 内容 | 预估工作量 |
|------|------|-----------|
| **Phase 0** | 数据库 Schema：新增 3 张 auth 表，profiles.id 改 UUID + email_hash 字段 + 部分唯一索引，56 个外键同步，RPC 函数重写/更新（含 restore RPC，详见 4.5-4.8），CHECK 约束更新 | 1.5 天 |
| **Phase 1** | 后端 Auth Domain：service/token/password/repository/API 全套 | 4 天 |
| **Phase 2** | 后端集成：修改 dependencies.py + config.py + container.py，删除 Clerk 模块 | 1 天 |
| **Phase 3** | 前端 Auth 抽象层：AuthProvider + useAuth + tokenManager + API Route 代理 | 3 天 |
| **Phase 4** | 前端认证页面：login（单步）+ register（三步 OTP）+ forgot-password（三步 OTP）+ OtpInput 组件 | 2 天 |
| **Phase 5** | 前端迁移：~30 个文件 import 替换 + 特殊文件逻辑调整 | 3 天 |
| **Phase 6** | 测试：后端单元测试 + 集成测试 + 前端测试 | 2 天 |
| **Phase 7** | 清理：移除 @clerk/nextjs、svix 依赖，更新环境变量，构建验证 | 1 天 |
| **总计** | | **~17.5 天** |

**Phase 并行优化说明**：
- Phase 0（Schema SQL 编写）和 Phase 1 的 Step 1.1~1.6（Domain 基础结构、聚合根、Repository 接口、PasswordService、TokenService、OTPService）**可以并行推进**
- 原因：Step 1.1~1.6 是纯 Python 代码定义，不依赖数据库实际执行，只依赖 Schema 设计（表结构、字段名）已确认
- Step 1.7（Repository 实现）开始依赖数据库表实际存在，必须等 Phase 0 完成
- 并行后预估总工期：**~15 天**（节省 ~2.5 天）

```
并行执行时间线:
Day 1-1.5:  Phase 0 (Schema)          ←→ Phase 1 Step 1.1-1.6 (Domain 纯代码)
Day 1.5:    Phase 0 完成，数据库表创建
Day 2-4:    Phase 1 Step 1.7-1.13 (Repository 实现 + AuthService + API + 测试)
Day 5:      Phase 2 (后端集成)
Day 6-8:    Phase 3 (前端 Auth 抽象层)
Day 9-10:   Phase 4 (前端认证页面)
Day 11-13:  Phase 5 (前端迁移)
Day 14:     Phase 6 (测试)
Day 15:     Phase 7 (清理)
```

### Phase 0: 数据库 Schema（1.5 天）

```
前置条件: 无
Git 分支: feat/auth-phase0-schema
仓库: decodables (后端)
```

**Step 0.1: 新增 auth 表到 `01_core_business.sql`**
- 在文件末尾（RPC 函数之前）添加 3 张新表：
  - `auth_users` 表定义 + 部分索引（详见 4.1）
  - `auth_sessions` 表定义 + 索引（详见 4.2）
  - `auth_oauth_accounts` 表定义 + 唯一约束（详见 4.3，预留）
- 为 3 张表添加 RLS 策略（详见 4.9）
- ✅ 验证：SQL 语法检查通过

**Step 0.2: `profiles` 表改造（`01_core_business.sql`）**
- 修改 `profiles` 表定义：`id TEXT PRIMARY KEY` → `id UUID PRIMARY KEY DEFAULT uuid_generate_v4()`
- 新增字段：`email_hash TEXT`（SHA-256 hash，账户删除时写入，用于去重分析）
- 新增部分唯一索引：`CREATE UNIQUE INDEX idx_profiles_email_unique ON profiles(email) WHERE is_deleted = false;`
  （活跃用户邮箱唯一，软删除记录不受约束，详见 4.4）
- 逐一修改该文件内 **32 个外键列**的类型声明（TEXT → UUID）：
  - `projects.owner_id`, `marketplace_listings.created_by`, `marketplace_categories.created_by`
  - `assets.user_id`, `assets.origin_owner_id`, `asset_licenses.seller_id`
  - `asset_moderation_queue.moderated_by`, `user_collections.user_id`
  - `collection_assets.origin_owner_id`, `user_favorite_assets.added_by`
  - `user_favorite_listings.added_by`, `comments.created_by`, `ratings.user_id`
  - `purchases.user_id`, `user_downloads.user_id`, `user_asset_usage.user_id`
  - `asset_views.user_id`, `listing_views.user_id`, `user_search_history.user_id`
  - `content_reports.reporter_id`, `content_reports.reviewed_by`
  - `asset_reviews.reviewer_id`, `subscription_history.user_id`
  - `credits_ledger.user_id`, `credits_ledger.source_user_id`
  - `workspaces.user_id`, `tags.user_id`
  - `team_members.user_id`, `team_members.invited_by`
  - `team_invitations.invited_by`, `team_invitations.accepted_by`
  - `folders.user_id`
- ✅ 验证步骤（精确计数）：
  1. `grep -c "REFERENCES profiles(id)" 01_core_business.sql` → 确认实际外键数量
  2. `grep "REFERENCES profiles(id)" 01_core_business.sql` → 逐行核对列名与上述清单一致
  3. 如果实际数量 ≠ 文档中的 32，更新文档数字和清单（总数 = file1 + file2 + file3）
  4. 确认所有列类型已从 TEXT 改为 UUID

**Step 0.3: 同步 `02_platform_services.sql`**
- 逐一修改 **16 个外键列**类型（TEXT → UUID）：
  - `analytics_events.user_id`, `activity_logs.user_id`
  - `feature_flags.created_by`, `user_feature_states.user_id`
  - `notifications.user_id`, `user_feedback.reporter_id`, `user_feedback.reviewed_by`
  - `changelog_entries.author_id`, `user_onboarding_progress.user_id`
  - `user_daily_logins.user_id`, `theme_users.user_id`
  - `daily_doodle_users.user_id`, `user_daily_doodle_submissions.user_id`
  - `referrals.referrer_id`, `referrals.referee_id`, `coupon_redemptions.user_id`
- 更新 `02_platform_services.sql` 头部注释中对 `clerk_webhook_events` 的引用（该表定义实际在 `03_infrastructure.sql` 中，此文件仅有注释引用）
- ✅ 验证：grep 确认 16 个外键全部完成

**Step 0.4: 同步 `03_infrastructure.sql`**
- 逐一修改 **8 个外键列**类型（TEXT → UUID）：
  - `audit_logs.user_id`, `admin_actions.user_id`
  - `error_logs.user_id`, `error_logs.resolved_by`
  - `ai_usage_logs.user_id`, `task_queue.user_id`, `task_queue.assigned_to`
  - `notification_queue.user_id`
- 删除 `clerk_webhook_events` 表及其相关索引、RLS 策略（该表定义在此文件中，已标记为删除注释，现在正式移除注释残留）
- ✅ 验证：
  1. grep 确认总外键数量正确（file1 + file2 + file3 = 实际总数，文档标注 56 需实施时精确核实）
  2. grep 确认 `clerk_webhook_events` 在所有 SQL 文件中不再有表定义（仅允许注释说明"已删除"）

**Step 0.5: 更新 CHECK 约束**
- `profiles.created_by`：`('webhook','jit','legacy','manual')` → `('register','admin','legacy','oauth')`
- `admin_operations.operation_type`：`webhook_user_create` → `auth_user_register`
- ✅ 验证：CHECK 约束值正确

**Step 0.6: 重写 RPC 函数**
- `create_user_idempotent()` → 重写为 `create_auth_user_with_profile()`（详见 4.7 RPC 1）
  - 输入：p_email, p_password_hash, p_display_name, p_signup_bonus
  - 同一事务内创建 auth_users + profiles（共享 UUID）
- 新增 `restore_auth_user_with_profile()`（详见 4.7 RPC 2）
  - 输入：p_old_profile_id, p_email, p_password_hash, p_display_name
  - 复用旧 profiles UUID 创建 auth_users，恢复 profiles.is_deleted=false
  - 用于 30 天恢复期内用户选择恢复账号
- 更新 `get_user_creation_stats()`：适配新 source 枚举
- 保留 `generate_user_code()`：注册时仍需生成 26 位 user_code
- ✅ 验证：RPC 函数语法正确

**Step 0.7: 验证 + 提交**
- 在 Supabase SQL Editor 执行完整 3 个文件，确认无语法错误
- 确认 `auth_users`、`auth_sessions`、`auth_oauth_accounts` 创建成功
- 确认 `profiles.id` 为 UUID 类型
- 确认 `clerk_webhook_events` 已删除
- `git add + commit + push`

---

### Phase 1: 后端 Auth Domain（4 天）

```
前置条件: Phase 0 完成（auth 表已创建）
Git 分支: feat/auth-phase1-backend-domain
仓库: decodables (后端)
```

**Step 1.1: 创建 Domain 基础结构**
- 新建 `domains/auth/__init__.py`
- 新建 `domains/auth/constants.py`：Token 有效期、锁定阈值、密码规则等常量
- 新建 `domains/auth/value_objects.py`：Password、Email、Token 值对象
- ✅ 验证：`from domains.auth import constants` 不报错

**Step 1.2: 创建聚合根和实体**
- 新建 `domains/auth/aggregates/__init__.py`
- 新建 `domains/auth/aggregates/auth_user.py`：AuthUser 聚合根（id, email, password_hash, email_verified 等）
- 新建 `domains/auth/aggregates/session.py`：Session 实体（id, user_id, family_id, refresh_token_hash 等）
- ✅ 验证：dataclass 实例化正确

**Step 1.3: 定义 Repository 接口**
- 新建 `domains/auth/repository.py`
  - `IAuthUserRepository`：14 个方法签名（详见 5.1）
  - `ISessionRepository`：9 个方法签名（详见 5.1）
- ✅ 验证：ABC 类定义正确，类型注解完整

**Step 1.4: 实现 PasswordService**
- 新建 `domains/auth/password_service.py`
  - argon2id 哈希：`hash_password()`, `verify_password()`
  - 密码强度校验：`validate_strength()`（≥8字符、大小写+数字、不在常见密码列表）
- ✅ 验证：`pytest tests/domains/auth/test_password_service.py` 通过

**Step 1.5: 实现 TokenService**
- 新建 `domains/auth/token_service.py`
  - Access Token：HS256 签发 `create_access_token()`、验证 `verify_access_token()`
  - Refresh Token：`create_refresh_token()`（UUID + SHA-256 哈希）
  - 双密钥轮换：验证时先试 `AUTH_JWT_SECRET`，失败再试 `AUTH_JWT_SECRET_OLD`
  - `validate_secrets_at_startup()`：密钥长度 ≥ 43 字符
- ✅ 验证：`pytest tests/domains/auth/test_token_service.py` 通过（签发/验证/过期/轮换）

**Step 1.6: 实现 OTPService**
- 新建 `domains/auth/otp_service.py`
  - `generate_otp()`：生成 6 位随机数字 → SHA-256 哈希
  - `send_otp_email(email, otp_code, purpose)`：调用 Resend 发送 OTP 邮件
  - `verify_otp(user_id, otp_code, expected_purpose)`：哈希比对 + 过期检查 + 尝试次数检查
  - `create_register_token(email)`：生成临时注册 JWT（15分钟）
  - `create_otp_verified_token(user_id, purpose)`：生成临时验证 JWT（10分钟）
  - 邮件模板：清晰的 6 位验证码，支持 iOS/Android OTP 自动填充
  - 复用现有 Resend 配置（`RESEND_API_KEY`、`SUPPORT_EMAIL_FROM`）
- ✅ 验证：mock Resend 的单元测试通过

**Step 1.7: 实现 Repository（infrastructure 层）**
- 新建 `infrastructure/auth/__init__.py`
- 新建 `infrastructure/auth/auth_user_repository.py`：实现 `IAuthUserRepository`
  - `create()` 调用 RPC `create_auth_user_with_profile()`
  - `restore()` 调用 RPC `restore_auth_user_with_profile()`
  - `find_restorable_by_email(email)` 查询可恢复的软删除 profiles 记录
  - 其余方法通过 Supabase client 操作 `auth_users` 表
- 新建 `infrastructure/auth/session_repository.py`：实现 `ISessionRepository`
  - 操作 `auth_sessions` 表
  - `revoke_family()` 支持并发宽限期（`REFRESH_REUSE_GRACE_PERIOD_S`，默认 1 秒）
- ✅ 验证：集成测试通过（需 Supabase 连接）

**Step 1.8: 实现 RegistrationService**
- 新建 `domains/auth/registration_service.py`（~200 行）
  - `send_otp(email)`：校验邮箱 → 一次性邮箱检测 → 检查可恢复账户（profiles WHERE email=? AND is_deleted=true AND deleted_at > now()-30d）→ 创建/更新 pending auth_user → 异步发 OTP 邮件 → 返回 `{ success, has_restorable_account }`
  - `verify_otp(email, otp_code)`：校验 OTP → 标记 email_verified → 返回临时注册 token（JWT）
  - `complete(register_token, password, display_name, restore_account)`：
    - 校验注册 token → 幂等性检查 → 哈希密码
    - `restore_account=true`：调用 `restore_auth_user_with_profile()` RPC 恢复旧账户
    - `restore_account=false`：调用 `create_auth_user_with_profile()` RPC 创建新账户
    - 创建 session → 返回 tokens
- 一次性邮箱检测：维护黑名单列表（disposable-email-domains）
- ✅ 验证：`pytest tests/domains/auth/test_registration_service.py` 通过（含恢复流程测试）

**Step 1.8b: 实现 SessionService**
- 新建 `domains/auth/session_service.py`（~200 行）
  - `login(email, password)`：查用户 → 检查锁定 → 验证密码 → 记录登录 → 创建 session → 返回 tokens
  - `refresh_token(refresh_token, rotate)`：查 session → 检查过期/作废 → 轮换/不轮换 → 重用检测（并发宽限期 `REFRESH_REUSE_GRACE_PERIOD_S`）→ 返回 tokens
  - `logout(refresh_token)` / `logout_all(user_id)`：作废 session(s)
  - `get_sessions(user_id)` / `revoke_session(session_id)`：多设备管理
- 并发会话限制：≥ 10 个活跃 session 时自动踢出最旧的
- ✅ 验证：`pytest tests/domains/auth/test_session_service.py` 通过

**Step 1.8c: 实现 AccountService**
- 新建 `domains/auth/account_service.py`（~200 行）
  - `send_otp(user_id_or_email, purpose)`：通用 OTP 发送（修改密码/删除账户/忘记密码）→ 统一响应防枚举
  - `verify_otp(user_id_or_email, otp_code, purpose)`：通用 OTP 验证 → 返回 otp_verified_token（JWT）
  - `forgot_password_reset(otp_verified_token, new_password)`：校验 token → 更新密码 → 作废所有 sessions
  - `change_password(otp_verified_token, current_password, new_password)`：校验 token → 验证旧密码 → 更新 → 可选作废其他 sessions
  - `delete_account(otp_verified_token)`：校验 token → 取消 Stripe → 作废 sessions → 写入 email_hash(SHA-256) → 软删 profiles(is_deleted=true) → 硬删 auth_users → 异步匿名化内容
- ✅ 验证：`pytest tests/domains/auth/test_account_service.py` 通过

**Step 1.9: 创建 API 路由**
- 新建 `api/auth/__init__.py`
- 新建 `api/auth/schemas.py`：Pydantic Request/Response 模型（详见 5.3）
- 新建 `api/auth/router.py`：14 个端点（详见 5.3，含注册三步 + 通用 OTP 两个端点）
  - 统一错误响应格式：`{ error, message?, details? }`
  - 响应头：`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- 在 `main.py` 注册 auth router
- ✅ 验证：FastAPI 启动无报错，`/docs` Swagger 文档显示所有端点

**Step 1.10: 实现限流**
- SlowAPI 配置（基于 config.py 现有 `RATE_LIMIT_*`）
- 各端点限流规则（详见 5.3.1）：
  - `/auth/login`：10/min/IP+email
  - `/auth/register`：5/hour/IP
  - `/auth/refresh`：30/min/token
  - `/auth/forgot-password`：3/hour/email
- ✅ 验证：测试限流触发返回 429

**Step 1.11: 新增 `require_verified_email` 依赖**
- 新建 FastAPI 依赖函数（详见 7.8）
- 挂载到需要邮箱验证的端点：AI 生图、OCR、创建项目、购买等
- ✅ 验证：未验证邮箱用户调用受限 API 返回 403

**Step 1.12: 注册到 container.py**
- 新增：`get_registration_service()`, `get_session_service()`, `get_account_service()`, `get_token_service()`, `get_password_service()`, `get_otp_service()`
- 遵循现有 async factory 懒加载模式
- ✅ 验证：依赖注入正确

**Step 1.13: 完整验证 + 提交**
- `pytest tests/domains/auth/` 全部通过
- 手动测试：发送 OTP → 验证 OTP → 完成注册 → 登录 → 刷新 → 登出
- `git add + commit + push`

---

### Phase 2: 后端集成（1 天）

```
前置条件: Phase 1 完成（auth API 可用）
Git 分支: feat/auth-phase2-backend-integration
仓库: decodables (后端)
```

**Step 2.1: 修改 `config.py`**
- 移除：`CLERK_WEBHOOK_SECRET`, `CLERK_PEM_PUBLIC_KEY`, `CLERK_FRONTEND_API`, `CLERK_ALLOWED_ORIGINS`
- 移除：`TEST_JWT_PUBLIC_KEY` 相关逻辑
- 新增：`AUTH_JWT_SECRET`, `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES`, `AUTH_REFRESH_TOKEN_EXPIRE_DAYS` 等
- 新增：`validate_secrets_at_startup()`（密钥 ≥ 43 字符，否则启动失败）
- 更新：`REQUIRED_ENV_VARS` 新增 `AUTH_JWT_SECRET`
- 更新：`RECOMMENDED_ENV_VARS` 移除 Clerk 变量
- ✅ 验证：启动时配置校验通过

**Step 2.2: 修改 `dependencies.py`（核心改造）**
- 替换 Clerk RS256 JWT 验证 → 自签 HS256 验证（调用 `TokenService.verify_access_token()`）
- 移除 JIT 用户创建逻辑（~130 行：重试机制、Sentry 捕获、UserProfile.create_new 等）
- 移除 `user_id.startswith("user_")` 格式校验
- 移除 `_get_allowed_origins()` 函数和 `azp` 验证逻辑
- 移除 `import asyncio` 和 `asyncio.sleep(0.1)` 重试逻辑
- **保持 `get_current_user()` 签名不变**：`authorization: str = Header(None)` → 返回 `UserProfile`
- `optional_user()` / `require_admin()` / `require_member()` / `require_pro()` 等：依赖 `get_current_user()`，自动适配
- ✅ 验证：后端启动无报错，API 调用能正确验证自签 JWT

**Step 2.3: 修改 `container.py`**
- 移除：`get_clerk_webhook_service()`
- 确认 Phase 1.12 的 auth 服务注册已完成
- ✅ 验证：所有服务正确注入

**Step 2.4: 删除 Clerk 模块**
- 删除 `domains/webhooks/clerk_webhook_service.py` 整个文件
- 修改 `api/user/webhooks.py`：移除 Clerk webhook 路由（保留 Stripe webhook）
- ✅ 验证：`grep -r "clerk" --include="*.py"` 后端代码（除文档外）返回 0

**Step 2.5: 更新 UserProfile 实体**
- `domains/identity/aggregates/user_profile.py`：
  - `user_id: str` 保持不变（Python 中 UUID 以 str 传递）
  - 移除 Clerk 相关注释（"Clerk ID"、"from Clerk"、"Clerk username"）
  - 评估是否移除 `username` / `first_name` / `last_name`（Clerk 字段），改为仅保留 `display_name`
  - 更新 `create_new()` 工厂方法的参数和注释
- ✅ 验证：现有测试通过

**Step 2.6: 更新 `requirements.txt`**
- 移除：`svix`
- 新增：`argon2-cffi`（如未在 Phase 1 添加）
- ✅ 验证：`pip install -r requirements.txt` 成功

**Step 2.7: 更新环境变量**
- `.env`（本地）：移除 4 个 `CLERK_*` 变量，新增 `AUTH_*` 变量
- Railway（线上）：同步更新环境变量
- ✅ 验证：后端正常启动，无 Clerk 相关告警

**Step 2.8: 完整验证 + 提交**
- 后端启动无报错
- `get_current_user()` 正确验证自签 HS256 JWT
- 现有 API（非 auth 相关）正常工作
- `pytest` 全套通过
- `git add + commit + push`

---

### Phase 3: 前端 Auth 抽象层（3 天）

```
前置条件: Phase 2 完成（后端 auth API 可用）
Git 分支: feat/auth-phase3-frontend-auth-layer
仓库: decodables-fe (前端)
```

**Step 3.1: 创建 auth 目录结构和类型定义**
- 新建 `lib/auth/index.ts`：统一导出
- 新建 `lib/auth/types.ts`：`UseAuthReturn`, `AuthUser`, `UseUserReturn` 接口定义（详见 6.1）
- ✅ 验证：TypeScript 编译通过

**Step 3.2: 实现 BFF 代理**
- 新建 `app/api/auth/[...action]/route.ts`（~80 行，详见 6.2 伪代码）
  - `POST` handler：转发所有 `/api/auth/*` 到后端 `/auth/*`
  - refresh/logout 时从 cookie 注入 `refresh_token`
  - 登录/注册/刷新成功时设置 `httpOnly cookie`
  - 登出/注销时清除 cookie
  - cookie 属性：`httpOnly: true, secure: true, sameSite: 'lax', path: '/api/auth'`
- ✅ 验证：`curl -X POST localhost:3000/api/auth/login -d '{"email":"...","password":"..."}' -v` 返回 token + Set-Cookie

**Step 3.3: 实现 authStore.ts（Zustand）**
- 新建 `lib/auth/authStore.ts`
  - 状态：`accessToken`, `isSignedIn`, `isLoaded`
  - 独立于现有 `useUserStore`（业务数据）
  - 非 persist（纯内存，刷新后通过 refresh 恢复）
- ✅ 验证：store 状态正确读写

**Step 3.4: 实现 tokenManager.ts**
- 新建 `lib/auth/tokenManager.ts`
  - `getValidToken()`：返回有效 Access Token，过期时自动 refresh
  - `refreshPromise` 去重：多个请求同时触发 refresh 时只发一次
  - 主动刷新：Access Token 到期前 60 秒自动触发
  - 被动刷新：API 返回 401 时触发
  - `SessionExpiredError` 处理链（详见 6.2.1）
- ✅ 验证：单元测试通过

**Step 3.5: 实现跨标签同步**
- 在 `tokenManager.ts` 中集成 BroadcastChannel（详见 6.2.1）
  - 消息类型：`token_refreshed` / `user_logged_out` / `user_logged_in`
  - `CROSS_TAB_REFRESH_DELAY_MS = 300ms`：refresh 前等待广播，避免多标签竞态
  - localStorage fallback：`typeof BroadcastChannel === 'undefined'` 时使用 storage 事件
- ✅ 验证：打开两个标签页，一个登出后另一个同步跳转

**Step 3.6: 实现 authApi.ts**
- 新建 `lib/auth/authApi.ts`
  - 封装所有 `/api/auth/*` 调用：`login()`, `register()`, `refresh()`, `logout()` 等
  - 类型安全的请求/响应
- ✅ 验证：TypeScript 类型检查通过

**Step 3.7: 实现 AuthProvider.tsx**
- 新建 `lib/auth/AuthProvider.tsx`
  - 初始化流程（详见 6.1）：
    1. 检查内存中 Access Token
    2. 无 → 调用 `/api/auth/refresh`
    3. 有 → 调用 `/user/me` 获取用户数据 → 写入 Zustand
    4. `/user/me` 失败 → JWT payload 中的 tier/role 作为 fallback
    5. 标记 `isLoaded = true`
  - 替代 Clerk Fallback 机制（不再依赖 clerkUser.publicMetadata）
- ✅ 验证：Provider 能正确初始化，`isLoaded` 状态正确

**Step 3.8: 实现 useAuth.ts + useUser.ts**
- 新建 `lib/auth/useAuth.ts`：接口与 Clerk `useAuth()` 一致（详见 6.1）
- 新建 `lib/auth/useUser.ts`：接口与 Clerk `useUser()` 一致（详见 6.1）
- ✅ 验证：hooks 返回正确数据

**Step 3.9: 实现 server.ts（SSR Token 工具）**
- 新建 `lib/auth/server.ts`
  - `getServerAccessToken()`：从 cookie 获取 refresh_token → 调用后端 `/auth/refresh`（`rotate=false`）
  - 用 React `cache()` 包装：同一 SSR 请求内只调用一次
- ✅ 验证：Server Component 能获取 token

**Step 3.10: 更新 `lib/auth/index.ts` 导出**
- 统一导出所有 hooks、Provider、types、server 工具
- ✅ 验证：`import { useAuth, useUser, AuthProvider } from '@/lib/auth'` 正确

**Step 3.11: 完整验证 + 提交**
- AuthProvider 能初始化
- `useAuth()` 能获取 token
- BFF 代理正常工作
- `npm run build` 通过（此时 Clerk 引用未替换，两套并存）
- `git add + commit + push`

⚠️ **两套并存期间的注意事项**（Phase 3~4，Clerk 和自建 Auth 共存）：
- AuthProvider **不挂载到 `layout.tsx`**：此阶段 `layout.tsx` 仍使用 `<ClerkProvider>`，AuthProvider 仅用于独立测试页面验证（如创建 `/test-auth/page.tsx` 临时页面）
- 避免运行时冲突：两个 Provider 同时挂载可能导致 cookie 竞争（Clerk 有自己的 session cookie）、双重 auth 状态、SSR hydration 不匹配等问题
- 测试 BFF 代理时使用 curl/Postman 直接调用 `/api/auth/*`，不依赖前端 Provider
- Phase 5 Step 5.1 才正式将 `<ClerkProvider>` 替换为 `<AuthProvider>`，切换点明确且原子化
- 临时测试页面 `/test-auth/page.tsx` 在 Phase 7 清理时删除

---

### Phase 4: 前端认证页面（2 天）

```
前置条件: Phase 3 完成（Auth 抽象层可用）
Git 分支: feat/auth-phase4-auth-pages
仓库: decodables-fe (前端)
```

**Step 4.1: 创建 (auth) 路由组布局**
- 新建 `app/(auth)/layout.tsx`
  - 居中卡片布局：`max-w-md mx-auto`，白色卡片 + 阴影
  - 顶部：品牌 Logo（链接到首页）
  - 底部：返回首页 / 帮助链接
  - 背景：与 Design System 一致
- ✅ 验证：布局正确渲染

**Step 4.2: 实现 OTP 输入组件**
- 新建 `components/auth/OtpInput.tsx`
  - 6 位 OTP 输入框（每位一个 input）
  - 自动聚焦下一个框、退格回到上一个框
  - 支持粘贴完整 6 位验证码
  - 支持 `autocomplete="one-time-code"`（iOS/Android OTP 自动填充）
  - 失败时清空并聚焦第一个框
- ✅ 验证：OTP 输入交互正确

**Step 4.3: 实现 `login/page.tsx`**
- 新建 `app/(auth)/login/page.tsx`
  - 字段：Email + Password
  - 按钮："Sign In"（loading 状态）
  - 链接："Forgot password?" → `/forgot-password`
  - 链接："Don't have an account? Sign up" → `/register`
  - 错误处理：401 → "Invalid email or password" / 403 → "Account locked, try again in X minutes"
  - `redirect` 参数：从 `searchParams` 读取，安全校验（以 `/` 开头，不含 `//`）
  - 登录成功 → 跳转 redirect 或默认 `/dashboard`
- ✅ 验证：能登录 + 正确跳转

**Step 4.4: 实现 `register/page.tsx`（三步 + 可选恢复流程）**
- 新建 `app/(auth)/register/page.tsx`
  - Step 1: Email 输入 → 调用 `/auth/register/send-otp`
    - 响应 `has_restorable_account=true` → 进入 Step 1b
    - 响应 `has_restorable_account=false` → 进入 Step 2
  - Step 1b: 账户恢复选择（仅当 has_restorable_account=true）
    - 单选："Restore my previous account" / "Create a brand new account"
    - OTP 输入（复用 OtpInput）→ 调用 `/auth/register/verify-otp`
    - 保存 `restore_account` 选择传入 Step 3
  - Step 2: OTP 输入（使用 OtpInput 组件）→ 调用 `/auth/register/verify-otp` → 获取 register_token
    - 60 秒倒计时重发功能
    - "Use a different email" 返回 Step 1
  - Step 3: Display Name + Password + Confirm Password → 调用 `/auth/register/complete`（携带 restore_account）
    - 密码强度指示器
    - 按钮文案动态切换："Create Account" / "Restore Account"
    - 注册/恢复成功 → 自动登录 → 跳转 `/dashboard`
  - 链接："Already have an account? Sign in" → `/login`
- ✅ 验证：完整注册流程 + 恢复流程

**Step 4.5: 实现 `forgot-password/page.tsx`（三步流程）**
- 新建 `app/(auth)/forgot-password/page.tsx`
  - Step 1: Email 输入 → 调用 `/auth/otp/send { purpose: "forgot_password" }`
    - 提交后始终进入 Step 2（防枚举）
  - Step 2: OTP 输入 → 调用 `/auth/otp/verify { purpose: "forgot_password" }` → 获取 otp_verified_token
    - 60 秒倒计时重发功能
  - Step 3: New Password + Confirm Password → 调用 `/auth/forgot-password/reset`
    - 成功 → "Password reset successfully" + 自动跳转 `/login`
- ✅ 验证：完整密码重置流程

**Step 4.6: 实现 UserMenu 组件（替换 Clerk UserButton）**
- 新建 `components/common/UserMenu.tsx`（极简 4 项版本）
  - 头像（Gravatar + 首字母默认头像）+ 下拉菜单
  - 菜单项：用户信息区 / Account / Transactions / Buy Credits / Sign Out
  - Gravatar URL: `https://www.gravatar.com/avatar/${md5(email.trim().toLowerCase())}?d=404&s=80`（d=404 + 本地首字母 fallback）
- ✅ 验证：下拉菜单正常显示，4 个菜单项可点击

**Step 4.7: 实现 Account 页面（统一的账户管理页面）**
- 新建 `app/account/page.tsx`（响应式，PC/Mobile 共用路由）
- 新建 `app/account/_components/`：
  - `AccountSidebar.tsx`：PC 侧边栏导航（Profile/Security/Credits/Danger Zone）
  - `ProfileSection.tsx`：头像 + 显示名称 + 邮箱 + 编辑 Display Name
  - `SecuritySection.tsx`：修改密码（OTP 三步，复用 OtpInput）+ 设备管理
  - `CreditsSection.tsx`：复用 CreditsCard + SubscriptionCard
  - `DangerZoneSection.tsx`：删除账户（OTP 确认，ResponsiveModal）
- PC 布局（lg:）：左侧 sidebar 200px + 右侧 content（scroll spy 或 tab 切换）
- Mobile 布局（< lg）：沿用当前 iOS Settings 风格（ProfileHeader → Cards → QuickActions → SignOut）
  - 复用现有 components/profile/ 组件（ProfileHeader, UserIdCard, CreditsCard, SubscriptionCard, QuickActionsList, SignOutButton）
  - Quick Actions 中 "Account Settings" 打开包含密码修改 + 设备管理的 Bottom Sheet
- 更新 BottomNavbar：`{ id: 'account', label: 'Account', href: '/account', icon: User }`
- 删除旧 `app/profile/` 目录（功能已迁移到 /account）
- ✅ 验证：PC 和 Mobile 布局均正常，修改密码、设备管理、删除账户流程完整可用

**Step 4.8: 完整验证 + 提交**
- 手动测试完整流程：注册（邮箱 → OTP → 密码）→ 登录 → 登出
- 手动测试密码重置：忘记密码（邮箱 → OTP → 新密码）→ 登录
- 手动测试修改密码：OTP → 旧密码 + 新密码 → 成功
- 手动测试删除账户：OTP → 确认 → 账户删除
- 手动测试设备管理：查看设备列表 → 踢出设备
- OTP 自动填充测试（iOS/Android）
- `npm run build` 通过
- `git add + commit + push`

---

### Phase 5: 前端迁移（3 天）

```
前置条件: Phase 4 完成（认证页面可用）
Git 分支: feat/auth-phase5-frontend-migration
仓库: decodables-fe (前端)
```

**Step 5.1: 替换 `layout.tsx`**
- `<ClerkProvider>` → `<AuthProvider>`
- 移除 `@clerk/nextjs` import
- ✅ 验证：应用正常渲染

**Step 5.2: 替换 `middleware.ts`**
- `clerkMiddleware()` → 自定义路由保护（~40 行，详见 6.6）
- 路由分类：
  - PUBLIC_ROUTES：`/`, `/pricing`, `/marketplace/*`, `/articles/*`, `/api/*` 等
  - AUTH_ROUTES：`/login`, `/register`, `/forgot-password`
  - 其余为 PROTECTED（未登录 → `/login?redirect=`，已登录访问 AUTH → `/dashboard`）
- ✅ 验证：路由保护正确

**Step 5.3: 重写 `GlobalProviders.tsx`（最复杂）**
- 移除：`useAuth()` / `useUser()` from `@clerk/nextjs`
- 移除：Clerk CDN 超时 fallback（`useClerkWithTimeout`、`isEffectivelyLoaded`、`timedOut`）
- 移除：`clerkUser.publicMetadata.tier` fallback
- 保留：`fetchUserData()`（调用 `/user/me` → Zustand）
- 保留：`BroadcastChannel` 跨标签同步（改为新消息格式）
- 重构后从 ~389 行精简到 ~100 行（大部分逻辑已转移到 AuthProvider）
- ✅ 验证：Provider 正常工作

**Step 5.4: 重写 `Navbar.tsx`**
- 替换 Clerk UI 组件：
  - `<UserButton>` → `<UserMenu>`（自定义头像下拉）
  - `<SignedIn>` / `<SignedOut>` → `{isSignedIn && ...}` 条件渲染
  - `<SignInButton>` → `<Link href="/login">`
  - `<ClerkLoading>` → `{!isLoaded && <Skeleton>}`
  - `<ClerkLoaded>` → `{isLoaded && ...}`
- 移除：`ClerkBillingPage`、`ClerkTransactionHistory` import
- ✅ 验证：导航栏正常显示所有状态

**Step 5.5: 重写 `services/api.ts`**
- 移除：`getToken` 回调（当前从 Clerk `useAuth().getToken` 传入）
- 改为：从 `tokenManager.getValidToken()` 获取 token
- 401 重试：改为调用 `tokenManager.doRefresh()`
- 保留：`USE_PROXY` 模式兼容
- ✅ 验证：API 调用正常

**Step 5.6: 迁移 ~30 个 import-only 文件（逐文件改 import 路径）**

按类别分批，每批完成后运行 `npm run build` 验证：

批次 a — hooks/（5 个）：
- `hooks/useCredits.ts`
- `app/create/_hooks/ai/useAIGeneration.ts`
- `app/create/_hooks/ai/useAIPageGeneration.ts`
- `app/create/_hooks/editor/useEditorExport.ts`
- `app/marketplace/_hooks/usePurchase.ts`
- 改动：`import { useAuth } from "@clerk/nextjs"` → `import { useAuth } from "@/lib/auth"`

批次 b — pages/（8 个）：
- `app/admin/page.tsx`, `app/marketplace/page.tsx`, `app/notifications/page.tsx`, `app/contact-us/page.tsx`
- `app/_components/landing/CTAButton.tsx`, `LandingPageClient.tsx`, `pricing/CreditsTierCard.tsx`, `hero/PromptInput.tsx`

批次 c — modals/（6 个）：
- `components/OutOfCreditsModal.tsx`, `UpgradeModal.tsx`, `CreateProjectModal.tsx`
- `app/dashboard/_components/modals/PublishAssetDialog.tsx`
- `app/create/_components/scan/SmartScanDialog.tsx`
- `components/common/FeedbackDialog.tsx`

批次 d — common/（4 个）：
- `components/common/BottomNavbar.tsx`, `FloatingCTA.tsx`, `PlanButton.tsx`
- `components/common/support/ContactForm.tsx`, `AIChat.tsx`

批次 e — 特殊文件（6 个，需要额外改逻辑）：
- `components/common/MobileMenu.tsx`：`useUser()` + `useClerk()` → `useAuth()` + `useUser()` from `@/lib/auth`
- `app/account/page.tsx`（原 `app/profile/page.tsx`，重命名+重构）：`useUser()` + `useAuth()` + `useClerk()` → 新 hooks，移除 desktop redirect，新增 PC sidebar 布局
- `app/transaction-history/page.tsx`：`useAuth()` + `<SignIn>` → `useAuth()` + 跳转 `/login`
- `app/dashboard/_components/DashboardContent.tsx`：`useUser()` → `useUser()` from `@/lib/auth`
- `app/dashboard/_components/DashboardAuthGate.tsx`：`<SignIn>` → `redirect('/login')`
- `app/create/page.tsx`：`<SignIn>` → `redirect('/login')`
- `app/_components/landing/pricing/SubscriptionPlans.tsx`：`useClerkWithTimeout` → `useAuth()` from `@/lib/auth`

- ✅ 验证：每批完成后 `npm run build` 通过

**Step 5.7: 删除 Clerk 专用文件**
- 删除 `hooks/useClerkWithTimeout.ts`
- 删除 `components/common/ClerkBillingPage.tsx`（如独立存在）
- 删除 `components/common/ClerkTransactionHistory.tsx`（如独立存在）
- ✅ 验证：无残留引用

**Step 5.8: 更新环境变量**
- `.env.local`：移除 `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`、`CLERK_SECRET_KEY`
- Vercel：同步更新
- ✅ 验证：启动无 Clerk 相关警告

**Step 5.9: 完整验证 + 提交**
- `npm run build` 零错误
- 手动测试全流程（注册三步 → 自动登录 → 各页面 → 登出 → 忘记密码 OTP 流程）
- `git add + commit + push`

---

### Phase 6: 测试（2 天）

```
前置条件: Phase 5 完成（全部迁移完成）
Git 分支: feat/auth-phase6-tests
仓库: decodables + decodables-fe
```

**Step 6.1: 后端单元测试**
- `tests/domains/auth/test_password_service.py`：hash/verify/strength 校验
- `tests/domains/auth/test_token_service.py`：签发/验证/过期/轮换/密钥校验
- `tests/domains/auth/test_otp_service.py`：OTP 生成/验证/过期/尝试次数限制/临时 Token 签发
- `tests/domains/auth/test_auth_service.py`：三步注册/登录/刷新/登出/锁定/并发会话/修改密码/忘记密码/删除账户
- ✅ 验证：`pytest tests/domains/auth/` 全部通过

**Step 6.2: 后端集成测试**
- `tests/integration/auth/test_auth_api.py`：三步注册 → 登录 → 刷新 → 登出 API 调用
- `tests/integration/auth/test_otp_flow.py`：OTP 发送 → 验证 → 操作 完整流程
- `tests/integration/auth/test_password_reset.py`：忘记密码 OTP 流程
- `tests/integration/auth/test_session_management.py`：多设备管理、踢出
- JWT 测试策略：用 `AUTH_JWT_SECRET` 通过 `TokenService` 签发 test token
- ✅ 验证：`pytest tests/integration/auth/` 全部通过

**Step 6.3: 更新现有后端测试**
- `tests/conftest.py`：Clerk test setup → 自建 auth setup
- `tests/integration/staging/conftest.py`：Clerk test token → 自签 HS256 token
- `tests/integration/staging/get_test_token.py`：Clerk token 生成 → 自签 token 生成
- 删除 `tests/integration/staging/webhooks/test_webhooks.py`（Clerk webhook 测试）
- 更新 `tests/api/user/test_webhooks.py`（移除 Clerk 部分）
- ✅ 验证：`pytest` 全套通过

**Step 6.4: 前端测试更新**
- `jest.setup.js`：移除 `@clerk/nextjs` mock，添加 `@/lib/auth` mock
- `__tests__/components/Navbar.test.jsx`：更新 auth mock
- `__tests__/components/BottomNavbar.test.tsx`：更新 auth mock
- `app/create/__tests__/hooks/useProjectTitle.test.ts`：更新 auth mock
- ✅ 验证：`npm run test` 全部通过

**Step 6.5: 完整验证 + 提交**
- 后端 `pytest` 全部通过
- 前端 `jest` 全部通过
- `git add + commit + push`（两个仓库）

---

### Phase 7: 清理与最终验证（1 天）

```
前置条件: Phase 6 完成（测试全部通过）
Git 分支: feat/auth-phase7-cleanup（或直接在 develop 上）
仓库: decodables + decodables-fe
```

**Step 7.1: 移除前端 Clerk 依赖**
- `package.json`：移除 `@clerk/nextjs`
- 运行 `npm install`（更新 lock 文件）
- ✅ 验证：`npm run build` 通过

**Step 7.2: 移除后端 Clerk 依赖**
- `requirements.txt`：确认 `svix` 已移除
- ✅ 验证：`pip install -r requirements.txt` 无 Clerk 相关包

**Step 7.3: 更新 Vercel 环境变量**
- 移除所有 `CLERK_*` 变量
- 新增 `AUTH_*` 变量（如未在之前 Phase 添加）
- ✅ 验证：Vercel 部署成功

**Step 7.4: 更新 Railway 环境变量**
- 移除所有 `CLERK_*` 变量
- 确认 `AUTH_*` 变量已配置
- ✅ 验证：Railway 部署成功

**Step 7.5: 更新文档**
- 前端文档：
  - `docs/main/frontend-development-guide.md`：更新 auth 相关章节
  - `docs/main/integration-testing-guide.md`：更新测试 mock 说明
- 后端文档：
  - `docs/main/api-reference.md`：新增 auth API 文档
  - `docs/main/backend-business-logic.md`：更新认证流程说明
  - `docs/main/backend-architecture.md`：更新架构图
  - `docs/main/database-guide.md`：新增 auth 表说明
- 临时文档：
  - `docs/tmp/20260131-account-system-audit-report.md`：标记为历史归档
  - `docs/tmp/20260131-account-system-fix-plan.md`：标记为历史归档

**Step 7.6: 零 Clerk 残留验证**
- `grep -r "clerk" --include="*.ts" --include="*.tsx" --include="*.py"` → 0 结果（文档除外）
- `grep -r "@clerk" --include="*.json"` → 0 结果
- ✅ 验证：代码中无任何 Clerk 残留

**Step 7.7: 端到端验证**
- 执行 Section 十的完整 E2E 流程：
  1. 注册新用户 → 输入邮箱 → 收到 OTP 邮件
  2. 输入 OTP → 验证通过 → 设密码+昵称 → 完成注册 → 自动登录
  3. 访问 /dashboard → 正常加载，API 调用带 Bearer token
  4. 15 分钟后 → Access Token 过期 → 自动 refresh → 无感刷新
  5. 访问 /create → 编辑器正常加载
  6. 多标签页 → 一个标签登出 → 其他标签同步登出
  7. 忘记密码 → 输入邮箱 → 收到 OTP → 验证 → 设新密码 → 所有设备登出
  8. 修改密码 → 发送 OTP → 验证 → 输入旧密码+新密码 → 成功
  9. 删除账户 → 发送 OTP → 验证 → 确认删除 → 账户注销
  10. 查看设备管理 → 列出所有活跃 session → 踢出指定设备
  11. `npm run build` → 零错误零警告
- 后端 `pytest` 全部通过
- ✅ 验证：所有检查通过

**Step 7.8: 最终提交 + 合并**
- `git add + commit + push`（两个仓库）
- 合并各 Phase 分支到 `develop`

---

## 九、环境变量变更

### 移除
```
CLERK_WEBHOOK_SECRET
CLERK_PEM_PUBLIC_KEY
CLERK_FRONTEND_API
CLERK_ALLOWED_ORIGINS
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
CLERK_SECRET_KEY
```

### 新增
```
AUTH_JWT_SECRET              # 256-bit 随机密钥（必须，≥43 字符 base64 编码）
                             # 生成命令: python -c "import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
                             # 或: openssl rand -base64 32
AUTH_ACCESS_TOKEN_EXPIRE_MIN  # Access Token 有效期，默认 15
AUTH_REFRESH_TOKEN_EXPIRE_DAYS # Refresh Token 有效期，默认 7
AUTH_LOCKOUT_ATTEMPTS         # 锁定前最大失败次数，默认 5
AUTH_LOCKOUT_DURATION_MIN     # 锁定时长（分钟），默认 30
AUTH_ARGON2_MEMORY_KB         # argon2id 内存参数（KB），默认 65536（可选，低内存实例调小）
AUTH_REFRESH_GRACE_PERIOD_S   # Refresh Token 并发宽限期（秒），默认 1（可选）
AUTH_JWT_SECRET_OLD           # 旧 JWT 密钥（仅密钥轮换期间配置，平时不设）（可选）
RESEND_API_KEY               # Resend 邮件服务（已有，确认保留）
RESEND_FROM_EMAIL            # 发件人地址（已有 SUPPORT_EMAIL_FROM，复用或新增专用变量）
```

---

## 十、验证方案

### 每个 Phase 完成后的验证

| Phase | 验证方式 |
|-------|---------|
| Phase 0 (Schema) | 在 Supabase 执行 SQL，确认 3 张 auth 表创建成功（含 OTP 字段），profiles.id 为 UUID |
| Phase 1 (后端 Auth) | `pytest tests/domains/auth/` 全部通过，手动测试 OTP 注册三步流程 + 登录/刷新 API |
| Phase 2 (后端集成) | 后端启动无报错，`get_current_user()` 能正确验证自签 JWT |
| Phase 3 (前端抽象层) | AuthProvider 能初始化，useAuth() 能获取 token，API 调用成功 |
| Phase 4 (认证页面) | 手动测试：注册（邮箱→OTP→密码）→ 自动登录→dashboard→登出→ 忘记密码（邮箱→OTP→新密码）→ 删除账户→用同邮箱注册→选择恢复账户→验证数据恢复 |
| Phase 5 (前端迁移) | `npm run build` 零错误，所有页面功能正常 |
| Phase 6 (测试) | `pytest` 后端全部通过，前端 jest 全部通过。测试 JWT 策略：直接用 `AUTH_JWT_SECRET` 通过 `TokenService` 签发 HS256 test token |
| Phase 7 (清理) | `grep -r "clerk" --include="*.ts" --include="*.tsx" --include="*.py"` 返回 0 结果（文档除外） |

### 端到端验证流程

```
1. 注册新用户 → 输入邮箱 → 收到 OTP 邮件（6 位验证码）
2. 输入 OTP → 验证通过 → 设密码+昵称 → 完成注册 → 自动登录
3. 访问 /dashboard → 正常加载，API 调用带 Bearer token
4. 15 分钟后 → Access Token 过期 → 自动 refresh → 无感刷新
5. 访问 /create → 编辑器正常加载
6. 多标签页 → 一个标签登出 → 其他标签同步登出
7. 忘记密码 → 输入邮箱 → 收到 OTP → 验证 → 设新密码 → 所有设备登出
8. 修改密码 → 发送 OTP → 验证 → 输入旧密码+新密码 → 成功
9. 删除账户 → 发送 OTP → 验证 → 确认删除 → 账户注销
10. 查看设备管理 → 列出所有活跃 session → 踢出指定设备
11. npm run build → 零错误零警告
```

---

## 十一、回滚策略

- 项目未上线，每个 Phase 独立 git 分支
- Phase 0（Schema 变更）是不可逆点，但因无真实用户数据，可从 git 恢复
- Auth 抽象层设计确保未来切换认证方案只需修改 `lib/auth/` 内部实现

---

## 十二、关键设计原则

1. **重构式替换，不做补丁**: 完全移除 Clerk，不保留任何兼容层或 Clerk 代码残留
2. **auth_users 与 profiles 分离**: 认证凭据和业务数据职责分离，符合 DDD
3. **抽象层设计**: `lib/auth/` 封装所有认证逻辑，未来换方案只改内部实现
4. **接口兼容**: 新 `useAuth()` 暴露与 Clerk 相同的 API，最小化下游改动
5. **安全优先**: argon2id + Refresh Token 轮换 + 重用检测 + 防枚举
6. **零 Clerk 残留**: 最终通过 grep 验证，代码中不存在任何 Clerk 引用（文档除外）

---

## 附录：决策评估过程记录

以下保留完整的利弊分析过程，供后续参考。

### Token 存储：三方案对比

| | 方案 A (同域+Cookie) | 方案 B (Next.js 代理) | 方案 C (localStorage) |
|---|:---:|:---:|:---:|
| 安全性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| 实现简单度 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 性能 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 多环境兼容 | ❌ 不兼容 localhost/Preview | ✅ 全部兼容 | ✅ 全部兼容 |
| 域名变更影响 | 需重新配置 | 无影响 | 无影响 |
| 支付系统适用 | ✅ | ✅ | ❌ |

### JWT 算法：HS256 vs RS256

| | HS256 | RS256 |
|---|:---:|:---:|
| 性能（签名） | ~0.01ms | ~1ms |
| 性能（验证） | ~0.01ms | ~0.1ms |
| 配置复杂度 | 1 个 secret | 1 对密钥（私钥+公钥） |
| 单后端适用 | ✅ 最优 | ✅ 可以但过度 |
| 微服务适用 | ⚠️ 需分发 secret | ✅ 最优 |
| 当前架构需要 | ✅ | 不需要 |

### 密码哈希：三方案对比

| | argon2id | bcrypt | scrypt |
|---|:---:|:---:|:---:|
| OWASP 推荐级别 | **首选** | 可接受 | 可接受 |
| 抗 GPU 攻击 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 生态成熟度 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Python 库 | argon2-cffi | bcrypt | hashlib (内置) |
| 新项目推荐 | ✅ 首选 | ✅ 备选 | 不推荐 |
