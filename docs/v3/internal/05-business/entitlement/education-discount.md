# 教育优惠

> Education Discount - 教育用户优惠政策

**验证状态**: 🟡 待验证  
**同步范围**: [fullstack]

---

## 一、概述

为教育工作者和学生提供优惠订阅价格，支持教育事业发展。

---

## 二、适用对象

### 2.1 教育工作者

| 类型 | 验证方式 |
|------|----------|
| K-12 教师 | 学校邮箱 / 教师证 |
| 大学教授 | .edu 邮箱 |
| 学校管理员 | 官方证明 |
| 教育培训师 | 机构认证 |

### 2.2 学生

| 类型 | 验证方式 |
|------|----------|
| 在校学生 | .edu 邮箱 |
| 在校学生 | 学生证照片 |
| 在校学生 | 第三方验证 (SheerID) |

---

## 三、优惠方案

### 3.1 个人教育优惠

| 计划 | 原价 | 教育价 | 折扣 |
|------|------|--------|------|
| Starter (月付) | $6.9/月 | $3.45/月 | 50% |
| Pro (月付) | $9.9/月 | $4.95/月 | 50% |
| Starter (年付) | $82.8/年 | $41.4/年 | 50% |
| Pro (年付) | $118.8/年 | $59.4/年 | 50% |

### 3.2 学校批量许可

| 规模 | 折扣 | 额外权益 |
|------|------|----------|
| 10-49 席位 | 60% off | 管理后台 |
| 50-199 席位 | 70% off | 专属支持 |
| 200+ 席位 | 联系商务 | 定制方案 |

---

## 四、验证流程

### 4.1 邮箱验证

```python
async def verify_edu_email(email: str) -> VerificationResult:
    """
    验证教育邮箱
    
    支持的域名:
    - .edu (美国)
    - .edu.cn (中国)
    - .ac.uk (英国)
    - .edu.au (澳大利亚)
    - 其他官方教育域名
    """
    domain = email.split('@')[-1].lower()
    
    # 检查教育域名
    edu_suffixes = ['.edu', '.edu.cn', '.ac.uk', '.edu.au', '.ac.jp']
    is_edu = any(domain.endswith(suffix) for suffix in edu_suffixes)
    
    if is_edu:
        return VerificationResult(
            verified=True,
            method='email_domain',
            valid_until=datetime.utcnow() + timedelta(days=365)
        )
    
    # 检查已知学校域名列表
    if domain in KNOWN_SCHOOL_DOMAINS:
        return VerificationResult(
            verified=True,
            method='known_school',
            valid_until=datetime.utcnow() + timedelta(days=365)
        )
    
    return VerificationResult(verified=False, reason='NOT_EDU_EMAIL')
```

### 4.2 证件验证

```python
async def submit_edu_verification(
    user_id: UUID,
    verification_type: str,  # student_id / teacher_id / school_letter
    document_url: str
) -> VerificationRequest:
    """
    提交教育身份验证
    
    流程:
    1. 用户上传证件
    2. 创建验证请求
    3. 人工审核 (1-3 个工作日)
    4. 审核通过后激活优惠
    """
    request = await create_verification_request(
        user_id=user_id,
        type='education',
        subtype=verification_type,
        document_url=document_url,
        status='pending'
    )
    
    # 发送审核通知给管理员
    await notify_admin_verification_request(request.id)
    
    return request
```

### 4.3 第三方验证 (SheerID)

```python
async def verify_with_sheerid(user_id: UUID, sheerid_token: str) -> bool:
    """
    使用 SheerID 验证教育身份
    
    SheerID 提供:
    - 实时学生身份验证
    - 全球学校数据库
    - 防欺诈保护
    """
    result = await sheerid_client.verify(token=sheerid_token)
    
    if result.verified:
        await update_user_edu_status(
            user_id=user_id,
            edu_verified=True,
            edu_type=result.segment,  # student/teacher
            valid_until=result.expiration_date
        )
        return True
    
    return False
```

---

## 五、数据模型

### 5.1 教育验证记录

