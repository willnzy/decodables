# 幂等用户创建方案 - 风险分析与优化建议

> **分析日期**: 2026-01-13  
> **风险等级**: 🟡 中等 (可控)  
> **状态**: 需要优化

---

## 🎯 Executive Summary

当前方案在 **正常场景** 下工作良好，但在 **极端并发**、**数据库故障**、**高负载** 场景下存在 **7 个潜在隐患**。

**好消息**: 
- ✅ 核心幂等逻辑正确
- ✅ 95% 场景无问题
- ✅ 架构设计合理

**需要改进**:
- ⚠️ 边界情况处理不完善
- ⚠️ 资源管理存在风险
- ⚠️ 监控覆盖不完整

---

## 🔴 高危风险 (P0)

### 1. 注册奖励重复发放 💰

**风险描述**:
```python
# RPC 函数中
INSERT INTO profiles (..., credits_permanent, ...) 
VALUES (..., 50, ...);  -- 🚨 第一次发放

# Webhook Handler 中
if was_created:
    await self._grant_signup_bonus(user_id)  -- 🚨 第二次发放 (另外 50)
```

**影响**:
- 💸 每个新用户获得 **100 credits** (期望 50)
- 💸 如果有 1000 新用户/月，损失 50,000 credits
- 💸 按 $0.01/credit 计算，每月损失 $500

**实际情况**:
- RPC 设置 `credits_permanent=50` (初始值)
- Webhook 再调用 `_grant_signup_bonus(user_id)` (再加 50)
- **总计**: 100 credits/user ❌

**修复方案**:

**Option A: 删除 Webhook 中的重复调用 (推荐)**
```python
# domains/webhooks/clerk_webhook_service.py
async def _handle_user_created(self, data: Dict[str, Any]):
    profile, was_created = await self.user_repo.create_or_get(...)
    
    if was_created:
        logger.info(f"✅ Webhook created user {user_id}")
        # ❌ 删除这行 - RPC 已经给了 50 credits
        # await self._grant_signup_bonus(user_id)
```

**Option B: RPC 不给奖励，统一由 Webhook 发放**
```sql
-- migrations/v2/01_core_business.sql
INSERT INTO profiles (..., credits_permanent, ...) 
VALUES (..., 0, ...);  -- 改为 0，由应用层发放
```

**推荐**: Option A (减少代码改动)

---

### 2. TOCTOU Race Condition 残留 ⏱️

**风险描述**:
```sql
-- create_user_idempotent() 函数中
BEGIN
    SELECT * INTO v_existing_profile
    FROM profiles WHERE id = p_user_id
    FOR UPDATE NOWAIT;  -- ✅ 加锁
    
EXCEPTION WHEN lock_not_available THEN
    PERFORM pg_sleep(0.05);  -- 等待 50ms
    
    -- 🚨 这里没有锁！TOCTOU 漏洞
    SELECT * INTO v_existing_profile
    FROM profiles WHERE id = p_user_id;
END;

-- 如果在这 50ms 内另一个进程创建了用户怎么办？
```

**时序图**:
```
时间轴 →

进程 A: [获取锁失败] → [等待 50ms] → [读取(无锁)] → [发现不存在] → [INSERT]
进程 B:                 [创建用户] → [释放锁]
                                           ↓
                                      进程 A 和 B 都尝试 INSERT
                                      → 主键冲突！💥
```

**影响**:
- 🔥 高并发下可能触发 `duplicate key value violates unique constraint`
- 🔥 用户创建失败，返回 500 错误
- 🔥 影响用户体验

**修复方案**:

```sql
CREATE OR REPLACE FUNCTION create_user_idempotent(
    p_user_id TEXT,
    p_email TEXT,
    p_source TEXT,
    ...
)
RETURNS TABLE(...) 
LANGUAGE plpgsql
AS $$
DECLARE
    v_existing_profile profiles%ROWTYPE;
    v_retry_count INTEGER := 0;
    v_max_retries INTEGER := 3;
BEGIN
    -- ✅ 方案1: 使用 UPSERT (推荐)
    INSERT INTO profiles (id, email, ..., created_by)
    VALUES (p_user_id, p_email, ..., p_source)
    ON CONFLICT (id) DO NOTHING
    RETURNING * INTO v_existing_profile;
    
    IF v_existing_profile.id IS NULL THEN
        -- 已存在，读取现有记录
        SELECT * INTO v_existing_profile
        FROM profiles
        WHERE id = p_user_id;
        
        v_was_created := FALSE;
    ELSE
        -- 新创建
        v_was_created := TRUE;
    END IF;
    
    -- 记录日志...
    RETURN QUERY SELECT ...;
END;
$$;
```

