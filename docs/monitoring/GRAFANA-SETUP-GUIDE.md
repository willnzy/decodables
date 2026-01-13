# Grafana Dashboard 配置指南

> **版本**: v1.0  
> **日期**: 2026-01-13  
> **用途**: 监控用户创建健康度和 Webhook 质量

---

## 📊 Dashboard 概览

### 监控指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **Webhook Success Rate** | >95% | Webhook 创建成功率 |
| **JIT Fallback Rate** | <5% | JIT 创建回退率（安全网触发率） |
| **Total Users** | - | 7 天内新增用户总数 |
| **Errors** | 0 | 错误数量 |
| **Health Score** | >95% | 系统健康评分 |

### 可视化面板

1. **关键指标卡片** (Stat Panels)
   - Webhook Success Rate
   - JIT Fallback Rate
   - Total Users
   - Errors

2. **趋势图表** (Time Series)
   - User Creation Trend (按天/创建来源)
   - Duplicate Attempts (重复尝试频率)

3. **分布图** (Pie Chart)
   - Creation Source Distribution (webhook vs jit)

4. **数据表** (Tables)
   - Recent Error Logs
   - Log Tables Statistics

5. **健康评分** (Gauge)
   - System Health Score (0-100%)

---

## 🚀 快速开始

### Step 1: 配置数据源

#### 1.1 添加 PostgreSQL 数据源

在 Grafana 中：

1. 进入 **Configuration** > **Data Sources**
2. 点击 **Add data source**
3. 选择 **PostgreSQL**
4. 配置连接信息：

```yaml
Name: Supabase Production DB
Host: db.xxxxxxxxxxxx.supabase.co:5432
Database: postgres
User: postgres
Password: your_supabase_password
SSL Mode: require
```

5. 点击 **Save & Test**

#### 1.2 验证连接

测试 SQL 查询：
```sql
SELECT * FROM get_user_creation_stats(7);
```

---

### Step 2: 导入 Dashboard

#### 2.1 通过 JSON 导入

1. 在 Grafana 中，点击 **+ Create** > **Import**
2. 上传文件：`docs/monitoring/grafana-dashboard-user-creation.json`
3. 选择数据源：**Supabase Production DB**
4. 点击 **Import**

#### 2.2 配置刷新间隔

- 默认：每 1 分钟刷新
- 可调整为：5 分钟、15 分钟、30 分钟

---

## 📈 面板说明

### 1. Webhook Success Rate

**SQL 查询**:
```sql
SELECT webhook_success_rate 
FROM get_user_creation_stats(7);
```

**阈值**:
- 🟢 ≥95%: 健康
- 🟡 90-95%: 警告
- 🔴 <90%: 危险

**告警条件**: 如果 <90%，检查 Clerk Webhook 配置

---

### 2. JIT Fallback Rate

**SQL 查询**:
```sql
SELECT jit_fallback_rate 
FROM get_user_creation_stats(7);
```

**阈值**:
- 🟢 <5%: 正常
- 🟡 5-10%: 需关注
- 🔴 >10%: 危险

**告警条件**: 如果 >10%，说明 Webhook 延迟严重

---

### 3. User Creation Trend

**SQL 查询**:
```sql
SELECT 
    DATE(created_at) as time, 
    created_by, 
    COUNT(*) as value 
FROM profiles 
WHERE created_at >= NOW() - INTERVAL '30 days' 
GROUP BY DATE(created_at), created_by 
ORDER BY time;
```

**用途**: 观察每日新增用户趋势和创建来源分布

---

### 4. Recent Error Logs

**SQL 查询**:
```sql
SELECT 
    created_at as time, 
    operation, 
    error_message, 
    details 
FROM system_error_logs 
WHERE created_at >= NOW() - INTERVAL '24 hours' 
ORDER BY created_at DESC 
LIMIT 50;
```

**用途**: 快速发现和排查错误

---

## 🔔 配置告警规则

### Grafana Alerts 配置

#### 告警 1: Low Webhook Success Rate

```yaml
Name: Low Webhook Success Rate
Condition:
  - Query: SELECT webhook_success_rate FROM get_user_creation_stats(7)
  - Threshold: < 90
  - For: 5 minutes
Notification:
  - Slack: #backend-alerts
  - Email: dev-team@example.com
Severity: Warning
```

#### 告警 2: High JIT Fallback Rate

```yaml
Name: High JIT Fallback Rate
Condition:
  - Query: SELECT jit_fallback_rate FROM get_user_creation_stats(7)
  - Threshold: > 10
  - For: 10 minutes
Notification:
  - Slack: #backend-alerts
Severity: Warning
```

#### 告警 3: User Creation Errors

