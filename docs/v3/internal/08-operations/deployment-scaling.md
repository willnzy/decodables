# 部署与扩展指南

> 系统部署流程、环境配置、扩展策略

> **同步范围**: [backend]
> **状态**: 🟡 待验证
> **最后更新**: 2026-02-05
> **数据来源**: `v2/06-operations/deployment-scaling.md`, Railway/Vercel 配置

---

## 一、部署架构

### 1.1 服务组件

| 组件 | 服务 | 环境 |
|------|------|------|
| 前端 | Vercel | Edge Functions |
| 后端 | Railway | Container |
| 数据库 | Supabase | PostgreSQL 15 |
| 缓存 | Redis | Railway Add-on |
| 文件存储 | Supabase Storage | S3 兼容 |
| 支付 | Stripe | SaaS |
| AI | FAL.ai / OpenAI | SaaS |

### 1.2 架构图

```
                    ┌─────────────────┐
                    │    Cloudflare   │
                    │      (CDN)      │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
       │   Vercel    │ │  Railway  │ │  Supabase   │
       │  (Next.js)  │ │ (FastAPI) │ │ (Postgres)  │
       └──────┬──────┘ └─────┬─────┘ └──────┬──────┘
              │              │              │
              │         ┌────▼────┐         │
              │         │  Redis  │         │
              │         └─────────┘         │
              │                             │
              └─────────────┬───────────────┘
                            │
                     ┌──────▼──────┐
                     │   Storage   │
                     │ (Supabase)  │
                     └─────────────┘
```

---

## 二、环境配置

### 2.1 环境变量

#### 后端 (Railway)

```bash
# 数据库
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
DATABASE_URL=postgresql://...

# 认证
JWT_SECRET_KEY=your-secret-key
JWT_SECRET_KEY_SECONDARY=rotation-key  # 双密钥轮换

# 支付
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# AI
FAL_KEY=xxx
OPENAI_API_KEY=sk-...

# Redis
REDIS_URL=redis://...

# 监控
SENTRY_DSN=https://...

# 环境
ENVIRONMENT=production
LOG_LEVEL=INFO
```

#### 前端 (Vercel)

```bash
# API
NEXT_PUBLIC_API_URL=https://api.foliaz.com
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# Analytics
NEXT_PUBLIC_GA_ID=G-xxx
NEXT_PUBLIC_SENTRY_DSN=https://...

# Feature Flags
NEXT_PUBLIC_ENABLE_MARKETPLACE=true
```

### 2.2 Secrets 管理

```
敏感信息存储位置:
├── Railway Secrets    → 后端密钥
├── Vercel Secrets     → 前端密钥
├── Supabase Vault     → 数据库密钥
└── 1Password          → 团队共享
```

---

## 三、部署流程

### 3.1 前端部署 (Vercel)

```
触发条件:
├── Push to main       → 自动部署 Production
├── Push to develop    → 自动部署 Preview
└── Pull Request       → 自动部署 Preview

部署步骤:
1. Git Push
2. Vercel Build (npm run build)
3. Type Check + Lint
4. Deploy to Edge
5. 健康检查
6. DNS 切换 (零停机)
```

### 3.2 后端部署 (Railway)

```yaml
# railway.toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 依赖安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# 启动
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.3 数据库迁移

```bash
# 迁移流程
1. 本地测试迁移脚本
2. 在 Staging 执行
3. 验证数据完整性
4. 在 Production 执行 (低峰期)
5. 监控错误日志

# 执行命令
python -m alembic upgrade head
```

---

## 四、扩展策略

### 4.1 水平扩展

#### 后端 (Railway)

```yaml
# 自动扩展配置
scaling:
  min_instances: 2
  max_instances: 10
  target_cpu: 70
  target_memory: 80
```

#### 数据库 (Supabase)

```
扩展选项:
├── 连接池 (PgBouncer)
├── 只读副本
├── 计算资源升级
└── 存储扩展
```

### 4.2 缓存策略

```python
# 缓存层级
CACHE_TTL = {
    'user_profile': 300,      # 5 分钟
    'system_config': 3600,    # 1 小时
    'feature_flags': 300,     # 5 分钟
    'static_content': 86400,  # 24 小时
}

# Redis 使用模式
- 会话缓存
- Rate Limiting
- 分布式锁
- 消息队列
```

### 4.3 CDN 配置

```
Cloudflare 规则:
├── 静态资源 → 缓存 30 天
├── API → 不缓存
├── 图片 → 缓存 7 天 + 转换
└── HTML → 不缓存
```

---

## 五、监控与告警

### 5.1 监控指标

| 指标 | 阈值 | 告警 |
|------|------|------|
| API 延迟 P99 | > 2s | Slack |
| 错误率 | > 1% | PagerDuty |
| CPU 使用率 | > 80% | Slack |
| 内存使用率 | > 85% | Slack |
| 数据库连接数 | > 80% | Slack |

### 5.2 日志聚合

```
日志流向:
├── Railway Logs → LogDNA
├── Vercel Logs → LogDNA
├── Supabase Logs → 内置控制台
└── 应用错误 → Sentry
```

### 5.3 健康检查

```python
# /health 端点
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "storage": await check_storage(),
    }
    
    all_healthy = all(c["status"] == "ok" for c in checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## 六、回滚策略

### 6.1 前端回滚

```bash
# Vercel 回滚
vercel rollback [deployment-url]

# 或通过 Dashboard
1. 进入 Deployments
2. 选择上一个成功部署
3. 点击 "Promote to Production"
```

### 6.2 后端回滚

```bash
# Railway 回滚
1. 进入 Deployments
2. 选择上一个成功部署
3. 点击 "Rollback"

# 或重新部署指定 commit
railway up --commit <commit-sha>
```

### 6.3 数据库回滚

```sql
-- 使用 Supabase 时间点恢复
-- 联系 Supabase 支持进行 PITR

-- 或使用迁移回滚
python -m alembic downgrade -1
```

---

## 七、灾难恢复

### 7.1 备份策略

| 数据 | 频率 | 保留 |
|------|------|------|
| 数据库 | 每日 | 30 天 |
| 文件存储 | 实时复制 | 无限 |
| 配置 | Git 版本控制 | 无限 |

### 7.2 恢复流程

```
1. 评估故障范围
2. 启用维护页面
3. 从备份恢复数据
4. 验证数据完整性
5. 恢复服务
6. 监控异常
7. 事后复盘
```

---

## 八、安全加固

### 8.1 网络安全

- HTTPS 强制
- WAF 规则 (Cloudflare)
- Rate Limiting
- IP 白名单 (Admin)

### 8.2 应用安全

- 依赖漏洞扫描 (Dependabot)
- 代码安全扫描 (CodeQL)
- Secret 泄露检测

### 8.3 访问控制

- SSH 密钥认证
- 2FA 强制
- 最小权限原则
- 审计日志

---

## 九、相关文档

- [日志标准](../04-engineering/development/logging-standard.md)
- [测试指南](../04-engineering/development/testing-guide.md)
- [Admin 系统运维](../04-engineering/modules/admin/system-ops.md)
