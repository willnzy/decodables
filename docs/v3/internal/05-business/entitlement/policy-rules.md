# Entitlement Policy Rules

> 权益策略规则

**验证状态**: 🟢 已验证  
**同步范围**: [fullstack]

---

## 一、概述

权益策略规则定义了系统中各种权限的判断逻辑和优先级。

---

## 二、权限判断优先级

```
┌─────────────────────────────────────────────────────────────────┐
│                    权限判断优先级                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  优先级从高到低:                                                 │
│                                                                 │
│  1. Kill Switch (全局禁用)                                      │
│     │  ↓ 如果启用，直接返回 false                               │
│     │                                                           │
│  2. User Override (用户级覆盖)                                  │
│     │  ↓ 管理员为特定用户设置的权限                             │
│     │                                                           │
│  3. Tier Permission (层级权限)                                  │
│     │  ↓ 用户所属 Tier 的默认权限                               │
│     │                                                           │
│  4. Feature Flag Variant (功能标记)                             │
│     │  ↓ A/B 测试或灰度发布的权限                               │
│     │                                                           │
│  5. Default Value (默认值)                                      │
│        ↓ 如果以上都没有匹配，使用默认值                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、规则类型

### 3.1 Kill Switch 规则

**用途**: 紧急禁用某功能

```python
class KillSwitchRule:
    """Kill Switch 规则"""
    
    def evaluate(self, feature_key: str) -> Optional[bool]:
        """
        检查 Kill Switch 是否启用
        
        Returns:
            True: 功能被禁用
            None: 没有 Kill Switch，继续下一个规则
        """
        kill_switch = self.get_kill_switch(feature_key)
        
        if kill_switch and kill_switch.is_enabled:
            return False  # 禁用功能
        
        return None  # 继续下一个规则
```

**数据结构**:

```sql
-- Kill Switch 存储在 feature_flags 表
SELECT * FROM feature_flags 
WHERE key = 'kill_switch_{feature}'
  AND flag_type = 'boolean'
  AND environment = 'production';
```

### 3.2 User Override 规则

**用途**: 为特定用户覆盖权限

```python
class UserOverrideRule:
    """用户覆盖规则"""
    
    def evaluate(self, user_id: UUID, feature_key: str) -> Optional[bool]:
        """
        检查用户是否有特定覆盖
        
        场景:
        - VIP 用户提前体验新功能
        - 问题用户禁止使用某功能
        - 测试账号获得所有权限
        """
        override = self.get_user_override(user_id, feature_key)
        
        if override:
            return override.enabled
        
        return None  # 继续下一个规则
```

**数据结构**:

```sql
CREATE TABLE feature_flag_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    flag_key VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL,
    reason TEXT,
    expires_at TIMESTAMPTZ,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, flag_key)
);
```

### 3.3 Tier Permission 规则

**用途**: 基于用户 Tier 判断权限

```python
class TierPermissionRule:
    """Tier 权限规则"""
    
    # Tier 权限矩阵
    TIER_PERMISSIONS = {
        't1': {
            'ai_generation': True,
            'export_pdf': False,
            'priority_support': False,
            'custom_fonts': False,
            'watermark_removal': False,
        },
        't2': {
            'ai_generation': True,
            'export_pdf': True,
            'priority_support': False,
            'custom_fonts': True,
            'watermark_removal': True,
        },
        't3': {
            'ai_generation': True,
            'export_pdf': True,
            'priority_support': True,
            'custom_fonts': True,
            'watermark_removal': True,
        },
    }
    
    def evaluate(self, user_tier: str, feature_key: str) -> Optional[bool]:
        """
        基于 Tier 判断权限
        """
        permissions = self.TIER_PERMISSIONS.get(user_tier, {})
        
        if feature_key in permissions:
            return permissions[feature_key]
        
        return None  # 功能不在 Tier 权限范围内
