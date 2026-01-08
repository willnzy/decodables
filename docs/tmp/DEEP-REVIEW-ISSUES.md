# 深度调用链审查 - 完整问题清单

> **审查日期**: 2026-01-08
> **审查模块**: 6 个
> **发现问题**: 72 个
> **审查深度**: API → Handler → Service → Repository 全链路

---

## 问题统计

| 模块 | P0 | HIGH | MEDIUM | 总计 |
|------|-----|------|--------|------|
| Billing | 2 | 5 | 1 | 8 |
| Generation Images | 3 | 3 | 9 | 15 |
| Payment | 3 | 5 | 7 | 15 |
| User Profile | 3 | 4 | 7 | 14 |
| Generation Story | 3 | 3 | 4 | 10 |
| Config | 3 | 3 | 4 | 10 |
| **总计** | **17** | **23** | **32** | **72** |

---

## Billing 模块 (8 问题)

### P0 (Critical) - 2 个

| 序号 | 问题 | 文件 | 行号 | 描述 | 影响 |
|------|------|------|------|------|------|
| B-P0-1 | `/credits/add` 无权限验证 | `api/user/billing.py` | 266-308 | 任何登录用户可调用 `POST /credits/add` 添加积分，缺少 admin/internal 授权检查 | 🔴 用户可无限添加积分 |
| B-P0-2 | CreditTransaction 缺失 id 字段 | `domains/billing/aggregates/user_credits.py` | - | API 返回 `tx.id` 但 `CreditTransaction` 领域对象未定义 `id` 属性，会抛出 AttributeError | 🔴 API 500 错误 |

### HIGH - 5 个

| 序号 | 问题 | 文件 | 描述 | 影响 |
|------|------|------|------|------|
| B-H1 | 退款 Bucket 选择错误 | `api/user/billing.py` | 退款时硬编码 `bucket=CreditBucket.PERMANENT`，违反"先月度后永久"扣费规则 | 用户可利用失败获得永久积分 |
| B-H2 | 事务隔离级别不明确 | `infrastructure/repositories/credit_repository.py` | `deduct_atomic` RPC 未显式指定事务隔离级别 | 并发问题 |
| B-H3 | 并发扣费竞态条件 | `domains/billing/service.py` | 多请求同时检查余额可能导致超扣 | 积分透支 |
| B-H4 | 错误消息暴露用户余额 | `api/user/billing.py:72` | `"Insufficient credits: need {required}, have {available}"` | 信息泄露 |
| B-H5 | idempotency_key 截断风险 | `api/user/billing.py` | UUID 只取前 8 字符 (`uuid.uuid4().hex[:8]`)，碰撞概率提升 | 重复扣费 |

### MEDIUM - 1 个

| 序号 | 问题 | 文件 | 描述 |
|------|------|------|------|
| B-M1 | 交易历史无索引优化 | `domains/billing/repository.py` | 大量交易时查询性能下降 |

---

## Generation Images 模块 (15 问题)

### P0 (Critical) - 3 个

| 序号 | 问题 | 文件 | 行号 | 描述 | 影响 |
|------|------|------|------|------|------|
| GI-P0-1 | 空 prompts 数组绕过计费 | `api/user/generation_images.py` | - | `prompts=[]` 时 `cost = len(prompts) * 5 = 0`，但仍可能触发 AI 调用 | 🔴 免费使用 AI |
| GI-P0-2 | 异步任务失败无退款 | `shared/ai/image_generator.py` | - | 后台生成任务失败后，已扣积分不会退还 | 🔴 用户损失积分 |
| GI-P0-3 | 参考图上传失败仍扣高价 | `api/user/generation_images.py` | - | `reference_image` base64 解析失败，仍按 premium 费率扣费 (10积分 vs 5积分) | 🔴 多扣费 |

### HIGH - 3 个

| 序号 | 问题 | 文件 | 描述 | 影响 |
|------|------|------|------|------|
| GI-H1 | 安全检查位置靠后 | `api/user/generation_images.py` | 先扣费后检查 `check_prompt_safety()`，安全违规时无退款 | 扣费后拒绝服务 |
| GI-H2 | FAL 回调无签名验证 | `api/user/generation_images.py` | FAL AI 回调端点无签名验证，外部可伪造回调注入假结果 | 安全漏洞 |
| GI-H3 | 生成超时无清理机制 | `shared/ai/image_generator.py` | 长时间挂起的任务持续占用资源，无超时清理 | 资源泄漏 |

### MEDIUM - 9 个

