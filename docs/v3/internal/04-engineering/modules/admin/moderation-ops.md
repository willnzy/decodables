# 审核与举报系统设计

> **同步范围**: [backend]
> **状态**: 🟢 已验证 (来源: 代码分析 + v2 文档)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `api/admin/moderation.py`, `domains/moderation/`

---

## 一、概述

### 1.1 核心能力

| 能力 | 说明 |
|------|------|
| 内容审核 | Marketplace 商品审核 |
| 举报处理 | 用户举报的处理流程 |
| 状态管理 | 审核/举报状态流转 |
| 统计分析 | 审核量、处理效率 |

### 1.2 业务流程

```
用户发布 → 待审核 → 审核通过 → 上架
              ↓
          审核拒绝 → 通知用户

用户举报 → 待处理 → 处理完成 → 通知双方
```

---

## 二、内容审核

### 2.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/moderation/marketplace/moderation/list` | GET | 待审核列表 |
| `/api/admin/moderation/marketplace/moderation/{id}` | GET | 审核详情 |
| `/api/admin/moderation/marketplace/moderation/{id}/approve` | POST | 通过审核 |
| `/api/admin/moderation/marketplace/moderation/{id}/reject` | POST | 拒绝审核 |
| `/api/admin/moderation/marketplace/moderation/{id}/delete` | POST | 删除内容 |
| `/api/admin/moderation/marketplace/moderation/{id}/unpublish` | POST | 下架内容 |

### 2.2 审核状态

```python
class ModerationStatus(str, Enum):
    PENDING = "pending"      # 待审核
    APPROVED = "approved"    # 已通过
    REJECTED = "rejected"    # 已拒绝
```

### 2.3 资源类型

```python
class ResourceType(str, Enum):
    STICKER = "sticker"
    CLIPART = "clipart"
    TEMPLATE = "template"
    FONT = "font"
    ALL = "all"
```

### 2.4 数据结构

```python
class ModerationItem:
    id: UUID
    resource_type: ResourceType
    resource_id: UUID
    status: ModerationStatus
    
    # 内容信息
    title: str
    description: str
    preview_url: str
    
    # 提交信息
    submitted_by: UUID
    submitted_at: datetime
    
    # 审核信息
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    review_note: Optional[str]
```

### 2.5 审核流程

```python
async def approve_listing(
    listing_id: UUID,
    admin_id: UUID,
    note: Optional[str] = None
):
    """
    通过审核
    
    1. 更新状态为 approved
    2. 设置上架时间
    3. 通知卖家
    4. 记录审计日志
    """
    item = await moderation_repo.get(listing_id)
    
    if item.status != ModerationStatus.PENDING:
        raise InvalidStatusError()
    
    await moderation_repo.update(
        listing_id,
        status=ModerationStatus.APPROVED,
        reviewed_by=admin_id,
        reviewed_at=datetime.now(),
        review_note=note
    )
    
    # 通知卖家
    await notification_service.send(
        user_id=item.submitted_by,
        type="listing_approved",
        data={"listing_id": listing_id, "title": item.title}
    )
    
    # 审计日志
    await audit_log.create(
        action="listing_approved",
        target_id=listing_id,
        operator_id=admin_id
    )

async def reject_listing(
    listing_id: UUID,
    admin_id: UUID,
    reason: str
):
    """
    拒绝审核
    
    1. 更新状态为 rejected
    2. 记录拒绝原因
    3. 通知卖家
    """
    item = await moderation_repo.get(listing_id)
    
    await moderation_repo.update(
        listing_id,
        status=ModerationStatus.REJECTED,
        reviewed_by=admin_id,
        reviewed_at=datetime.now(),
        review_note=reason
    )
    
    # 通知卖家 (含拒绝原因)
    await notification_service.send(
        user_id=item.submitted_by,
        type="listing_rejected",
        data={"listing_id": listing_id, "reason": reason}
    )
```

---

## 三、举报处理