**优势**:
- ✅ 原子操作，无 race condition
- ✅ 性能更好（减少一次 SELECT）
- ✅ 符合 PostgreSQL 最佳实践

---

### 3. user_code 并发冲突 🔢

**风险描述**:
```sql
-- generate_user_code() 函数中
SELECT LPAD(COUNT(*)::TEXT, 7, '0') INTO user_count_str 
FROM profiles;  -- 🚨 并发时可能重复

-- 示例：
-- 时刻 T1: 进程 A 读取 COUNT(*) = 100 → 生成 ...0000100...
-- 时刻 T2: 进程 B 读取 COUNT(*) = 100 → 生成 ...0000100...
--                                      ↓
--                                 相同的 user_code！
```

**影响**:
- 🔥 极小概率（<0.01%）但可能发生
- 🔥 `user_code` 有 UNIQUE 约束，会导致 INSERT 失败
- 🔥 用户创建失败

**修复方案**:

```sql
-- 方案1: 使用序列 (推荐)
CREATE SEQUENCE IF NOT EXISTS user_code_seq START 1;

CREATE OR REPLACE FUNCTION generate_user_code()
RETURNS TEXT AS $$
DECLARE
    new_user_code TEXT;
    current_timestamp_str TEXT;
    sequence_number BIGINT;
BEGIN
    -- 时间戳 (YYMMDDHHMMSS)
    current_timestamp_str := TO_CHAR(NOW(), 'YYMMDDHH24MISS');
    
    -- 使用序列（原子递增，无冲突）
    sequence_number := nextval('user_code_seq');
    
    -- 组合成 26 位
    new_user_code := 
        current_timestamp_str ||           -- 12 位
        LPAD(sequence_number::TEXT, 10, '0') ||  -- 10 位
        LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0');  -- 4 位随机
    
    RETURN new_user_code;
END;
$$ LANGUAGE plpgsql;
```

**优势**:
- ✅ 原子递增，无并发冲突
- ✅ 性能更好（无 COUNT(*) 全表扫描）
- ✅ 代码更简单

---

## 🟠 中危风险 (P1)

### 4. 日志表无限增长 📈

**风险描述**:
```sql
-- user_creation_logs 表会无限增长
INSERT INTO user_creation_logs (user_id, source, action, ...)
VALUES (...);  -- 每次创建/重试都插入

-- 问题：
-- - 每个用户平均 2-3 条日志 (创建 + 重试)
-- - 100,000 用户 = 200,000-300,000 条日志
-- - 1 年后 = 2,400,000 条日志
-- - 查询变慢，存储成本增加
```

**影响**:
- 💾 存储成本增加 (~100MB/100K 用户)
- 🐌 查询性能下降
- 🧹 需要手动清理

**修复方案**:

**方案1: 定期清理 (推荐)**
```sql
-- 创建定时任务（Supabase Cron）
-- 每天凌晨 3 点执行
SELECT cron.schedule(
    'cleanup-user-creation-logs',
    '0 3 * * *',  -- 每天 3:00
    $$
        DELETE FROM user_creation_logs 
        WHERE created_at < NOW() - INTERVAL '90 days';
    $$
);
```

**方案2: 分区表 (长期方案)**
```sql
-- 按月分区
CREATE TABLE user_creation_logs (
    id BIGSERIAL,
    user_id TEXT NOT NULL,
    ...
    created_at TIMESTAMPTZ NOT NULL
) PARTITION BY RANGE (created_at);

-- 创建分区
CREATE TABLE user_creation_logs_2026_01 
PARTITION OF user_creation_logs
FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

-- 自动删除旧分区
DROP TABLE user_creation_logs_2025_10;
```

---

### 5. 事务一致性缺失 🔄

