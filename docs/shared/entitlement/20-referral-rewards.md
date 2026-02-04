# 邀请奖励完整规则

> **版本**: v2.0
> **日期**: 2026-02-04
> **状态**: 产品确认

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [15-credits-lifecycle.md](./15-credits-lifecycle.md) | 积分生命周期 |
| [19-promotions.md](./19-promotions.md) | 促销活动 |

---

## 一、奖励机制

### 1.1 双向奖励

| 角色 | 奖励 | 发放条件 |
|------|------|----------|
| **邀请人** | 50 积分 | 被邀请人完成注册 |
| **被邀请人** | 50 积分 | 完成注册 |

### 1.2 奖励类型

邀请奖励积分类型为 `gift`，按积分扣费优先级排在第 3 位。

---

## 二、邀请流程

### 2.1 生成邀请链接

```
1. 用户进入 "邀请好友" 页面
2. 系统生成专属邀请码
3. 用户获得邀请链接: https://makedecodables.com/invite/{code}
4. 用户分享链接
```

### 2.2 被邀请人注册

```
1. 被邀请人点击链接
2. 跳转到注册页面 (带邀请码)
3. 完成注册
4. 双方获得奖励
```

### 2.3 奖励发放时机

```
被邀请人完成注册后立即:
1. 被邀请人账户 +50 gift 积分
2. 邀请人账户 +50 gift 积分
3. 双方收到通知
```

---

## 三、邀请限制

### 3.1 邀请人限制

| 限制项 | 规则 |
|--------|------|
| 账户状态 | 必须是激活状态 |
| 最低 Tier | 无限制 (t1 也可邀请) |
| 每日邀请上限 | 无限制 |
| 总邀请上限 | 无限制 |
| 单日奖励上限 | 500 积分 (10 人) |
| 总奖励上限 | 5000 积分 (100 人) |

### 3.2 被邀请人限制

| 限制项 | 规则 |
|--------|------|
| 必须是新用户 | 从未注册过 |
| 邮箱验证 | 必须完成邮箱验证 |
| 同一设备 | 同一设备只能被邀请一次 |
| 同一 IP | 同一 IP 24 小时内最多 3 次 |

---

## 四、防滥用机制

### 4.1 检测规则

| 检测项 | 规则 | 处理 |
|--------|------|------|
| 设备指纹 | 同一设备多次注册 | 拒绝奖励 |
| IP 地址 | 同一 IP 短时间大量注册 | 人工审核 |
| 邮箱模式 | 批量生成的邮箱 (如 test1@, test2@) | 人工审核 |
| 注册后行为 | 注册后立即闲置 | 延迟发放 |

### 4.2 奖励状态

| 状态 | 说明 |
|------|------|
| pending | 待审核 (触发风控) |
| approved | 已批准，奖励已发放 |
| rejected | 已拒绝，不发放奖励 |
| expired | 已过期 (未完成验证) |

### 4.3 延迟发放

对于触发风控的邀请，采用延迟发放:
```
被邀请人注册 → 7 天观察期 → 正常使用 → 发放奖励
```

---

## 五、邀请码系统

### 5.1 邀请码规则

| 属性 | 规则 |
|------|------|
| 长度 | 8 字符 |
| 字符 | 大写字母 + 数字 |
| 生成 | 首次访问邀请页面时自动生成 |
| 有效期 | 永久有效 |

### 5.2 邀请链接格式

```
标准链接: https://makedecodables.com/invite/ABC12345
短链接: https://md.link/ABC12345 (可选)
```

---

## 六、数据结构

### 6.1 邀请记录表

```sql
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id TEXT NOT NULL REFERENCES profiles(user_id),
    referee_id TEXT REFERENCES profiles(user_id), -- 注册后填充
    referral_code VARCHAR(20) NOT NULL,
    referee_email TEXT, -- 被邀请人邮箱 (可选预填)
    status VARCHAR(20) DEFAULT 'pending', -- pending, completed, rejected, expired
    referrer_reward INT DEFAULT 50,
    referee_reward INT DEFAULT 50,
    reward_status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected
    risk_flags TEXT[], -- 风控标记
    device_fingerprint TEXT,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    reward_issued_at TIMESTAMPTZ
);

-- 用户邀请码表
CREATE TABLE IF NOT EXISTS referral_codes (
    user_id UUID PRIMARY KEY REFERENCES profiles(id),
    code VARCHAR(20) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX idx_referrals_code ON referrals(referral_code);
CREATE INDEX idx_referral_codes_code ON referral_codes(code);
```

---

## 七、用户界面

### 7.1 邀请页面

```
┌─────────────────────────────────┐
│ 邀请好友，双方各得 50 积分       │
│                                 │
│ 您的专属邀请链接:                │
│ ┌─────────────────────────────┐ │
│ │ https://md.link/ABC12345   │ │
│ └─────────────────────────────┘ │
│ [复制链接]                       │
│                                 │
│ ─────────────────────────────── │
│ 邀请记录                         │
│                                 │
│ 已邀请: 5 人                     │
│ 已获得: 250 积分                 │
│                                 │
│ 最近邀请:                        │
│ • j***@gmail.com - 已完成       │
│ • t***@outlook.com - 待验证     │
└─────────────────────────────────┘
```

### 7.2 奖励通知

```
邀请人通知:
"🎉 您邀请的好友 j***@gmail.com 已完成注册，
您获得 50 积分奖励！"

被邀请人通知:
"🎉 欢迎加入！感谢您通过好友邀请注册，
您获得 50 积分奖励！"
```

---

## 八、API 接口

```python
# 获取/生成邀请码
GET /api/v1/referrals/code
Response: {
    "code": "ABC12345",
    "link": "https://makedecodables.com/invite/ABC12345"
}

# 验证邀请码 (注册时)
POST /api/v1/referrals/validate
{
    "code": "ABC12345"
}

# 获取邀请统计
GET /api/v1/referrals/stats
Response: {
    "total_referrals": 5,
    "completed_referrals": 4,
    "total_rewards": 200,
    "pending_rewards": 50
}

# 获取邀请记录
GET /api/v1/referrals?limit=20&offset=0
```

---

## 九、监控指标

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| 日均邀请数 | 异常波动 >100% | 可能存在刷单 |
| 邀请转化率 | < 20% | 邀请效果差 |
| 风控拦截率 | > 30% | 需要调整规则 |

---

**END OF DOCUMENT**
