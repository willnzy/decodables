# 系统审计综合标准 v1.0

> 本文档汇总自 5 份审计实践文档的所有有用审计点，作为 Make Decodables 项目代码审计的统一标准。

**版本**: 1.0
**日期**: 2026-02-12
**来源文档**:
- `20260201-systems-audit-prompts.md` — 18 系统审计模板 + 附录 A-G
- `20260130-audit-methodology.md` — 审计方法论 + Phase 5 用户流
- `00-execution-workflow.md` — 执行生命周期 SOP
- `verification-progress.md` — 验证统计 + 误报分析
- `fix-execution-playbook.md` — 修复执行手册

---

## 第一部分: 审计维度 (25 项)

### A. 后端维度 (D1-D8)

| ID | 维度 | 检查要点 |
|----|------|----------|
| D1 | **Router ↔ 文档对齐** | 每个 API 端点必须在设计文档中有对应描述；反向验证文档列出的端点必须在 router 中存在 |
| D2 | **Router ↔ Service 调用链** | Router handler 只调用 Service 方法，不直接访问 Repository 或数据库；验证参数传递完整性 |
| D3 | **Service ↔ Repository 数据流** | Service 层通过 Repository 接口操作数据；验证 Entity 返回类型 (非 dict)；检查事务边界 |
| D4 | **Repository ↔ 数据库 Schema** | Repository 查询字段与数据库表定义一致；检查索引覆盖查询条件；验证外键关系 |
| D5 | **错误处理链路** | 从 Repository 异常 → Service 业务异常 → Router HTTP 响应的完整转换链；检查异常吞没 |
| D6 | **认证与授权** | 所有端点有正确的 auth 装饰器/依赖；admin 端点使用 `require_admin`；用户端点验证资源归属 |
| D7 | **数据验证** | Pydantic schema 覆盖所有入参；必填/可选字段正确；枚举值与数据库 CHECK 约束一致 |
| D8 | **DDD 合规性** | 遵循 api → application → domains ← infrastructure 依赖方向；Service 不跨域直接调用其他 Repository |

### B. 前端维度 (D9-D16)

| ID | 维度 | 检查要点 |
|----|------|----------|
| D9 | **API 调用 ↔ 后端端点** | 前端 API 函数的 URL/Method/参数与后端 Router 完全匹配；注意 path 参数类型 (slug vs id) |
| D10 | **Hook/Store ↔ API 函数** | 每个 Hook/Store action 调用正确的 API 函数；检查参数映射和响应解构 |
| D11 | **组件 ↔ Hook/Store 消费** | 组件只通过 Hook/Store 获取数据；精确订阅具体字段避免不必要重渲染 |
| D12 | **TypeScript 类型一致性** | 前端 interface/type 定义与后端 Pydantic schema 字段名、类型完全一致 |
| D13 | **加载/错误/空状态** | 每个数据获取场景必须处理 loading/error/empty 三种状态；Skeleton 优于 Spinner |
| D14 | **表单验证** | 前端验证规则与后端 Pydantic 验证一致；用户友好错误消息 (非技术性) |
| D15 | **路由与权限** | 页面路由守卫与用户角色/tier 权限匹配；未授权时正确重定向 |
| D16 | **响应式设计** | Mobile-First；md (768px) 为桌面/移动分界；关键交互在移动端可用 |

### C. 跨层维度 (D17-D23)

| ID | 维度 | 检查要点 |
|----|------|----------|
| D17 | **端到端数据流** | 从用户操作 → 前端 → API → Service → DB → 响应 → 前端更新的完整链路验证 |
| D18 | **分页参数一致性** | DDD 规范: 使用 `offset` + `limit` (非 `page` + `limit`)；前后端参数名一致 |
| D19 | **排序/筛选参数** | 前端传递的 sort/filter 参数后端确实处理；未处理的参数不应出现在 UI |
| D20 | **缓存策略** | 前端缓存键与后端数据更新频率匹配；写操作后正确失效缓存 |
| D21 | **WebSocket/实时更新** | 如有实时功能，验证事件类型定义一致；重连机制；消息格式匹配 |
| D22 | **国际化** | 用户可见文本通过 i18n 系统；不硬编码文案；日期/数字格式本地化 |
| D23 | **安全审计** | SQL 参数化查询；XSS 防护 (html.escape)；敏感字段脱敏 (日志中的 password/token/email) |

### D. 用户流维度 (D24-D25) — 来自 Phase 5

| ID | 维度 | 检查要点 |
|----|------|----------|
| D24 | **页面数据加载状态** | 页面首次加载时所有数据源的 loading 编排；避免瀑布式加载；白屏防护 |
| D25 | **跨组件状态消费** | 多个组件消费同一 Store 时的状态同步；乐观更新一致性；竞态条件处理 |

---

## 第二部分: 审计检查清单 (Checklists)

### CL-3: 模块级检查清单

#### CL-3.2 后端 Router 检查
- [ ] 每个端点有文档对应 (D1)
- [ ] Handler 只调用 Service，不直接访问 Repository (D2)
- [ ] 正确使用 auth 依赖 (D6)
- [ ] 入参有 Pydantic schema 验证 (D7)
- [ ] 返回值有 response_model 定义
- [ ] 错误响应有统一格式 (status_code + detail)
- [ ] 分页使用 offset+limit (D18)

#### CL-3.3 后端 Service 检查
- [ ] 通过依赖注入获取 Repository (非直接实例化)
- [ ] 返回 Entity 对象 (非 dict) (D3)
- [ ] 多步操作使用事务保证原子性 (D3)
- [ ] 跨域数据通过 Application Service 协调 (D8)
- [ ] 业务异常有明确的异常类型 (D5)
- [ ] 日志为结构化格式 (event + extra)

#### CL-3.4 后端 Repository 检查
- [ ] 使用 Lazy Loading 模式 (属性访问时初始化 client)
- [ ] 接口使用 ABC + @abstractmethod
- [ ] 查询字段与数据库 schema 一致 (D4)
- [ ] 返回 Entity (通过 from_dict 转换)
- [ ] RPC 参数使用 `p_` 前缀

#### CL-3.5 数据库 Schema 检查
- [ ] 新表有 `updated_at` 触发器
- [ ] 新表有合理索引
- [ ] 软删除表索引使用 `WHERE deleted_at IS NULL`
- [ ] CHECK 约束覆盖枚举字段
- [ ] 外键关系正确且有索引
- [ ] 直接修改 v2 主 schema 文件 (01/02/03)，不创建新迁移文件

