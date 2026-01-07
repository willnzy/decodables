# Webhook v2 Staging Environment Testing Guide

> 在生产环境切换之前，在 staging 环境测试 webhook v2 端点

## 概述

本指南帮助你在 staging 环境中测试 webhook v2 端点，确保功能正常后再切换生产环境。

---

## 前提条件

### 1. 环境准备

- ✅ Staging 环境已部署最新代码 (包含 `api/webhooks_api.py`)
- ✅ Staging 环境可公网访问 (或使用 ngrok/localtunnel 等工具)
- ✅ 有 Clerk 和 Stripe 的测试账号访问权限

### 2. 环境变量确认

确保 staging 环境配置了以下环境变量：

```bash
# Clerk
CLERK_WEBHOOK_SECRET=whsec_...  # Clerk webhook signing secret

# Stripe
STRIPE_WEBHOOK_SECRET=whsec_...  # Stripe webhook signing secret
STRIPE_SECRET_KEY=sk_test_...    # Stripe test mode secret key
```

---

## Clerk Webhook 测试

### Step 1: 配置 Staging Webhook

1. 访问 https://dashboard.clerk.com
2. 选择你的应用 (Application)
3. 点击左侧导航栏的 **"Webhooks"**
4. 点击 **"Add Endpoint"** (或编辑现有 staging 端点)
5. 配置端点:
   ```
   Endpoint URL: https://your-staging-domain.com/api/v2/webhooks/clerk
   ```
6. 订阅以下事件:
   - ✅ `user.created`
   - ✅ `user.updated`
   - ✅ `session.created`
   - ✅ `session.ended`
   - ✅ `session.removed`
   - ✅ `session.revoked`
7. 点击 **"Create"**，复制 **Signing Secret**
8. 更新 staging 环境变量:
   ```bash
   CLERK_WEBHOOK_SECRET=whsec_新的signing_secret
   ```
9. 重启 staging 服务

### Step 2: 测试 Clerk Webhook

#### 测试 2.1: user.created 事件

1. 在 Clerk Dashboard 中点击 **"Testing"** 标签
2. 选择事件类型: `user.created`
3. 点击 **"Send Example"**
4. 检查 staging 日志:
   ```bash
   # 应该看到类似日志
   ✅ Created user profile for user_xxx
   ```
5. 验证数据库:
   ```sql
   SELECT * FROM profiles WHERE id = 'user_xxx';
   -- 应该能看到新创建的用户记录
   ```

#### 测试 2.2: user.updated 事件

1. 在 Clerk Dashboard 中更新测试用户的头像或用户名
2. Webhook 应自动触发
3. 检查 staging 日志:
   ```bash
   ✅ Updated profile for user user_xxx
   ```
4. 验证数据库:
   ```sql
   SELECT avatar_url, username FROM profiles WHERE id = 'user_xxx';
   -- 应该看到更新后的值
   ```

#### 测试 2.3: session.created 事件

1. 在 staging 前端登录一个测试账号
2. 检查 staging 日志:
   ```bash
   # 应该记录登录活动
   ```
3. 验证数据库:
   ```sql
   SELECT * FROM user_activities
   WHERE user_id = 'user_xxx'
   AND activity_type = 'user_login'
   ORDER BY created_at DESC LIMIT 1;
   ```

### Step 3: 验证 Clerk Webhook 成功标准

- [ ] user.created 事件成功创建用户记录
- [ ] user.updated 事件成功同步用户信息
- [ ] session.created 事件成功记录登录日志
- [ ] session.ended 事件成功记录登出日志
- [ ] Webhook 签名验证通过 (无 400 Invalid signature 错误)
- [ ] Clerk Dashboard 显示 webhook 状态为 "Healthy"

---

## Stripe Webhook 测试

### Step 1: 配置 Staging Webhook

1. 访问 https://dashboard.stripe.com/test/webhooks
2. 点击 **"Add endpoint"**
3. 配置端点:
   ```
   Endpoint URL: https://your-staging-domain.com/api/v2/webhooks/stripe
   Events to send: Select events
   ```
4. 选择以下事件:
   - ✅ `checkout.session.completed`
   - ✅ `invoice.payment_succeeded`
   - ✅ `customer.subscription.deleted`
   - ✅ `customer.subscription.updated`
5. 点击 **"Add endpoint"**
6. 复制 **Signing secret** (以 `whsec_` 开头)
7. 更新 staging 环境变量:
   ```bash
   STRIPE_WEBHOOK_SECRET=whsec_新的signing_secret
   ```
8. 重启 staging 服务

### Step 2: 测试 Stripe Webhook

#### 测试 2.1: checkout.session.completed - 积分购买

1. 在 staging 前端点击 **"购买 100 积分"**
2. 使用 Stripe 测试卡号完成支付:
   ```
   卡号: 4242 4242 4242 4242
   有效期: 任意未来日期 (如 12/34)
   CVC: 任意 3 位数字 (如 123)
   ```