| 序号 | 问题 | 描述 |
|------|------|------|
| GI-M1 | prompts 数组无最大长度限制 | 可传入大量 prompts 触发巨额扣费 |
| GI-M2 | 单个 prompt 无字符长度限制 | 超长 prompt 可能导致 FAL API 超时 |
| GI-M3 | reference_image 无大小限制 | 大文件 base64 可能 OOM |
| GI-M4 | 生成结果未关联用户验证 | 获取生成结果时未验证所有权 |
| GI-M5 | 批量生成无进度反馈 | 多图生成时用户无法知道进度 |
| GI-M6 | 重试逻辑缺失 | FAL API 暂时性失败无自动重试 |
| GI-M7 | 图片存储 URL 未签名 | 生成的图片 URL 可被公开访问 |
| GI-M8 | 生成历史无分页优化 | 大量历史记录查询性能问题 |
| GI-M9 | 错误消息过于详细 | FAL 内部错误直接暴露给用户 |

---

## Payment 模块 (15 问题)

### P0 (Critical) - 3 个

| 序号 | 问题 | 文件 | 行号 | 描述 | 影响 |
|------|------|------|------|------|------|
| P-P0-1 | 异步/同步混用阻塞 | `api/user/payment.py` | 70 | 在 async 函数中同步调用 `create_checkout_session()`，阻塞事件循环 | 🔴 服务器性能下降 |
| P-P0-2 | 敏感信息泄露 | `api/user/payment.py` | 92 | `except Exception as e: raise HTTPException(500, str(e))` 暴露 Stripe 内部错误 | 🔴 安全漏洞 |
| P-P0-3 | customer_id 管理缺失 | `domains/billing/payment_service.py` | - | 新用户无 Stripe Customer ID，调用 portal 时失败 | 🔴 功能不可用 |

### HIGH - 5 个

| 序号 | 问题 | 文件 | 描述 | 影响 |
|------|------|------|------|------|
| P-H1 | 折扣获取无缓存 | `api/user/payment.py:75` | 每次 checkout 都查询数据库获取折扣 | 性能问题 |
| P-H2 | Portal URL 无过期处理 | `api/user/payment.py` | Stripe Portal URL 有时效，返回后可能已过期 | 用户体验差 |
| P-H3 | Stripe API Key 无启动验证 | `domains/billing/payment_service.py` | 环境变量缺失时静默失败 | 部署问题 |
| P-H4 | Rate Limit 配置不一致 | `api/user/payment.py` | checkout 5/min vs portal 10/min，缺乏统一策略 | 安全风险 |
| P-H5 | 幂等性窗口太短 | `domains/billing/payment_service.py:305` | 1 分钟窗口可能导致用户快速重试时创建重复会话 | 重复支付 |

### MEDIUM - 7 个

| 序号 | 问题 | 描述 |
|------|------|------|
| P-M1 | checkout 无取消回调处理 | 用户取消支付后无清理逻辑 |
| P-M2 | 价格 ID 硬编码依赖环境变量 | 缺少默认值和验证 |
| P-M3 | 折扣过期检查缺失 | 可能应用已过期的折扣 |
| P-M4 | 支付历史无导出功能 | 用户无法导出支付记录 |
| P-M5 | Webhook 重试策略未说明 | Stripe 重试时可能重复处理 |
| P-M6 | 货币硬编码为 USD | 不支持其他货币 |
| P-M7 | 退款流程未实现 | 管理员无法通过 API 发起退款 |

---

## User Profile 模块 (14 问题)

### P0 (Critical) - 3 个

| 序号 | 问题 | 文件 | 行号 | 描述 | 影响 |
|------|------|------|------|------|------|
| UP-P0-1 | Repository 方法名不匹配 | `api/user/profile.py` | 200 | API 调用 `mark_notification_read()` 但 Repository 定义为 `mark_as_read()` | 🔴 AttributeError |
| UP-P0-2 | is_member() 实现不一致 | `infrastructure/repositories/` | - | UserRepository 和 Profile 逻辑中 `is_member()` 判断条件不同 | 🔴 权限判断错误 |
| UP-P0-3 | 分页实现不匹配 | `api/user/profile.py` | - | API 使用 `page/limit` 参数，但 DDD 规范要求 `offset/limit` | 🔴 分页错误 |

### HIGH - 4 个

| 序号 | 问题 | 文件 | 描述 | 影响 |
|------|------|------|------|------|
| UP-H1 | Email 更新无验证 | `api/user/profile.py` | 可直接更新为任意 email，无验证流程 | 安全风险 |
| UP-H2 | Avatar URL 无校验 | `api/user/profile.py` | 可注入任意 URL 作为头像，XSS 风险 | 安全漏洞 |
| UP-H3 | 通知标记缺失权限检查 | `api/user/profile.py` | 可标记他人通知为已读 (只检查登录，未验证通知所有权) | 权限绕过 |
| UP-H4 | 头像上传无大小限制 | `api/user/profile.py` | API 层无文件大小验证，可上传大文件 | DoS 风险 |