#### CL-3.6 前端 API 层检查
- [ ] URL 路径与后端 Router 完全一致 (D9)
- [ ] HTTP Method 正确 (GET/POST/PUT/PATCH/DELETE) (D9)
- [ ] Path 参数类型匹配 (slug vs id) (D9)
- [ ] Query 参数名与后端一致 (D18, D19)
- [ ] 请求/响应 TypeScript 类型与后端 Pydantic schema 一致 (D12)
- [ ] 使用 AbortController 支持请求取消

#### CL-3.7 前端 Store/Hook 检查
- [ ] 按领域拆分 Store (非单一大 Store) (D11)
- [ ] 组件精确订阅具体字段 (D11)
- [ ] 异步操作有 loading/error 状态 (D13)
- [ ] 写操作后正确更新本地状态或重新获取 (D20)
- [ ] 使用 Logger 类 (非裸 console.*)

#### CL-3.8 前端组件检查
- [ ] 处理 loading/error/empty 三种状态 (D13)
- [ ] 表单验证与后端一致 (D14)
- [ ] 路由权限守卫正确 (D15)
- [ ] Mobile-First 响应式 (D16)
- [ ] 错误消息用户友好 (getUserFriendlyMessage)

#### CL-3.9 端到端数据流检查
- [ ] 创建流: UI → Store → API → Router → Service → Repository → DB (D17)
- [ ] 读取流: DB → Repository → Service → Router → API → Store → UI (D17)
- [ ] 更新流: 含乐观更新回滚机制 (D25)
- [ ] 删除流: 软删除/硬删除一致 (D17)
- [ ] 批量操作: 事务原子性 + 前端批量状态更新 (D3)

#### CL-3.10 安全检查
- [ ] SQL 查询参数化 (D23)
- [ ] 用户输入 html.escape (D23)
- [ ] 日志脱敏 password/token/email/phone/card (D23)
- [ ] API 端点认证/授权正确 (D6)
- [ ] 敏感操作有速率限制

#### CL-3.11 用户流端到端检查 (Phase 5)
- [ ] 页面首次加载: 所有数据源并行获取 (非瀑布式)
- [ ] 数据依赖: 有依赖的请求正确串联
- [ ] 白屏防护: 关键数据加载失败时有 fallback UI
- [ ] 跨组件: 多组件消费同一 Store 时状态一致
- [ ] 竞态条件: 快速导航时旧请求不覆盖新数据

### CL-3 专项检查清单 (扩展)

#### CL-3.12 跨层审计检查
- [ ] 请求参数: 前端发送的字段名/类型 vs 后端接受的字段名/类型
- [ ] 响应格式: 前端期望的字段 vs 后端实际返回的字段
- [ ] 枚举值: 前端使用的枚举值 vs 后端 Schema/Validator 允许的枚举值
- [ ] 竞态保护: 所有数据获取 hook 是否有统一的竞态保护模式 (requestId)
- [ ] 上下文切换 (workspace/user) 时旧数据是否被正确丢弃
- [ ] 并发写入操作是否有乐观锁或幂等性保护
- [ ] 创建的 blob URL 是否在 unmount 时 revoke
- [ ] HTTP 请求是否在 unmount 时通过 AbortController 取消
- [ ] API 响应是否有运行时类型校验 (Zod/io-ts)
- [ ] 是否有不安全的 `as` 类型断言绕过 TypeScript 保护
- [ ] Application 层 Handler 是否通过 Domain Service 而非直接 Repository

#### CL-3.13 支付/金融系统专项检查
- [ ] CHECK 约束是否覆盖代码实际写入的所有枚举值
- [ ] 代码写入字段名是否与表定义完全一致 (amount vs amount_usd)
- [ ] 积分数值 (月度/注册赠送/AI 消耗) 是否都来自 TierService/system_configs
- [ ] 全局搜索硬编码数字 (50/100/500/1000) → 是否为业务配置值
- [ ] Webhook handler 是否防止重放攻击 (idempotency_key / 事件去重)
- [ ] 积分操作 (发放/扣减) 是否有幂等保护
- [ ] 列出所有导致同一业务结果的路径 (如: 取消订阅 = admin取消 + webhook取消 + unpaid自动取消)
- [ ] 每条路径是否执行了完整的副作用 (如: 清零月度积分 + 降级 tier + 记录 payment_record)
- [ ] 退费处理是否区分不同原始交易类型 (积分购买退费 vs 订阅退费)
- [ ] Stripe Customer 是否与系统用户绑定 (checkout 时传入 customer_id)
- [ ] 已有活跃订阅时是否拦截重复购买
- [ ] Webhook 签名验证是否显式设置 tolerance
- [ ] 所有需要处理的 Stripe event 类型是否都有对应 handler
- [ ] Stripe API 调用是否在 async 环境中正确处理 (run_in_threadpool)
- [ ] 关键环境变量缺失时是否 fail-fast (STRIPE_SECRET_KEY/STRIPE_WEBHOOK_SECRET)
- [ ] 涉及多表操作是否使用 RPC 保证原子性 (订阅开始/续费/取消/退费)
- [ ] 缓存是否有 TTL 过期机制 (TierService._cache)
- [ ] 是否有定时任务检测数据异常 (活跃订阅月度积分 >32 天未刷新)

#### CL-3.14 后端通用审计检查
- [ ] async 方法内是否有同步阻塞调用 (httpx.Client, time.sleep, 文件 I/O)
- [ ] 同步第三方 SDK (Stripe/OpenAI/FAL) 是否通过 run_in_threadpool 包装
- [ ] 重试逻辑是否使用 asyncio.sleep 而非 time.sleep
- [ ] asyncio.gather() 是否使用 return_exceptions=True
- [ ] asyncio.create_task() 是否保存引用防止 GC 回收
- [ ] Scheduler (APScheduler) 任务是否使用独立 DB client (非 FastAPI singleton)
- [ ] Scheduler 任务是否有超时保护 (asyncio.wait_for)
- [ ] 是否使用 Pydantic v2 语法 (model_config 替代 class Config)
- [ ] datetime.utcnow() → datetime.now(timezone.utc) (Python 3.12+ 推荐)
- [ ] APScheduler 任务是否设置 max_instances=1 (防重叠执行)
- [ ] 分布式部署时定时任务是否有 Redis 分布式锁 (SETNX)
- [ ] 全局单例 lazy init 是否有 asyncio.Lock() 保护 (TOCTOU 竞态)
- [ ] 关键 secret 是否支持双 key 轮换窗口

