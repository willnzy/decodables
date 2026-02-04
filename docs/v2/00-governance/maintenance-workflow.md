# 文档维护流程

## 新增文档

1. 放入 `docs/v2/` 对应目录
2. 使用 `document-template.md`
3. 标注 `scope/source_repo/sync_required`
4. 状态设为 `draft`

## 更新文档

1. 校验与代码实现一致
2. 更新版本号与版本日期
3. 记录变更记录
4. 如为 `scope: shared`，同步更新另一仓

## 归档文档

1. 状态改为 `archived`
2. 迁入 `99-archive/`
3. 新文档中注明替代关系
