# 后端安全风险审计报告

> **审计日期**: 2026-01-16
> **审计范围**: decodables/ 后端项目安全风险分析
> **状态**: 完成
> **风险等级**: 🔴 2 关键 | 🟠 4 高危 | 🟡 5 中等 | 🟢 2 低危

---

## 执行摘要

经过深入分析后端代码，发现以下安全风险：

| 优先级 | 数量 | 修复时间 | 影响范围 |
|--------|------|----------|----------|
| 🔴 **关键** | 2 | 2-3 天 | 认证绕过、积分原子性 |
| 🟠 **高危** | 4 | 3-5 天 | 权限控制、竞态条件 |
| 🟡 **中等** | 5 | 5-7 天 | 配置、日志脱敏 |
| 🟢 **低危** | 2 | 1-2 天 | 代码质量 |

---

## 🔴 关键风险 (CRITICAL)

### 1. JWT 验证模式缺陷

**位置**: `dependencies.py:45-72`

**问题**:
```python
# 跳过 audience 验证 - 允许其他应用的 JWT!
payload = jwt.decode(token, CLERK_PEM_PUBLIC_KEY,
                    algorithms=["RS256"],
                    options={"verify_aud": False})

# 开发环境：完全禁用签名验证 (UNSAFE)
else:
    payload = jwt.decode(token, options={"verify_signature": False})
```

**影响**:
- ⚠️ 攻击者可伪造 JWT 冒充任意用户
- ⚠️ 如果环境变量未设置，任何人都可以登录

**修复方案**:
```python
# 1. 启用 audience 验证
options={"verify_aud": True, "require": ["aud"]}

# 2. 生产环境强制要求密钥
if not CLERK_PEM_PUBLIC_KEY and os.environ.get("ENV") == "production":
    raise RuntimeError("CLERK_PEM_PUBLIC_KEY required in production")

# 3. 拒绝格式异常的 user_id
if not user_id or not user_id.startswith("user_"):
    raise UnauthorizedException("Invalid user_id format")
```

---

### 2. 积分交易的非原子操作

**位置**: `domains/webhooks/stripe_webhook_service.py:251-279`

**问题**:
```python
# 步骤 1: 记录支付
await self.payment_repo.create(uid, amount_total, ...)

# 步骤 2: 添加积分 (如果在此之前服务器崩溃，用户付款但获得 0 积分)
await self.credit_repo.add_credits_permanent(uid, credits_amount, ...)
```

**影响**:
- ⚠️ 用户付款后可能获得 0 积分
- ⚠️ 部分操作成功导致数据不一致

**修复方案**:
```sql
-- 创建原子 RPC 函数
CREATE OR REPLACE FUNCTION process_credits_purchase_atomic(
    p_user_id TEXT,
    p_credits_amount INT,
    p_amount_total INT,
    p_session_id TEXT
) RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    -- 事务内执行所有操作
    INSERT INTO payment_records (...) VALUES (...);
    UPDATE profiles SET credits_permanent = credits_permanent + p_credits_amount WHERE id = p_user_id;
    INSERT INTO credit_transactions (...) VALUES (...);

    result := json_build_object('success', true, 'new_balance', ...);
    RETURN result;
EXCEPTION WHEN OTHERS THEN
    RAISE;
END;
$$ LANGUAGE plpgsql;
```

---

## 🟠 高危风险 (HIGH)

### 3. Admin 权限检查不足

**位置**: `dependencies.py:218-245`

**问题**:
- 没有检查用户是否被禁用
- 没有检查 admin 账号是否被撤销
- 没有操作审计时间戳

**修复方案**:
```python
async def require_admin(user = Depends(get_current_user)):
    if getattr(user, 'is_disabled', False):
        raise AdminRequiredException("Admin account disabled")

    if getattr(user, 'admin_revoked_at', None):
        raise AdminRequiredException("Admin privileges revoked")

    return {
        "id": user.user_id,
        "email": user.email,
        "role": "admin",
        "checked_at": datetime.utcnow().isoformat()
    }
```

---

### 4. JIT 用户创建的竞态条件

**位置**: `dependencies.py:98-104`

**问题**:
- 100ms 延迟不足以处理网络延迟
- 仅重试一次，不使用指数退避
- 没有分布式锁

**影响**:
- 同一用户可能被创建多次
- Signup bonus 可能被授予多次

**修复方案**:
```python
# 使用数据库级别的幂等创建
profile, was_created = await user_repo.create_or_get(
    user_profile,
    source='jit'
)
# 必须使用 INSERT ON CONFLICT 确保原子性
```

---

### 5. Monthly Credits Reset 竞态条件

