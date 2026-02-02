# 自建认证系统 - 完整技术方案

> **状态**: ✅ 技术方案已确认（不涉及代码实施）
> **目标**: 完全移除 Clerk 依赖，自建 Email+Password 认证系统，架构预留 OAuth 扩展能力
> **确认日期**: 2026-02-02

---

## 一、已确认决策汇总

| 决策项 | 选择 | 理由 | 状态 |
|--------|------|------|------|
| 登录方式 | 邮箱+密码（架构预留 OAuth） | 用户需求，先核心后扩展 | ✅ 已确认 |
| 用户 ID | UUID v4 | 业界标准，无第三方依赖 | ✅ 已确认 |
| 邮件服务 | Resend | 现代 API，开发体验好 | ✅ 已确认 |
| 数据迁移 | 全新开始 | 项目未上线，无真实用户 | ✅ 已确认 |
| 表结构 | auth_users 与 profiles 分表 | 认证凭据与业务数据职责分离，符合 DDD | ✅ 已确认 |
| 注册流程 | 必须先验证邮箱 | 防止垃圾注册，确保邮箱可达 | ✅ 已确认 |
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
参数: memory=65536KB, iterations=3, parallelism=4
输出: $argon2id$v=19$m=65536,t=3,p=4$salt$hash
Python库: argon2-cffi
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
| `components/common/MobileMenu.tsx` | Clerk auth 状态 | → `useAuth()` from `@/lib/auth` |
| `components/common/FloatingCTA.tsx` | Clerk auth 状态 | → `useAuth()` from `@/lib/auth` |
| `components/common/PlanButton.tsx` | Clerk auth 状态 | → `useAuth()` from `@/lib/auth` |
| `app/dashboard/_components/DashboardAuthGate.tsx` | `<SignIn>` 内嵌登录 | → 跳转到 `/login` |
| `app/create/page.tsx` | `<SignIn>` 内嵌登录 | → 跳转到 `/login` |
| `app/profile/page.tsx` | `<SignIn>` 内嵌 + `openUserProfile()` | → 跳转到 `/login` + 自定义设置页 |
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
| `requirements.txt` | 移除 `svix`，新增 `argon2-cffi`、`resend` |

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
| 前端 - 需重写逻辑 | ~8 个 |
| 前端 - 需改 import | ~30 个 |
| 前端 - 需删除 | ~3 个 |
| 前端 - 测试更新 | ~4 个 |
| 前端 - 文档更新 | ~4 个 |
| 后端 - 需重写 | ~3 个 |
| 后端 - 需删除 | ~2 个 |
| 后端 - Schema 修改 | 3 个（涉及 56 个外键引用） |
| 后端 - 测试更新 | ~6 个 |
| 后端 - 文档更新 | ~5 个 |
| **总计** | **~68 个文件** |

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
├── password_hash               TEXT NOT NULL (argon2id)
├── email_verified              BOOLEAN DEFAULT FALSE
├── email_verified_at           TIMESTAMPTZ
├── email_verification_token    TEXT (部分索引)
├── email_verification_expires_at TIMESTAMPTZ
├── password_reset_token        TEXT (部分索引)
├── password_reset_expires_at   TIMESTAMPTZ
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
- `auth_users.id` 与 `profiles.id` 使用**同一个 UUID**（注册时同时创建）
- 认证数据（密码、验证token）与业务数据（tier、credits）分离
- 部分索引：仅对 `token IS NOT NULL` 的行建索引
- CHECK 约束：`CHECK (email = LOWER(email))`（邮箱统一小写，详见 7.4）
- **验证 Token 安全存储**：`email_verification_token` 和 `password_reset_token` 存储的是 **SHA-256 哈希值**，不存明文。URL 发给用户的是明文 token，后端校验时 `SHA256(url_token) == db_stored_hash`（与 refresh_token_hash 保持一致的安全策略）

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

### 4.4 修改：`profiles` 表主键类型变更

