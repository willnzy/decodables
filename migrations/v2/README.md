# Schema v2 Migration - Production Ready

**Status**: ✅ Production Ready
**Last Updated**: 2026-01-10

---

## 📁 Directory Structure

```
migrations/v2/
├── refactored_schema_v2.sql       # 主迁移脚本 (3,100+ 行)
├── rollback_v2.sql                # 回滚脚本
├── 003_create_pricing_tables.sql  # 定价表迁移
├── docs/                          # 文档归档目录
└── archived/                      # 历史文件
```

---

## 🚀 Quick Start

### 1. 运行迁移

```bash
# 在 Supabase SQL Editor 或通过 psql 运行
psql "postgresql://..." -f refactored_schema_v2.sql
```

### 2. 验证结果

迁移完成后应看到:
```
✅ RLS Enabled: 45 tables
✅ Policies Created: 180 policies
✅ All tables protected with admin-only access
```

### 3. FastAPI 集成

在每次数据库查询前设置 admin role:

```python
from sqlalchemy import text

# 在查询前设置角色
await db.execute(text("SET app.current_user_role = 'admin'"))

# 然后执行正常查询
result = await db.execute(text("SELECT * FROM profiles"))
```

---

## 🔒 RLS (Row-Level Security) 说明

### 默认行为

- ✅ **RLS 已启用** (ENABLE ROW LEVEL SECURITY)
- ✅ **Admin-Only 策略** (所有表只有 admin 可访问)
- ✅ **无 UNRESTRICTED 警告** (所有表都有完整的策略)

### 如何工作

1. **is_admin() 函数**: 检查 `app.current_user_role` 是否为 `'admin'`
2. **4 个策略/表**: SELECT, INSERT, UPDATE, DELETE 都需要 admin
3. **FastAPI 集成**: 后端在查询前设置 session 变量

### 如果不需要 RLS

在生产环境如果使用 Railway/独立 PostgreSQL 且不需要 RLS，可以运行:

```sql
-- 禁用所有表的 RLS
ALTER TABLE profiles DISABLE ROW LEVEL SECURITY;
-- ... (重复所有表)
```

或使用提供的 `rollback_v2.sql` 然后重新运行不带 RLS 的迁移。

---

## 📊 Migration Features

### Critical Fixes (14/15 完成)
- ✅ 幂等性竞态条件修复
- ✅ 软删除触发器 NULL 处理
- ✅ Append-only 表保护 (credit_transactions)
- ✅ 事务包装 (BEGIN/COMMIT)
- ✅ 循环 CASCADE 修复
- ✅ 类型一致性修复
- ✅ CHECK 约束增强
- ✅ 外键完整性
- ✅ 日期验证
- ✅ 积分上限
- ✅ Stripe ID 格式验证
- ✅ 市场购买余额检查
- ⏳ 表分区 (延期 - 需生产数据)

### Warning Fixes (9/18 完成)
- ✅ 重复索引删除
- ✅ RLS 策略完整实现 (180+ policies)
- ✅ 输入验证增强
- ✅ Stripe 占位符检查
- ✅ 幂等性键格式验证
- ✅ GIN 索引优化
- ✅ Rollback 脚本
- ✅ user_code 格式验证
- ⏳ 其他优化 (延期 - 需生产指标)

---

## 📚 Documentation

详细文档已归档在 `docs/` 目录:

| 文档 | 用途 |
|------|------|
| FIXES_COMPLETION_SUMMARY.md | 修复完成总结 (23/33 issues) |
| VERIFICATION_REPORT.md | 代码验证报告 (100% 通过) |
| SCHEMA_REVIEW_REPORT.md | Schema 审查报告 |
| design_reasoning.md | 设计原理说明 (50KB) |
| mapping_and_changes.md | 映射和变更记录 (66KB) |

---

## ⚠️ Important Notes

### Stripe Price ID Placeholders

迁移中使用了 Stripe Price ID 占位符 (如 `{{ STRIPE_PRICE_T2 }}`),
需要在运行前替换为实际的 Stripe Price ID。

迁移完成后会自动检查并报告未替换的占位符。

### Production Checklist

运行迁移前确认:
- [ ] 已备份现有数据库
- [ ] 已替换所有 Stripe Price ID 占位符
- [ ] 已在 staging 环境测试
- [ ] FastAPI 后端已准备设置 `app.current_user_role`
- [ ] 了解 RLS 对查询的影响

---

## 🔄 Rollback

如需回滚迁移:

```bash
psql "postgresql://..." -f rollback_v2.sql
```

回滚脚本会:
1. 5 秒安全延迟
2. 删除所有 RLS 策略
3. 删除所有函数
4. 删除所有触发器
5. 删除所有表 (CASCADE)

---

**Questions?** 查看 `docs/` 目录中的详细文档
