# daily_themes 表 Schema 更新计划

> **版本**: v2.1
> **日期**: 2026-01-12
> **状态**: 执行中
> **关联文档**: `docs/shared/theme-system-design.md`

---

## I. 现有字段清单 (21 个)

| # | 字段名 | 类型 | 说明 |
|---|--------|------|------|
| 1 | id | UUID | 主键 |
| 2 | name | TEXT NOT NULL | 主题名称 |
| 3 | title | TEXT | name 的别名 (向后兼容) |
| 4 | description | TEXT | 描述 |
| 5 | is_active | BOOLEAN | 是否启用 |
| 6 | priority | INTEGER | 优先级 |
| 7 | date | DATE | 具体日期 |
| 8 | date_rule | JSONB | 日期规则 |
| 9 | thumbnail_url | TEXT | 缩略图 |
| 10 | preview_urls | TEXT[] | 预览图数组 |
| 11 | featured_asset_ids | UUID[] | 精选素材 ID |
| 12 | recommended_categories | TEXT[] | 推荐分类 |
| 13 | tags | TEXT[] | 标签 |
| 14 | theme_config | JSONB | 主题配置 |
| 15 | status | TEXT | 状态 (draft/active/archived) |
| 16 | metadata | JSONB | 元数据 |
| 17 | created_at | TIMESTAMPTZ | 创建时间 |
| 18 | updated_at | TIMESTAMPTZ | 更新时间 |
| 19 | is_deleted | BOOLEAN | 软删除标记 |
| 20 | deleted_at | TIMESTAMPTZ | 删除时间 |
| 21 | recovery_expires_at | TIMESTAMPTZ | 恢复过期时间 |

---

## II. 新增字段清单 (19 个)

### A. 分类信息 (1 个)

| # | 字段名 | 类型 | 默认值 | 说明 |
|---|--------|------|--------|------|
| 1 | category | TEXT | 'holiday' | 主题分类: holiday/memorial/historical/notable/campaign/special |

### B. 国际化字段 (3 个)

| # | 字段名 | 类型 | 默认值 | 说明 |
|---|--------|------|--------|------|
| 2 | name_i18n | JSONB | '{}' | 多语言名称 {"en": "...", "zh": "..."} |
| 3 | slogan | TEXT | NULL | 标语 (主语言) |
| 4 | slogan_i18n | JSONB | '{}' | 多语言标语 |
| 5 | description_i18n | JSONB | '{}' | 多语言描述 |

### C. 地区控制 (1 个)

| # | 字段名 | 类型 | 默认值 | 说明 |
|---|--------|------|--------|------|
| 6 | regions | TEXT[] | ARRAY[]::TEXT[] | 适用地区 ['US', 'CN', 'GLOBAL'] |

### D. 营销活动关联 (1 个)

| # | 字段名 | 类型 | 默认值 | 说明 |
|---|--------|------|--------|------|
| 7 | linked_campaign_id | UUID | NULL | 关联的营销活动 ID (FK → campaigns.id) |

### E. AI 生成字段 (4 个)

| # | 字段名 | 类型 | 默认值 | 说明 |
|---|--------|------|--------|------|
| 8 | ai_generated | BOOLEAN | false | 是否 AI 生成 |
| 9 | ai_alternatives | JSONB | '[]' | AI 备选方案数组 [{id, name, config, created_at}] |
| 10 | selected_alternative_id | TEXT | NULL | 已选中的备选方案 ID |
| 11 | ai_recommended_id | TEXT | NULL | AI 推荐的方案 ID |

### F. 外部链接 (2 个)

| # | 字段名 | 类型 | 默认值 | 说明 |
|---|--------|------|--------|------|
| 12 | source_url | TEXT | NULL | 信息来源 URL |
| 13 | learn_more_url | TEXT | NULL | 了解更多 URL |

### G. 审核工作流 (4 个)

| # | 字段名 | 类型 | 默认值 | 说明 |
|---|--------|------|--------|------|
| 14 | review_status | TEXT | 'pending' | 审核状态: pending/auto_approved/reviewed/rejected |
| 15 | reviewed_by | TEXT | NULL | 审核人 user_id |
| 16 | reviewed_at | TIMESTAMPTZ | NULL | 审核时间 |
| 17 | review_notes | TEXT | NULL | 审核备注 |

### H. 重新生成历史 (2 个)

| # | 字段名 | 类型 | 默认值 | 说明 |
|---|--------|------|--------|------|
| 18 | generation_history | JSONB | '[]' | 生成历史 [{timestamp, reason, by, snapshot}] |
| 19 | regenerate_count | INTEGER | 0 | 重新生成次数 |

---

## III. 新增索引清单 (5 个)

| # | 索引名 | 字段 | 类型 | 说明 |
|---|--------|------|------|------|
| 1 | idx_daily_themes_category | category | B-tree | 分类查询 |
| 2 | idx_daily_themes_regions | regions | GIN | 地区数组查询 |
| 3 | idx_daily_themes_review_status | review_status | B-tree (部分) | 审核状态过滤 (WHERE is_deleted = false) |
| 4 | idx_daily_themes_date | date | B-tree (部分) | 日期查询 (WHERE is_deleted = false) |
| 5 | idx_daily_themes_ai_generated | ai_generated | B-tree (部分) | AI 生成标记 (WHERE is_deleted = false) |

---

## IV. 新增约束清单 (2 个)

| # | 约束名 | 类型 | 约束内容 |
|---|--------|------|----------|
| 1 | chk_daily_themes_category | CHECK | category IN ('holiday', 'memorial', 'historical', 'notable', 'campaign', 'special') |
| 2 | chk_daily_themes_review_status | CHECK | review_status IN ('pending', 'auto_approved', 'reviewed', 'rejected') |

---

## V. 外键关系 (1 个)

| # | 约束名 | 字段 | 引用 | ON DELETE |
|---|--------|------|------|-----------|
| 1 | fk_daily_themes_campaign | linked_campaign_id | campaigns(id) | SET NULL |

---

## VI. 更新后字段总览 (40 个)

```
总字段数: 21 (现有) + 19 (新增) = 40 个
新增索引: 5 个
新增约束: 2 个 CHECK + 1 个 FK = 3 个
```

---

## VII. 执行步骤

### Step 1: 更新 Schema 文件 ✅ 完成

- [x] 修改 `migrations/v2/02_platform_services.sql`
- [x] 在 `daily_themes` 表中添加 19 个新字段
- [x] 添加 2 个 CHECK 约束
- [x] 添加 1 个外键约束
- [x] 添加 5 个索引

### Step 2: 验证 ✅ 完成

- [x] 检查 SQL 语法正确性
- [x] 验证字段顺序和注释

### Step 3: 提交代码 ⏳ 进行中

- [ ] git add migrations/v2/02_platform_services.sql
- [ ] git commit -m "feat(schema): add v2.1 fields to daily_themes table"
- [ ] git push

---

## VIII. 注意事项

1. **外键依赖**: `campaigns` 表必须存在 (已确认在 line 539)
2. **字段顺序**: 新字段按功能分组添加，保持代码可读性
3. **默认值**: 所有新字段都有合理默认值，确保向后兼容
4. **部分索引**: 使用 `WHERE is_deleted = false` 减少索引大小

---

## IX. 回滚策略

如需回滚，直接使用 Git:

```bash
git checkout HEAD^ -- migrations/v2/02_platform_services.sql
git commit -m "revert: rollback daily_themes schema changes"
git push
```

---

**最后更新**: 2026-01-12