```
profiles.id: TEXT → UUID

影响范围：56 个外键需要同步变更为 UUID 类型
操作方式：直接修改 3 个主 schema 文件（项目未上线，无数据迁移）
修改顺序：01_core_business.sql → 02_platform_services.sql → 03_infrastructure.sql（外键依赖顺序）
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
输入: p_email, p_password_hash, p_username, p_display_name, p_signup_bonus
操作:
  1. 生成 UUID (uuid_generate_v4())
  2. INSERT INTO auth_users (id, email, password_hash, ...)
  3. INSERT INTO profiles (id, email, user_code, credits_permanent, created_by='register', ...)
  4. 两个 INSERT 在同一事务中，保证原子性
返回: auth_user + profile 完整数据
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
└── 理由: 存储密码哈希和验证 token，安全等级最高

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
│   ├── auth_user.py          # AuthUser 聚合根
│   └── session.py            # Session 实体
├── value_objects.py          # Password, Email, Token 值对象
├── repository.py             # IAuthUserRepository, ISessionRepository 接口（见下方方法签名）
├── service.py                # AuthService 核心编排（注册/登录/刷新/登出）
├── token_service.py          # JWT 签发/验证 (Access + Refresh)
├── email_service.py          # 邮箱验证/密码重置邮件 (通过 Resend)
├── password_service.py       # 密码哈希 (argon2id) + 强度校验
└── constants.py              # Token 有效期、锁定阈值等常量
```

**Repository 接口方法签名**：

```
IAuthUserRepository:
├── get_by_id(user_id: UUID) → AuthUser | None
├── get_by_email(email: str) → AuthUser | None
├── create(auth_user: AuthUser) → AuthUser           # 通过 RPC create_auth_user_with_profile()
├── update_password(user_id: UUID, password_hash: str) → None
├── update_email_verified(user_id: UUID, verified: bool) → None
├── update_login_attempt(user_id: UUID, failed_attempts: int, locked_until: datetime | None) → None
├── set_verification_token(user_id: UUID, token_hash: str, expires_at: datetime) → None
├── set_password_reset_token(user_id: UUID, token_hash: str, expires_at: datetime) → None
├── clear_verification_token(user_id: UUID) → None
├── clear_password_reset_token(user_id: UUID) → None
├── delete(user_id: UUID) → None                     # 硬删除 auth_users
└── record_login(user_id: UUID, ip: str, timestamp: datetime) → None

ISessionRepository:
├── create(session: Session) → Session
├── get_by_token_hash(token_hash: str) → Session | None
├── get_active_by_user(user_id: UUID) → List[Session]
├── count_active_by_user(user_id: UUID) → int
├── revoke(session_id: UUID, reason: str) → None
├── revoke_family(family_id: UUID, reason: str) → None
├── revoke_all_by_user(user_id: UUID, reason: str) → None
├── revoke_oldest_by_user(user_id: UUID, reason: str) → None  # 踢出最旧会话
└── update_last_used(session_id: UUID) → None
```

### 5.2 核心服务职责

**AuthService（核心编排）**：
| 方法 | 职责 |
|------|------|
| `register()` | 校验 → 哈希密码 → **原子创建** auth_users + profiles（同一 UUID，通过 RPC `create_auth_user_with_profile()` 保证事务一致性）→ 发验证邮件 → 创建 session → 返回 tokens |
| `login()` | 限流检查 → 查用户 → 检查锁定 → 验证密码 → 记录登录 → 创建 session → 返回 tokens |
| `refresh_token()` | 查 session → 检查过期/作废 → 轮换（废旧发新）→ 重用检测 → 返回新 tokens |
| `logout()` | 作废当前 session |
| `logout_all()` | 作废用户所有 sessions |
| `verify_email()` | 校验 token → 标记 email_verified |
| `request_password_reset()` | 生成 token → 发邮件（无论邮箱是否存在都返回成功，防枚举） |
| `reset_password()` | 校验 token → 更新密码 → 作废所有 sessions |
| `change_password()` | 验证旧密码 → 更新密码 → 可选作废其他 sessions |
| `get_sessions()` | 列出用户所有活跃 sessions（多设备管理） |
| `revoke_session()` | 踢出指定设备 |
| `delete_account()` | 验证密码 → 取消 Stripe 订阅 → 作废 sessions → 软删除 profiles → 硬删除 auth_users → 异步匿名化内容（详见 7.3） |

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
| POST | `/auth/register` | 注册 | 5/hour/IP | 否 |
| POST | `/auth/login` | 登录 | 10/min/IP | 否 |
| POST | `/auth/refresh` | 刷新 Access Token | 30/min/token | Refresh Token |
| POST | `/auth/logout` | 登出当前设备 | — | Refresh Token |
| POST | `/auth/logout-all` | 登出所有设备 | — | Access Token |
| POST | `/auth/verify-email` | 验证邮箱 | 10/hour/IP | 否 |
| POST | `/auth/resend-verification` | 重发验证邮件 | 3/hour/email | Access Token |
| POST | `/auth/forgot-password` | 请求密码重置 | 3/hour/email | 否 |
| POST | `/auth/reset-password` | 执行密码重置 | 5/hour/IP | 否 |
| POST | `/auth/change-password` | 修改密码（已登录） | 5/hour/user | Access Token |
| GET | `/auth/sessions` | 查看活跃设备 | — | Access Token |
| DELETE | `/auth/sessions/{id}` | 踢出指定设备 | — | Access Token |
| POST | `/auth/delete-account` | 注销账户（需密码确认） | 1/hour/user | Access Token |