**位置**: `domains/billing/service.py:265-290`

**问题**:
- webhook 被重复发送可能导致双倍积分
- 没有幂等性检查

**修复方案**:
```python
# 使用幂等性键
result = await self.db_client.rpc("reset_monthly_credits_atomic", {
    "p_user_id": user_id,
    "p_new_amount": new_amount,
    "p_idempotency_key": f"renewal_{user_id}_{datetime.utcnow().date()}"
}).execute()
```

---

### 6. 支付记录重复创建

**位置**: `domains/webhooks/stripe_webhook_service.py:866-872`

**问题**:
```python
try:
    existing = self.payment_repo.get_by_payment_intent_and_type(...)
except Exception as e:
    logger.warning(f"Failed to check existing refund: {e}")
    # ⚠️ 没有检查而继续处理 - 可能创建重复
```

**修复方案**:
```python
try:
    existing = await self.payment_repo.get_by_refund_id(refund_id)
    if existing:
        return {"status": "ok"}
except Exception as e:
    logger.critical(f"Failed to check: {e}")
    raise HTTPException(503, "Temporarily unavailable")  # 不继续，让 webhook 重试
```

---

## 🟡 中等风险 (MEDIUM)

### 7. Webhook 密钥配置缺失检查

**位置**: `domains/billing/payment_service.py:34`

**问题**: 缺少密钥时服务仍然启动

**修复方案**:
```python
@app.on_event("startup")
async def startup_checks():
    required = ["STRIPE_WEBHOOK_SECRET", "STRIPE_API_KEY",
                "CLERK_WEBHOOK_SECRET", "CLERK_PEM_PUBLIC_KEY"]
    missing = [var for var in required if not os.environ.get(var)]
    if missing:
        raise RuntimeError(f"Missing: {missing}")
```

---

### 8. Webhook 元数据信任问题

**位置**: `stripe_webhook_service.py:843-848`

**问题**: webhook 元数据可被伪造

**修复方案**:
```python
if not user_id or not user_id.startswith("user_"):
    logger.error(f"Invalid user_id in webhook")
    return {"status": "error", "error": "invalid_user_id"}
```

---

### 9. Log 中暴露敏感信息

**位置**: `dependencies.py:122-143`

**问题**: user_id 被完整记录

**修复方案**:
```python
user_id_hash = hashlib.sha256(user_id.encode()).hexdigest()[:8]
logger.warning(f"User not found (hash: {user_id_hash})")
```

---

### 10. 积分余额被记录在 Log

**位置**: `stripe_webhook_service.py:307-321`

**问题**: 审计日志中记录了具体金额

**修复方案**: 只记录操作类型，不记录具体金额

---

### 11. Tier 参数验证绕过

**位置**: `api/admin/users.py:243-246`

**问题**: 错误消息暴露有效值列表

**修复方案**:
```python
if tier_lower not in VALID_TIERS:
    raise HTTPException(400, "Invalid tier specified")  # 不说哪些有效
```

---

## 🟢 低危风险 (LOW)

### 12. 开发日志中的用户标识符

**建议**: 使用哈希值而非截断

### 13. 支付端点费率限制不足

**建议**: 为 webhook 端点添加专门的费率限制

---

## 修复优先级

### 立即修复 (1-2 天)

1. **JWT 验证逻辑** - 启用 aud 验证，强制生产环境密钥
2. **积分原子操作** - 创建 RPC 函数

### 本周修复 (3-5 天)

3. **Admin 权限检查** - 添加禁用/撤销检查
4. **Webhook 幂等性** - 使用数据库级别约束
5. **JIT 用户创建** - 使用 INSERT ON CONFLICT

### 下周修复 (5-7 天)

6. **配置检查** - 启动时验证环境变量
7. **日志脱敏** - 使用哈希替代明文
8. **费率限制** - 添加专门的限制规则

---

## 已确认的安全措施 ✅

1. **Supabase SDK 参数化查询** - SQL 注入防护
2. **Pydantic 输入验证** - 请求体验证
3. **CORS 配置** - 跨域保护
4. **RLS (Row Level Security)** - 数据库级别访问控制
5. **Stripe 签名验证** - Webhook 完整性

---

## 相关文档

- [.claude/guides/SECURITY-DEEP-DEFENSE.md](.claude/guides/SECURITY-DEEP-DEFENSE.md) - 安全防御指南
- [domains/billing/service.py](domains/billing/service.py) - 积分服务
- [dependencies.py](dependencies.py) - 认证依赖

---

**审计完成日期**: 2026-01-16
**下次审计建议**: 2026-02-16 (每月一次)