3. 检查 staging 日志:
   ```bash
   ✅ Checkout completed: credits_added for user_xxx
   ```
4. 验证数据库:
   ```sql
   SELECT credits_permanent FROM profiles WHERE id = 'user_xxx';
   -- 应该增加 100 积分

   SELECT * FROM credits_history
   WHERE user_id = 'user_xxx'
   AND change_type = 'topup_purchase'
   ORDER BY created_at DESC LIMIT 1;
   -- 应该有记录
   ```

#### 测试 2.2: checkout.session.completed - 订阅开通

1. 在 staging 前端点击 **"订阅 Starter 计划"**
2. 使用测试卡完成支付
3. 检查 staging 日志:
   ```bash
   ✅ Checkout completed: subscription_started for user_xxx, plan: starter
   ```
4. 验证数据库:
   ```sql
   SELECT tier, credits_monthly, subscription_status
   FROM profiles WHERE id = 'user_xxx';
   -- tier 应该是 'starter'
   -- credits_monthly 应该是 500
   -- subscription_status 应该是 'active'
   ```

#### 测试 2.3: invoice.payment_succeeded - 订阅续费

1. 在 Stripe Dashboard 中手动触发测试订阅的续费:
   - 进入 **Customers**
   - 找到测试用户
   - 点击订阅 (Subscription)
   - 点击 **"..."** → **"Update subscription"** → **"Renew now"**
2. 检查 staging 日志:
   ```bash
   ✅ Invoice payment succeeded: credits_refreshed for user_xxx
   ```
3. 验证数据库:
   ```sql
   SELECT credits_monthly FROM profiles WHERE id = 'user_xxx';
   -- 月度积分应该被刷新 (重置为 500 或 1000)

   SELECT * FROM credits_history
   WHERE user_id = 'user_xxx'
   AND change_type = 'monthly_refresh'
   ORDER BY created_at DESC LIMIT 1;
   ```

#### 测试 2.4: customer.subscription.deleted - 订阅取消

1. 在 Stripe Dashboard 中取消测试订阅:
   - 进入 **Customers** → 找到测试用户 → 订阅
   - 点击 **"Cancel subscription"** → **"Cancel immediately"**
2. 检查 staging 日志:
   ```bash
   ✅ Subscription ended for user_xxx
   ```
3. 验证数据库:
   ```sql
   SELECT tier, subscription_status FROM profiles WHERE id = 'user_xxx';
   -- tier 应该降级为 'free'
   -- subscription_status 应该是 'inactive' 或 'canceled'
   ```

### Step 3: 测试 Webhook 幂等性

**目的**: 验证重复 webhook 不会导致重复处理

1. 在 Stripe Dashboard 中找到一个已处理的 webhook 事件
2. 点击 **"..."** → **"Resend webhook"**
3. 检查 staging 日志:
   ```bash
   [Webhook] Duplicate event ignored: evt_xxx (checkout.session.completed)
   ```
4. 验证数据库:
   ```sql
   SELECT * FROM webhook_events WHERE event_id = 'evt_xxx';
   -- 应该只有一条记录，processed_at 应该是第一次处理的时间
   ```

### Step 4: 验证 Stripe Webhook 成功标准

- [ ] 积分购买成功触发 `checkout.session.completed`
- [ ] 订阅开通成功触发 `checkout.session.completed`
- [ ] 订阅续费成功触发 `invoice.payment_succeeded`
- [ ] 订阅取消成功触发 `customer.subscription.deleted`
- [ ] Webhook 幂等性机制生效 (重复事件被忽略)
- [ ] Webhook 签名验证通过 (无 400 错误)
- [ ] Stripe Dashboard 显示 webhook 状态为成功 (绿色勾号)

---

## 常见问题排查

### 问题 1: Webhook 返回 400 Invalid signature

**可能原因**:
- `CLERK_WEBHOOK_SECRET` 或 `STRIPE_WEBHOOK_SECRET` 配置错误
- 环境变量更新后未重启服务

**解决方案**:
1. 检查环境变量是否正确:
   ```bash
   echo $CLERK_WEBHOOK_SECRET
   echo $STRIPE_WEBHOOK_SECRET
   ```
2. 重新复制 Signing Secret 并更新环境变量
3. 重启服务:
   ```bash
   # Railway
   railway up

   # Docker
   docker-compose restart api
   ```

### 问题 2: Webhook 返回 500 Internal Server Error

**排查步骤**:
1. 查看 staging 日志:
   ```bash
   # Railway
   railway logs

   # Docker
   docker logs decodables-api -f
   ```
2. 检查数据库连接是否正常
3. 检查依赖服务是否可用 (Supabase, Stripe API)

### 问题 3: Webhook 成功但数据库无变化

**排查步骤**:
1. 确认 webhook payload 中的 `user_id` 或 `customer_id` 存在
2. 检查数据库中是否有对应的用户记录
3. 查看日志中的详细错误信息

### 问题 4: Clerk webhook 创建了重复用户

**可能原因**:
- `user.created` 事件触发了多次
- JIT 用户创建逻辑未生效

