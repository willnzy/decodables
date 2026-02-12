# 审计报告：主题管理 + 文章管理

## 主题管理 (Themes)

### 总结
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档一致性 | ⚠️ | v2/v3互补但不完整，v3仅概览 |
| 文档→API | ✅ | 13个端点全部有文档对应 |
| API→前端 | ⚠️ | 2个端点前端已定义但后端未实现 |
| 总体评分 | 🟡 7/10 | 核心完整，batch-generate preview/status缺失 |

### 问题清单
| 优先级 | 问题 |
|--------|------|
| P0 | 后端缺失: GET /themes/batch-generate/preview (前端已调用) |
| P0 | 后端缺失: GET /themes/batch-generate/{jobId} (前端已调用) |
| P2 | v3文档过于简化，需同步v2的设计详情 |

---

## 文章管理 (Articles)

### 总结
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档一致性 | ⚠️ | v2设计文档详细(含实现边界)，v3过于简化 |
| 文档→API | ⚠️ | search/status/sort参数为前端占位，后端未实现 |
| API→前端 | ⚠️ | 2个端点后端缺失: check-slug, stats |
| 总体评分 | 🟢 8/10 | 核心CRUD完整，辅助功能可选 |

### 问题清单
| 优先级 | 问题 |
|--------|------|
| P1 | search/status/sort_by/sort_order 前端传递但后端不处理 |
| P1 | 后端缺失: GET /articles/check-slug (slug唯一性校验) |
| P1 | 后端缺失: GET /articles/stats (文章统计) |
| P2 | v3文档需同步v2设计 |