#### CL-3.15 前端专项审计检查
- [ ] 是否在 render 函数体中直接调用 setState (应使用 useEffect)
- [ ] useCallback/useMemo 依赖数组是否正确 (不含 JSON.stringify 等动态调用)
- [ ] error 是否用 useState 存储 (useRef 存储不触发重渲染)
- [ ] loading 状态在 early return 时是否正确重置
- [ ] 模块级 cache/变量是否会跨用户/workspace 泄漏
- [ ] Zustand Store 是否使用 selector 订阅 (非 get() 反模式)
- [ ] URL.createObjectURL() 创建的 blob URL 是否在 unmount 时 revoke
- [ ] 定时器 (setInterval/setTimeout) 是否在 useEffect cleanup 中清理
- [ ] window.addEventListener 是否有对应的 removeEventListener
- [ ] WebSocket/SSE 连接是否在 unmount 时关闭
- [ ] 是否有 empty catch 块静默吞掉错误
- [ ] 不可逆操作 (永久删除) 是否有确认对话框
- [ ] 用户 ID 拼接 URL 时是否使用 encodeURIComponent
- [ ] console.log 调试输出是否清理 (使用 createLogger)
- [ ] sessionStorage/localStorage 访问是否包裹 try/catch (隐私模式兼容)
- [ ] API 响应 Zod Schema 是否覆盖所有后端可能返回的枚举值

#### CL-3.16 组件复杂度与拆分检查
- [ ] 文件行数是否超过 300 行 (审视拆分)
- [ ] 单组件 useState 数量是否超过 15 个 (建议拆分 hooks)
- [ ] 单方法/函数是否超过 100 行 (建议拆分子函数)
- [ ] useCallback/useMemo 依赖数组是否超过 5 个 (职责过多信号)
- [ ] 是否存在 3+ 处 80% 以上相似的组件
- [ ] 请求/响应模型是否在多个文件重复定义
- [ ] 一个 hook 是否同时管理 列表+分页+搜索+删除+乐观更新+星标 (应拆分)
- [ ] API 路由文件是否超过 12+ 端点 (考虑按功能拆分)

#### CL-3.17 输入校验检查
- [ ] limit 参数是否有上界 (le=100), 不允许 limit=1000000
- [ ] offset 参数是否有下界 (ge=0)
- [ ] search/query 参数是否有 max_length (建议 200)
- [ ] ID 参数是否有 UUID 格式校验 — 且所有端点一致
- [ ] email 是否使用 Pydantic EmailStr 或正则校验
- [ ] 枚举参数 (role, status) 是否使用 Pydantic Literal/Enum 类型
- [ ] 文件上传 Content-Length 检查后再 read() (防大文件内存 DoS)
- [ ] MIME 类型验证是否配合 magic bytes (文件头) 验证
- [ ] SVG 文件上传后是否通过 sanitizer 移除 script/事件属性 (存储型 XSS)
- [ ] 文件扩展名是否使用白名单校验
- [ ] 前端校验规则与后端是否一致 (如 email 格式)

#### CL-3.18 分页一致性检查
- [ ] 所有端点是否统一使用 offset + limit (非 page + limit)
- [ ] 前端调用与后端接受的参数名是否完全一致
- [ ] 默认值是否一致 (如 limit 默认 20)
- [ ] total 是否返回真实总数 (非 len(items) 即当前页数量)
- [ ] 是否有 has_more 字段 (或前端能通过 total + offset 计算)
- [ ] 所有分页端点的响应格式是否统一
- [ ] offset 超出 total 时是否正确返回空页
- [ ] 前端 "加载更多" / 无限滚动是否正确判断终止条件

#### CL-3.19 可观测性与监控检查
- [ ] 所有 API 路由文件是否有 logger 实例
- [ ] 错误日志是否包含上下文信息 (user_id, endpoint, 参数)
- [ ] 日志中 user_id/email 是否做部分遮蔽
- [ ] Sentry 事件是否脱敏 request_body / response_body
- [ ] api_logs/error_logs 表 request_body JSONB 是否入库前脱敏敏感字段
- [ ] Admin 写操作 (退费/取消/降级) 是否有审计日志
- [ ] 审计日志是否包含: 操作人/操作对象/操作类型/操作前后值
- [ ] 是否使用 createLogger/logger.debug 替代 console.log
- [ ] 后端是否有 /health 端点
- [ ] 关键异步任务失败是否有告警
- [ ] 数据异常检测是否有定时任务

#### CL-3.20 软删除一致性检查
- [ ] 项目中使用了哪些软删除模式 (is_deleted+deleted_at vs status="deleted" vs is_active=false)
- [ ] 同一业务域内是否统一一种模式
- [ ] 列表查询是否过滤 is_deleted=false
- [ ] 计数查询是否排除已删除记录
- [ ] soft_delete 操作是否同时设置 is_deleted + deleted_at + recovery_expires_at
- [ ] 硬删除的实体误删是否可恢复 → 是否需要加软删除支持
- [ ] 同一业务域的 FK 是 CASCADE 还是 SET NULL 是否策略统一
- [ ] SET NULL FK 删除后产生的孤儿记录是否有清理机制
- [ ] created_by / updated_by 等用户引用是否有 ON DELETE 规则
- [ ] 软删除清理脚本是否按依赖顺序处理 (先子表后父表)

### CL-4: 最佳实践检查清单

#### CL-4.1 API 安全与设计
- [ ] BOLA/IDOR: 所有端点是否验证资源归属
- [ ] Broken Authentication: JWT 过期/刷新/吊销策略是否完整
- [ ] Excessive Data Exposure: API 响应是否只返回必要字段 (非 SELECT *)
- [ ] Rate Limiting: 所有端点是否有速率限制
- [ ] Mass Assignment: 是否限制客户端可写字段 (Pydantic 白名单模型)
- [ ] Security Misconfiguration: CORS/CSP/HTTPS 是否正确配置
- [ ] 错误响应格式是否统一 (统一 ErrorResponse schema)
- [ ] HTTP 方法是否语义正确 (GET 无副作用, DELETE 幂等)
- [ ] 路由命名是否 RESTful 一致 (复数名词, 嵌套资源)
- [ ] Access-Control-Allow-Origin 是否为白名单 (非 *)
- [ ] Access-Control-Allow-Credentials 与 Origin: * 是否互斥

#### CL-4.2 依赖管理与供应链安全
- [ ] npm audit / pip audit 是否定期执行
- [ ] 是否使用 lockfile (package-lock.json / poetry.lock) 锁定版本
- [ ] 是否有 Dependabot/Renovate 等自动更新工具
- [ ] 核心框架版本是否与项目声明一致 (Next.js 16.1.1 / FastAPI 0.128.0)
- [ ] peerDependency 冲突是否已解决
- [ ] requirements.txt 中所有包是否固定版本范围

