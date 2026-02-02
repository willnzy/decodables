"""
Test User Configuration

测试用户信息配置文件，方便管理和修改测试账号。

注意:
- Token 通过 test_jwt_generator (HS256) 自动生成
- 也可通过环境变量直接设置
- 这里只存储用户的静态信息
- 敏感信息不要提交到代码仓库

@module tests.integration.staging.test_users
@version 2.0.0 (self-hosted auth, removed Clerk dependency)
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
    }

    PRO = {
        "user_id": None,
        "email": None,
        "tier": "t3",  # Pro tier
        "role": "user",
        "credits_monthly": 200,
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

    # JWT Secret (for auto-generating test tokens)
    JWT_SECRET = "AUTH_JWT_SECRET"


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


### 方式 1: 自动生成 (推荐)

设置 AUTH_JWT_SECRET 匹配 staging 后端配置，token 会自动生成：

```bash
export AUTH_JWT_SECRET='your-staging-jwt-secret-at-least-43-chars'
```

### 方式 2: 直接设置 Token

```bash
export TEST_USER_TOKEN='eyJhbG...'
export TEST_STARTER_TOKEN='eyJhbG...'
export TEST_PRO_TOKEN='eyJhbG...'
export TEST_ADMIN_TOKEN='eyJhbG...'
```

Token 优先级：
1. 环境变量直接设置的 Token
2. test_jwt_generator 自动生成 (HS256)


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
