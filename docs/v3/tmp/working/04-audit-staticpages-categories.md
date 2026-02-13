# 审计报告：静态页面CMS + 资产分类

## 静态页面CMS (Static Pages)

### 总结
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档一致性 | ⚠️ | v2详细(17字段+SEO)，v3过于简化 |
| 文档→API | ✅ | 7个端点100%覆盖 |
| API→前端 | ⚠️ | 参数映射问题 + 前端定义了后端未实现的字段 |
| 总体评分 | 🟡 7/10 | 核心CRUD完整，类型定义有偏差 |

### 问题清单
| 优先级 | 问题 |
|--------|------|
| P1 | PageStatus定义包含archived但后端不支持；筛选用status但后端用include_drafts |
| P1 | 前端types定义了9个后端未实现字段: template/content_format/robots/canonical_url/og_image/author_id/author_email/view_count |
| P2 | v3文档需同步v2设计详情 |

---

## 资产分类 (Asset Categories)

### 总结
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档一致性 | ❌ | v2设计为通用树形系统，v3硬编码10个分类，严重不一致 |
| 文档→API | ✅ | 7个端点100%覆盖 |
| API→前端 | 🔴 | 路径标识符错误 + HTTP方法错误 + 字段名不匹配 |
| 总体评分 | 🔴 4/10 | 前端实现与后端严重脱节 |

### 问题清单 (🔴 严重)
| 优先级 | 问题 |
|--------|------|
| P0 | 后端用slug标识资源，前端用id — 所有操作路径错误 |
| P0 | updateCategory前端用PUT，后端实际是PATCH |
| P0 | 字段名不匹配: 前端type vs 后端asset_type; 前端is_active vs 后端is_visible/is_featured |
| P1 | 前端缺失2个API调用: GET /tree (树形查询), GET /{slug}/resources (资源查询) |
| P1 | parent_id应为parent_slug (创建时) |
| P2 | v2/v3文档方向不一致，需澄清当前使用哪个版本 |

---

## v2.0 审计复核 (2026-02-13)

**复核结论**: ✅ 无新增发现。v1.0 问题清单仍然有效。

补充说明:
- **M1 (P2)**: AssetCategoriesPanel.tsx 达 985 行 (超标 3.3x)，属于前端超大文件问题 (CL-3.16)
- **M5 (P2)**: asset_categories.py 虽通过 Container DI，但与前端字段命名不一致属于 C1 问题的子集
