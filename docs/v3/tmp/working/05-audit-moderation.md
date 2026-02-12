# 审计报告：内容审核 (Moderation)

### 总结
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档一致性 | ⚠️ | v3标记为待补充，字段命名不一致(response vs resolution_note) |
| 文档→API | ✅ | 10个端点100%覆盖 |
| API→前端 | ✅ | 10个端点100%前端调用验证通过 |
| 总体评分 | 🟢 8.8/10 | 架构合理，细节差异需补齐 |

### 问题清单
| 优先级 | 问题 |
|--------|------|
| P1 | v3文档待补充(仅49行)，需对标v2结构扩展至200+行 |
| P1 | response vs resolution_note 命名不统一(v2用response，v3用resolution_note) |
| P1 | 前端未映射 reviewed_by/reviewed_at 字段，无法显示审核员信息 |
| P2 | ReportStats 缺少 by_reason / by_target_type 聚合统计(v3文档定义了但未实现) |
| P2 | submitted_at 时间映射用了 updated_at 代替，语义不准确 |