### MEDIUM - 7 个

| 序号 | 问题 | 描述 |
|------|------|------|
| UP-M1 | 用户名无敏感词过滤 | 可设置不当用户名 |
| UP-M2 | Profile 更新无频率限制 | 可频繁更新触发大量数据库写入 |
| UP-M3 | 通知列表无已读/未读过滤 | 查询效率低 |
| UP-M4 | 头像删除无清理 | 旧头像文件未从存储中删除 |
| UP-M5 | 账户删除非软删除 | 无法恢复误删账户 |
| UP-M6 | 偏好设置无 schema 验证 | 可存入任意 JSON |
| UP-M7 | 活动日志无分页 | 大量活动时性能问题 |

---

## Generation Story 模块 (10 问题)

### P0 (Critical) - 3 个

| 序号 | 问题 | 文件 | 行号 | 描述 | 影响 |
|------|------|------|------|------|------|
| GS-P0-1 | 退款 Bucket 硬编码错误 | `api/user/generation_story.py` | 93 | 退款时 `bucket=CreditBucket.PERMANENT` 硬编码，应根据原扣费 bucket 决定 | 🔴 用户获得额外永久积分 |
| GS-P0-2 | Topic 无长度限制 | `api/schemas/user/generation.py` | 11-14 | `topic: str` 无最大长度，可发送超长内容触发 OpenAI API 超时 | 🔴 服务不可用 |
| GS-P0-3 | Inspiration fallback 掩盖错误 | `api/user/generation_story.py` | 184-213 | 所有异常返回 200 + hardcoded fallback，监控系统无法告警 | 🔴 故障不可见 |

### HIGH - 3 个

| 序号 | 问题 | 文件 | 描述 | 影响 |
|------|------|------|------|------|
| GS-H1 | Idempotency Key 碰撞风险 | `api/user/generation_story.py:56-61` | 毫秒时间戳 + 8字符 UUID，并发时碰撞概率高 | 重复扣费 |
| GS-H2 | 退款失败无恢复机制 | `api/user/generation_story.py:86-102` | 退款异常只记日志，无后台补偿任务 | 用户投诉 |
| GS-H3 | Story 生成无内容审核 | `api/user/generation_story.py` | 不像 Image 有 `check_prompt_safety()`，可生成不当内容 | 合规风险 |

### MEDIUM - 4 个

| 序号 | 问题 | 描述 |
|------|------|------|
| GS-M1 | 日志 topic 未转义 | `topic[:30]` 直接进入日志，CRLF 注入风险 |
| GS-M2 | Response 无明确 Schema | Story 返回结构由 AI 决定，客户端难以验证 |
| GS-M3 | Style 参数无白名单 | 可传入任意 style，可能被 prompt 注入 |
| GS-M4 | 生成结果未持久化 | Story 生成后不保存，用户刷新即丢失 |

---

## Config 模块 (10 问题)

### P0 (Critical) - 3 个

| 序号 | 问题 | 文件 | 行号 | 描述 | 影响 |
|------|------|------|------|------|------|
| C-P0-1 | 敏感配置无访问控制 | `api/user/config.py` | 45-72 | `GET /api/v2/user/config` 无认证，任何人可读取所有 `system_configs` | 🔴 敏感信息泄露 |
| C-P0-2 | 缓存中毒风险 | `infrastructure/repositories/config_repository.py` | 32-54 | 缓存过期检查逻辑有缺陷，可能返回过期数据 | 🔴 配置不一致 |
| C-P0-3 | 批量更新无原子性 | `api/admin/config.py` | 106-125 | 批量更新逐条执行，部分失败导致不一致状态 | 🔴 数据不一致 |

### HIGH - 3 个

| 序号 | 问题 | 文件 | 描述 | 影响 |
|------|------|------|------|------|
| C-H1 | Rate Limit 可被全局禁用 | `domains/platform/config_service.py:287-332` | 单 API 调用即可禁用所有限流，无二次确认 | 安全风险 |
| C-H2 | 配置值类型混乱 | `domains/platform/config_service.py:99-122` | JSON 解析失败降级为字符串，调用者期望 dict 得到 str | 类型错误 |
| C-H3 | 双重缓存不一致 | `infrastructure/repositories/config_repository.py` | Repository 缓存 + cache_service 缓存，清除时不同步 | 缓存污染 |

### MEDIUM - 4 个

| 序号 | 问题 | 描述 |
|------|------|------|
| C-M1 | 配置键无格式验证 | key 可包含危险字符，虽有 ORM 保护但应前置验证 |
| C-M2 | 管理员操作审计不完整 | 未记录旧值→新值变更，无操作理由 |
| C-M3 | 缓存 TTL 硬编码 | 300 秒硬编码，不可动态配置 |
| C-M4 | 错误处理过于宽泛 | 所有异常静默回退到默认值，难以调试 |

