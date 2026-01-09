# Database Schema Review Report

**文件**: `refactored_schema_v2.sql`
**版本**: v4.0
**审查日期**: 2026-01-10
**审查工具**: Claude Code + Manual Review
**总行数**: 2,609 lines

---

## 执行摘要

通过系统性审查,发现 **15 个 Critical 问题** 和 **18 个 Warning 级别问题**。

### 修复状态

- ✅ **已修复**: 2/15 Critical
- 🚧 **进行中**: 0/15 Critical
- 📋 **待修复**: 13/15 Critical

---

## Critical Issues (🔴 必须修复)

### ✅ 1. Missing Idempotency Check in `deduct_credits_atomic`
- **状态**: 已修复 (Commit: bee2cc8)
- **行数**: 1840-1853
- **问题**: 并发调用可能导致重复扣费
- **修复**: 添加幂等性检查,基于 `idempotency_key` 防止重复执行

### ✅ 2. Soft Delete Trigger NULL Handling
- **状态**: 已修复 (Commit: bee2cc8)
- **行数**: 49-65
- **问题**: INSERT 操作时 OLD 为 NULL 会导致触发器崩溃
- **修复**: 添加 `IF OLD IS NULL THEN RETURN NEW` 检查

### 📋 3. Missing Trigger to Prevent credit_transactions Modification
- **状态**: 待修复
- **行数**: 273
- **问题**: `credit_transactions` 标记为 Append-Only 但没有数据库层面强制
- **建议修复**:
```sql
CREATE OR REPLACE FUNCTION prevent_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'credit_transactions is append-only table';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_credit_tx_prevent_modification
    BEFORE UPDATE OR DELETE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_modification();
```
- **影响**: 高 - 可能导致财务数据被意外修改

### 📋 4. Missing Balance Check in `execute_marketplace_purchase`
- **状态**: 待修复
- **行数**: 1975-2043
- **问题**: 函数不预先检查余额,依赖 `deduct_credits_atomic` 返回错误
- **建议修复**:
```sql
-- 在调用 deduct 之前添加
IF (SELECT credits_monthly + credits_permanent FROM profiles WHERE id = p_user_id) < v_price THEN
    RETURN QUERY SELECT FALSE, 'Insufficient credits';
    RETURN;
END IF;
```
- **影响**: 中 - 用户体验差,错误信息不清晰

### 📋 5. Inconsistent CHECK Constraint in `pricing_plans`
- **状态**: 待修复
- **行数**: 1278-1281
- **问题**: CHECK 约束不够严格,允许无效组合
- **当前约束**:
```sql
CHECK ((plan_type = 'subscription' AND billing_interval IS NOT NULL)
    OR (plan_type = 'credits' AND credits_amount IS NOT NULL))
```
- **问题**: 允许 `subscription` 同时有 `credits_amount`
- **建议修复**:
```sql
CHECK (
    (plan_type = 'subscription'
     AND billing_interval IS NOT NULL
     AND tier IS NOT NULL
     AND credits_amount IS NULL)
    OR
    (plan_type = 'credits'
     AND credits_amount IS NOT NULL
     AND billing_interval IS NULL
     AND tier IS NULL)
)
```
- **影响**: 中 - 可能存储无效的价格计划组合

### 📋 6. Circular Cascade Delete in `asset_categories`
- **状态**: 待修复
- **行数**: 573, 633
- **问题**: `parent_id` 使用 `ON DELETE CASCADE` + 软删除可能导致意外硬删除
- **建议修复**: 改为 `ON DELETE SET NULL`
- **影响**: 高 - 删除父分类可能级联删除所有子分类

### 📋 7. Missing Foreign Keys for `projects` Listing References
- **状态**: 待修复
- **行数**: 309-310
- **问题**: `marketplace_listing_id` 和 `source_listing_id` 没有外键约束
- **建议修复**:
```sql
ALTER TABLE projects
    ADD CONSTRAINT fk_projects_marketplace_listing
    FOREIGN KEY (marketplace_listing_id)
    REFERENCES marketplace_listings(id)
    ON DELETE SET NULL;

ALTER TABLE projects
    ADD CONSTRAINT fk_projects_source_listing
    FOREIGN KEY (source_listing_id)
    REFERENCES marketplace_listings(id)
    ON DELETE SET NULL;
```
- **影响**: 中 - 可能产生孤立引用