#### CL-4.3 错误处理与韧性
- [ ] 用户错误 (4xx) 和系统错误 (5xx) 是否正确区分
- [ ] 系统错误是否不泄漏内部堆栈/SQL 语句
- [ ] 全局异常处理器 (FastAPI exception_handler) 是否覆盖所有异常类型
- [ ] 外部服务调用 (Stripe/FAL/Supabase) 是否有超时设置
- [ ] 重试逻辑是否使用指数回退 (注释与实现一致)
- [ ] 是否有熔断器 (Circuit Breaker) 或 fallback 机制
- [ ] 重试是否只对幂等操作 (GET/PUT)，非幂等 (POST) 需谨慎
- [ ] DB 查询是否有全局超时保护
- [ ] bare except: pass 是否已消除 (至少 logger.exception())
- [ ] 启动时是否验证所有外部依赖连接 — fail-fast
- [ ] 优雅关闭是否完整 (Scheduler 停止 → 连接清理 → Worker drain)
- [ ] Redis 不可用时是否 graceful fallback
- [ ] 是否配置全局 JSON 请求体大小限制 (如 10MB)
- [ ] 批量操作 API 的数组参数是否有最大长度校验
- [ ] 文件上传是否分块读取验证大小 (非 await file.read() 一次性读入内存)

#### CL-4.4 数据安全与隐私
- [ ] 密码/token/API key 是否从不在日志/响应/前端中暴露
- [ ] 用户 PII (邮箱/姓名) 是否有脱敏策略 (日志中部分遮蔽)
- [ ] 前端是否不存储敏感信息在 localStorage (使用 httpOnly cookie 或内存)
- [ ] Sentry before_send hook 是否脱敏 request_body 和 response_body
- [ ] 用户上传文件的原始文件名是否用 UUID 替代 (防 PII 泄露)
- [ ] 所有 API 通信是否强制 HTTPS
- [ ] Webhook 签名是否验证 (Stripe/Clerk)

#### CL-4.5 前端性能与 UX
- [ ] 长列表是否使用虚拟化 (react-window/react-virtuoso)
- [ ] 图片是否使用 next/image 优化 (lazy loading + responsive)
- [ ] 是否有不必要的全量重渲染 (React DevTools Profiler)
- [ ] Bundle size 是否合理 (next/bundle-analyzer)
- [ ] Error Boundary 是否覆盖关键页面区域 (非全页白屏)
- [ ] 网络失败是否有重试/降级 UI (非无限 loading)
- [ ] 乐观更新是否有回滚机制 (服务端失败时恢复 UI)
- [ ] 表单提交是否有防重复点击 (loading 状态 / debounce)

#### CL-4.6 SEO / GEO / AEO
- [ ] 每个页面是否有唯一的 `<title>` (50-60 字符)
- [ ] 每个页面是否有 `<meta name="description">` (120-160 字符)
- [ ] 是否有 `<meta name="robots">` (公开 index,follow / 非公开 noindex)
- [ ] 是否使用 `<link rel="canonical">` 避免重复内容
- [ ] 图片是否有 alt 属性
- [ ] HTML 语义标签是否正确使用 (main/article/nav/header/footer)
- [ ] 标题层级是否正确 (唯一 h1, 依次 h2-h6, 不跳级)
- [ ] 公开页面是否使用 Server Component / SSG / ISR (非全量 'use client')
- [ ] 是否通过 generateMetadata() 动态生成 title/description
- [ ] 是否有 app/sitemap.ts + app/robots.ts
- [ ] 关键页面 LCP < 2.5s, CLS < 0.1
- [ ] 是否有 Open Graph + Twitter Card meta 标签
- [ ] 是否有 JSON-LD 结构化数据 (Product/FAQPage/Organization schema)
- [ ] 关键内容是否以清晰段落+列表呈现 (AI 引擎易于提取)
- [ ] 关键问题是否以 "What is X?" / "How to X?" 格式呈现 (AEO)
- [ ] 多语言页面是否使用 hreflang
- [ ] 是否已注册 Google Search Console + Bing Webmaster Tools

#### CL-4.7 跨平台兼容性
- [ ] iOS: Safari 100vh 使用 CSS dvh 或 JS 替代方案
- [ ] iOS: 软键盘弹出时布局正常；Safe Area 使用 env(safe-area-inset-*)
- [ ] iOS: input 默认 font-size ≥16px (< 16px 触发自动缩放)
- [ ] Android: 软键盘弹出使用 visualViewport API 适配
- [ ] Android: 返回键行为合理 (关闭 modal > 返回上一页)
- [ ] Windows: 高 DPI (125%/150% 缩放) 布局正常
- [ ] Mobile: 触摸目标 ≥ 44x44px；底部导航避开系统手势区域
- [ ] Mobile: 下拉刷新不与浏览器原生下拉冲突 (overscroll-behavior: contain)
- [ ] Tablet: iPad Split View / Slide Over 多任务模式下正常显示
- [ ] Desktop: 超宽屏 (>1920px) 内容有 max-width 约束
- [ ] Desktop: 键盘导航 (Tab/Shift+Tab/Enter/Escape) 完整可用
- [ ] 折叠屏: 展开/折叠切换时布局自动适配
- [ ] Safari: backdrop-filter 加 -webkit- 前缀
- [ ] Safari: structuredClone 有 polyfill (15.4+ 才支持)
- [ ] Safari: 日期解析使用 ISO 8601 格式
- [ ] Firefox: scrollbar 自定义有 Firefox 兼容 (scrollbar-width + scrollbar-color)
- [ ] 是否配置了 browserslist 定义支持范围
- [ ] CSS autoprefixer 是否根据 browserslist 自动添加前缀
- [ ] 字体加载策略使用 font-display: swap

#### CL-4.8 测试覆盖
- [ ] Entity to_dict/from_dict 100% 覆盖
- [ ] API 集成测试验证 HTTP 状态码 (200/400/422)
- [ ] 业务异常路径有测试
- [ ] bug 修复附带回归测试
- [ ] 覆盖率 ≥60% (目标 75%+)

### CL-5: 技术栈特定检查

#### CL-5.1 FastAPI
- [ ] 路由函数 async def (所有 I/O 操作)
- [ ] Pydantic v2 模型 (非 v1)
- [ ] 依赖注入用 Depends()
- [ ] Background Tasks 用于非关键异步操作
- [ ] CORS 配置正确

#### CL-5.2 Next.js (App Router)
- [ ] Server Components vs Client Components 正确划分
- [ ] 'use client' 指令只在需要时添加
- [ ] Metadata API 用于 SEO
- [ ] 动态路由参数类型安全
- [ ] Image 组件用于图片优化

#### CL-5.3 Supabase
- [ ] RPC 用于复杂事务
- [ ] Row Level Security (RLS) 策略
- [ ] 实时订阅正确清理
- [ ] Storage 桶权限配置

#### CL-5.4 Zustand
- [ ] 按领域拆分 Store
- [ ] 精确订阅 (selector 函数)
- [ ] 异步 action 有 loading/error 状态
- [ ] DevTools 中间件 (开发环境)