### 3.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/moderation/reports` | GET | 举报列表 |
| `/api/admin/moderation/reports/stats` | GET | 举报统计 |
| `/api/admin/moderation/reports/{id}` | GET | 举报详情 |
| `/api/admin/moderation/reports/{id}/respond` | POST | 处理举报 |

### 3.2 举报状态

```python
class ReportStatus(str, Enum):
    PENDING = "pending"      # 待处理
    REVIEWED = "reviewed"    # 已审核
    RESOLVED = "resolved"    # 已解决
    DISMISSED = "dismissed"  # 已驳回
```

### 3.3 数据结构

```python
class ContentReport:
    id: UUID
    
    # 举报目标
    target_type: str         # listing/user/project
    target_id: UUID
    
    # 举报信息
    reason: ReportReason
    description: str
    
    # 举报人
    reported_by: UUID
    reported_at: datetime
    
    # 处理信息
    status: ReportStatus
    resolution_note: Optional[str]
    resolved_by: Optional[UUID]
    resolved_at: Optional[datetime]

class ReportReason(str, Enum):
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    COPYRIGHT_VIOLATION = "copyright_violation"
    SPAM = "spam"
    MISLEADING = "misleading"
    OTHER = "other"
```

### 3.4 统计数据

```python
class ReportStats:
    total: int
    pending: int
    resolved: int
    dismissed: int
    
    avg_resolution_time_hours: float
    by_reason: Dict[str, int]
    by_target_type: Dict[str, int]
```

### 3.5 处理流程

```python
async def respond_to_report(
    report_id: UUID,
    admin_id: UUID,
    resolution: str,         # resolved/dismissed
    note: str,
    action: Optional[str]    # warning/suspend/delete
):
    """
    处理举报
    
    1. 更新举报状态
    2. 对被举报内容/用户采取措施
    3. 通知举报人
    4. 通知被举报人
    """
    report = await report_repo.get(report_id)
    
    # 更新状态
    new_status = (
        ReportStatus.RESOLVED 
        if resolution == "resolved" 
        else ReportStatus.DISMISSED
    )
    
    await report_repo.update(
        report_id,
        status=new_status,
        resolution_note=note,
        resolved_by=admin_id,
        resolved_at=datetime.now()
    )
    
    # 采取措施
    if action == "delete":
        await delete_content(report.target_type, report.target_id)
    elif action == "suspend":
        await suspend_user(report.target_id)
    elif action == "warning":
        await send_warning(report.target_id)
    
    # 通知举报人
    await notification_service.send(
        user_id=report.reported_by,
        type="report_resolved",
        data={"report_id": report_id}
    )
```

---

## 四、安全与护栏

### 4.1 权限控制

- 所有端点需要 Admin 角色
- 敏感操作 (删除、封禁) 需要二次确认

### 4.2 Rate Limiting

| 操作类型 | 限制 |
|----------|------|
| 列表查询 | 30/min |
| 审核操作 | 10/min |
| 批量操作 | 5/min |

### 4.3 审计日志

```python
# 审核操作审计
AuditLog(
    action="listing_approved",
    target_type="moderation_item",
    target_id=listing_id,
    operator_id=admin_id,
    details={"note": review_note}
)

# 举报处理审计
AuditLog(
    action="report_resolved",
    target_type="content_report",
    target_id=report_id,
    operator_id=admin_id,
    details={"resolution": resolution, "action": action}
)
```

---

## 五、前端交互

### 5.1 布局

```
┌─────────────────────────────────────────────────────┐
│  [审核] [举报] [统计]                               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  筛选: [状态▼] [类型▼] [日期范围]                   │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ 商品预览  │ 提交信息 │ 操作                  │  │
│  │           │ 卖家: xxx│ [通过] [拒绝] [删除] │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 5.2 操作弹窗

- 拒绝: 必须填写拒绝原因
- 删除: 二次确认弹窗
- 举报处理: 选择处理结果 + 措施

---

## 六、相关文档

- [Admin API 端点](../../api/admin-endpoints.md)
- [Marketplace 架构](../marketplace/architecture.md)
- [通知系统](../notifications/architecture.md)

---

**END OF DOCUMENT**