```

### 3.4 Feature Flag 规则

**用途**: A/B 测试和灰度发布

```python
class FeatureFlagRule:
    """Feature Flag 规则"""
    
    def evaluate(self, user_id: UUID, feature_key: str) -> Optional[bool]:
        """
        基于 Feature Flag 判断
        
        支持类型:
        - boolean: 全局开关
        - percentage: 百分比灰度
        - segment: 用户分群
        - experiment: A/B 实验
        """
        flag = self.get_feature_flag(feature_key)
        
        if not flag or not flag.is_enabled:
            return None
        
        match flag.flag_type:
            case 'boolean':
                return flag.value
            case 'percentage':
                return self.evaluate_percentage(user_id, flag)
            case 'segment':
                return self.evaluate_segment(user_id, flag)
            case 'experiment':
                return self.evaluate_experiment(user_id, flag)
        
        return None
    
    def evaluate_percentage(self, user_id: UUID, flag) -> bool:
        """百分比灰度"""
        hash_input = f"{user_id}:{flag.key}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = hash_value % 100
        return bucket < flag.percentage
```

---

## 四、配额规则

### 4.1 积分配额

```python
class CreditsQuotaRule:
    """积分配额规则"""
    
    TIER_CREDITS = {
        't1': {'monthly': 0, 'signup_bonus': 100},
        't2': {'monthly': 100, 'signup_bonus': 0},
        't3': {'monthly': 200, 'signup_bonus': 0},
    }
    
    def check_quota(self, user: User, cost: int) -> QuotaResult:
        """
        检查用户积分是否足够
        """
        total_credits = user.credits_monthly + user.credits_permanent
        
        if total_credits < cost:
            return QuotaResult(
                allowed=False,
                reason='insufficient_credits',
                current=total_credits,
                required=cost
            )
        
        return QuotaResult(allowed=True)
```

### 4.2 存储配额

```python
class StorageQuotaRule:
    """存储配额规则"""
    
    TIER_STORAGE = {
        't1': {'max_mb': 100, 'max_projects': 3},
        't2': {'max_mb': 1024, 'max_projects': 20},
        't3': {'max_mb': 5120, 'max_projects': 100},
    }
    
    def check_quota(self, user: User, file_size_mb: float) -> QuotaResult:
        """
        检查存储配额
        """
        limits = self.TIER_STORAGE[user.tier]
        current_usage = await self.get_storage_usage(user.id)
        
        if current_usage + file_size_mb > limits['max_mb']:
            return QuotaResult(
                allowed=False,
                reason='storage_limit_exceeded',
                current=current_usage,
                limit=limits['max_mb']
            )
        
        return QuotaResult(allowed=True)
```

### 4.3 速率配额

```python
class RateLimitRule:
    """速率限制规则"""
    
    TIER_RATE_LIMITS = {
        't1': {'ai_calls_per_day': 10, 'api_calls_per_minute': 30},
        't2': {'ai_calls_per_day': 50, 'api_calls_per_minute': 60},
        't3': {'ai_calls_per_day': 200, 'api_calls_per_minute': 120},
    }
    
    async def check_rate_limit(self, user: User, action: str) -> QuotaResult:
        """
        检查速率限制
        """
        limits = self.TIER_RATE_LIMITS[user.tier]
        
        if action == 'ai_call':
            key = f"rate:{user.id}:ai_calls:{date.today()}"
            limit = limits['ai_calls_per_day']
        else:
            key = f"rate:{user.id}:api:{datetime.now().minute}"
            limit = limits['api_calls_per_minute']
        
        current = await self.redis.incr(key)
        
        if current > limit:
            return QuotaResult(
                allowed=False,
                reason='rate_limit_exceeded',
                retry_after=self.calculate_retry_after(key)
            )
        
        return QuotaResult(allowed=True)
```

---

## 五、组合规则

### 5.1 权限检查器

```python
class EntitlementChecker:
    """权益检查器 - 组合所有规则"""
    
    def __init__(self):
        self.rules = [
            KillSwitchRule(),
            UserOverrideRule(),
            TierPermissionRule(),
            FeatureFlagRule(),
        ]
    
    async def check_feature(
        self, 
        user: User, 
        feature_key: str,
        default: bool = False
    ) -> FeatureAccess:
        """
        检查用户是否有权限使用某功能
        """
        for rule in self.rules:
            result = await rule.evaluate(user, feature_key)
            
            if result is not None:
                return FeatureAccess(
                    allowed=result,
                    rule=rule.__class__.__name__,
                    feature=feature_key
                )
        
        # 所有规则都没有匹配，返回默认值
        return FeatureAccess(
            allowed=default,
            rule='default',
            feature=feature_key
        )
    
    async def check_quota(
        self, 
        user: User, 
        quota_type: str,
        **params
    ) -> QuotaResult:
        """
        检查用户配额
        """
        match quota_type:
            case 'credits':
                return await CreditsQuotaRule().check_quota(user, **params)
            case 'storage':
                return await StorageQuotaRule().check_quota(user, **params)
            case 'rate_limit':
                return await RateLimitRule().check_rate_limit(user, **params)
            case _:
                raise ValueError(f"Unknown quota type: {quota_type}")
