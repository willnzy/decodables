# 认证模块架构

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/auth/`, `api/auth/`

---

## 一、模块概述

### 1.1 职责范围

认证模块负责：
- 用户注册 (3 步 OTP 验证)
- 用户登录 (带锁定保护)
- Token 管理 (JWT Access + Opaque Refresh)
- 会话管理 (多设备支持)
- 密码管理 (重置、修改)
- 账户安全 (软删除、恢复)

### 1.2 技术特点

| 特性 | 实现 |
|------|------|
| Access Token | JWT HS256, 15 分钟有效期 |
| Refresh Token | Opaque UUID, SHA-256 哈希存储 |
| 密码加密 | Argon2id |
| OTP | 6 位数字, 5 分钟有效 |
| 会话限制 | 最多 5 个活跃会话 |

---

## 二、代码结构

### 2.1 目录结构

```
domains/auth/
├── __init__.py
├── aggregates/
│   ├── auth_user.py      # AuthUser 聚合根
│   └── session.py        # Session 聚合
├── constants.py          # 常量定义
├── email_service.py      # 邮件发送服务
├── exceptions.py         # 领域异常
├── password_service.py   # 密码服务
├── repository.py         # Repository 接口
├── service.py            # AuthService 主服务
├── token_service.py      # Token 服务
└── value_objects.py      # 值对象

api/auth/
├── __init__.py
├── router.py             # API 路由
└── schemas.py            # 请求/响应模型
```

### 2.2 职责划分

| 文件 | 职责 |
|------|------|
| `service.py` | 认证流程编排 (AuthService) |
| `token_service.py` | JWT/Refresh Token 生成验证 |
| `password_service.py` | 密码哈希验证 (Argon2) |
| `email_service.py` | OTP 邮件发送 |
| `repository.py` | 数据访问接口定义 |

---

## 三、核心 Entity

### 3.1 AuthUser (聚合根)

```python
@dataclass
class AuthUser:
    """认证用户聚合根"""
    id: UUID
    email: Email
    password_hash: str
    email_verified: bool
    is_active: bool
    
    # OTP 状态
    otp_code: Optional[str]
    otp_expires_at: Optional[datetime]
    otp_purpose: Optional[str]
    otp_attempts: int
    
    # 登录锁定
    failed_login_attempts: int
    locked_until: Optional[datetime]
    
    # 软删除
    deleted_at: Optional[datetime]
    restore_token: Optional[str]
```

### 3.2 Session

```python
@dataclass
class Session:
    """用户会话"""
    id: UUID
    user_id: UUID
    refresh_token_hash: str
    device_info: DeviceInfo
    
    # Token 链
    token_family_id: UUID
    previous_token_hash: Optional[str]
    
    # 状态
    is_revoked: bool
    revoke_reason: Optional[str]
    
    # 时间
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
```

---

## 四、认证流程

### 4.1 注册流程 (3 步 OTP)

```
┌────────────────────────────────────────────────────────────┐
│                    3-Step OTP Registration                  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Step 1: Send OTP                                          │
│  POST /auth/register/send-otp                              │
│  ┌─────────┐                                               │
│  │ email   │ → 检查邮箱可用 → 生成 OTP → 发送邮件           │
│  └─────────┘                                               │
│       ↓                                                    │
│  Step 2: Verify OTP                                        │
│  POST /auth/register/verify-otp                            │
│  ┌─────────┐                                               │
│  │ email   │                                               │
│  │ otp     │ → 验证 OTP → 返回临时 token                   │
│  └─────────┘                                               │
│       ↓                                                    │
│  Step 3: Complete Registration                             │
│  POST /auth/register/complete                              │
│  ┌─────────┐                                               │
│  │ token   │                                               │
│  │password │ → 验证临时 token → 创建用户 → 发放登录 Token   │
│  └─────────┘                                               │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 4.2 登录流程