---

## 修复优先级排序

### 本周必须修复 (P0) - 17 个

| 优先级 | 问题 | 严重性 | 修复难度 |
|--------|------|--------|----------|
| 1 | B-P0-1 | `/credits/add` 无权限 | 🔴 最高 | 简单 |
| 2 | C-P0-1 | 配置无访问控制 | 🔴 最高 | 简单 |
| 3 | P-P0-2 | 敏感信息泄露 | 🔴 最高 | 简单 |
| 4 | GI-P0-1 | 空 prompts 绕过计费 | 🔴 最高 | 简单 |
| 5 | UP-P0-1 | 方法名不匹配 | 🔴 最高 | 简单 |
| 6 | B-P0-2 | CreditTransaction 缺 id | 🔴 高 | 中等 |
| 7 | GS-P0-1 | 退款 Bucket 错误 | 🔴 高 | 中等 |
| 8 | GS-P0-2 | Topic 无长度限制 | 🔴 高 | 简单 |
| 9 | GI-P0-2 | 异步失败无退款 | 🔴 高 | 复杂 |
| 10 | GI-P0-3 | 参考图失败仍扣费 | 🔴 高 | 中等 |
| 11 | P-P0-1 | 异步/同步混用 | 🔴 高 | 中等 |
| 12 | P-P0-3 | customer_id 缺失 | 🔴 高 | 中等 |
| 13 | UP-P0-2 | is_member 不一致 | 🔴 高 | 中等 |
| 14 | UP-P0-3 | 分页实现不匹配 | 🔴 高 | 中等 |
| 15 | GS-P0-3 | Fallback 掩盖错误 | 🔴 高 | 简单 |
| 16 | C-P0-2 | 缓存中毒 | 🔴 高 | 中等 |
| 17 | C-P0-3 | 批量更新非原子 | 🔴 高 | 复杂 |

### 下周修复 (HIGH) - 23 个

| 模块 | 问题数 | 主要问题 |
|------|--------|----------|
| Billing | 5 | 退款 Bucket、并发竞态、idempotency_key |
| Generation Images | 3 | 安全检查位置、FAL 回调验证、超时清理 |
| Payment | 5 | 折扣缓存、Portal 过期、幂等性窗口 |
| User Profile | 4 | Email 验证、Avatar XSS、通知权限、上传限制 |
| Generation Story | 3 | Idempotency 碰撞、退款恢复、内容审核 |
| Config | 3 | Rate Limit 禁用、类型混乱、双重缓存 |

### 后续迭代 (MEDIUM) - 32 个

主要为性能优化、用户体验改进和代码规范问题。

---

## 修复建议代码片段

### B-P0-1: /credits/add 添加权限验证

```python
# api/user/billing.py

from dependencies import require_admin  # 新增

@router.post("/credits/add")
async def add_credits(
    req: AddCreditsRequest,
    admin: dict = Depends(require_admin),  # 改为 admin 权限
):
    """
    Add credits to user account.

    Note: This endpoint requires admin permissions.
    """
    # ... 其余代码不变
```

### C-P0-1: Config API 添加白名单

```python
# api/user/config.py

PUBLIC_CONFIG_WHITELIST = {
    "FEATURE_AI_GENERATION",
    "FEATURE_MARKETPLACE",
    "FEATURE_OCR",
    "MAX_UPLOAD_FILE_SIZE_MB",
    # ... 仅 UI 相关配置
}

@router.get("/{key}")
async def get_config(key: str) -> Dict[str, Any]:
    if key not in PUBLIC_CONFIG_WHITELIST:
        raise HTTPException(403, "Access denied")
    # ... 其余逻辑
```

### GI-P0-1: 验证 prompts 非空

```python
# api/user/generation_images.py

@router.post("/generate")
async def generate_images(req: ImageGenRequest, ...):
    if not req.prompts or len(req.prompts) == 0:
        raise HTTPException(400, "At least one prompt is required")

    if len(req.prompts) > 10:
        raise HTTPException(400, "Maximum 10 prompts allowed")

    # ... 继续处理
```

### P-P0-2: 敏感信息不泄露

```python
# api/user/payment.py

except Exception as e:
    logger.error(f"Checkout error for user {user['id']}: {e}")
    raise HTTPException(500, "Failed to create checkout session")  # 不暴露 str(e)
```

### GS-P0-2: Topic 添加长度限制

```python
# api/schemas/user/generation.py

class StoryGenRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    style: Optional[str] = Field("Children's book illustration", max_length=200)
```

---

*生成日期: 2026-01-08*
*审查人: Claude Code*
*下次审查: 修复完成后*
