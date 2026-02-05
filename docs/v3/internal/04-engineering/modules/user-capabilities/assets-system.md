# Assets System - 资产管理系统

> 用户资产上传、存储、管理的完整设计

**验证状态**: 🟢 已验证  
**同步范围**: [fullstack]  
**代码来源**: `domains/assets/`, `infrastructure/repositories/asset_repository.py`

---

## 一、概述

资产系统负责管理用户的图片、文件等数字资产，包括上传、存储、检索、删除等功能。

---

## 二、核心能力

### 2.1 功能清单

| 功能 | 描述 | Tier 限制 |
|------|------|-----------|
| 上传文件 | 本地上传图片/SVG/PDF | t3 (Pro) |
| URL 导入 | 从外部 URL 导入图片 | 所有用户 |
| 文件夹管理 | 按文件夹分类资产 | t2+ |
| 收藏功能 | 星标重要资产 | 所有用户 |
| 软删除 | 移入回收站 | 所有用户 |
| 永久删除 | 彻底删除资产 | 所有用户 |
| 回收站恢复 | 从回收站恢复 | 30 天内有效 |

### 2.2 文件类型支持

```python
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "application/pdf",
}
```

### 2.3 文件大小限制

| Tier | 最大文件大小 |
|------|--------------|
| t1 (Free) | 5 MB |
| t2 (Starter) | 10 MB |
| t3 (Pro) | 20 MB |

---

## 三、核心流程

### 3.1 文件上传流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      文件上传流程                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 接收文件                                                    │
│     │                                                           │
│     ↓                                                           │
│  2. Tier 权限检查 (t3 required)                                 │
│     │                                                           │
│     ↓                                                           │
│  3. MIME 类型验证 (白名单)                                      │
│     │                                                           │
│     ↓                                                           │
│  4. 文件大小验证 (按 Tier)                                      │
│     │                                                           │
│     ↓                                                           │
│  5. Magic Bytes 验证 (防止 MIME 欺骗)                           │
│     │                                                           │
│     ↓                                                           │
│  6. SVG 安全清洗 (如果是 SVG)                                   │
│     │                                                           │
│     ↓                                                           │
│  7. 上传到 Supabase Storage                                     │
│     │                                                           │
│     ↓                                                           │
│  8. 保存元数据到数据库                                          │
│     │                                                           │
│     ↓                                                           │
│  9. 返回资产信息                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 URL 导入流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      URL 导入流程                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 接收 URL                                                    │
│     │                                                           │
│     ↓                                                           │
│  2. URL 长度验证 (≤ 2048 字符)                                  │
│     │                                                           │
│     ↓                                                           │
│  3. 协议验证 (http/https only)                                  │
│     │                                                           │
│     ↓                                                           │
│  4. SSRF 检查 (禁止内网 IP)                                     │
│     │                                                           │
│     ↓                                                           │
│  5. HTTP HEAD 请求验证                                          │
│     │  - 状态码 = 200                                           │
│     │  - Content-Type = image/*                                 │
│     │  - 最大 3 次重定向                                        │
│     ↓                                                           │
│  6. 保存 URL 引用到数据库                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、安全措施

### 4.1 SSRF 防护

```python
def _is_private_ip(self, hostname: str) -> bool:
    """检查是否为私有 IP"""
    ip = socket.gethostbyname(hostname)
    ip_obj = ipaddress.ip_address(ip)
    
    return (
        ip_obj.is_private or
        ip_obj.is_loopback or
        ip_obj.is_link_local or
        ip_obj.is_reserved or
        ip_obj.is_multicast
    )
```

**被拦截的地址**:
- `localhost`, `127.0.0.1`
- 私有 IP: `10.x.x.x`, `192.168.x.x`, `172.16-31.x.x`
- 链路本地: `169.254.x.x`
- 环回地址: `::1`

### 4.2 Magic Bytes 验证

```python
MAGIC_BYTES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [b"RIFF"],  # + WEBP at offset 8
    "application/pdf": [b"%PDF"],
}
```

### 4.3 SVG 安全清洗

移除的危险元素:
- `<script>` - JavaScript 执行
- `<foreignObject>` - 嵌入外部内容
- `on*` 事件处理器 - onclick, onload 等
- `javascript:` URI - 在 href 中

---

## 五、数据模型

### 5.1 Asset Entity

```python
class Asset:
    id: UUID
    user_id: UUID
    filename: str
    file_type: str           # image/jpeg, image/png, etc.
    file_url: str
    thumbnail_url: Optional[str]
    source: str              # upload/ai_generated/import
    project_id: Optional[UUID]
    workspace_id: Optional[UUID]
    folder_id: Optional[UUID]
    is_starred: bool
    usage_count: int
    deleted_at: Optional[datetime]
    recovery_expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
```

### 5.2 数据库表

```sql
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(100) NOT NULL,
    file_url TEXT NOT NULL,
    thumbnail_url TEXT,
    source VARCHAR(50) DEFAULT 'upload',
    project_id UUID REFERENCES projects(id),
    workspace_id UUID,
    folder_id UUID,
    is_starred BOOLEAN DEFAULT false,
    usage_count INTEGER DEFAULT 0,
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_assets_user_id ON assets(user_id);
CREATE INDEX idx_assets_folder_id ON assets(folder_id);
CREATE INDEX idx_assets_deleted ON assets(deleted_at) WHERE deleted_at IS NOT NULL;
```

---

## 六、API 端点

### 6.1 端点列表

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/assets` | 获取资产列表 |
| GET | `/api/v1/assets/{id}` | 获取单个资产 |
| POST | `/api/v1/assets/upload` | 上传文件 |
| POST | `/api/v1/assets/from-url` | URL 导入 |
| PATCH | `/api/v1/assets/{id}/star` | 切换收藏 |
| PATCH | `/api/v1/assets/{id}/folder` | 移动到文件夹 |
| DELETE | `/api/v1/assets/{id}` | 删除资产 |
| POST | `/api/v1/assets/{id}/restore` | 恢复资产 |

### 6.2 请求/响应示例

**上传文件**:
```http
POST /api/v1/assets/upload
Content-Type: multipart/form-data

file: <binary>
project_id: uuid (optional)
folder_id: uuid (optional)
```

**响应**:
```json
{
    "url": "https://storage.supabase.co/...",
    "filename": "user-id/uploads/uuid.png"
}
```

---

## 七、跨系统保护

### 7.1 Marketplace 引用保护

```python
async def delete_asset(self, asset_id: str, permanent: bool = False):
    """
    WS-24: 永久删除前检查 Marketplace 引用
    """
    if permanent:
        refs = await self.repository.get_active_references(asset_id)
        if refs["has_references"]:
            # 降级为软删除，保护引用系统
            result = await self.repository.soft_delete_asset(asset_id, user_id)
            # 返回警告信息
```

---

## 八、相关文档

- [Dashboard 架构](../dashboard/architecture.md)
- [Marketplace 架构](../marketplace/architecture.md)
- [文件导入功能](../../features/file-import.md)