**解决方案**:
- 检查 `search_users(email)` 逻辑是否正常
- 验证数据库 `profiles` 表的 `email` 字段是否有唯一约束

---

## 性能监控

### 监控指标

在 staging 测试期间，监控以下指标:

1. **Webhook 响应时间**
   - 目标: < 2 秒
   - 检查: Clerk/Stripe Dashboard 中的 webhook 日志

2. **Webhook 成功率**
   - 目标: > 99%
   - 检查: Clerk/Stripe Dashboard 中的 webhook 统计

3. **数据库写入延迟**
   - 目标: < 500ms
   - 检查: Staging 日志中的处理时间

### 监控工具

推荐使用以下工具监控 webhook:

- **Sentry**: 捕获 webhook 处理错误
- **DataDog / New Relic**: 监控 webhook 响应时间
- **Stripe Dashboard**: 查看 webhook 发送历史
- **Clerk Dashboard**: 查看 webhook 发送历史

---

## 切换到生产环境

### 前提条件

在切换生产环境之前，确保:

- [x] Staging 环境所有测试通过
- [x] Webhook 幂等性机制验证通过
- [x] 无 500 错误或签名验证失败
- [x] 数据库数据正确更新
- [x] 性能指标达标

### 切换步骤

#### 1. 更新 Clerk 生产环境

1. 访问 https://dashboard.clerk.com (切换到生产环境)
2. 进入 **Webhooks**
3. 添加新端点:
   ```
   Endpoint URL: https://your-production-domain.com/api/v2/webhooks/clerk
   ```
4. 订阅事件 (同 staging)
5. 复制 Signing Secret
6. 更新生产环境变量:
   ```bash
   CLERK_WEBHOOK_SECRET=whsec_生产环境secret
   ```
7. **保留旧端点**: 暂时不要删除 `/api/webhooks/clerk`，观察 7 天

#### 2. 更新 Stripe 生产环境

1. 访问 https://dashboard.stripe.com/webhooks (切换到 Live mode)
2. 添加新端点:
   ```
   Endpoint URL: https://your-production-domain.com/api/v2/webhooks/stripe
   ```
3. 选择事件 (同 staging)
4. 复制 Signing Secret
5. 更新生产环境变量:
   ```bash
   STRIPE_WEBHOOK_SECRET=whsec_生产环境secret
   ```
6. **保留旧端点**: 暂时不要删除 `/api/webhooks/stripe`，观察 7 天

#### 3. 观察期 (7 天)

- 监控 v2 webhook 成功率
- 对比 v1 和 v2 的流量
- 确认 v2 处理所有事件

#### 4. 废弃 v1 端点 (7 天后)

1. 在 Clerk/Stripe Dashboard 中删除 v1 端点
2. 在代码中标记 v1 端点为 deprecated
3. 30 天后完全移除 v1 端点代码

---

## 回滚计划

如果 v2 出现问题，快速回滚步骤:

1. **停用 v2 端点**:
   - 在 Clerk/Stripe Dashboard 中禁用 v2 端点
   - 启用 v1 端点

2. **回滚代码** (如果必要):
   ```bash
   git revert <commit_hash>
   railway up  # 或其他部署命令
   ```

3. **验证 v1 恢复**:
   - 测试用户注册
   - 测试支付流程
   - 检查日志确认 v1 正常工作

---

## 测试清单

复制此清单，在测试时逐项勾选:

### Clerk Webhook v2

- [ ] staging 环境已配置 v2 端点
- [ ] `CLERK_WEBHOOK_SECRET` 已更新
- [ ] user.created 事件测试通过
- [ ] user.updated 事件测试通过
- [ ] session.created 事件测试通过
- [ ] session.ended 事件测试通过
- [ ] 签名验证正常 (无 400 错误)
- [ ] Clerk Dashboard 显示 webhook 健康

### Stripe Webhook v2

- [ ] staging 环境已配置 v2 端点
- [ ] `STRIPE_WEBHOOK_SECRET` 已更新
- [ ] checkout.session.completed (积分购买) 测试通过
- [ ] checkout.session.completed (订阅开通) 测试通过
- [ ] invoice.payment_succeeded (续费) 测试通过
- [ ] customer.subscription.deleted (取消) 测试通过
- [ ] Webhook 幂等性测试通过
- [ ] 签名验证正常 (无 400 错误)
- [ ] Stripe Dashboard 显示 webhook 成功

### 性能与稳定性

- [ ] Webhook 响应时间 < 2s
- [ ] Webhook 成功率 > 99%
- [ ] 数据库数据正确更新
- [ ] 无内存泄漏或性能问题

### 生产环境准备

- [ ] 所有 staging 测试通过
- [ ] 回滚计划已准备
- [ ] 监控告警已配置
- [ ] 团队已通知切换计划

---

## 支持与反馈

如有问题，请联系:
- **技术支持**: tech-support@makedecodables.com
- **Slack 频道**: #backend-team
- **文档问题**: 在 GitHub 提 Issue
