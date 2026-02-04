# 学生/教育优惠

> **版本**: v2.0
> **日期**: 2026-02-04
> **状态**: 产品确认
> **参考**: Adobe / GitHub Education

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [01-permission-matrix.md](./01-permission-matrix.md) | 权限矩阵 |
| [19-promotions.md](./19-promotions.md) | 促销活动 |

---

## 一、优惠政策

### 1.1 适用对象

| 对象 | 认证方式 |
|------|----------|
| 在校学生 | .edu 邮箱 / 学生证照片 |
| 教师 | .edu 邮箱 / 教师证照片 |
| 教育机构 | 机构证明 |

### 1.2 优惠内容

| Plan | 原价 | 教育价 | 折扣 |
|------|------|--------|------|
| Starter (t2) 月付 | $6.9 | $3.45 | 50% off |
| Starter (t2) 年付 | $69 | $34.5 | 50% off |
| Pro (t3) 月付 | $9.9 | $4.95 | 50% off |
| Pro (t3) 年付 | $99 | $49.5 | 50% off |

---

## 二、认证流程

### 2.1 .edu 邮箱认证 (自动)

```
1. 用户进入教育优惠页面
2. 输入 .edu 邮箱地址
3. 系统发送验证邮件
4. 用户点击验证链接
5. 认证完成，自动获得教育优惠资格
```

### 2.2 证件认证 (人工)

```
1. 用户进入教育优惠页面
2. 上传学生证/教师证照片
3. 提交审核
4. 人工审核 (1-3 个工作日)
5. 审核通过，获得教育优惠资格
```

### 2.3 机构认证

```
1. 机构管理员联系客服
2. 提交机构证明文件
3. 商务审核
4. 创建机构账户
5. 批量开通教育优惠
```

---

## 三、资格有效期

### 3.1 有效期规则

| 认证方式 | 初始有效期 | 续期方式 |
|----------|------------|----------|
| .edu 邮箱 | 1 年 | 每年重新验证邮箱 |
| 学生证 | 至证件有效期 | 上传新证件 |
| 教师证 | 1 年 | 每年重新提交 |
| 机构 | 合同期 | 续签合同 |

### 3.2 过期处理

```
过期前 30 天: 邮件提醒续期
过期前 7 天: 再次提醒
过期当天: 教育优惠失效
过期后: 下次续费按原价计算
```

---

## 四、使用规则

### 4.1 限制

| 限制项 | 规则 |
|--------|------|
| 每人限用 | 1 个账户 |
| 不可转让 | 不可将优惠转给他人 |
| 不可叠加 | 不与其他促销叠加 |
| 商业使用 | 禁止商业用途 |

### 4.2 违规处理

| 违规行为 | 处理方式 |
|----------|----------|
| 提供虚假证件 | 永久取消资格 + 补缴差价 |
| 多账户使用 | 取消资格 |
| 商业使用 | 取消资格 + 补缴差价 |

---

## 五、数据结构

### 5.1 教育认证表

```sql
CREATE TABLE IF NOT EXISTS education_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    verification_type VARCHAR(20) NOT NULL, -- edu_email, student_id, teacher_id, institution
    verification_data JSONB, -- 存储认证信息
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected, expired
    verified_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    reviewed_by UUID, -- 审核人 (人工审核时)
    review_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_edu_verifications_user ON education_verifications(user_id);
CREATE INDEX idx_edu_verifications_status ON education_verifications(status);
```

### 5.2 profiles 扩展

```sql
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS
    education_verified BOOLEAN DEFAULT FALSE;

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS
    education_expires_at TIMESTAMPTZ;
```

---

## 六、用户界面

### 6.1 教育优惠申请页面

```
┌─────────────────────────────────┐
│ 🎓 教育优惠                      │
│                                 │
│ 学生和教师享受 50% 优惠          │
│                                 │
│ 认证方式:                        │
│                                 │
│ ○ 使用 .edu 邮箱验证 (推荐)      │
│   [___________________@___.edu] │
│   [发送验证邮件]                 │
│                                 │
│ ○ 上传学生证/教师证              │
│   [选择文件...]                  │
│   [提交审核]                     │
│                                 │
└─────────────────────────────────┘
```

### 6.2 认证状态显示

```
认证中: "您的教育认证正在审核中，预计 1-3 个工作日"
已认证: "🎓 教育优惠已激活，有效期至 2027-02-04"
即将过期: "⚠️ 教育优惠将于 30 天后过期，请及时续期"
```

---

## 七、API 接口

```python
# 发送 .edu 邮箱验证
POST /api/v1/education/verify-email
{
    "email": "student@university.edu"
}

# 验证 .edu 邮箱 (点击链接后)
POST /api/v1/education/confirm-email
{
    "token": "verification_token"
}

# 上传证件
POST /api/v1/education/upload-document
Content-Type: multipart/form-data
{
    "document_type": "student_id",
    "file": <binary>
}

# 查询认证状态
GET /api/v1/education/status
Response: {
    "is_verified": true,
    "verification_type": "edu_email",
    "expires_at": "2027-02-04T00:00:00Z",
    "days_until_expiry": 365
}
```

---

## 八、监控指标

| 指标 | 说明 |
|------|------|
| 教育用户占比 | 教育优惠用户 / 总付费用户 |
| 认证通过率 | 通过 / 总申请 |
| 平均审核时长 | 人工审核耗时 |
| 续期率 | 续期成功 / 到期用户 |

---

**END OF DOCUMENT**
