# ADR-0004 JWT 双密钥轮换

> **状态**: ✅ Active
> **日期**: 2026-01-20
> **决策者**: Backend Team

---

## 背景

JWT 认证系统需要考虑密钥安全:

1. 密钥泄露风险需要能快速应对
2. 密钥轮换不能影响已登录用户
3. 需要支持平滑过渡

传统单密钥方案的问题:

- 更换密钥会使所有 Token 失效
- 用户需要重新登录
- 无法实现平滑过渡

---

## 决策

采用 JWT 双密钥轮换机制 (Dual-Key Rotation):

1. 同时维护 `primary_key` 和 `secondary_key`
2. 签发 Token 使用 `primary_key`
3. 验证 Token 先尝试 `primary_key`，失败后尝试 `secondary_key`
4. 轮换时: `primary` → `secondary`，生成新 `primary`

---

## 考虑的选项

### 选项 A: 单密钥 + 强制重登

- **优点**: 实现简单
- **缺点**: 用户体验差，轮换成本高

### 选项 B: 密钥版本号

- **优点**: 可追踪密钥版本
- **缺点**: 需要在 Token 中存储版本，增加复杂度

### 选项 C: 双密钥轮换 (选中)

- **优点**: 平滑过渡，用户无感知
- **缺点**: 验证时需要尝试两个密钥

### 选项 D: JWKS (JSON Web Key Set)

- **优点**: 标准方案，支持多密钥
- **缺点**: 对当前规模过重

---

## 理由

1. **用户体验**: 密钥轮换不影响已登录用户
2. **安全性**: 可以定期轮换密钥
3. **简单性**: 相比 JWKS 更简单
4. **灵活性**: 可以在紧急情况下快速轮换

---

## 影响

### 正面影响

- 支持平滑密钥轮换
- 提升安全性
- 不影响用户体验

### 负面影响

- 验证时可能需要两次尝试
- 需要管理两个密钥

### 需要的改动

1. 配置支持双密钥
2. 签名逻辑使用 primary_key
3. 验证逻辑支持双密钥尝试
4. 添加密钥轮换 API/脚本

---

## 实现方案

### 配置

```python
# settings.py
class JWTSettings:
    # 主密钥 (用于签发)
    JWT_SECRET_KEY_PRIMARY: str
    
    # 次密钥 (用于验证过渡期 Token)
    JWT_SECRET_KEY_SECONDARY: str = ""
    
    # Token 有效期
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
```

### 签发 Token

```python
def create_access_token(payload: dict) -> str:
    """
    始终使用 primary_key 签发
    """
    expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode = {
        **payload,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY_PRIMARY,
        algorithm="HS256"
    )
```

### 验证 Token

```python
def verify_access_token(token: str) -> dict:
    """
    双密钥验证: primary 优先，secondary 备用
    """
    # 1. 尝试 primary_key
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY_PRIMARY,
            algorithms=["HS256"]
        )
        return payload
    except jwt.InvalidTokenError:
        pass
    
    # 2. 尝试 secondary_key (如果配置了)
    if settings.JWT_SECRET_KEY_SECONDARY:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY_SECONDARY,
                algorithms=["HS256"]
            )
            return payload
        except jwt.InvalidTokenError:
            pass
    
    # 3. 两个都失败
    raise InvalidTokenError("Invalid or expired token")
```

### 密钥轮换流程

```python
async def rotate_jwt_keys():
    """
    密钥轮换流程
    
    1. 当前 primary → secondary
    2. 生成新 primary
    3. 更新配置
    4. 重启/热加载
    """
    # 生成新密钥
    new_primary = secrets.token_urlsafe(32)
    
    # 更新配置
    await update_config('JWT_SECRET_KEY_SECONDARY', settings.JWT_SECRET_KEY_PRIMARY)
    await update_config('JWT_SECRET_KEY_PRIMARY', new_primary)
    
    # 记录审计
    await audit_log.create(
        action="jwt_key_rotated",
        details={"timestamp": datetime.utcnow().isoformat()}
    )
    
    # 热加载配置
    await reload_settings()
```

### 轮换时机

```
┌─────────────────────────────────────────────────────┐
│  轮换建议:                                           │
│                                                     │
│  1. 定期轮换: 每 90 天                              │
│  2. 紧急轮换: 疑似密钥泄露                          │
│  3. 安全事件: 安全审计后                            │
│                                                     │
│  过渡期:                                            │
│                                                     │
│  • Access Token: 15 分钟 (过渡期短)                 │
│  • Refresh Token: 7 天 (需要保留 secondary 7 天)   │
│                                                     │
│  时间线:                                            │
│                                                     │
│  Day 0: 轮换密钥                                    │
│  Day 1-7: 两个密钥都有效                            │
│  Day 8+: 可以移除 secondary                         │
└─────────────────────────────────────────────────────┘
```

---

## 相关文档

- [认证模块架构](../../modules/auth/architecture.md)
- [API 参考 - 认证](../../api/api-reference.md)
