# 01 - 用户管理 (含订阅) 审计报告

> 审计时间: 2026-02-12 ~ 2026-02-13 | 后端: users.py, subscriptions.py | 前端: /admin/users

---

## 1. 文档一致性

| 检查项 | v2-users.md | v2-user-ops.md | v3-users.md | 一致性 |
|--------|------------|----------------|------------|--------|
| 页面结构 | UserSearchPanel + UserDetailCard | 左侧搜索 + 右侧详情 | 分页 + 搜索 | ⚠️ 细节不一致 |
| 搜索参数 | 未指定 | 前后端不统一 (q/page/page_size vs search/offset/limit) | 未指定 | ❌ 前后端参数不对齐 |
| 管理操作 | 未列举 | 详细列举 (积分、Tier、退款、取消订阅、降级) | 仅列 Tier/积分/禁用 | ⚠️ 覆盖不完整 |
| Tier 变更 | 未提及 | POST /users/{user_id}/tier 已废弃(410)但前端仍调用 | 支持调整 Tier | ❌ API 已废弃但文档未同步 |
| 积分字段 | 未区分 | 前后端字段不统一 (credit_type vs bucket) | 仅提"积分余额" | ⚠️ 字段映射未明确 |
| 操作限流 | 无 | 读 30/min、写 10/min | 无 | ❌ v3 未继承限流要求 |
| 审计日志 | 无 | 强制记录 | 无 | ⚠️ v3 遗漏审计需求 |

**一致性评分**: ⚠️ 40%

## 2. 文档 → API 覆盖度

| 功能 | 文档提及 | 对应 API 端点 | 覆盖状态 |
|------|--------|------------|---------|
| 用户搜索 | ✅ | GET /users | ✅ |
| 用户详情 | ✅ | GET /users/{user_id} | ✅ |
| 按 Tier 筛选 | ✅ v2 | GET /users/by-tier/{tier} | ✅ 但v3未提及 |
| 积分调整 | ✅ | POST /users/{user_id}/credits | ✅ |
| Tier 变更 | ✅ | POST /users/{user_id}/tier | ❌ API已废弃(410) |
| 折扣创建 | ✅ v2 | POST /users/{user_id}/discount | ⚠️ 前端未调用 |
| 支付记录 | ✅ | GET /users/{user_id}/payments | ✅ |
| 项目列表 | ✅ | GET /users/{user_id}/projects | ✅ |
| 资产使用 | ✅ | GET /users/{user_id}/asset-usage | ✅ |
| 环境统计 | ✅ | GET /users/{user_id}/env-stats | ✅ |
| 项目恢复 | ✅ | POST /projects/{project_id}/restore | ✅ |
| 项目动态 | ✅ v2 | GET /projects/feed | ⚠️ 前端未调用 |
| 退款 | ✅ | POST /refund | ✅ |
| 取消订阅 | ✅ | POST /subscription/cancel | ✅ |
| 降级订阅 | ✅ | POST /subscription/downgrade | ✅ |
| 账户禁用/启用 | ✅ v3 | ❌ 不存在 | ❌ 功能缺失 |

## 3. API → 前端覆盖度

| API 端点 | 前端调用 | 状态 |
|----------|---------|------|
| GET /users | ✅ | ✅ |
| GET /users/{user_id} | ✅ | ✅ |
| GET /users/by-tier/{tier} | ❌ 未调用 | ⚠️ 功能未利用 |
| POST /users/{user_id}/credits | ✅ | ✅ |
| PATCH /users/{user_id} | ❌ 未调用 | ⚠️ 更新能力未用 |
| POST /users/{user_id}/tier | ❌ 调用已废弃API | ❌ 严重 |
| POST /users/{user_id}/discount | ❌ 未调用 | ⚠️ 折扣功能未暴露 |
| GET /users/{user_id}/payments | ✅ | ✅ |
| GET /users/{user_id}/projects | ✅ | ✅ |
| GET /users/{user_id}/asset-usage | ✅ | ✅ |
| GET /users/{user_id}/env-stats | ✅ | ✅ |
| POST /projects/{project_id}/restore | ✅ | ✅ |
| GET /projects/feed | ❌ 未调用 | ⚠️ 功能未利用 |
| POST /refund | ✅ | ✅ |
| POST /subscription/cancel | ✅ | ✅ |
| POST /subscription/downgrade | ✅ | ✅ |

## 4. 问题清单

| 编号 | 优先级 | 问题 | 审计维度 |
|------|--------|------|---------|
| C8 | 🔴 P0 | **跨层参数不匹配** — 前端 `admin/_lib/types.ts` 使用 `page/page_size`，后端已迁移到 `offset/limit` (v3.26+)，运行时分页失败。此问题为系统性问题，影响 users/logs/monitoring 等多个模块 | D17 |
| H1 | 🟡 P1 | **Tier 过滤使用显示名称** — users.py 的 by-tier 过滤使用 `free/starter/pro` 字符串而非标准 `t1/t2/t3/t4` 系统代码，若 Tier 显示名称修改则过滤逻辑失效 | D4 |
| H2 | 🟡 P1 | **订阅 Tier 白名单缺失** — subscriptions.py 的 `VALID_TARGET_TIERS` 白名单缺少 `t3` (Pro Plan)，管理员无法将用户切换到 Pro Plan | D4 |
| - | 🟡 P1 | 前端仍调用已废弃 POST /users/{user_id}/tier (返回 410) | D9 |
| - | ⚠️ | 4 个有效 API 端点前端未调用 (by-tier, PATCH, discount, feed) | D9 |
| - | ⚠️ | 前端 credit_type vs 后端 bucket 字段映射不统一 | D10 |

### 修复建议

1. **C8**: 前端 `admin/_lib/types.ts` 中分页类型从 `page/page_size` 改为 `offset/limit`，或 API 层添加兼容转换
2. **H1**: users.py 中 `free/starter/pro` 替换为 `TIER_T1/TIER_T2/TIER_T3` 常量
3. **H2**: `VALID_TARGET_TIERS` 列表添加 `t3`

## 5. 总评

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档一致性 | ❌ | 三份文档 5 处直接冲突 |
| 文档→API | ⚠️ | v3 遗漏 3 项功能，含已废弃 API |
| API→前端 | ⚠️ | 4 个有效 API 未调用；前端仍调用已废弃 Tier API |
| DDD 合规 | ✅ | users.py/subscriptions.py 均通过 Container DI |
| 安全加固 | ✅ | 速率限制已配置 |

**总体评分**: 🔴 低 — 优先修复废弃 API 调用 > C8 参数对齐 > 文档统一 > 功能补全

## 6. 跨层审计 (D17-D25) 复核

- D17 (参数一致性): 🔴 C8 — page/page_size vs offset/limit 系统性不匹配
- D18 (错误处理): ✅ 遵循标准模式
- D22 (鉴权): ✅ 认证 100%
- D25 (性能): ✅ 无 N+1 风险