```yaml
Name: User Creation Errors
Condition:
  - Query: SELECT errors FROM get_user_creation_stats(7)
  - Threshold: > 0
  - For: 1 minute
Notification:
  - Slack: #backend-alerts
  - PagerDuty: On-call engineer
Severity: Critical
```

---

## 🛠️ 自定义 Dashboard

### 添加新面板

#### 示例：Webhook 延迟分布

```sql
-- 查询 Webhook 延迟
WITH recent_logs AS (
    SELECT 
        user_id,
        created_at as log_time,
        source
    FROM user_creation_logs
    WHERE source = 'webhook'
      AND created_at >= NOW() - INTERVAL '7 days'
),
users AS (
    SELECT 
        id,
        created_at as user_time
    FROM profiles
    WHERE created_at >= NOW() - INTERVAL '7 days'
)
SELECT 
    DATE(u.user_time) as time,
    AVG(EXTRACT(EPOCH FROM (l.log_time - u.user_time))) as avg_delay_seconds
FROM users u
JOIN recent_logs l ON u.id = l.user_id
GROUP BY DATE(u.user_time)
ORDER BY time;
```

#### 示例：按小时统计创建数

```sql
SELECT 
    date_trunc('hour', created_at) as time,
    created_by,
    COUNT(*) as value
FROM profiles
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY date_trunc('hour', created_at), created_by
ORDER BY time;
```

---

## 📊 业界参考

### Stripe Dashboard

Stripe 的监控面板关注：
- API 成功率
- 延迟 (P50, P95, P99)
- 错误率
- 吞吐量

**参考**: https://stripe.com/docs/dashboard

### AWS CloudWatch

AWS 的最佳实践：
- 设置多个阈值（warning, critical）
- 使用复合告警（多个条件）
- 结合日志和指标

**参考**: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/

---

## 🧪 测试 Dashboard

### 验证查询

在 Grafana Query Inspector 中测试：

```sql
-- 1. 验证统计函数
SELECT * FROM get_user_creation_stats(7);

-- 2. 验证表大小视图
SELECT * FROM v_table_sizes 
WHERE tablename IN ('user_creation_logs', 'system_error_logs', 'error_logs', 'profiles');

-- 3. 验证日志统计
SELECT * FROM get_log_tables_stats();
```

### 模拟数据

如果需要测试面板效果，可以插入模拟数据：

```sql
-- 插入模拟用户创建日志
INSERT INTO user_creation_logs (user_id, source, action, created_at)
VALUES 
    ('test_user_1', 'webhook', 'created', NOW() - INTERVAL '1 hour'),
    ('test_user_2', 'jit', 'created', NOW() - INTERVAL '2 hours'),
    ('test_user_1', 'jit', 'duplicate_attempt', NOW() - INTERVAL '30 minutes');

-- 清理模拟数据
DELETE FROM user_creation_logs WHERE user_id LIKE 'test_user_%';
```

---

## 📚 相关文档

- [用户创建监控 API](../api/admin/user_creation_monitoring.py)
- [风险分析文档](../tmp/IDEMPOTENT-USER-CREATION-RISK-ANALYSIS.md)
- [实施指南](../tmp/IDEMPOTENT-USER-CREATION-IMPLEMENTATION.md)
- [维护任务配置](../../migrations/v2/02_maintenance_jobs.sql)

---

## 🆘 故障排查

### 问题 1: 数据源连接失败

**检查**:
- Supabase 连接字符串是否正确
- SSL 模式是否设置为 `require`
- 数据库用户权限是否足够

**解决方案**:
```bash
# 测试连接
psql "postgresql://postgres:password@db.xxx.supabase.co:5432/postgres?sslmode=require"

# 验证权限
\dp profiles
\dp user_creation_logs
```

### 问题 2: 查询返回空数据

**检查**:
- RPC 函数是否已创建
- 视图是否已创建
- 数据是否存在

**解决方案**:
```sql
-- 检查函数
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_name IN (
    'get_user_creation_stats', 
    'get_log_tables_stats'
);

-- 检查视图
SELECT viewname 
FROM pg_views 
WHERE viewname IN ('v_table_sizes', 'v_user_creation_events');

-- 检查数据
SELECT COUNT(*) FROM user_creation_logs;
```

### 问题 3: 面板显示错误

**检查**:
- SQL 语法是否正确
- 字段名是否匹配
- 数据类型是否匹配

**解决方案**:
- 在 Query Inspector 中测试 SQL
- 查看 Grafana 日志
- 使用 `EXPLAIN` 分析查询性能

---

**维护人**: Make Decodables Team  
**更新日期**: 2026-01-13  
**下次审核**: 2026-02-13