#### CL-5.5 Stripe
- [ ] Webhook 签名验证
- [ ] 幂等键处理
- [ ] 价格 ID 通过配置管理 (非硬编码)
- [ ] 退款/争议处理流程

#### CL-5.6 Fabric.js
- [ ] Canvas 对象生命周期管理
- [ ] 事件监听正确清理
- [ ] 大画布性能优化
- [ ] 序列化/反序列化一致性

### CL-6: 部署与运维检查

#### CL-6.1 Railway (后端)
- [ ] 环境变量完整
- [ ] 健康检查端点
- [ ] 优雅关闭处理
- [ ] 日志聚合配置

#### CL-6.2 Vercel (前端)
- [ ] 构建优化 (tree-shaking)
- [ ] 环境变量区分 NEXT_PUBLIC_ 前缀
- [ ] Edge/Serverless 函数超时配置
- [ ] ISR/SSG 缓存策略

#### CL-6.3 CI/CD
- [ ] 构建通过后才能合并
- [ ] 测试通过后才能部署
- [ ] 前后端 Feature Key 一致性检查
- [ ] 数据库迁移在部署前执行

---

## 第三部分: 审计执行流程

### 3.1 审计生命周期 (5 阶段)

```
Phase 0: 准备 → 读取设计文档 + 代码结构 + ground-truth.json
Phase 1: 后端审计 → Router → Service → Repository → Schema (D1-D8)
Phase 2: 前端审计 → API 层 → Hook/Store → 组件 (D9-D16)
Phase 3: 跨层审计 → 数据流 → 参数一致性 → 安全 (D17-D23)
Phase 4: 用户流审计 → 页面加载 → 状态编排 → 竞态条件 (D24-D25)
```

### 3.2 每阶段 4 步骤模板

```
Step 1: 读取目标文件 (Router/Hook/Component)
Step 2: 对照检查清单逐项验证
Step 3: 记录发现 (Findings)
Step 4: 交叉验证 (与其他层对比)
```

### 3.3 六轮执行顺序 (基于依赖拓扑)

| 轮次 | 模块 | 依赖关系 |
|------|------|----------|
| R1 | Auth + Users + Configs | 基础设施层，被所有模块依赖 |
| R2 | Tiers + Feature Flags + Billing | 权限与计费层 |
| R3 | Content (Articles/Themes/Assets) | 核心业务层 |
| R4 | Editor + AI | 编辑器层 |
| R5 | Dashboard + Analytics + Notifications | 展示层 |
| R6 | Admin + Operations + Moderation | 管理层 |

### 3.4 会话管理策略

**上下文预算分配**:
- Phase 0 (准备): ≤15% 上下文
- Phase 1-4 (审计): 每阶段 ≤20%
- 汇总报告: ≤5%

**Agent 分片规则**:
- 每个 Agent 处理文件总量 ≤ 3000-4000 行
- Agent 返回格式: 结论摘要 + 问题列表 (禁止返回原文)
- 最多 3 个并行 Agent
- Agent prompt 必须包含完整的检查清单

**会话续接规则**:
- 每完成一个模块立即 commit
- commit message 包含下一步计划
- 超过 6 轮交互或 5 个文件修改 → 主动建议开新对话
- Forward-ref: 跨模块发现记录到 `forward-refs.md`，在目标模块轮次处理

---

## 第四部分: 发现报告标准

### 4.1 严重度定义

| 级别 | 定义 | 示例 |
|------|------|------|
| **P0 (Critical)** | 功能完全不可用或数据损坏风险 | 路径标识符错误 (slug vs id)；HTTP Method 错误；数据库字段不匹配 |
| **P1 (High)** | 功能部分受损或安全隐患 | 参数传递但后端不处理；缺失端点；认证缺失 |
| **P2 (Medium)** | 非阻塞但需改进 | 文档不一致；代码风格不统一；缺少错误处理 |
| **P3 (Low)** | 建议性改进 | 性能优化；代码简化；注释完善 |

### 4.2 发现编号规则

```
格式: {模块简写}-{严重度}-{序号}
示例: AUTH-P0-001, BILL-P1-003, EDIT-P2-012
```

### 4.3 单条发现报告模板

```markdown
### {编号}: {一行摘要}
- **维度**: D{N}
- **严重度**: P{0-3}
- **位置**: {文件路径}:{行号}
- **现状**: {当前代码行为}
- **期望**: {正确行为}
- **修复方案**: {具体修改建议}
- **影响范围**: {受影响的其他文件/功能}
```

### 4.4 严重度调整矩阵 (来自验证实践)

以下情况可将严重度 **下调**:

| 条件 | 调整 |
|------|------|
| 后端有默认值兜底，前端参数不传不影响功能 | HIGH → MED |
| 功能在 Admin 面板，用户不可见 | 可下调一级 |
| 已有其他路径达成相同目的 | 可下调一级 |
| 仅影响文档，不影响运行时 | 保持 P2+ |

### 4.5 误报识别 (8 类常见误报)

| 类型 | 描述 | 判断标准 |
|------|------|----------|
| FK 约束误报 | 表通过 RPC 或应用层关联 | 查 seed 数据和 RPC 函数 |
| useEffect 清理误报 | 组件不需要清理 | 确认是否有订阅/定时器 |
| 默认值兜底 | 后端有 fallback | 查 Service 层默认值处理 |
| 旧代码正常 | Legacy 代码但功能正确 | 查调用链是否完整 |
| 多路径实现 | 看似缺失但有替代路径 | 查全局搜索 |
| 条件性功能 | 功能受 Feature Flag 控制 | 查 feature_flags 表 |
| 环境差异 | 开发/生产配置不同 | 查环境变量 |
| 版本差异 | v2 vs v3 迁移过渡 | 查迁移计划 |

---

## 第五部分: 修复执行标准

### 5.1 八步修复 SOP

```
Step 1: 阅读 CLAUDE.md 和相关 guide
Step 2: 读取目标文件 (完整理解上下文)
Step 3: 确认修复方案 (向用户展示方案)
Step 4: 逐文件修改 (使用 Edit 工具)
Step 5: 同步修改测试文件
Step 6: 构建验证 (后端 pytest / 前端 npm run build)
Step 7: git commit + push
Step 8: 更新审计发现状态
```

### 5.2 五条铁律

1. **批次顺序**: 先 P0，再 P1，最后 P2；同优先级按依赖顺序
2. **单模块完成**: 一个模块的所有问题全部解决后才进入下一个
3. **审修分离**: 审计和修复不在同一个工作会话中进行
4. **禁止自动化脚本**: 绝对禁止 sed/awk/grep 批量修改代码
5. **先读后改**: 每次修改前必须先读取目标文件

### 5.3 Git 提交规范

```
格式: fix(audit): WS-{ID} - {description}
示例: fix(audit): WS-001 - align asset category slug/id parameters
```