**核心端点 Request/Response Schema**：

```
POST /auth/register
  Request:  { email: string, password: string, display_name?: string }
  Response: { access_token: string, user: { id: UUID, email: string, display_name: string } }
  Errors:   422 (验证失败) / 409 (邮箱已注册，但为防枚举返回与成功相同的 HTTP 200 + "请查收验证邮件")

POST /auth/login
  Request:  { email: string, password: string }
  Response: { access_token: string, user: { id: UUID, email: string, tier: string, role: string } }
  Errors:   401 { error: "invalid_credentials" } / 403 { error: "account_locked", retry_after: number }

POST /auth/refresh
  Request:  { refresh_token: string, rotate?: boolean }  // rotate 默认 true
  Response: { access_token: string, refresh_token?: string }  // rotate=false 时不返回 refresh_token
  Errors:   401 { error: "token_expired" | "token_revoked" | "reuse_detected" }

POST /auth/logout
  Request:  { refresh_token: string }
  Response: { success: true }

POST /auth/verify-email
  Request:  { token: string, email: string }
  Response: { success: true, message: "邮箱验证成功" }
  Errors:   400 { error: "invalid_token" | "token_expired" }

POST /auth/forgot-password
  Request:  { email: string }
  Response: { success: true, message: "如果该邮箱已注册，重置邮件已发送" }  // 统一响应，防枚举

POST /auth/reset-password
  Request:  { token: string, email: string, new_password: string }
  Response: { success: true }
  Errors:   400 { error: "invalid_token" | "token_expired" | "weak_password" }

POST /auth/change-password
  Request:  { current_password: string, new_password: string }
  Response: { success: true }

GET /auth/sessions
  Response: { sessions: [{ id: UUID, device_name: string, ip_address: string, last_used_at: string, is_current: boolean }] }

DELETE /auth/sessions/{id}
  Response: { success: true }

POST /auth/delete-account
  Request:  { password: string }
  Response: { success: true }

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
- /auth/login:    IP + email（防止同 IP 不同账号暴力破解）
- /auth/register: IP（防止同 IP 批量注册）
- /auth/refresh:  Refresh Token hash（防止单 token 滥用）
- /auth/forgot-password: email（防止对同一邮箱频繁发送重置邮件）

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

### 5.3.2 验证 Token 安全规范

```
邮箱验证 Token (email_verification_token):
├── 格式: 32 字节随机数 → base64url 编码（43 字符）
├── 生成: secrets.token_urlsafe(32)
├── 存储: SHA-256 哈希后存入数据库（不存明文，与 refresh_token_hash 策略一致）
├── 有效期: 24 小时
├── 一次性使用: 验证成功后立即设为 NULL
├── 重发机制: 重发时生成新 token，旧 token hash 立即覆盖
├── URL 格式: /verify-email?token=xxx&email=user@example.com
└── 后端校验: SHA256(url_token) == db_hash AND 未过期 AND email 匹配

密码重置 Token (password_reset_token):
├── 格式: 同上，32 字节 base64url
├── 存储: 同上，SHA-256 哈希后存入数据库
├── 有效期: 1 小时（比邮箱验证更短，安全要求更高）
├── 一次性使用: 重置成功后立即设为 NULL
├── 重发机制: 重发时生成新 token，旧 token hash 立即覆盖
├── URL 格式: /reset-password?token=xxx&email=user@example.com
└── 后端校验: SHA256(url_token) == db_hash AND 未过期 AND email 匹配

安全理由: 如果数据库被攻破，明文 token 可直接用于验证任意邮箱/重置任意密码。
哈希存储后攻击者无法从 hash 反推 token，需要拦截用户邮件才能获取明文。

过期 Token 清理:
├── 方式: 不主动清理，验证时检查 expires_at
├── 可选: 定期任务清理 > 7 天的过期 token（减少数据库碎片）
└── 部分索引: WHERE token IS NOT NULL（只索引有 token 的行）
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
- 注册新服务：`get_auth_service()`, `get_token_service()`, `get_password_service()` 等
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

**关键设计**：新 `useAuth()` 暴露与 Clerk 相同的接口，最小化下游改动：

