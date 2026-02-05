# 错误码速查

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05

---

## 一、错误码规范

### 1.1 格式

```
{CATEGORY}_{CODE}
```

### 1.2 HTTP 状态码对应

| HTTP | 类型 | 说明 |
|------|------|------|
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突 |
| 422 | Validation Error | 验证失败 |
| 429 | Too Many Requests | 请求过多 |
| 500 | Server Error | 服务器错误 |

---

## 二、认证错误 (AUTH_xxx)

| 错误码 | HTTP | 说明 | 处理建议 |
|--------|------|------|----------|
| AUTH_INVALID_CREDENTIALS | 401 | 邮箱或密码错误 | 检查输入 |
| AUTH_ACCOUNT_LOCKED | 403 | 账户已锁定 | 等待 15 分钟 |
| AUTH_ACCOUNT_DISABLED | 403 | 账户已禁用 | 联系客服 |
| AUTH_EMAIL_EXISTS | 409 | 邮箱已注册 | 使用其他邮箱或登录 |
| AUTH_DISPOSABLE_EMAIL | 400 | 一次性邮箱 | 使用正规邮箱 |
| AUTH_WEAK_PASSWORD | 400 | 密码强度不足 | 使用更强密码 |
| AUTH_TOKEN_EXPIRED | 401 | Token 已过期 | 重新登录 |
| AUTH_TOKEN_REVOKED | 401 | Token 已撤销 | 重新登录 |
| AUTH_TOKEN_REUSE | 401 | Token 重用检测 | 重新登录 |
| AUTH_SESSION_NOT_FOUND | 404 | 会话不存在 | 重新登录 |

---

## 三、OTP 错误 (OTP_xxx)

| 错误码 | HTTP | 说明 | 处理建议 |
|--------|------|------|----------|
| OTP_INVALID | 400 | 验证码错误 | 检查输入 |
| OTP_EXPIRED | 400 | 验证码已过期 | 重新获取 |
| OTP_COOLDOWN | 429 | 发送过于频繁 | 等待 60 秒 |
| OTP_MAX_ATTEMPTS | 429 | 超过验证次数 | 重新获取 |

---

## 四、业务错误 (BIZ_xxx)

| 错误码 | HTTP | 说明 | 处理建议 |
|--------|------|------|----------|
| BIZ_INSUFFICIENT_CREDITS | 402 | 积分不足 | 充值积分 |
| BIZ_PROJECT_NOT_FOUND | 404 | 项目不存在 | 检查项目 ID |
| BIZ_TEMPLATE_NOT_FOUND | 404 | 模板不存在 | 检查模板 ID |
| BIZ_TIER_UPGRADE_REQUIRED | 403 | 需要升级 Tier | 升级订阅 |
| BIZ_QUOTA_EXCEEDED | 403 | 超出配额限制 | 升级或删除内容 |
| BIZ_INVALID_TIER | 400 | 无效的 Tier | 检查参数 |

---

## 五、支付错误 (PAY_xxx)

| 错误码 | HTTP | 说明 | 处理建议 |
|--------|------|------|----------|
| PAY_CHECKOUT_FAILED | 500 | 创建支付失败 | 重试或联系客服 |
| PAY_SUBSCRIPTION_NOT_ACTIVE | 400 | 订阅未激活 | 检查订阅状态 |
| PAY_INVALID_PLAN | 400 | 无效的计划 | 检查参数 |
| PAY_STRIPE_ERROR | 500 | Stripe 错误 | 联系客服 |

---

## 六、AI 错误 (AI_xxx)

| 错误码 | HTTP | 说明 | 处理建议 |
|--------|------|------|----------|
| AI_GENERATION_FAILED | 500 | 生成失败 | 重试 |
| AI_CONTENT_FILTERED | 400 | 内容被过滤 | 修改提示词 |
| AI_RATE_LIMIT | 429 | 请求过多 | 稍后重试 |
| AI_TIMEOUT | 504 | 生成超时 | 重试 |

---

## 七、系统错误 (SYS_xxx)

| 错误码 | HTTP | 说明 | 处理建议 |
|--------|------|------|----------|
| SYS_INTERNAL_ERROR | 500 | 内部错误 | 联系客服 |
| SYS_SERVICE_UNAVAILABLE | 503 | 服务不可用 | 稍后重试 |
| SYS_DATABASE_ERROR | 500 | 数据库错误 | 联系客服 |
| SYS_RATE_LIMIT | 429 | 请求限流 | 稍后重试 |

---

## 八、验证错误 (VAL_xxx)

| 错误码 | HTTP | 说明 | 处理建议 |
|--------|------|------|----------|
| VAL_REQUIRED_FIELD | 422 | 必填字段缺失 | 补充必填项 |
| VAL_INVALID_FORMAT | 422 | 格式错误 | 检查输入格式 |
| VAL_OUT_OF_RANGE | 422 | 超出范围 | 调整数值 |
| VAL_INVALID_EMAIL | 422 | 邮箱格式错误 | 检查邮箱 |

---

## 九、错误响应格式

### 9.1 标准格式

```json
{
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "details": {}
  }
}
```

### 9.2 验证错误格式

```json
{
  "error": {
    "code": "VAL_VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "email": ["Invalid email format"],
      "password": ["Password must be at least 8 characters"]
    }
  }
}
```

---

**END OF DOCUMENT**