### 5.4 共享文件冲突处理

当多个修复涉及同一文件:
1. **先修改者**: 增量修改，不改动无关代码
2. **后修改者**: 先拉取最新，在前者基础上继续
3. **最后集成者**: 验证所有修改无冲突
4. **删除阈值**: 单次删除 > 20 行必须解释原因

### 5.5 收敛跟踪

| 模块 | 初始发现 | 修复后剩余 | Delta | 状态 |
|------|----------|------------|-------|------|
| {模块名} | {N} | {M} | {N-M} | {收敛/未收敛} |

**收敛标准**: 连续 2 次 Delta 审计 (重新审核) 零新发现 = 该模块收敛

---

## 第六部分: 25 种标准修复模式

### F.1 安全类修复

| 模式 | 适用场景 | 修复方式 |
|------|----------|----------|
| SQL 参数化 | 字符串拼接 SQL | 改为参数化查询或 ORM |
| XSS 防护 | 用户输入直接输出 | `html.escape()` 编码 |
| 日志脱敏 | 日志含敏感信息 | 自动脱敏 password/token/email |
| 认证加固 | 端点缺少 auth | 添加 `require_admin` / `get_current_user` |
| 速率限制 | 无频率控制 | 添加 rate_limit 中间件 |

### F.2 架构类修复

| 模式 | 适用场景 | 修复方式 |
|------|----------|----------|
| DDD 迁移 | Router 直接调用 Repository | 添加 Service 层 |
| Entity 包装 | 返回 dict | 创建 Entity + from_dict/to_dict |
| 分页统一 | page+limit 混用 | 统一为 offset+limit |
| 事务包装 | 多步操作无原子性 | RPC 或 transaction 包装 |
| 依赖注入 | 硬编码依赖 | Depends() 或 Container |

### F.3 数据一致性修复

| 模式 | 适用场景 | 修复方式 |
|------|----------|----------|
| 字段名对齐 | 前后端字段名不匹配 | 以后端为准，修改前端映射 |
| 类型对齐 | slug vs id 混用 | 以数据库定义为准统一 |
| 枚举对齐 | 前后端枚举值不一致 | 建立共享枚举定义 |
| 参数对齐 | 查询参数名不匹配 | 以 API 文档为准对齐 |
| 状态码对齐 | 前端未处理特定状态码 | 补充错误处理分支 |

### F.4 前端类修复

| 模式 | 适用场景 | 修复方式 |
|------|----------|----------|
| Store 拆分 | 单一大 Store | 按领域拆分为独立 Store |
| 状态完整性 | 缺少 loading/error | 补充三态处理 |
| 类型迁移 | .js/.jsx 文件 | 迁移为 .ts/.tsx |
| 竞态处理 | 快速操作状态混乱 | AbortController + 版本号 |
| 响应式补全 | 移动端不可用 | Mobile-First 重构 |

### F.5 性能类修复

| 模式 | 适用场景 | 修复方式 |
|------|----------|----------|
| 并发 I/O | 顺序 await 多个请求 | `asyncio.gather()` |
| 线程分流 | CPU 密集阻塞事件循环 | `run_in_threadpool()` |
| 索引优化 | 慢查询 | 添加数据库索引 |
| 缓存策略 | 重复查询 | 添加适当缓存层 |
| 批量操作 | N+1 查询 | 批量查询 + 内存关联 |

---

## 第七部分: 质量保证方法论

### 7.1 模块质量评分 (6 维度)

| 维度 | 权重 | 评分标准 |
|------|------|----------|
| 文档覆盖率 | 15% | 0: 无文档, 5: 完整覆盖所有端点 |
| API 对齐度 | 25% | 0: 路径/方法错误, 5: 100%匹配 |
| 前端覆盖率 | 20% | 0: 无调用, 5: 所有端点有 UI |
| DDD 合规性 | 15% | 0: Router 直调 DB, 5: 完整分层 |
| 安全合规性 | 15% | 0: SQL 注入风险, 5: 全面防护 |
| 测试覆盖率 | 10% | 0: 无测试, 5: ≥75% 覆盖 |

**综合评分**: `Σ (维度分 × 权重)` → 映射到 10 分制

### 7.2 Anti-Local-Optima 五层防御

防止审计/修复陷入局部最优的 5 层机制:

1. **跨模块视角**: 不只看单模块，检查模块间的交互
2. **逆向验证**: 从用户操作倒推，验证每一层是否正确
3. **边界测试**: 空值、极值、并发、超时等边界场景
4. **根因追溯**: 发现一个问题后，追溯是否有相同根因的其他问题
5. **正向模式识别**: 记录优秀实现，作为其他模块的参考标准

### 7.3 正向模式识别

审计中发现的优秀实现应当记录，作为标杆:

```markdown
### 正向模式: {模块名} - {模式描述}
- **文件**: {路径}
- **亮点**: {为什么好}
- **可推广到**: {哪些模块可以学习}
```

### 7.4 根因分组方法

将多个发现归类到同一根因:

```
根因: {描述}
├── 发现 1: AUTH-P1-001
├── 发现 2: USER-P1-003
└── 发现 3: BILL-P2-007
修复策略: 修复根因一次性解决所有关联发现
```

---

## 第八部分: Delta 审计与收敛

### 8.1 Delta 审计规则

修复完成后执行增量审计:

1. **范围**: 只审计修改过的文件 + 其直接依赖
2. **对比**: 与初始发现清单对比
3. **新发现**: 修复引入的新问题需立即修复
4. **收敛判定**: 连续 2 次 Delta 审计零新发现 = 收敛

### 8.2 阻塞处理协议

| 阻塞类型 | 处理方式 |
|----------|----------|
| 需要用户决策 | 记录问题 + 列出选项 → 等待用户确认 |
| 需要其他模块先修复 | Forward-ref → 进入下一个模块 |
| 技术不确定 | 最小化假设 → 标记 ASSUMPTION → 继续 |
| 上下文溢出 | 立即 commit → 输出剩余任务清单 → 开新对话 |

### 8.3 三个正向反馈循环

1. **模式积累**: 每发现一个修复模式 → 加入标准模式库 → 加速后续审计
2. **基线强化**: 每修复一个模块 → 该模块成为其他模块的参考标准
3. **质量门积累**: 每过一个质量门 → 提高整体代码质量 → 降低新发现概率

---

## 第九部分: 修复方案方法论 (G.1-G.18)

### G.1 方案设计 6 原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | **根因驱动** | 从根因出发设计方案，不逐问题修补 |
| 2 | **重构式修复** | 完全替换有问题的实现，不保留旧代码 |
| 3 | **全局考量** | 方案覆盖所有审计发现，无遗漏 |
| 4 | **依赖顺序** | WS 之间有明确依赖图，按序执行 |
| 5 | **原子提交** | 每个 WS 独立完成、独立验证、独立提交 |
| 6 | **模式统一** | 同类问题用同一模式解决 |