### 📋 8. Type Inconsistency in `user_price_overrides.user_id`
- **状态**: 待修复
- **行数**: 1344-1345
- **问题**: 定义为 `VARCHAR(100)` 但 `profiles.id` 是 `TEXT`
- **建议修复**: 改为 `TEXT NOT NULL`
- **影响**: 低 - 类型不一致可能导致隐藏的查询问题

### 📋 9. Missing Composite Index on `credit_transactions`
- **状态**: 待修复
- **行数**: 282-287
- **问题**: 常见查询 `WHERE user_id = X AND transaction_type = Y ORDER BY created_at DESC` 需要多次索引扫描
- **建议修复**:
```sql
CREATE INDEX idx_credit_tx_user_type_time
    ON credit_transactions(user_id, transaction_type, created_at DESC);
```
- **影响**: 高 - 用户交易历史查询性能差

### 📋 10. Missing Transaction Wrapping for Migration
- **状态**: 待修复
- **行数**: 全文件
- **问题**: 没有 BEGIN/COMMIT,失败时可能产生部分迁移
- **建议修复**:
```sql
BEGIN;
SET client_min_messages = WARNING;
-- ... 所有 DDL ...
COMMIT;
```
- **影响**: 高 - 迁移失败时数据库状态不一致

### 📋 11. Stripe Price ID Placeholders Not Validated
- **状态**: 待修复
- **行数**: 2283-2499
- **问题**: 使用 `{{ STRIPE_PRICE_XXX }}` 占位符,未验证
- **建议**: 部署前替换所有占位符,或添加应用层验证
- **影响**: 高 - 生产环境支付失败

### 📋 12. Missing Partitioning on Large Tables
- **状态**: 待修复
- **行数**: 223-273, 411-423, 441-475
- **表**: `credit_transactions`, `api_logs`, `ai_call_logs`
- **问题**: 时间序列表无分区,随时间增长性能下降
- **建议修复**: 实施按月分区
- **影响**: 高 - 长期性能问题

### 📋 13. Incomplete Snapshot in Marketplace Purchases
- **状态**: 待修复
- **行数**: 803-809, 1994-1995
- **问题**: `execute_marketplace_purchase` 只复制 5 个字段到快照
- **缺失字段**: `resource_url`, `category`, `source`
- **影响**: 中 - 审计追溯不完整

### 📋 14. Missing Validation for Date Ranges
- **状态**: 待修复
- **行数**: 153-155, 1390, 1799
- **问题**: 试用期和订阅日期没有 `end_date > start_date` 验证
- **建议修复**: 添加 CHECK 约束
- **影响**: 低 - 可能存储无效日期范围

### 📋 15. Expensive JSONB Operations in AI Aggregation
- **状态**: 待修复
- **行数**: 2137-2144
- **问题**: `upsert_ai_usage_daily` 频繁执行 JSONB 合并操作
- **建议优化**: 使用单独的整数计数器 + 只存储 Top 5 错误
- **影响**: 中 - AI 调用量大时性能下降

---

## Warning Issues (🟡 建议修复)

### 1. Duplicate Index on `profiles.email`
- **行数**: 200-201
- **问题**: UNIQUE 约束自动创建索引,显式索引重复
- **建议**: 删除显式 `CREATE INDEX`
- **影响**: 浪费存储空间

### 2. Missing Index on `projects.origin_owner_id`
- **行数**: 312
- **问题**: 外键列无索引
- **建议**: `CREATE INDEX idx_projects_origin_owner ON projects(origin_owner_id) WHERE origin_owner_id IS NOT NULL;`
- **影响**: 查询性能

### 3. No Row-Level Security Policies
- **位置**: 全局
- **问题**: Supabase 部署需要 RLS,当前未定义
- **建议**: 添加 RLS 策略保护多租户数据
- **影响**: 安全风险

### 4. No Input Validation in Functions
- **行数**: 1819-2147
- **问题**: 函数接受 TEXT 参数无长度检查
- **建议**: 添加长度和格式验证
- **影响**: DoS 风险

### 5. Weak Idempotency Key Format
- **行数**: 254, 801, 1413
- **问题**: TEXT 类型无格式约束
- **建议**: 添加 CHECK 约束验证格式
- **影响**: 弱防护

