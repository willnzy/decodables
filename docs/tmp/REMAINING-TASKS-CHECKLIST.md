# 遗留工作清单

> **最后更新**: 2026-01-13  
> **P0 修复状态**: ✅ 已完成  
> **当前状态**: 等待部署和验证

---

## 🔴 立即需要完成（部署前，5-10 分钟）

### 1. 执行数据库迁移 ⚠️ **必须**

**状态**: ❌ 未完成  
**优先级**: P0  
**责任人**: 数据库管理员 / 开发者  
**预计时间**: 5 分钟

**操作步骤**:
```bash
# 方法 A: 在 Supabase Dashboard SQL Editor 中执行
# 1. 打开 Supabase Dashboard
# 2. 进入 SQL Editor
# 3. 复制并执行以下文件内容：
#    - migrations/v2/HOTFIX_user_creation_p0.sql
#
# 或者
#
# 方法 B: 使用 psql 命令行
psql "postgresql://your_connection_string" \
  -f migrations/v2/HOTFIX_user_creation_p0.sql
```

**验证**:
```sql
-- 验证序列
SELECT * FROM pg_sequences WHERE sequencename = 'user_code_seq';

-- 验证函数
SELECT proname FROM pg_proc WHERE proname = 'create_user_idempotent';

-- 验证错误日志表
SELECT * FROM pg_tables WHERE tablename = 'error_logs';
```

**预期输出**:
```
✅ user_code_seq 序列创建成功
✅ create_user_idempotent 函数已更新
✅ error_logs 表已创建
🎉 所有 P0 修复已成功应用！
```

---

### 2. 等待 Railway 部署完成

**状态**: ⏳ 进行中（自动）  
**优先级**: P0  
**预计时间**: 2-5 分钟

**操作步骤**:
```bash
# 监控部署日志
railway logs --follow

# 或在 Railway Dashboard 查看部署状态
# https://railway.app/project/your-project/deployments
```

**验证部署成功**:
```bash
# 测试健康检查
curl https://your-backend.railway.app/api/health

# 预期响应: {"status": "ok", ...}
```

---

## 🟡 24 小时内验证（部署后，15 分钟）

### 3. 验证修复生效

**状态**: ❌ 待执行  
**优先级**: P0  
**责任人**: 开发者  
**预计时间**: 15 分钟

#### 3.1 验证新用户 Credits
```sql
-- 检查最近创建的用户
SELECT 
    id, 
    email, 
    credits_permanent, 
    created_by,
    created_at
FROM profiles 
WHERE created_at >= NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC 
LIMIT 10;

-- ✅ 预期: credits_permanent = 50 (不是 100)
-- ✅ 预期: created_by 为 'webhook' 或 'jit'
```

#### 3.2 验证监控 API
```bash
# 测试监控端点（需要 Admin Token）
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  https://your-backend.railway.app/api/v2/admin/monitoring/user-creation/health

# ✅ 预期响应:
{
  "success": true,
  "data": {
    "status": "healthy",
    "stats": {
      "webhook_success_rate": 96.67,
      "jit_fallback_rate": 3.33
    },
    "alerts": []
  }
}
```

#### 3.3 验证并发场景
```bash
# 运行集成测试
cd decodables
pytest tests/integration/test_user_creation_hotfix.py -v

# ✅ 预期: 6 个测试全部通过
```

---

## 🟢 一周内完成（P1 优化，可选）

### 4. 配置日志表定期清理

**状态**: ❌ 未完成  
**优先级**: P1  
**预计时间**: 30 分钟

**操作步骤**:

#### 方法 A: 使用 Supabase Cron（推荐）
```sql
-- 创建定时任务（每天凌晨 3 点执行）
SELECT cron.schedule(
    'cleanup-user-creation-logs',
    '0 3 * * *',  -- 每天 3:00
    $$
        DELETE FROM user_creation_logs 
        WHERE created_at < NOW() - INTERVAL '90 days';
    $$
);

-- 验证任务
SELECT * FROM cron.job WHERE jobname = 'cleanup-user-creation-logs';
```

#### 方法 B: 使用应用层定时任务
```python
# scheduler.py (或 worker.py)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def cleanup_old_logs():
    """每天清理 90 天前的日志"""
    db = await get_async_db_client()
    result = await db.rpc('cleanup_old_user_creation_logs', {
        'p_retention_days': 90
    }).execute()
    logger.info(f"Cleaned up {result.data} old logs")

scheduler = AsyncIOScheduler()
scheduler.add_job(cleanup_old_logs, 'cron', hour=3, minute=0)
```