### G.2 方案评估维度 (8 个)

| # | 评估维度 | 通过标准 |
|---|---------|---------|
| 1 | **覆盖完整性** | N/N (100%) findings 覆盖 |
| 2 | **全局考量** | 根因数 < 发现数的 10%；依赖图无环 |
| 3 | **业界最佳实践** | 每个 WS 核心思路可引用业界文献 |
| 4 | **根因修复** | 无 workaround/临时修复/if-else 特殊处理 |
| 5 | **稳定可靠** | 有 Error Boundary/原子操作/降级策略 |
| 6 | **低耦合模块化** | 共享组件/通用 hooks/统一工具层 |
| 7 | **代码可维护性** | 巨型文件拆分/类型安全/barrel exports |
| 8 | **架构规范合规** | 符合 CLAUDE.md DDD 分层/TypeScript 规则 |

### G.3 WS 排序原则

```
优先级从高到低:
1. 安全漏洞 (IDOR/注入/未授权) → 最先
2. 架构统一 (DDD/DI/分层)
3. 数据库/Schema (RPC/索引/RLS)
4. 输入校验/安全加固
5. 前后端契约对齐 (在前端修复之前)
6. 后端 Repository/Service 修复
7. 前端核心架构 (巨型组件拆分)
8. 前端 Hooks/Stores/Components
9. 类型安全/资源管理
10. 代码质量收尾 → 最后
```

### G.4 回归风险分析

| 修改类型 | 可能的副作用 | 检查方法 |
|---------|-------------|---------|
| RPC 函数新增/修改 | SQL 语法错误; 参数类型不匹配 | SQL Editor 中运行测试; 检查所有调用方 |
| 组件拆分 | 状态传递遗漏; 事件处理断裂; CSS 丢失 | 手动测试所有交互; 对比拆分前后 UI |
| Store/selector 迁移 | 订阅关系断裂; 派生状态计算错误 | React DevTools 检查; 验证所有消费者 |
| API 契约变更 | 前端解析失败; 第三方调用方不兼容 | Zod schema 更新; 检查所有调用方 |
| RLS 策略修改 | 正常查询被阻断; 权限过于宽松 | 用不同角色测试 |
| DI 依赖变更 | Container 初始化失败; 循环依赖 | 启动测试; 检查 Container 工厂 |
| 类型定义变更 | 条件渲染逻辑变化; TS 编译错误 | npm run build 全量检查 |

**风险评级**:
- 🔴 **高**: 涉及支付/积分/认证; 修改共享层; 影响 5+ 文件
- 🟡 **中**: 修改 Service/Repository; API 响应格式变更; 组件拆分
- 🟢 **低**: 前端样式/文案; 日志/注释; 增加校验 (只新增不修改)

### G.5 全局完成门禁 (3 层)

```
Level 1: WS 级门禁 (每个 WS 完成后)
├── build 通过 (后端 + 前端)
├── WS 内验证标准全部通过
├── git commit + push
└── 更新进度看板

Level 2: 批次级门禁 (一批并行 WS 完成后)
├── 该批次所有 WS 的 Level 1 全部通过
├── 跨 WS 集成验证 (依赖的 WS 之间是否兼容)
└── 无阻塞项遗留

Level 3: 全局完成门禁 (所有 WS 完成后)
├── 全量 build 通过
├── 审计发现覆盖率 100%
├── 回归验证: 核心用户流程手动走通
└── 审计报告标记所有 findings 为 "已修复"
```

### G.6 WS 组织方法

**从根因到 WS 的映射流程**:
```
根因归纳 (RC1-RCn)
  → 按修复领域分组 (后端安全/架构/数据库/前端/跨层)
  → 按依赖关系排序
  → 形成 WS 依赖图
  → 每个 WS 包含: 根因/解决问题列表/修改文件/验证标准
```

**WS 模板**:
```markdown
## WS{N}: {名称}
**根因**: RC{x} — {描述}
**解决**: {问题编号列表}
**优先级**: P{N}
### 核心思路
{重构式方案的设计理念}
### 修改文件
1. **`文件路径`** — 具体修改内容 ({问题编号})
### 验证
- 验证条件 1 ✓
- 验证条件 2 ✓
```

### G.7 依赖图规范

依赖图必须满足:
- 有向无环图 (DAG)
- 后端 WS 在前端 WS 之前
- 安全 WS 在功能 WS 之前
- 架构 WS 在业务 WS 之前
- 跨层 WS (契约对齐) 在纯前端 WS 之前
- 质量收尾 WS 最后执行

### G.8 风险评估模板

| 风险 | 概率 (低/中/高) | 影响 (低/中/高) | 缓解措施 |
|------|----------------|----------------|---------|
| {风险描述} | {概率} | {影响} | {具体措施} |

### G.9 验证标准

每个 WS 完成后必须执行:
1. 运行 build 验证 (后端 + 前端)
2. WS 特定验证条件
3. git commit + push
4. 更新审计报告标记已修复的问题

### G.10 方案范围决策

| 信号 | 决策 | 理由 |
|------|------|------|
| 问题只出现在 1 个文件 | 局部修复 | 影响范围小 |
| 同一问题出现在 3+ 个文件 | 架构重构 — 提取共享模式 | 根因是缺少统一模式 |
| 问题涉及跨层 (前端+后端) | 架构重构 — 对齐契约 | 单层修复不能解决 |
| 问题来自根因归纳 (RC) | 架构重构 — 从根因出发 | 逐问题修补会遗漏 |

### G.11 方案交叉验证流程

> 来自 Dashboard 修复方案 v1.0 遗漏 33 个 findings 的教训。

**Step 1**: 构建 Finding → WS 映射表 (每个 finding 标注归属 WS)
**Step 2**: 逐条验证 100% 覆盖 (未覆盖的 → 补充到 WS 或创建新 WS)
**Step 3**: 解决方案质量逐 WS 审查 (根因驱动 + 重构式 + 修复模式库)
**Step 4**: 依赖图验证 (DAG 无环 + 排序正确)
**Step 5**: 生成验证报告 (覆盖率 + 未覆盖 findings + WS 变更)

### G.12 方案迭代版本管理

```
v1.0: 初版方案 (基于审计报告设计)
v1.x: 补充遗漏 findings (交叉验证后)
v2.0: 架构合规修正 (代码探查后发现方案与实际不匹配)
v3.x: 实施过程中发现新问题
v4.0: 全部实施完成
```

| 触发条件 | 版本跳幅 |
|---------|---------|
| 交叉验证发现覆盖缺口 | +0.x |
| 代码探查发现方案与实际不符 | +1.0 |
| 实施中发现新审计问题 | +0.x |
| 全部实施完成 | → v4.0 |