```
useAuth() 接口对比:
├── isSignedIn    — 相同
├── isLoaded      — 相同
├── getToken()    — 相同签名，返回 Access Token string
├── signOut()     — 相同签名
├── userId        — 相同（现在是 UUID）
└── 新增 signIn() / signUp()
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
```

**Next.js API Route 代理**：
```
decodables-fe/app/api/auth/[...action]/route.ts
→ 代理所有 /auth/* 请求到后端
→ 管理 httpOnly cookie 的设置/清除
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
// 4. 重置所有 loading/modal 状态（防止 token null 时 UI 卡死）
// 5. router.push('/login?redirect=' + currentPath)
// 6. BroadcastChannel 广播 user_logged_out → 其他标签同步登出
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
├── layout.tsx              # 居中卡片布局
├── login/page.tsx          # 登录表单
├── register/page.tsx       # 注册表单
├── forgot-password/page.tsx # 忘记密码
├── reset-password/page.tsx  # 重置密码（带 token）
└── verify-email/page.tsx    # 邮箱验证（带 token）
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
| `<UserButton>` | `<UserMenu>` (自定义头像下拉：头像+用户名+tier badge) | Navbar |
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

**需要改逻辑的特殊文件**：
1. `GlobalProviders.tsx` — 移除 Clerk fallback，改用自建 auth 初始化
2. `Navbar.tsx` — 替换 Clerk UI 组件为自定义组件
3. `DashboardAuthGate.tsx` — 替换 `<SignIn>` 为路由跳转
4. `services/api.ts` — token refresh 回调改为调用自建 auth

### 6.6 Middleware 替换

```
公开路由: /, /login, /register, /forgot-password, /reset-password,
          /verify-email, /pricing, /marketplace, /articles, /manual, 等
认证路由: /login, /register（已登录用户跳转到 /dashboard）
保护路由: /dashboard, /create, /profile 等（未登录跳转到 /login）

判断方式: 检查 refresh_token httpOnly cookie 是否存在
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
```

---

## 七、安全设计

| 安全措施 | 实现方式 |
|---------|---------|
| 密码存储 | argon2id（OWASP 推荐） |
| XSS 防护 | Access Token 仅存内存，Refresh Token 为 httpOnly cookie |
| CSRF 防护 | API 使用 Bearer Token 认证（非 cookie 认证），天然防 CSRF |
| 暴力破解 | 5 次失败后锁定 30 分钟 + API 限流 |
| Token 泄露 | Refresh Token 轮换 + 重用检测（作废整个 family） |
| 邮箱枚举 | 注册/密码重置对不存在的邮箱也返回成功 |
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

### 7.2 邮箱未验证用户的功能限制

注册后邮箱未验证的用户能做什么？

```
✅ 可以做：
- 登录（返回 token，email_verified=false 在 JWT payload 中标记）
- 浏览 dashboard、查看项目列表
- 浏览 marketplace

❌ 不可以做（后端校验 email_verified）：
- 消耗积分的操作（AI 生图、OCR 识别等）
- 创建项目
- 购买积分 / 订阅升级

前端体验：
- 顶部显示 "请验证邮箱" 提示条（含重发验证邮件按钮）
- 尝试受限操作时弹出 "请先验证邮箱" 提示

理由：
- 提供更好的 UX：不要求用户立即去收邮件
- 防止垃圾注册：未验证用户无法消耗系统资源
- 保护支付安全：未验证邮箱不能进行付费操作
```

### 7.3 账户删除 / 注销

用户可以主动注销账户，需要安全流程和数据处理策略。

**注销流程**：
```
前端：
1. 用户在 /profile 点击 "删除账户"
2. 弹出确认对话框：输入密码 + 勾选 "我理解此操作不可逆"
3. 调用 POST /auth/delete-account { password }

后端 AuthService.delete_account():
1. 验证密码正确
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

软删除 + 30 天恢复期：
- profiles 记录（is_deleted=true，现有字段已支持）
  30 天内可通过管理员操作恢复
  30 天后彻底删除（定期清理任务）

保留但匿名化：
- projects/assets：owner_id 设为特殊 "deleted_user" UUID
  用户的创作内容不丢失（便于已购买者继续访问 marketplace 资产）
- payment_records：保留交易记录（法律要求保留 7 年）
  但脱敏用户信息（email → hash）