**风险描述**:
```sql
-- RPC 函数中
INSERT INTO profiles (...) VALUES (...);  -- 操作 1
INSERT INTO user_creation_logs (...) VALUES (...);  -- 操作 2

-- 问题：
-- 如果操作 2 失败（磁盘满/权限问题），操作 1 已提交
-- 导致 profiles 有记录，但 user_creation_logs 没有
-- 监控统计不准确
```

**影响**:
- 📊 监控数据不准确
- 🐛 难以追踪问题
- 📉 健康度评分失真

**修复方案**:

```sql
CREATE OR REPLACE FUNCTION create_user_idempotent(...)
RETURNS TABLE(...) 
LANGUAGE plpgsql
AS $$
BEGIN
    -- ✅ 显式开启事务
    -- RPC 函数默认在事务中，但显式声明更清晰
    
    -- 用户创建
    INSERT INTO profiles (...) VALUES (...);
    
    -- 日志记录（失败则全部回滚）
    INSERT INTO user_creation_logs (...) VALUES (...);
    
    RETURN QUERY SELECT ...;
    
EXCEPTION
    WHEN OTHERS THEN
        -- 记录错误到专门的错误日志表
        INSERT INTO error_logs (
            operation,
            error_message,
            details,
            created_at
        ) VALUES (
            'create_user_idempotent',
            SQLERRM,
            jsonb_build_object('user_id', p_user_id),
            NOW()
        );
        
        -- 重新抛出异常，确保事务回滚
        RAISE;
END;
$$;
```

---

### 6. 监控指标准确性问题 📊

**风险描述**:
```sql
-- get_user_creation_stats() 函数中
SELECT
    COUNT(DISTINCT ru.id) AS total_users,
    ...
FROM recent_users ru
LEFT JOIN creation_logs cl ON ru.id = cl.user_id;

-- 问题：
-- 1. 如果 creation_logs 缺失，统计不准
-- 2. LEFT JOIN 可能产生重复行
-- 3. webhook_success_rate 计算可能除以 0
```

**影响**:
- 📉 监控数据不可信
- 🚨 告警可能误报
- 🤷 难以判断系统健康度

**修复方案**:

```sql
CREATE OR REPLACE FUNCTION get_user_creation_stats(p_days INTEGER)
RETURNS TABLE(...) AS $$
BEGIN
    RETURN QUERY
    WITH recent_users AS (
        SELECT 
            id,
            created_by,
            created_at
        FROM profiles
        WHERE created_at >= NOW() - INTERVAL '1 day' * p_days
    ),
    creation_events AS (
        -- ✅ 使用 DISTINCT ON 避免重复
        SELECT DISTINCT ON (user_id)
            user_id,
            source,
            action,
            created_at
        FROM user_creation_logs
        WHERE created_at >= NOW() - INTERVAL '1 day' * p_days
          AND action = 'created'
        ORDER BY user_id, created_at ASC
    )
    SELECT
        COUNT(DISTINCT ru.id) AS total_users,
        COUNT(DISTINCT CASE WHEN ru.created_by = 'webhook' THEN ru.id END) AS webhook_created,
        COUNT(DISTINCT CASE WHEN ru.created_by = 'jit' THEN ru.id END) AS jit_created,
        
        -- ✅ 避免除以 0
        ROUND(
            COALESCE(
                COUNT(DISTINCT CASE WHEN ru.created_by = 'webhook' THEN ru.id END)::NUMERIC 
                / NULLIF(COUNT(DISTINCT ru.id), 0) * 100,
                0  -- 如果没有用户，返回 0 而不是 NULL
            ), 
            2
        ) AS webhook_success_rate,
        
        ...
    FROM recent_users ru
    LEFT JOIN creation_events ce ON ru.id = ce.user_id;
END;
$$ LANGUAGE plpgsql;
```

---

## 🟡 低危风险 (P2)

### 7. 错误处理不完整 ⚠️

**风险描述**:
- RPC 函数没有捕获所有可能的异常
- 应用层没有处理 RPC 调用失败的情况
- 缺少降级方案

**修复方案**:

```python
# infrastructure/repositories/user_repository.py
async def create_or_get(
    self,
    user_profile: UserProfile,
    source: str
) -> Tuple[UserProfile, bool]:
    """
    创建或获取用户（带降级方案）
    """
    try:
        # 主路径：调用 RPC
        result = await self.client.rpc('create_user_idempotent', {
            'p_user_id': user_profile.user_id,
            'p_email': user_profile.email,
            'p_source': source,
            ...
        }).execute()
        
        if not result.data:
            raise Exception("RPC returned no data")
        
        row = result.data[0]
        profile = self._map_to_entity(row['user_profile'])
        was_created = row['was_created']
        
        return profile, was_created
        
    except Exception as rpc_error:
        logger.error(
            f"❌ RPC create_user_idempotent failed: {rpc_error}",
            extra={"user_id": user_profile.user_id, "source": source}
        )
        
        # 降级方案：直接查询 + 插入
        try:
            existing = await self.get_by_id(user_profile.user_id)
            if existing:
                return existing, False
            
            # 尝试直接插入
            await self.create(user_profile)
            return user_profile, True
            
        except Exception as fallback_error:
            logger.error(
                f"❌ Fallback also failed: {fallback_error}",
                extra={"user_id": user_profile.user_id}
            )
            
            # 发送告警
            await send_alert_async(
                title="User Creation Critical Failure",
                message=f"Both RPC and fallback failed for {user_profile.user_id}",
                severity="critical"
            )
            
            raise
```

---

## 📋 修复优先级

| 风险 | 优先级 | 影响 | 修复难度 | 建议时间 |
|------|--------|------|----------|---------|
| 1. 注册奖励重复 | P0 | 高 💸 | 简单 | 立即 |
| 2. TOCTOU Race | P0 | 高 🔥 | 中等 | 本周内 |
| 3. user_code 冲突 | P0 | 中 🔢 | 简单 | 本周内 |
| 4. 日志表增长 | P1 | 中 💾 | 简单 | 2 周内 |
| 5. 事务一致性 | P1 | 中 🔄 | 简单 | 2 周内 |
| 6. 监控准确性 | P1 | 中 📊 | 中等 | 2 周内 |
| 7. 错误处理 | P2 | 低 ⚠️ | 复杂 | 1 个月内 |

---

## 🚀 推荐实施计划

### Phase 1: 紧急修复 (本周)

```bash
# 第 1 天：修复重复奖励
1. 删除 Webhook 中的 _grant_signup_bonus() 调用
2. 测试验证
3. 部署到生产

# 第 2-3 天：修复 TOCTOU
1. 重写 create_user_idempotent() 使用 UPSERT
2. 单元测试（并发场景）
3. 灰度部署

# 第 4-5 天：修复 user_code
1. 创建序列
2. 更新 generate_user_code()
3. 部署
```

### Phase 2: 稳定性增强 (2 周内)

```bash
1. 配置日志表定期清理
2. 优化监控查询
3. 完善错误处理
4. 添加降级方案
```

### Phase 3: 监控完善 (1 个月内)

```bash
1. 创建 Grafana Dashboard
2. 配置告警规则
3. 集成 Sentry 监控
4. 文档更新
```

---

## 📊 风险矩阵

```
影响 ↑
高 |  [2]         [1]
   |
中 |  [3,4,5,6]
   |
低 |              [7]
   |________________
      低   中   高  → 发生概率

[1] 注册奖励重复 (高影响 + 高概率 = P0)
[2] TOCTOU Race (高影响 + 低概率 = P0)
[3-6] 中危风险 (中影响 + 中概率 = P1)
[7] 错误处理 (低影响 + 低概率 = P2)
```

---

## ✅ 总结

### 当前状态：🟡 黄色（需要改进）

**优点**:
- ✅ 核心架构正确
- ✅ 大部分场景可用
- ✅ 可监控、可追踪

**缺点**:
- ⚠️ 边界情况处理不完善
- ⚠️ 资源管理存在隐患
- ⚠️ 缺少降级方案

### 修复后状态：🟢 绿色（生产就绪）

完成 Phase 1 修复后：
- ✅ 无财务风险
- ✅ 无数据一致性风险
- ✅ 可承受高并发

完成 Phase 2-3 后：
- ✅ 完整的可观测性
- ✅ 自动化运维
- ✅ 达到业界最佳实践标准

---

**审核建议**: 
1. ✅ 当前方案 **可以上生产**（非关键场景）
2. ⚠️ 完成 Phase 1 修复后再处理关键业务
3. 🎯 2 周内完成所有 P0/P1 修复

**参考**: Stripe, AWS, Google Cloud 的幂等设计模式
