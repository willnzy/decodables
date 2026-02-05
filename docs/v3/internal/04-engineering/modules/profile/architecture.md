# Profile 模块架构

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/identity/`, `app/(protected)/profile/`

---

## 一、模块概述

### 1.1 职责

Profile 模块负责用户个人信息的查看和管理。

### 1.2 核心功能

| 功能 | 说明 |
|------|------|
| 个人信息 | 查看和编辑基本信息 |
| 头像管理 | 上传和更换头像 |
| 密码修改 | 修改登录密码 |
| 账户安全 | 查看登录记录 |
| 账户删除 | 永久删除账户 |

---

## 二、系统架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     Profile Module                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                    Frontend                            │ │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐         │ │
│  │  │  Profile  │  │  Security │  │  Settings │         │ │
│  │  │   Info    │  │   Page    │  │   Page    │         │ │
│  │  └───────────┘  └───────────┘  └───────────┘         │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                       API                              │ │
│  │  /profile  /profile/avatar  /profile/password         │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                     Domain                             │ │
│  │  UserProfileService  AvatarService  SecurityService   │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、后端架构

### 3.1 目录结构

```
domains/identity/
├── aggregates/
│   └── user_profile.py      # UserProfile 聚合根
├── entities.py              # 实体定义
├── repository.py            # 数据访问接口
├── user_profile_service.py  # 用户资料服务
└── value_objects.py         # 值对象

api/user/
├── profile.py               # 用户资料 API
└── avatar.py                # 头像 API
```

### 3.2 核心实体

**UserProfile 聚合根**:

```python
@dataclass
class UserProfile:
    id: UUID
    user_id: UUID
    user_code: str
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    tier: str
    credits_monthly: int
    credits_permanent: int
    created_at: datetime
    updated_at: datetime
```

### 3.3 服务层

```python
class UserProfileService:
    async def get_profile(self, user_id: UUID) -> UserProfile
    async def update_profile(self, user_id: UUID, name: str) -> UserProfile
    async def update_avatar(self, user_id: UUID, file: UploadFile) -> str
    async def change_password(self, user_id: UUID, old_pw: str, new_pw: str) -> None
    async def delete_account(self, user_id: UUID, password: str) -> None
```

---

## 四、前端架构

### 4.1 目录结构

```
app/(protected)/profile/
├── page.tsx                 # 主页面
├── security/
│   └── page.tsx             # 安全设置
├── settings/
│   └── page.tsx             # 账户设置
└── _components/
    ├── ProfileForm.tsx      # 个人信息表单
    ├── AvatarUpload.tsx     # 头像上传
    ├── PasswordForm.tsx     # 密码修改表单
    └── DeleteAccount.tsx    # 删除账户
```

### 4.2 页面布局

```
┌────────────────────────────────────────────────────────────┐
│  Profile                                                   │
├─────────────┬──────────────────────────────────────────────┤
│             │                                              │
│  👤 Profile │  ┌──────────────────────────────────────┐   │
│  🔒 Security│  │  Avatar                              │   │
│  ⚙️ Settings│  │  ┌─────┐                             │   │
│             │  │  │     │  [Upload new]               │   │
│             │  │  └─────┘                             │   │
│             │  │                                      │   │
│             │  │  Name: [________________]            │   │
│             │  │                                      │   │
│             │  │  Email: user@example.com (verified)  │   │
│             │  │                                      │   │
│             │  │  User Code: 26010914305278900123    │   │
│             │  │                                      │   │
│             │  │  Tier: Starter ⭐                    │   │
│             │  │                                      │   │
│             │  │  [Save Changes]                      │   │
│             │  └──────────────────────────────────────┘   │
│             │                                              │
└─────────────┴──────────────────────────────────────────────┘
```

---

## 五、头像管理

### 5.1 上传流程

```
选择文件 → 预览裁剪 → 上传存储 → 更新 URL
```

### 5.2 限制

| 限制 | 值 |
|------|-----|
| 格式 | JPG, PNG, GIF, WEBP |
| 大小 | 最大 5 MB |
| 尺寸 | 自动裁剪为 256x256 |

### 5.3 存储

```
storage/avatars/{user_id}/{filename}
```

---

## 六、密码修改

### 6.1 验证规则

| 规则 | 说明 |
|------|------|
| 当前密码 | 必须正确 |
| 新密码长度 | 至少 8 位 |
| 密码强度 | 包含字母和数字 |
| 确认密码 | 必须一致 |

### 6.2 安全措施

- 密码使用 Argon2id 哈希
- 修改后所有其他设备登出
- 发送邮件通知

---

## 七、账户删除

### 7.1 删除流程

```
请求删除 → 输入密码确认 → 30 天冷静期 → 永久删除
```

### 7.2 删除内容

| 内容 | 处理方式 |
|------|----------|
| 个人信息 | 匿名化 |
| 项目数据 | 删除 |
| 订阅 | 自动取消 |
| 积分 | 清零 |

### 7.3 冷静期

- 30 天内可撤销
- 期间账户处于停用状态
- 无法登录但数据保留

---

## 八、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/profile` | GET | 获取个人资料 |
| `/profile` | PUT | 更新个人资料 |
| `/profile/avatar` | POST | 上传头像 |
| `/profile/password` | PUT | 修改密码 |
| `/profile/delete` | POST | 请求删除账户 |
| `/profile/delete/cancel` | POST | 撤销删除 |

---

## 九、数据库设计

### 9.1 表结构

```sql
-- 用户资料表
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_code VARCHAR(26) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(100),
    avatar_url TEXT,
    tier VARCHAR(10) DEFAULT 't1',
    credits_monthly INTEGER DEFAULT 0,
    credits_permanent INTEGER DEFAULT 100,
    status VARCHAR(20) DEFAULT 'active',
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 9.2 索引

```sql
CREATE UNIQUE INDEX idx_profiles_email ON profiles(email);
CREATE UNIQUE INDEX idx_profiles_user_code ON profiles(user_code);
CREATE INDEX idx_profiles_status ON profiles(status);
```

---

## 十、相关文档

- [Profile 功能规格](../../02-product/features/profile.md)
- [用户 ID 系统](../../05-business/user-id-system.md)
- [认证模块架构](../auth/architecture.md)

---

**END OF DOCUMENT**