立即清除：
- Stripe: 调用 Stripe API 取消订阅、删除 customer（或标记不活跃）
- Resend: 移除邮件列表（如有）
```

**新增 API 端点**：
```
POST /auth/delete-account    需要密码确认    Access Token
```

**邮箱复用**：
- 账户删除后，该邮箱可以重新注册（因为 auth_users 已硬删除）
- 30 天恢复期内，新注册返回与正常注册**完全相同**的响应（"请查收验证邮件"），防止邮箱枚举
  → 实际发送的是"账户恢复"邮件（非验证邮件），让用户通过邮件中的链接选择恢复旧账户或注册新账户
  → 攻击者无法通过 API 响应判断该邮箱是否曾注册过

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

### 7.5 垃圾注册防护

```
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

| 阶段 | 内容 | 预估工作量 |
|------|------|-----------|
| **Phase 0** | 数据库 Schema：新增 3 张 auth 表，profiles.id 改 UUID，56 个外键同步，RPC 函数重写/更新（详见 4.5-4.8），CHECK 约束更新 | 1.5 天 |
| **Phase 1** | 后端 Auth Domain：service/token/password/repository/API 全套 | 4 天 |
| **Phase 2** | 后端集成：修改 dependencies.py + config.py + container.py，删除 Clerk 模块 | 1 天 |
| **Phase 3** | 前端 Auth 抽象层：AuthProvider + useAuth + tokenManager + API Route 代理 | 3 天 |
| **Phase 4** | 前端认证页面：login/register/forgot-password/reset-password/verify-email | 2 天 |
| **Phase 5** | 前端迁移：~30 个文件 import 替换 + 特殊文件逻辑调整 | 3 天 |
| **Phase 6** | 测试：后端单元测试 + 集成测试 + 前端测试 | 2 天 |
| **Phase 7** | 清理：移除 @clerk/nextjs、svix 依赖，更新环境变量，构建验证 | 1 天 |
| **总计** | | **~17.5 天** |

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
AUTH_JWT_SECRET              # 256-bit 随机密钥（必须）
AUTH_ACCESS_TOKEN_EXPIRE_MIN  # Access Token 有效期，默认 15
AUTH_REFRESH_TOKEN_EXPIRE_DAYS # Refresh Token 有效期，默认 7
AUTH_LOCKOUT_ATTEMPTS         # 锁定前最大失败次数，默认 5
AUTH_LOCKOUT_DURATION_MIN     # 锁定时长（分钟），默认 30
RESEND_API_KEY               # Resend 邮件服务（已有，确认保留）
RESEND_FROM_EMAIL            # 发件人地址（已有 SUPPORT_EMAIL_FROM，复用或新增专用变量）
```

---

## 十、验证方案

### 每个 Phase 完成后的验证

| Phase | 验证方式 |
|-------|---------|
| Phase 0 (Schema) | 在 Supabase 执行 SQL，确认 3 张 auth 表创建成功，profiles.id 为 UUID |
| Phase 1 (后端 Auth) | `pytest tests/domains/auth/` 全部通过，手动测试注册/登录/刷新 API |
| Phase 2 (后端集成) | 后端启动无报错，`get_current_user()` 能正确验证自签 JWT |
| Phase 3 (前端抽象层) | AuthProvider 能初始化，useAuth() 能获取 token，API 调用成功 |
| Phase 4 (认证页面) | 手动测试：注册→收到验证邮件→登录→跳转 dashboard→登出→跳转 login |
| Phase 5 (前端迁移) | `npm run build` 零错误，所有页面功能正常 |
| Phase 6 (测试) | `pytest` 后端全部通过，前端 jest 全部通过。测试 JWT 策略：移除 `TEST_JWT_PUBLIC_KEY` 机制，测试中直接用 `AUTH_JWT_SECRET` 通过 `TokenService` 签发 HS256 test token；或调用 `/auth/register` + `/auth/login` 获取真实 token |
| Phase 7 (清理) | `grep -r "clerk" --include="*.ts" --include="*.tsx" --include="*.py"` 返回 0 结果（文档除外） |

### 端到端验证流程

```
1. 注册新用户 → 收到 Resend 验证邮件
2. 点击验证链接 → 邮箱标记已验证
3. 登录 → 获取 Access Token + Refresh Token (httpOnly cookie)
4. 访问 /dashboard → 正常加载，API 调用带 Bearer token
5. 15 分钟后 → Access Token 过期 → 自动 refresh → 无感刷新
6. 访问 /create → 编辑器正常加载
7. 多标签页 → 一个标签登出 → 其他标签同步登出
8. 忘记密码 → 收到重置邮件 → 重置成功 → 所有设备登出
9. 查看设备管理 → 列出所有活跃 session → 踢出指定设备
10. npm run build → 零错误零警告
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