### G.13 修复计划制定流程 (7 步)

```
Step 1: 审计报告输入 — 确认版本/总发现数/严重级别分布
Step 2: 根因归纳 (RC) — 合并相同根因, 目标: 根因数 < 发现数 10%
Step 3: RC → WS 映射 — 按修复领域分组, 1 WS 解决 1-3 个 RC
Step 4: 依赖图设计 — 画 DAG, 验证无环
Step 5: WS 详细设计 — 核心思路 + 修改文件 + 验证标准
Step 6: 方案交叉验证 (G.11) — 100% 覆盖
Step 7: 方案评估与定稿 — 8 评估维度 (G.2) + 回归风险 (G.4)
```

### G.14 WS 内部任务分解

| 原则 | 说明 |
|------|------|
| **单文件原子** | 每步修改 1 个文件 (最多 2-3 个强关联文件) |
| **先底层后上层** | Schema → Repository → Service → API → 前端 |
| **先新增后删除** | 新组件先创建, 旧代码最后删除 |
| **验证穿插** | 每完成一个逻辑单元即验证 |

### G.15 WS 间执行策略

| 策略 | 适用条件 |
|------|---------|
| **串行** | WS-B 的输入依赖 WS-A 的输出 |
| **并行** | 两个 WS 修改的文件无交集 |
| **流水线** | WS-B 只依赖 WS-A 的部分产出 |

### G.16 执行进度追踪

| WS | 名称 | 状态 | 步骤进度 | 阻塞 | 验证 |
|----|------|------|---------|------|------|
| WS1 | {名称} | ✅ 完成 | 5/5 | - | build ✓ |
| WS2 | {名称} | 🔄 进行中 | 3/12 | - | - |
| WS3 | {名称} | ⏳ 等待 | 0/9 | - | - |

### G.17 审计收敛机制

**三类新发现及处理**:

| 类型 | 场景 | 处理方式 |
|------|------|---------|
| **Forward-ref** | 审计系统 A 时发现系统 B 的问题 | 记录到 forward-ref, 注入系统 B 审计 |
| **Delta 发现** | 修复中发现变更文件的新问题 | fix-plan +0.x 版本, 仅对 git diff 文件审计 |
| **跨系统发现** | 综合审计暴露契约/竞态问题 | 归入现有 WS 或创建新 WS |

**两层收敛规则**:
```
第一层: 审计阶段 (只发现, 不修代码)
├── 所有系统全部审完后再开始修复
├── 避免"边审边改"导致审计基线漂移
└── 产出: fix-plan v1.0 (100% 覆盖)

第二层: 修复阶段 (delta 审计收敛)
├── 每个 WS 完成后仅审 git diff 涉及的文件
├── LOW 级发现记录但不阻塞, 汇总到最后
├── 收敛判定: 连续 2 个 WS 的 delta 审计零新发现 → 停止
└── 如果 >3 轮仍有新发现 → 方案架构有问题, 需重新评估
```

### G.18 审计质量保障 (Anti-Local-Optima 5 层防御)

#### 第 1 层: 架构基准线预加载 (审计前)
每个系统审计前必须先建立基准认知:
- 该系统的设计文档
- 项目规范化模式 (Hook/Store/Service/Error/API/Config/Component)
- 与当前系统相关的标准规则
- 前次审计同类系统的结论

#### 第 2 层: 根因链追溯 (审计中)
每个 finding 必须回答 5-Why 根因链 (至少 3 层):
```
症状 → 直接原因 → 根本原因 → 是否跨系统 → 修复层级
```

#### 第 3 层: 方案一致性验证 (方案设计时)
每个修复方案必须通过 3 项一致性检查:
1. **模式一致性**: 方案是否复用项目已有的规范化模式
2. **跨系统兼容性**: 修改共享文件是否兼容所有消费者
3. **架构层级正确性**: 修复是否在正确的层级 (禁止在高层级绕过低层级缺陷)

#### 第 4 层: 方案质量门禁 (方案定稿前)
每个 WS 必须通过 8 项质量门禁:
1. **幂等性**: 写操作重试不会创建重复数据
2. **竞态安全**: 多标签页同时操作/快速连续点击/响应乱序
3. **状态泄露**: 账户切换时 store 是否完全清理
4. **错误恢复**: 每个步骤失败后系统能否恢复到一致状态
5. **耦合度**: 方案是否增加了系统间的耦合
6. **可测试性**: 核心逻辑是否可单元测试
7. **可维护性**: 是否符合项目已有模式
8. **向后兼容**: 现有 API 消费者是否需要修改

#### 第 5 层: 全局交叉验证 (综合审计)
所有系统审计完成后执行:
1. **方案一致性矩阵**: 所有 WS 对同一关注点是否采用相同模式
2. **共享文件变更冲突检测**: 多个 WS 修改同一共享文件是否兼容
3. **全局回归风险评估**: 修改量最大的 5 个文件标注额外测试覆盖
4. **设计文档偏离检查**: 方案是否违反设计约束

**触发时机**:
```
准备 → 第 1 层 (预加载基准线)
审计中 → 第 2 层 (根因链追溯)
方案设计 → 第 3 层 (一致性验证)
方案定稿 → 第 4 层 (质量门禁)
综合审计 → 第 5 层 (全局交叉验证)
```

---

## 附录: 快速参考卡

### A. 审计启动检查

```
□ 读取 CLAUDE.md
□ 读取模块设计文档
□ 读取 ground-truth.json (如涉及 entitlement)
□ 确认审计维度适用列表
□ 准备发现记录模板
```

### B. 单模块审计输出格式

```markdown
# 审计报告: {模块名}

## 总结
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档一致性 | {状态} | {说明} |
| 文档→API | {状态} | {N/M 端点覆盖} |
| API→前端 | {状态} | {N/M 端点前端调用} |
| 总体评分 | {X/10} | {一句话评价} |

## 问题清单
| 优先级 | 问题 |
|--------|------|
| P0 | {描述} |
| P1 | {描述} |
| P2 | {描述} |
```

### C. 常用命令

```bash
# 后端测试
pytest tests/test_app_startup.py -v          # 冒烟测试
pytest tests/{module}/ -v                     # 模块测试

# 前端构建
npm run build                                 # 构建验证
npx tsc --noEmit                              # 类型检查
```

---

**文档版本**: v1.1
**最后更新**: 2026-02-12
**维护者**: Make Decodables 工程团队

**v1.0**: 初版，汇总 5 份源文档核心审计点
**v1.1**: 补充 CL-3 专项清单 (CL-3.12~3.20)、CL-4 扩展版 (OWASP/SEO/跨平台)、G.1-G.18 方法论