---

### 5. 完善错误处理（可选）

**状态**: ❌ 未完成  
**优先级**: P1  
**预计时间**: 1 小时

**当前状态**: RPC 函数已有基本错误处理  
**建议增强**: 应用层降级方案

**参考**: `docs/tmp/IDEMPOTENT-USER-CREATION-RISK-ANALYSIS.md` 中的"测试7: 错误处理不完整"部分

---

## 🔵 一个月内完成（P2 监控，可选）

### 6. 创建 Grafana Dashboard

**状态**: ❌ 未完成  
**优先级**: P2  
**预计时间**: 2-3 小时

**建议面板**:
1. 用户创建趋势（按天/周/月）
2. Webhook 成功率（实时）
3. JIT Fallback 率（实时）
4. 创建来源分布（饼图）
5. 重复尝试次数（折线图）
6. 错误日志（表格）

**数据源**: PostgreSQL (Supabase)

---

### 7. 配置告警规则

**状态**: ❌ 未完成  
**优先级**: P2  
**预计时间**: 30 分钟

**建议告警**:
```yaml
alerts:
  - name: low_webhook_success_rate
    condition: webhook_success_rate < 90%
    severity: warning
    notification: slack/email
    
  - name: high_jit_fallback_rate
    condition: jit_fallback_rate > 10%
    severity: warning
    notification: slack/email
    
  - name: creation_errors
    condition: errors > 0
    severity: critical
    notification: slack/email/pagerduty
```

**实施方式**:
- Grafana Alerts
- Sentry Alerts
- Supabase Database Webhooks

---

### 8. 集成 Sentry 监控

**状态**: ✅ 已部分完成（Sentry SDK 已配置）  
**优先级**: P2  
**预计时间**: 30 分钟

**建议增强**:
```python
# 在关键位置添加 Sentry 事件
import sentry_sdk

# JIT Fallback 触发时
sentry_sdk.capture_message(
    f"JIT Fallback triggered for user {user_id}",
    level="warning",
    extras={
        "user_id": user_id,
        "email": email,
        "source": "jit_fallback"
    }
)

# 重复创建尝试时
sentry_sdk.capture_message(
    f"Duplicate user creation attempt for {user_id}",
    level="info",
    extras={
        "user_id": user_id,
        "source": source,
        "created_by": existing_created_by
    }
)
```

---

## 📋 验收清单汇总

### 立即需要（部署前）
- [ ] 执行数据库迁移（Supabase）
- [ ] 等待 Railway 部署完成

### 24 小时内（部署后）
- [ ] 验证新用户 credits = 50
- [ ] 验证监控 API 正常工作
- [ ] 验证并发测试通过
- [ ] 检查 Webhook 成功率 >95%
- [ ] 检查 JIT Fallback 率 <5%

### 一周内（P1 优化）
- [ ] 配置日志表定期清理
- [ ] 完善错误处理和降级方案
- [ ] 审核 error_logs 表

### 一个月内（P2 监控）
- [ ] 创建 Grafana Dashboard
- [ ] 配置告警规则
- [ ] 增强 Sentry 集成
- [ ] 更新运维文档

---

## 🎯 快速命令参考

### 数据库迁移
```bash
# Supabase Dashboard SQL Editor
# 复制粘贴: migrations/v2/HOTFIX_user_creation_p0.sql
```

### 部署监控
```bash
# Railway
railway logs --follow

# 测试端点
curl https://your-backend.railway.app/api/health
```

### 验证修复
```sql
-- 新用户 credits
SELECT credits_permanent FROM profiles 
WHERE created_at >= NOW() - INTERVAL '1 hour';

-- 监控统计
SELECT * FROM get_user_creation_stats(7);
```

### 测试
```bash
pytest tests/integration/test_user_creation_hotfix.py -v
```

---

## 📞 问题联系

如果遇到问题：

1. **数据库迁移失败**: 
   - 检查 PostgreSQL 版本 ≥ 12
   - 检查用户权限
   - 查看错误信息

2. **部署失败**:
   - 检查 Railway logs
   - 检查依赖安装
   - 检查环境变量

3. **监控 API 404**:
   - 确认路由已注册（已完成）
   - 确认部署成功
   - 检查 API 前缀

4. **Credits 仍然是 100**:
   - 检查代码是否最新
   - 检查数据库迁移是否执行
   - 查看应用层日志

---

**最后更新**: 2026-01-13  
**P0 状态**: ✅ 代码已完成并推送  
**下一步**: 执行数据库迁移 → 等待部署 → 验证修复