### 6. No Upper Bound on Credit Balances
- **行数**: 149-150
- **问题**: CHECK >= 0 但无上限,可能整数溢出
- **建议**: 添加 CHECK <= 1000000
- **影响**: 边界情况 bug

### 7. Price Type Inconsistency
- **行数**: 1278, 1409
- **问题**: 混用 cents(INT) 和 dollars(DECIMAL)
- **建议**: 统一使用 cents
- **影响**: 混乱和潜在舍入错误

### 8. JSONB Fields Without Size Limits
- **行数**: 420-421
- **问题**: `api_logs` JSONB 可能无限增长
- **建议**: 文档化最大大小或添加检查
- **影响**: 存储膨胀

### 9. Inefficient Partial Index Strategy
- **行数**: 1809
- **问题**: 注释说明不能用 VOLATILE 函数,但查询模式需要优化
- **建议**: 使用物化视图缓存活跃折扣
- **影响**: 每次查询全表扫描

### 10. Inconsistent ON DELETE CASCADE Usage
- **行数**: 228, 1138, 1698
- **问题**: 某些表用 CASCADE,可能意外删除重要数据
- **建议**: 审查每个 CASCADE,考虑改为 RESTRICT
- **影响**: 数据丢失风险

### 11. No GIN Indexes on Audit JSONB
- **行数**: 1316
- **问题**: `pricing_history.old_data/new_data` 无 GIN 索引
- **建议**: 如果查询 JSONB 内容,添加 GIN 索引
- **影响**: 审计查询慢

### 12. No Stripe ID Format Validation
- **行数**: 158-159, 1253-1254
- **问题**: Stripe 客户和订阅 ID 无格式验证
- **建议**: 添加 CHECK 约束验证前缀
- **影响**: 存储无效 ID

### 13-18. 其他性能和可维护性建议
- 缺少覆盖索引
- 缺少回滚脚本
- Timestamp 类型混用
- 缺少 `user_code` 格式验证
- 缺少 FK 索引
- 等等

---

## 建议的修复优先级

### P0 (立即修复)
1. ✅ 幂等性检查 (已修复)
2. ✅ 软删除触发器 (已修复)
3. 📋 Append-only 触发器
4. 📋 Transaction 包装
5. 📋 Stripe ID 占位符验证

### P1 (短期 - 1周内)
6. 📋 外键约束补全
7. 📋 复合索引优化
8. 📋 CHECK 约束加强
9. 📋 级联删除审查

### P2 (中期 - 1个月内)
10. 📋 表分区实施
11. 📋 RLS 策略
12. 📋 JSONB 操作优化
13. 📋 回滚脚本

---

## 测试建议

### 并发测试
```python
# 测试幂等性
async def test_idempotency():
    key = "test-key-123"
    results = await asyncio.gather(
        deduct_credits(user_id, 100, key),
        deduct_credits(user_id, 100, key),
        deduct_credits(user_id, 100, key)
    )
    assert results.count(True) == 1  # 只有一个成功
    assert results.count(False) == 2  # 两个被拒绝
```

### 触发器测试
```sql
-- 测试软删除触发器不阻止 INSERT
INSERT INTO projects (user_id, title, is_deleted)
VALUES ('user_test', 'Test Project', FALSE);

-- 测试软删除设置 deleted_at
UPDATE projects SET is_deleted = TRUE WHERE id = '...';
SELECT deleted_at FROM projects WHERE id = '...';  -- 应该不为 NULL
```

### 约束测试
```sql
-- 测试 pricing_plans CHECK 约束
INSERT INTO pricing_plans (plan_type, billing_interval, credits_amount)
VALUES ('subscription', 'month', 100);  -- 应该失败 (subscription 不应有 credits_amount)
```

---

## 总结

Schema 整体结构良好,但存在一些关键的并发安全和数据完整性问题。

**优点**:
- ✅ 完整的审计字段
- ✅ 良好的命名规范
- ✅ 详细的注释
- ✅ 合理的 DDD 架构

**风险点**:
- 🔴 并发控制不足
- 🔴 缺少数据验证
- 🔴 外键约束不完整
- 🔴 无事务保护

**建议**: 在生产部署前至少完成 P0 级别的所有修复。

---

**审查者**: Claude Code
**最后更新**: 2026-01-10
**下次审查**: 修复完成后

**END OF REPORT**