```sql
CREATE TABLE edu_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    verification_type VARCHAR(50) NOT NULL,  -- email/document/sheerid
    edu_type VARCHAR(50),                    -- student/teacher/admin
    institution_name VARCHAR(200),
    document_url TEXT,
    status VARCHAR(20) DEFAULT 'pending',    -- pending/approved/rejected
    verified_at TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    reviewer_id UUID,
    reviewer_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.2 用户教育状态

```python
class UserEduStatus:
    is_edu_verified: bool
    edu_type: Optional[str]          # student/teacher
    institution_name: Optional[str]
    edu_valid_until: Optional[datetime]
    edu_discount_rate: float         # 0.5 = 50% off
```

---

## 六、优惠应用

### 6.1 Stripe 折扣

```python
async def apply_edu_discount(user_id: UUID, price_id: str) -> str:
    """
    应用教育折扣到 Stripe 订阅
    """
    # 验证教育身份
    edu_status = await get_user_edu_status(user_id)
    if not edu_status.is_edu_verified:
        raise NotEduVerifiedError()
    
    if edu_status.edu_valid_until < datetime.utcnow():
        raise EduVerificationExpiredError()
    
    # 创建或获取教育折扣券
    coupon = await get_or_create_edu_coupon(
        percent_off=50,
        duration='forever',
        metadata={'type': 'education'}
    )
    
    # 创建订阅时应用折扣
    return coupon.id
```

### 6.2 价格显示

```typescript
// 前端价格显示
function EducationPricing({ isEduVerified }: { isEduVerified: boolean }) {
  const plans = [
    { name: 'Starter', price: 6.9, eduPrice: 3.45 },
    { name: 'Pro', price: 9.9, eduPrice: 4.95 },
  ];
  
  return (
    <div>
      {plans.map(plan => (
        <PlanCard key={plan.name}>
          {isEduVerified ? (
            <>
              <OriginalPrice strikethrough>${plan.price}/mo</OriginalPrice>
              <EduPrice>${plan.eduPrice}/mo</EduPrice>
              <Badge>Education 50% off</Badge>
            </>
          ) : (
            <Price>${plan.price}/mo</Price>
          )}
        </PlanCard>
      ))}
    </div>
  );
}
```

---

## 七、续期与过期

### 7.1 年度重新验证

```python
async def check_edu_renewal(user_id: UUID):
    """
    检查教育身份是否需要重新验证
    
    规则:
    - 每年需要重新验证
    - 到期前 30 天提醒
    - 到期后 14 天宽限期
    """
    edu_status = await get_user_edu_status(user_id)
    
    if not edu_status.is_edu_verified:
        return
    
    days_until_expiry = (edu_status.edu_valid_until - datetime.utcnow()).days
    
    if days_until_expiry <= 30 and days_until_expiry > 0:
        # 发送续期提醒
        await send_edu_renewal_reminder(user_id, days_until_expiry)
    
    elif days_until_expiry <= 0 and days_until_expiry > -14:
        # 宽限期
        await send_edu_grace_period_warning(user_id)
    
    elif days_until_expiry <= -14:
        # 过期，移除教育优惠
        await remove_edu_discount(user_id)
```

### 7.2 过期处理

```python
async def remove_edu_discount(user_id: UUID):
    """
    移除教育优惠
    
    流程:
    1. 更新订阅价格到原价
    2. 发送通知
    3. 提供重新验证入口
    """
    # 1. 更新 Stripe 订阅
    subscription = await get_user_subscription(user_id)
    if subscription and subscription.discount:
        await stripe.Subscription.modify(
            subscription.id,
            discounts=[]  # 移除折扣
        )
    
    # 2. 更新本地状态
    await update_user_edu_status(
        user_id=user_id,
        edu_verified=False
    )
    
    # 3. 发送通知
    await send_edu_expired_notification(user_id)
```

---

## 八、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/edu/status` | 获取教育验证状态 |
| POST | `/api/v1/edu/verify/email` | 邮箱验证 |
| POST | `/api/v1/edu/verify/document` | 提交证件验证 |
| POST | `/api/v1/edu/verify/sheerid` | SheerID 验证 |
| GET | `/api/v1/edu/pricing` | 获取教育优惠价格 |

---

## 九、相关文档

- [促销规则](./promotions.md)
- [Billing 架构](../../04-engineering/modules/billing/architecture.md)
- [权益策略规则](./policy-rules.md)