```
┌────────────────────────────────────────────────────────────┐
│                      Login Flow                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  POST /auth/login                                          │
│  ┌─────────┐                                               │
│  │ email   │                                               │
│  │password │                                               │
│  │device   │                                               │
│  └─────────┘                                               │
│       ↓                                                    │
│  1. 查找用户 (by email)                                    │
│       ↓                                                    │
│  2. 检查账户状态                                           │
│     - 是否禁用? → AccountDisabledException                 │
│     - 是否锁定? → AccountLockedException                   │
│       ↓                                                    │
│  3. 验证密码 (Argon2id)                                    │
│     - 失败? → 累计失败次数, 可能触发锁定                    │
│       ↓                                                    │
│  4. 创建会话                                               │
│     - 超过 5 个? → 撤销最旧会话                            │
│       ↓                                                    │
│  5. 生成 Token                                             │
│     - Access Token (JWT, 15min)                            │
│     - Refresh Token (Opaque, 7d)                           │
│       ↓                                                    │
│  Response: { access_token, refresh_token, expires_in }     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 4.3 Token 刷新流程

```
┌────────────────────────────────────────────────────────────┐
│                  Token Refresh Flow                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  POST /auth/refresh                                        │
│  ┌──────────────┐                                          │
│  │refresh_token │                                          │
│  └──────────────┘                                          │
│       ↓                                                    │
│  1. 计算 SHA-256 哈希                                      │
│       ↓                                                    │
│  2. 查找会话 (by token_hash)                               │
│     - 未找到? → TokenInvalidException                      │
│       ↓                                                    │
│  3. 检查会话状态                                           │
│     - 已撤销? → TokenRevokedException                      │
│     - 已过期? → TokenExpiredException                      │
│       ↓                                                    │
│  4. 重用检测                                               │
│     - 旧 token 再次使用? → 撤销整个 token family!           │
│       ↓                                                    │
│  5. Token 轮换                                             │
│     - 生成新 Refresh Token                                 │
│     - 保存 previous_token_hash (用于重用检测)              │
│       ↓                                                    │
│  6. 生成新 Access Token                                    │
│       ↓                                                    │
│  Response: { access_token, refresh_token, expires_in }     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 五、JWT 管理

### 5.1 Access Token 结构

```python
# JWT Payload
{
    "sub": "user_id (UUID)",      # Subject
    "email": "user@example.com",
    "role": "user",               # user / admin
    "tier": "t2",                 # t1 / t2 / t3
    "sid": "session_id (UUID)",   # Session ID
    "iss": "make-decodables",     # Issuer
    "aud": "make-decodables",     # Audience
    "iat": 1738750000,            # Issued At
    "exp": 1738750900,            # Expiration (15 min)
    "jti": "unique_token_id"      # JWT ID
}
```

### 5.2 Token 配置

```python
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
ACCESS_TOKEN_ALGORITHM = "HS256"
JWT_SECRET_MIN_LENGTH = 43  # 256-bit base64
```

### 5.3 双密钥轮换

```python
# 支持零停机密钥轮换
TokenService(
    jwt_secret=current_secret,
    jwt_secret_old=old_secret  # 验证时先试新密钥，失败再试旧密钥
)
```

---

## 六、安全措施

### 6.1 登录保护

| 措施 | 配置 |
|------|------|
| 最大失败次数 | 5 次 |
| 锁定时间 | 15 分钟 |
| 密码强度 | 至少 8 字符 |

### 6.2 OTP 保护

| 措施 | 配置 |
|------|------|
| OTP 长度 | 6 位数字 |
| 有效期 | 5 分钟 |
| 冷却时间 | 60 秒 |
| 最大验证次数 | 5 次 |

### 6.3 会话保护

| 措施 | 说明 |
|------|------|
| 最多 5 会话 | 超出自动撤销最旧会话 |
| Token 轮换 | 每次刷新生成新 Refresh Token |
| 重用检测 | 检测到重用立即撤销整个 Token Family |

