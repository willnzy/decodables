"""
Test User Configuration

测试用户信息配置文件，方便管理和修改测试账号。

注意:
- Token 需要通过环境变量或 Clerk API 动态获取 (60秒过期)
- 这里只存储用户的静态信息
- 敏感信息不要提交到代码仓库

@module tests.integration.staging.test_users
@version 1.0.0
"""


class TestUsers:
    """测试用户配置"""

    # ==========================================
    # Admin 用户 (用于 Admin API 测试)
    # ==========================================
    ADMIN = {
        "user_id": "user_38J7ztkfxMPma40Q5FQ2ryO80eg",
        "email": "willnzy@gmail.com",
        "display_name": "Yi",
        "first_name": "Yi",
        "last_name": "Zhang",
        "user_code": "26011519412600000000015518",
        "tier": "t1",
        "role": "admin",  # 注意: 数据库中 role='user'，需要确认 admin 权限来源
        "credits_monthly": 0,
        "credits_permanent": 50,
        "timezone": "Asia/Shanghai",
        "language": "en",
        # Clerk Session ID (用于通过 Clerk API 获取 token)
        # 需要用户登录后从 Clerk Dashboard 或 API 获取
        "clerk_session_id": None,  # 填入后可自动刷新 token
    }

    # ==========================================
    # 普通用户 (用于 User API 测试)
    # ==========================================
    # 当前使用自动获取 token 的方式，不需要预配置
    # 如果需要特定测试用户，可以在这里添加
    REGULAR = {
        "user_id": None,  # 从 token 解析
        "email": None,
        "tier": "t1",  # Free tier
        "role": "user",
        "clerk_session_id": None,
    }

    # ==========================================
    # 付费用户 (用于测试付费功能)
    # ==========================================
    STARTER = {
        "user_id": None,
        "email": None,
        "tier": "t2",  # Starter tier
        "role": "user",
        "credits_monthly": 100,
        "clerk_session_id": None,
    }

    PRO = {
        "user_id": None,
        "email": None,
        "tier": "t3",  # Pro tier
        "role": "user",
        "credits_monthly": 200,
        "clerk_session_id": None,
    }


# ==========================================
# 环境变量名称
# ==========================================

class TokenEnvVars:
    """Token 环境变量名称"""

    # 普通用户 token (t1 Free)
    USER_TOKEN = "TEST_USER_TOKEN"

    # Starter 用户 token (t2)
    STARTER_TOKEN = "TEST_STARTER_TOKEN"

    # Pro 用户 token (t3)
    PRO_TOKEN = "TEST_PRO_TOKEN"

    # Admin 用户 token
    ADMIN_TOKEN = "TEST_ADMIN_TOKEN"

    # Clerk Secret Key (用于通过 API 获取 token)
    CLERK_SECRET_KEY = "CLERK_SECRET_KEY"

    # Session IDs for auto-refresh
    ADMIN_SESSION_ID = "TEST_ADMIN_SESSION_ID"
    USER_SESSION_ID = "TEST_USER_SESSION_ID"
    STARTER_SESSION_ID = "TEST_STARTER_SESSION_ID"
    PRO_SESSION_ID = "TEST_PRO_SESSION_ID"


# ==========================================
# 使用说明
# ==========================================

"""
## 配置测试 Token 的方式

### 测试用户类型

| 环境变量 | 用户类型 | Tier | 用途 |
|----------|----------|------|------|
| TEST_USER_TOKEN | 普通用户 | t1 (Free) | 测试基础功能和限制 |
| TEST_STARTER_TOKEN | Starter 用户 | t2 | 测试付费功能 |
| TEST_PRO_TOKEN | Pro 用户 | t3 | 测试高级功能 |
| TEST_ADMIN_TOKEN | Admin 用户 | - | 测试管理接口 |


### 方式 1: 直接设置 Token (最简单)

从浏览器登录后获取 token，设置环境变量：

```bash
# Free 用户 (t1) - 必需
export TEST_USER_TOKEN='eyJhbG...'

# Starter 用户 (t2) - Tier 测试需要
export TEST_STARTER_TOKEN='eyJhbG...'

# Pro 用户 (t3) - Tier 测试需要
export TEST_PRO_TOKEN='eyJhbG...'

# Admin 用户 - Admin 测试需要
export TEST_ADMIN_TOKEN='eyJhbG...'
```

获取方式:
1. 打开 https://decodables-staging.up.railway.app
2. 登录对应账号 (Free/Starter/Pro/Admin)
3. 打开 DevTools (F12) → Console
4. 执行: await window.Clerk.session.getToken()
5. 复制返回的 token

注意: Token 60 秒后过期，需要重新获取


### 方式 2: 通过 Clerk API 自动获取 (推荐)

设置 Clerk Secret Key 和各用户的 Session ID：

```bash
# Clerk Secret Key (从 Clerk Dashboard 获取)
export CLERK_SECRET_KEY='sk_test_...'

# 各用户的 Session ID
export TEST_USER_SESSION_ID='sess_...'      # Free 用户
export TEST_STARTER_SESSION_ID='sess_...'   # Starter 用户
export TEST_PRO_SESSION_ID='sess_...'       # Pro 用户
export TEST_ADMIN_SESSION_ID='sess_...'     # Admin 用户
```

Session ID 获取方式:
1. Clerk Dashboard → Users → 选择用户
2. Sessions 标签 → 复制 Session ID

或者通过 API:
```bash
curl -H "Authorization: Bearer sk_test_..." \\
  https://api.clerk.com/v1/users/{user_id}/sessions
```


### 方式 3: 混合使用

可以同时配置多种方式，代码会按优先级尝试：
1. 直接 Token (TEST_USER_TOKEN 等)
2. Clerk API 生成 (CLERK_SECRET_KEY + SESSION_ID)


## 运行测试

```bash
# 运行基础测试 (只需要 TEST_USER_TOKEN)
pytest tests/integration/staging/projects/ -v

# 运行 Tier 限制测试 (需要不同 Tier 的用户)
pytest tests/integration/staging/tier_enforcement/ -v

# 运行 Admin 测试 (需要 TEST_ADMIN_TOKEN)
pytest tests/integration/staging/system_resources/ -v -m admin
```


## 可用的 Fixture

| Fixture | 需要的环境变量 | 说明 |
|---------|----------------|------|
| anon_client | 无 | 匿名客户端 (webhook 测试) |
| auth_client | TEST_USER_TOKEN | Free 用户客户端 |
| starter_client | TEST_STARTER_TOKEN | Starter 用户客户端 |
| pro_client | TEST_PRO_TOKEN | Pro 用户客户端 |
| admin_client | TEST_ADMIN_TOKEN | Admin 客户端 |
"""
