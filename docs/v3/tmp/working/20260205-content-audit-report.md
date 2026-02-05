# V3 文档内容审计报告

> **审计日期**: 2026-02-05
> **审计依据**: 实际代码实现
> **审计范围**: 核心业务文档 (05-business/, 04-engineering/)

---

## 审计摘要

| 文档 | 状态 | 主要问题 |
|------|------|----------|
| tier-system/overview.md | 🟡 | 缺少原价、t4 名称不一致 |
| credits-system/*.md | 🟡 | 充值价格不一致、配置项缺失 |
| user-id-system.md | 🔴 | **格式与代码严重不一致** |
| pricing-strategy.md | 🔴 | **数据库价格与文档不一致** |
| entitlement/*.md | 🟡 | 试用期天数不一致、Feature Key 不一致 |
| auth/architecture.md | 🟡 | JWT Payload 缺失、配置值不一致 |
| billing/architecture.md | 🟡 | Webhook 事件名称错误 |

---

## 一、严重问题 (🔴 P0 - 立即修复)

### 1.1 pricing-strategy.md - 数据库价格与文档不一致

| 项目 | 文档值 | 数据库值 | 差异 |
|------|--------|----------|------|
| Starter 现价 | $6.9 | $9.9 (990 cents) | **$3.0** |
| Pro 现价 | $9.9 | $19.9 (1990 cents) | **$10.0** |
| Starter 原价 | $9.9 | $14.9 (1490 cents) | $5.0 |
| Pro 原价 | $15.9 | $29.9 (2990 cents) | $14.0 |
| Starter 月度积分 | 100 | 200 | **100** |
| Pro 月度积分 | 200 | 500 | **300** |

**影响**: 用户实际付费金额与文档不符，可能导致计费纠纷。

**建议**: 
- 方案 A: 更新数据库配置 (`platform_config_seed.sql`) 以匹配文档
- 方案 B: 更新文档以匹配数据库（如果当前价格是正确的）

**位置**: `decodables/migrations/v2/seeds/platform_config_seed.sql`

---

### 1.2 user-id-system.md - 格式与代码严重不一致

| 项目 | 文档描述 | 实际代码 |
|------|----------|----------|
| 格式结构 | `YYMMDD(6) + HHMMSS(6) + mmmm(4) + 序号(7) + 随机(3)` | `YYMMDDHHMMSS(12) + 序列号(10) + 随机(4)` |
| 序号部分 | 用户总数+1 (7位) | PostgreSQL 序列号 (10位) |
| 随机数 | 3位 (000-999) | 4位 (0000-9999) |
| 毫秒部分 | 有 (4位) | 无 |

**影响**: 文档示例无法按实际格式解析，新人理解错误。

**建议**: 更新文档以匹配 PostgreSQL `generate_user_code()` 函数的实际实现。

**位置**: `decodables/migrations/v2/01_core_business.sql` 中的 `generate_user_code()` 函数

---

### 1.3 OCR 成本不一致

| 位置 | 值 |
|------|-----|
| pricing-strategy.md | 10 积分 |
| CLAUDE.md | **5 积分** (错误) |
| 前端 configApi.ts | **5 积分** (错误) |
| 数据库配置 | 10 积分 |
| 后端代码 | 10 积分 |

**建议**: 
1. 更新 CLAUDE.md: 5 → 10 积分
2. 更新前端 configApi.ts 默认值: 5 → 10 积分

---

## 二、中等问题 (🟡 P1 - 本周修复)

### 2.1 试用期天数不一致

| 位置 | 值 |
|------|-----|
| permission-matrix.md | 7 天 |
| 代码 constants.py | 30 天 |

**建议**: 确认产品需求，统一为 7 天或 30 天。

---

### 2.2 auth/architecture.md - 配置值不一致

| 项目 | 文档值 | 代码值 |
|------|--------|--------|
| OTP 有效期 | 5 分钟 | 10 分钟 |
| 账户锁定时间 | 15 分钟 | 30 分钟 |
| 最大活跃会话数 | 5 个 | 10 个 |
| JWT Audience | `make-decodables` | `make-decodables-api` |

**建议**: 更新文档以匹配代码（更宽松的配置），或修改代码以匹配文档（更严格的安全策略）。

---

### 2.3 auth/architecture.md - JWT Payload 缺失

文档声明 JWT 包含 `sid` 和 `jti`，但代码未实现。

**建议**: 
- 如果需要：在 `token_service.py` 中添加 `sid` 参数
- 如果不需要：从文档中移除

---

### 2.4 billing/architecture.md - Webhook 事件名称错误

| 项目 | 文档值 | 正确值 |
|------|--------|--------|
| 续期事件 | `invoice.paid` | `invoice.payment_succeeded` |

**建议**: 更新文档第 259 行。

---

### 2.5 billing/architecture.md - Webhook 事件列表不完整

文档缺失的事件：
- `invoice.payment_action_required`
- `charge.refunded`
- `customer.deleted`

**建议**: 补充到文档中。

---

### 2.6 充值档位价格微小不一致

| 档位 | 文档值 | 数据库值 | 差异 |
|------|--------|----------|------|
| 500 积分 | $13.46 | $13.49 | $0.03 |
| 2000 积分 | $47.84 | $48.00 | $0.16 |

**建议**: 统一价格（建议以数据库为准）。

---

### 2.7 tier-system/overview.md - 缺少原价信息

文档的 Tier 对比表缺少"原价"列，而 CLAUDE.md 和数据库都有原价配置。

**建议**: 在 overview.md 的表格中补充原价列。

---

### 2.8 Feature Key 命名不一致

| 文档值 | 代码值 |
|--------|--------|
| `feature.pdf_download` | `pdf_export` |
| `ai_generate_assets`, `ai_generate_page` (细分) | `ai_features` (统一) |
| `feature.smart_scan` | 未找到 |

**建议**: 统一 Feature Key 命名规范，更新文档或代码。

---

## 三、低优先级问题 (🟢 P2 - 按需修复)

### 3.1 API 端点路径文档过时

auth/architecture.md 使用旧路径：
- `/auth/forgot-password/send-otp` → 实际为 `/auth/otp/send`
- `/auth/forgot-password/verify-otp` → 实际为 `/auth/otp/verify`

**建议**: 更新文档以反映统一的 OTP 端点设计。

---

### 3.2 订阅升级流程描述不准确

billing/architecture.md 描述升级为"创建 Checkout Session"，但代码实际使用 `Subscription.modify()`。

**建议**: 更新文档，说明升级使用 `modify()` 而非创建新 Session。

---

### 3.3 t4 显示名称不一致

| 位置 | 值 |
|------|-----|
| overview.md | "Fourth Tier (预留)" |
| constants.py | "Enterprise Plan" |

**建议**: 统一命名，建议使用"预留"或明确 t4 的实际用途。

---

## 四、修复优先级汇总

### P0 - 立即修复 (影响计费/核心业务)

1. [ ] 确认并统一订阅价格和月度积分（数据库 vs 文档）
2. [ ] 更新 user-id-system.md 中的 user_code 格式
3. [ ] 修复 CLAUDE.md 和前端的 OCR 成本值 (5 → 10)

### P1 - 本周修复 (文档准确性)

4. [ ] 确认并统一试用期天数 (7天 vs 30天)
5. [ ] 更新 auth 配置值（OTP、锁定时间、会话数）
6. [ ] 修复 billing Webhook 事件名称
7. [ ] 补充 billing 缺失的 Webhook 事件
8. [ ] 统一充值档位价格
9. [ ] 补充 tier-system 原价信息
10. [ ] 统一 Feature Key 命名

### P2 - 按需修复 (优化类)

11. [ ] 更新 auth API 端点路径文档
12. [ ] 修正订阅升级流程描述
13. [ ] 统一 t4 显示名称
14. [ ] 添加 JWT sid/jti（如需要）

---

## 五、后续建议

1. **建立文档更新流程**: 代码变更时同步更新文档
2. **添加自动化检查**: 考虑添加 CI 检查，验证文档中的配置值与代码一致
3. **定期审计**: 每月进行一次文档与代码的对比审计

---

**审计完成时间**: 2026-02-05
**下次审计建议**: 2026-03-05
