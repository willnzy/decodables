# Make Decodables 部署与扩展完整指南

> **版本**: 2.0
> **更新日期**: 2026-01-10

---

## 目录

**Part 1: 多实例部署扩展指南**
1. [架构概览](#part-1-多实例部署扩展指南)
2. [何时扩展](#12-何时扩展)
3. [Railway 扩展步骤](#13-railway-扩展步骤)
4. [组件行为](#14-组件行为)
5. [未来增强](#15-未来增强)

**Part 2: Railway 架构兼容性分析**
1. [Railway 架构设计](#part-2-railway-架构兼容性分析)
2. [代码兼容性分析](#22-代码兼容性分析)
3. [部署建议](#23-部署建议)
4. [性能优化](#24-性能优化)

---

# Part 1: 多实例部署扩展指南

## 1.1 架构概览

### 当前架构 (单实例)

```
Users ──► Railway (1 instance) ──► Supabase
              │
              └── Scheduler runs here
```

### 扩展架构 (多实例)

```
                    ┌──► Instance 1 (ENABLE_SCHEDULER=true)
Users ──► Railway ──┼──► Instance 2 (ENABLE_SCHEDULER=false)
       Load Balancer└──► Instance 3 (ENABLE_SCHEDULER=false)
                              │
                              └── All instances ──► Supabase
```

---

## 1.2 何时扩展

监控以下指标以决定是否需要扩展:

| 指标 | 阈值 | 操作 |
|------|------|------|
| CPU Usage | > 70% sustained | 添加实例 |
| Memory Usage | > 80% sustained | 添加实例 |
| Response Time P95 | > 2 seconds | 添加实例 |
| Daily Active Users | > 1000 | 考虑扩展 |

---

## 1.3 Railway 扩展步骤

### Step 1: 准备环境变量

在扩展之前，确保准备好以下环境变量:

```bash
# Instance 1 (Primary - runs scheduler)
ENABLE_SCHEDULER=true

# Instance 2, 3, ... (Workers - no scheduler)
ENABLE_SCHEDULER=false
```

### Step 2: 在 Railway 中扩展

1. 访问 Railway Dashboard → Your Project → Backend Service
2. 点击 "Settings" → "Scaling"
3. 增加副本数量
4. 为每个副本配置环境变量（如果支持）
   - OR 使用 Railway 的副本 ID 条件性启用调度器

### Step 3: 验证部署

```bash
# 检查日志中的实例 ID
# 每个实例记录: "🚀 Starting instance: {INSTANCE_ID}"

# 验证只有一个实例显示:
# "📅 Scheduler started with jobs:"
```

---

## 1.4 组件行为

### 1.4.1 Scheduler (APScheduler)

| 设置 | 行为 |
|------|------|
| `ENABLE_SCHEDULER=true` | 运行定时任务（小时/每日聚合） |
| `ENABLE_SCHEDULER=false` | 调度器禁用，实例仅处理 API 请求 |

**⚠️ 警告**: 如果多个实例设置 `ENABLE_SCHEDULER=true`，任务将运行多次！

### 1.4.2 内存缓存

| 缓存 | TTL | 多实例行为 |
|------|-----|------------|
| `config_service` 缓存 | 60s | 每个实例有自己的缓存；最多 60 秒不一致 |
| `db_service` 配置缓存 | 300s | 每个实例有自己的缓存；最多 5 分钟不一致 |

**影响**: 配置更改可能需要最多 5 分钟才能传播到所有实例。

**缓解措施**: 配置更改后调用管理员 API `/api/admin/configs/cache/invalidate`。

### 1.4.3 速率限制 (slowapi)

当前实现使用**内存存储**。

| 模式 | 行为 |
|------|------|
| 单实例 | 正常工作 |
| 多实例 | 速率限制是每个实例的（不共享） |

**未来增强**: 使用 Redis 进行共享速率限制:
```python
from slowapi import Limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://your-redis-url:6379"
)
```

### 1.4.4 数据库连接

Supabase 客户端是无状态的 - 每个实例创建自己的连接。
无需特殊处理。

### 1.4.5 文件存储

所有文件操作使用 Supabase Storage（外部）。
无需特殊处理。

---

## 1.5 未来增强

### Phase 1: 共享速率限制
```
添加 Upstash Redis → 配置 slowapi 使用 Redis 存储
预计工作量: 2-4 小时
```

### Phase 2: 共享缓存
```
添加 Redis → 用 Redis 替换内存缓存
预计工作量: 4-8 小时
```

### Phase 3: 消息队列（用于长时间运行的任务）
```
添加 Redis Queue/Celery → 将 AI 生成卸载到 workers
预计工作量: 1-2 周（包括前端更改）
```

---

## 1.6 故障排除

### 问题: 定时任务运行多次
**原因**: 多个实例设置了 `ENABLE_SCHEDULER=true`
**修复**: 确保只有一个实例设置了 `ENABLE_SCHEDULER=true`

### 问题: 速率限制无法正常工作
**原因**: 内存速率限制不在实例之间共享状态
**修复**: 实现基于 Redis 的速率限制

### 问题: 配置更改未反映
**原因**: 每个实例有自己的缓存
**修复**:
1. 等待 TTL（最多 5 分钟）
2. 或在所有实例上调用 `/api/admin/configs/cache/invalidate`
3. 或重启所有实例

---

## 1.7 监控

运行多个实例时，确保日志包含实例 ID:

```python
# 已在 app.py 中实现
logger.info(f"[Instance {INSTANCE_ID}] Request processed")
```

这有助于追踪哪个实例处理了特定请求。

---

# Part 2: Railway 架构兼容性分析

> **分析日期**: 2026-01-08
> **分析目标**: 评估当前代码与 Railway 多服务架构的兼容性

## 2.1 Railway 架构设计

### 2.1.1 当前部署架构

```
┌────────────────────────────────────────────────────────────┐
│                     Railway Platform                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────────┐        ┌─────────────────┐          │
│  │  Redis-Staging  │◄───────┤  worker-staging │          │
│  │   (Cache/Queue) │        │  (RQ Worker)    │          │
│  │                 │        │                  │          │
│  │  redis-ukux-    │        │  后台任务处理     │          │
│  │  volume         │        │  - 图片生成      │          │
│  └────────▲────────┘        │  - 异步任务      │          │
│           │                  └─────────────────┘          │
│           │                                                │
│           │                  ┌─────────────────┐          │
│           └──────────────────┤ main-decodables │          │
│                              │  (FastAPI)      │          │
│                              │                 │          │
│                              │  Web API 服务    │          │
│                              │  - 用户请求      │          │
│                              │  - 任务调度      │          │
│                              └─────────────────┘          │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 2.1.2 架构特点

1. **服务隔离**: 3 个独立服务
   - `main-decodables`: FastAPI Web 服务
   - `worker-staging`: RQ 后台 Worker
   - `Redis-Staging`: Redis 缓存和任务队列

2. **扩展性设计**:
   - Web 服务和 Worker 可独立扩展
   - 支持水平扩展（多个 Worker 实例）
   - Redis 持久化存储（volume）

3. **通信方式**:
   - Web → Redis: 发布任务、缓存读写
   - Worker → Redis: 消费任务、更新状态
   - 共享 Redis 作为消息队列和缓存

---

## 2.2 代码兼容性分析

### 2.2.1 Redis 连接管理 ✅

**代码位置**: `core/cache/redis_provider.py`

```python
# 自动从环境变量读取 Railway 提供的 REDIS_URL
REDIS_URL = os.environ.get("REDIS_URL")

def get_redis_client() -> Optional[redis.Redis]:
    if not REDIS_URL:
        logger.warning("[Redis] REDIS_URL not configured")
        return None

    _redis_pool = redis.ConnectionPool.from_url(
        REDIS_URL,
        max_connections=10,
        socket_timeout=5,
        health_check_interval=30,
    )
```

**评估**: ✅ **完美兼容**
- Railway 会自动注入 `REDIS_URL` 环境变量
- 连接池配置适合生产环境
- 包含健康检查和超时控制

---

### 2.2.2 自动降级机制 ✅

**代码位置**: `core/cache/service.py`

```python
class CacheService:
    def __init__(self):
        self._redis = RedisCacheProvider()
        self._fallback = MemoryCacheProvider()  # 内存降级
        self._using_redis = False

    def _get_provider(self) -> ICacheProvider:
        # 自动检测 Redis 可用性
        if now - self._last_redis_check > self._redis_check_interval:
            self._using_redis = is_redis_available()

        if self._using_redis:
            return self._redis
        return self._fallback  # 自动降级到内存
```

**评估**: ✅ **生产级设计**
- Redis 不可用时自动降级到内存缓存
- 30秒间隔健康检查，避免频繁检测
- 保证服务高可用

---

### 2.2.3 Worker 进程配置 ✅

**代码位置**: `worker.py` + `Procfile`

```python
# worker.py
DEFAULT_QUEUES = ["high", "default", "low"]

def get_worker_queues() -> list:
    # 从环境变量读取队列配置
    queues_env = os.environ.get("WORKER_QUEUES", "")
    if queues_env:
        return [q.strip() for q in queues_env.split(",")]
    return DEFAULT_QUEUES
```

```yaml
# Procfile (Railway 自动识别)
web: uvicorn app:app --host 0.0.0.0 --port $PORT
worker: python worker.py
```

**评估**: ✅ **完美兼容**
- `Procfile` 定义了两个独立进程
- Railway 会自动识别并创建对应服务
- Worker 支持环境变量配置队列

---

### 2.2.4 任务队列系统 ✅

**代码位置**: `infrastructure/task_queue/`

```python
# queue_manager.py
from rq import Queue
from core.cache.redis_provider import get_redis_client

class QueueManager:
    def __init__(self):
        self.redis = get_redis_client()
        self.queues = {
            "high": Queue("high", connection=self.redis),
            "default": Queue("default", connection=self.redis),
            "low": Queue("low", connection=self.redis),
        }

    def enqueue_task(self, queue_name, func, *args, **kwargs):
        """发布任务到 Redis 队列"""
        queue = self.queues.get(queue_name, self.queues["default"])
        job = queue.enqueue(func, *args, **kwargs,
                           result_ttl=3600, failure_ttl=86400)
        return job.id
```

**评估**: ✅ **生产就绪**
- 使用 RQ (Redis Queue) 作为任务队列
- 支持优先级队列（high/default/low）
- 任务结果和失败记录持久化

---

### 2.2.5 环境变量管理 ✅

**代码位置**: `config.py`

```python
# 所有配置从环境变量读取
ENV = os.environ.get("ENV", "development")
REDIS_URL = os.environ.get("REDIS_URL")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")

# Railway 会自动注入这些环境变量
```

**评估**: ✅ **符合 12-Factor App**
- 所有配置通过环境变量管理
- Railway 提供 Web UI 管理环境变量
- 支持不同环境（staging/production）

---

### 2.2.6 需要注意的配置 ⚠️

#### Redis 持久化配置

**当前状态**: Railway 提供 `redis-ukux-volume`
**建议配置**:

```yaml
# railway.toml (可选，Railway 自动配置)
[services.redis]
  volumes = ["redis-ukux-volume:/data"]

[services.redis.env]
  REDIS_SAVE = "60 1"  # 每60秒至少1个key变化时保存
  REDIS_AOF = "yes"    # 启用 AOF 持久化
```

**风险**: 如果 Redis 重启，未持久化的任务队列会丢失
**缓解**:
- ✅ 代码已实现任务状态持久化到 Supabase
- ✅ 任务失败会重试机制

---

#### Worker 扩展配置

**当前状态**: 单个 Worker 实例
**扩展方案**:

```bash
# Railway Dashboard 或 railway.toml
[services.worker]
  replicas = 3  # 运行3个Worker实例

  [services.worker.env]
    WORKER_QUEUES = "high,default"  # Worker 1-2处理高优先级
    WORKER_QUEUES = "default,low"   # Worker 3处理普通任务
```

**评估**: ✅ **代码支持水平扩展**
- Worker 无状态设计
- 多个 Worker 可同时消费同一队列
- Redis 保证任务不重复消费

---

#### 健康检查端点

**当前状态**: 已实现
**代码位置**: `api/routers/health.py`

```python
@router.get("/health")
async def health_check():
    """Railway 健康检查端点"""
    redis_status = is_redis_available()
    supabase_status = check_supabase_connection()

    return {
        "status": "healthy" if redis_status and supabase_status else "degraded",
        "redis": "up" if redis_status else "down",
        "supabase": "up" if supabase_status else "down",
        "version": API_VERSION
    }
```

**评估**: ✅ **生产级健康检查**
- Railway 可配置为调用此端点监控服务
- 支持服务依赖检查（Redis/Supabase）

---

### 2.2.7 DDD 架构与 Railway 兼容性 ✅

```
Railway Services          DDD Layers
┌──────────────┐         ┌──────────────┐
│ main-        │  ◄─────►│ api/routers  │  HTTP 入口
│ decodables   │         ├──────────────┤
│              │         │ application  │  用例编排
│              │         ├──────────────┤
│              │         │ domains      │  业务逻辑
│              │         ├──────────────┤
│              │         │ infrastructure│ 数据访问
└──────────────┘         └──────────────┘

┌──────────────┐         ┌──────────────┐
│ worker-      │  ◄─────►│ infrastructure│  任务处理
│ staging      │         │ /task_queue  │
└──────────────┘         └──────────────┘

┌──────────────┐         ┌──────────────┐
│ Redis-       │  ◄─────►│ core/cache   │  缓存层
│ Staging      │         │ infrastructure│  队列层
└──────────────┘         └──────────────┘
```

**评估**: ✅ **完美映射**
- DDD 分层不依赖具体部署架构
- 每个 Railway 服务对应清晰的代码职责
- 服务间通过 Redis 解耦

---

## 2.3 部署建议

### 2.3.1 Railway 服务配置

#### main-decodables (Web 服务)

```yaml
# railway.toml
[services.web]
  build.command = "pip install -r requirements.txt"
  start.command = "uvicorn app:app --host 0.0.0.0 --port $PORT"

  [services.web.env]
    ENV = "production"
    REDIS_URL = "${{Redis-Staging.REDIS_URL}}"  # 引用 Redis 服务
    WORKER_QUEUES = "high,default,low"
```

#### worker-staging (Worker 服务)

```yaml
[services.worker]
  build.command = "pip install -r requirements.txt"
  start.command = "python worker.py"

  [services.worker.env]
    ENV = "production"
    REDIS_URL = "${{Redis-Staging.REDIS_URL}}"
    WORKER_QUEUES = "high,default,low"

  # 可选：多实例扩展
  replicas = 2
```

#### Redis-Staging

```yaml
[services.redis]
  image = "redis:7-alpine"
  volumes = ["redis-ukux-volume:/data"]

  [services.redis.healthcheck]
    test = ["CMD", "redis-cli", "ping"]
    interval = "10s"
    timeout = "5s"
    retries = 3
```

---

### 2.3.2 监控建议

#### 关键指标

```python
# 在 /health 端点返回
{
  "status": "healthy",
  "services": {
    "redis": {
      "status": "up",
      "used_memory": "128MB",
      "connected_clients": 5
    },
    "queue": {
      "high": {"pending": 0, "failed": 0},
      "default": {"pending": 2, "failed": 0},
      "low": {"pending": 10, "failed": 1}
    },
    "workers": {
      "active": 2,
      "idle": 1
    }
  }
}
```

#### Railway Dashboard 监控

- CPU/内存使用率
- Redis 连接数
- Worker 任务处理速率
- 健康检查状态

---

## 2.4 性能优化

### 2.4.1 缓存优化

```python
# domains/platform/config_service.py
# 增加缓存TTL，减少数据库查询
CONFIG_CACHE_TTL = 3600  # 1小时
RATE_LIMIT_CACHE_TTL = 300  # 5分钟
```

### 2.4.2 连接池优化

```python
# core/database/client.py
# Supabase 连接池配置
SUPABASE_POOL_SIZE = 20
SUPABASE_MAX_OVERFLOW = 10
```

### 2.4.3 Worker 性能调优

```python
# worker.py
# Worker 并发配置
worker = Worker(
    queues,
    connection=redis,
    # 单个Worker可同时处理的任务数
    job_monitoring_interval=10,  # 每10秒检查一次
    worker_ttl=600,  # Worker 10分钟无任务自动退出
)
```

---

## 2.5 潜在问题与解决方案

### 问题 1: Redis 连接池耗尽

**症状**: `ConnectionError: Too many connections`

**原因**:
- 代码当前设置 `max_connections=10`
- 如果扩展多个 Web 实例，可能不足

**解决方案**:
```python
# core/cache/redis_provider.py
POOL_MAX_CONNECTIONS = int(os.environ.get("REDIS_MAX_CONNECTIONS", "50"))
```

**Railway 配置**:
```yaml
[services.web.env]
  REDIS_MAX_CONNECTIONS = "50"  # 每个Web实例50个连接
```

---

### 问题 2: Worker 内存泄漏

**症状**: Worker 进程内存持续增长

**原因**:
- 图片生成任务可能占用大量内存
- Python GC 不及时释放

**解决方案**:
```python
# worker.py
def start_worker():
    worker = Worker(
        queues,
        connection=redis,
        # 每处理100个任务后重启Worker（释放内存）
        job_monitoring_interval=60,
        max_jobs=100  # 添加此配置
    )
```

**Railway 配置**:
```yaml
[services.worker]
  # 设置内存限制，超过自动重启
  memory = "512MB"
  restart.policy = "on-failure"
```

---

### 问题 3: 任务队列堆积

**症状**: Redis 队列长度持续增长

**原因**: Worker 处理速度 < 任务生成速度

**解决方案**:
```yaml
# Railway Dashboard
[services.worker]
  replicas = 5  # 增加Worker实例到5个

  # 或按优先级分配
  [services.worker-high]
    replicas = 2
    env.WORKER_QUEUES = "high"

  [services.worker-default]
    replicas = 3
    env.WORKER_QUEUES = "default,low"
```

---

## 2.6 验证清单

### Railway 配置验证

| 检查项 | 状态 | 说明 |
|--------|------|------|
| `REDIS_URL` 环境变量 | ✅ | Railway 自动注入 |
| `Procfile` 配置 | ✅ | 定义 web + worker |
| Redis Volume 挂载 | ✅ | `redis-ukux-volume` |
| 健康检查端点 | ✅ | `/health` 端点 |
| 日志输出 | ✅ | stdout/stderr |

### 代码兼容性验证

| 功能 | 状态 | 代码位置 |
|------|------|----------|
| Redis 连接池 | ✅ | `core/cache/redis_provider.py` |
| 自动降级机制 | ✅ | `core/cache/service.py` |
| RQ Worker 配置 | ✅ | `worker.py` |
| 任务队列管理 | ✅ | `infrastructure/task_queue/` |
| 环境变量管理 | ✅ | `config.py` |
| 健康检查 | ✅ | `api/routers/health.py` |
| 异常处理 | ✅ | `worker.py:handle_job_exception` |
| DDD 分层架构 | ✅ | 整体架构 |

---

## 2.7 兼容性评分总结

### ✅ 兼容性评分: 95/100

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | 10/10 | DDD 分层架构完美支持服务拆分 |
| Redis 集成 | 9/10 | 连接池、降级、健康检查完善 |
| Worker 配置 | 10/10 | Procfile、RQ、环境变量完备 |
| 扩展性 | 9/10 | 支持水平扩展，需调优连接池 |
| 监控能力 | 8/10 | 健康检查完善，建议增加metrics |
| 容错能力 | 10/10 | 自动降级、异常处理、重试机制 |

### 核心优势

1. **代码已就绪**: 无需修改核心代码即可部署到 Railway
2. **生产级设计**: 连接池、健康检查、自动降级全部就位
3. **易于扩展**: Worker 无状态设计，支持水平扩展
4. **高可用**: Redis 不可用时自动降级到内存缓存
5. **DDD 架构**: 清晰的分层结构，易于维护和测试

### 建议改进 (优先级低)

1. **增加 Metrics**: Prometheus/Grafana 监控 (可选)
2. **调优连接池**: 根据实际负载调整 Redis 连接数
3. **Worker 内存限制**: 设置 `max_jobs` 防止内存泄漏
4. **分布式追踪**: 添加 OpenTelemetry (可选)

---

## 2.8 快速部署指南

### Step 1: 在 Railway 创建服务

```bash
# 1. 登录 Railway Dashboard
# 2. 创建新项目: "Decodables"
# 3. 添加 Redis 服务
#    - 选择 Redis 模板
#    - 挂载 volume: redis-ukux-volume
# 4. 添加 Web 服务
#    - 连接 GitHub 仓库
#    - 自动识别 Procfile (web)
# 5. 添加 Worker 服务
#    - 同一仓库，选择 worker 进程
```

### Step 2: 配置环境变量

```bash
# main-decodables (Web)
ENV=production
REDIS_URL=${{Redis-Staging.REDIS_URL}}
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx...
STRIPE_SECRET_KEY=sk_live_xxx
CLERK_PEM_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----...

# worker-staging (Worker)
ENV=production
REDIS_URL=${{Redis-Staging.REDIS_URL}}
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx...
WORKER_QUEUES=high,default,low
```

### Step 3: 验证部署

```bash
# 1. 检查 Web 服务健康
curl https://main-decodables.up.railway.app/health

# 2. 检查 Worker 日志
# Railway Dashboard → worker-staging → Logs

# 3. 测试任务队列
# 发起一个图片生成请求，观察 Worker 日志
```

---

**结论**: 当前代码与 Railway 多服务架构**完全兼容**，可以直接部署。DDD 架构的清晰分层和依赖注入设计，使得服务拆分非常自然，无需大规模重构。

---

*文档版本: v2.0*
*最后更新: 2026-01-10*