```

### 5.2 使用示例

```python
# 检查功能权限
async def use_ai_generation(user: User, prompt: str):
    checker = EntitlementChecker()
    
    # 1. 检查功能权限
    access = await checker.check_feature(user, 'ai_generation')
    if not access.allowed:
        raise FeatureNotAllowedError(access.reason)
    
    # 2. 检查积分配额
    ai_cost = 5
    quota = await checker.check_quota(user, 'credits', cost=ai_cost)
    if not quota.allowed:
        raise InsufficientCreditsError(quota.required)
    
    # 3. 检查速率限制
    rate = await checker.check_quota(user, 'rate_limit', action='ai_call')
    if not rate.allowed:
        raise RateLimitError(retry_after=rate.retry_after)
    
    # 4. 执行功能
    result = await ai_service.generate(prompt)
    
    # 5. 扣减积分
    await credits_service.deduct(user.id, ai_cost, 'ai_generation')
    
    return result
```

---

## 六、特殊规则

### 6.1 试用期规则

```python
class TrialPeriodRule:
    """试用期规则"""
    
    TRIAL_FEATURES = ['export_pdf', 'custom_fonts', 'priority_support']
    TRIAL_DURATION_DAYS = 7
    
    def is_in_trial(self, user: User) -> bool:
        """检查用户是否在试用期"""
        if user.tier != 't1':
            return False
        
        days_since_signup = (datetime.now() - user.created_at).days
        return days_since_signup <= self.TRIAL_DURATION_DAYS
    
    def evaluate(self, user: User, feature_key: str) -> Optional[bool]:
        """试用期内可以使用部分高级功能"""
        if not self.is_in_trial(user):
            return None
        
        if feature_key in self.TRIAL_FEATURES:
            return True
        
        return None
```

### 6.2 促销规则

```python
class PromotionRule:
    """促销规则"""
    
    async def evaluate(self, user: User, feature_key: str) -> Optional[bool]:
        """检查用户是否有激活的促销"""
        promotions = await self.get_active_promotions(user.id)
        
        for promo in promotions:
            if feature_key in promo.granted_features:
                return True
        
        return None
```

---

## 七、规则缓存

### 7.1 缓存策略

```python
class RuleCache:
    """规则缓存"""
    
    # 缓存 TTL (秒)
    CACHE_TTL = {
        'kill_switch': 60,      # 1 分钟 (需要快速生效)
        'user_override': 300,   # 5 分钟
        'tier_permission': 3600,# 1 小时 (很少变化)
        'feature_flag': 300,    # 5 分钟
    }
    
    async def get_cached(self, rule_type: str, key: str) -> Optional[Any]:
        """获取缓存的规则结果"""
        cache_key = f"rule:{rule_type}:{key}"
        return await self.redis.get(cache_key)
    
    async def set_cached(self, rule_type: str, key: str, value: Any):
        """缓存规则结果"""
        cache_key = f"rule:{rule_type}:{key}"
        ttl = self.CACHE_TTL.get(rule_type, 300)
        await self.redis.setex(cache_key, ttl, value)
```

### 7.2 缓存失效

```python
async def invalidate_rule_cache(rule_type: str, key: str = None):
    """
    使规则缓存失效
    
    触发时机:
    - 管理员修改 Feature Flag
    - 管理员添加 User Override
    - 用户 Tier 变更
    """
    if key:
        await redis.delete(f"rule:{rule_type}:{key}")
    else:
        # 删除该类型所有缓存
        pattern = f"rule:{rule_type}:*"
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
```

---

## 八、相关文档

- [权益系统设计](./system-design.md)
- [权限矩阵](./permission-matrix.md)
- [Feature Flag 引擎](../../02-standards/feature-flag-engine.md)