### 6.4 一次性邮箱拦截

```python
DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com", "tempmail.com", "guerrillamail.com",
    "yopmail.com", "10minutemail.com", ...
}
```

---

## 七、API 端点

### 7.1 注册

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/register/send-otp` | POST | 发送注册 OTP |
| `/auth/register/verify-otp` | POST | 验证 OTP |
| `/auth/register/complete` | POST | 完成注册 |

### 7.2 登录/登出

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/login` | POST | 登录 |
| `/auth/refresh` | POST | 刷新 Token |
| `/auth/logout` | POST | 登出当前设备 |
| `/auth/logout-all` | POST | 登出所有设备 |

### 7.3 密码管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/forgot-password/send-otp` | POST | 发送重置 OTP |
| `/auth/forgot-password/verify-otp` | POST | 验证 OTP |
| `/auth/forgot-password/reset` | POST | 设置新密码 |
| `/auth/change-password` | POST | 修改密码 (需登录) |

### 7.4 会话管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/sessions` | GET | 列出所有会话 |
| `/auth/sessions/{id}` | DELETE | 撤销指定会话 |

### 7.5 账户管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/delete-account/send-otp` | POST | 发送删除 OTP |
| `/auth/delete-account/confirm` | POST | 确认删除账户 |
| `/auth/restore-account` | POST | 恢复已删除账户 |

---

## 八、异常定义

### 8.1 认证异常

| 异常 | HTTP | 说明 |
|------|------|------|
| `InvalidCredentialsException` | 401 | 邮箱或密码错误 |
| `AccountLockedException` | 403 | 账户已锁定 |
| `AccountDisabledException` | 403 | 账户已禁用 |
| `EmailAlreadyExistsException` | 409 | 邮箱已注册 |
| `DisposableEmailException` | 400 | 一次性邮箱 |
| `WeakPasswordException` | 400 | 密码强度不足 |

### 8.2 OTP 异常

| 异常 | HTTP | 说明 |
|------|------|------|
| `OtpInvalidException` | 400 | OTP 错误 |
| `OtpExpiredException` | 400 | OTP 已过期 |
| `OtpCooldownException` | 429 | 发送过于频繁 |
| `OtpMaxAttemptsException` | 429 | 超过验证次数 |

### 8.3 Token 异常

| 异常 | HTTP | 说明 |
|------|------|------|
| `TokenExpiredException` | 401 | Token 已过期 |
| `TokenRevokedException` | 401 | Token 已撤销 |
| `TokenReuseDetectedException` | 401 | 检测到重用攻击 |
| `SessionNotFoundException` | 404 | 会话不存在 |

---

## 九、数据库表

### 9.1 auth_users 表

```sql
CREATE TABLE auth_users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- OTP
    otp_code TEXT,
    otp_expires_at TIMESTAMPTZ,
    otp_purpose TEXT,
    otp_attempts INTEGER DEFAULT 0,
    otp_cooldown_until TIMESTAMPTZ,
    
    -- 锁定
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    
    -- 软删除
    deleted_at TIMESTAMPTZ,
    restore_token TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 9.2 sessions 表

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth_users(id),
    refresh_token_hash TEXT NOT NULL,
    
    -- 设备信息
    device_type TEXT,
    device_name TEXT,
    ip_address TEXT,
    user_agent TEXT,
    
    -- Token 链
    token_family_id UUID NOT NULL,
    previous_token_hash TEXT,
    
    -- 状态
    is_revoked BOOLEAN DEFAULT FALSE,
    revoke_reason TEXT,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);
```

---

## 十、相关文档

- [API 参考 - 认证](../../03-api/auth.md)
- [用户 ID 系统](../../05-business/user-id-system.md)
- [安全指南](../../06-security/overview.md)

---

**END OF DOCUMENT**
