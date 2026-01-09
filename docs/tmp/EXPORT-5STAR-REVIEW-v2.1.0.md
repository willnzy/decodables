# Export 模块 5 星 Review (v2.1.0)

**日期**: 2026-01-10
**模块**: `api/user/export.py` (PDF, Preview, ZIP Export)
**当前版本**: v2.1.0
**评级**: ⭐⭐⭐⭐ (78/100)
**风险级别**: 🟡 中风险

---

## 📊 5 星评分

### ⭐ Star 1: Code Standards (90/100)

**优点**:
- ✅ 代码结构清晰 (352 行,职责明确)
- ✅ 完整的安全注释 (v2.1.0 改进)
- ✅ Helper 函数职责单一
- ✅ 常量定义完整 (ALLOWED_URL_DOMAINS, UUID_PATTERN)

**问题**:
- 🟡 **EX-CODE-1**: 重复代码 - 4 个端点都有相同的 Repository 创建逻辑
  ```python
  # 在 4 个端点中重复出现
  project_repo = SupabaseProjectRepository(get_database_client())
  proj = await project_repo.get_project_detail(project_id, user["id"])
  if not proj:
      raise HTTPException(404, "Project not found")
  ```

- 🟡 **EX-CODE-2**: 重复的数据提取逻辑
  ```python
  # export_project_pdf 和 export_project_preview 都有相同的提取逻辑
  canvas_data = proj.get("canvas_data", {})
  image_urls, texts, paper_size = _extract_project_data(canvas_data)
  ```

**评分**: 90/100

---

### ⭐ Star 2: Architecture Compliance (55/100)

**问题** (与 Generation PDF/Story v3.27 相同):

**EX-CRITICAL-1**: 无 Service 层，无依赖注入 (DDD 违规)

**问题详情**:
```python
# ❌ 直接在 API 层创建 Repository
@router.get("/projects/{project_id}/pdf")
async def export_project_pdf(...):
    # 手动创建 Repository
    project_repo = SupabaseProjectRepository(get_database_client())
    proj = await project_repo.get_project_detail(project_id, user["id"])

    # 直接调用外部函数
    image_urls, texts, paper_size = _extract_project_data(canvas_data)
    buf = BytesIO()
    create_foldable_book(image_urls, texts, buf, paper_type=paper_size)

    # 直接调用日志函数
    log_activity(user["id"], "download_pdf", {"project_id": project_id})
```

**对比 Generation PDF v3.26 (5星)**:
```python
# ✅ v3.26 - 完美 DDD
def get_pdf_service() -> PdfGenerationService:
    db = get_database_client()
    project_repo = SupabaseProjectRepository(db)
    return PdfGenerationService(project_repository=project_repo)

@router.get("/pdf")
async def gen_pdf(
    pdf_service: PdfGenerationService = Depends(get_pdf_service),
):
    buf = await pdf_service.generate_pdf(...)
    return StreamingResponse(buf, ...)
```

**架构对比**:

| 特征 | Export v2.1.0 | Generation PDF v3.26 (5星) |
|------|---------------|---------------------------|
| DI 工厂 | ❌ 无 | ✅ `get_pdf_service()` |
| API 依赖注入 | ❌ 手动创建 Repository | ✅ `Depends(get_pdf_service)` |
| Service 层 | ❌ 无 | ✅ PdfGenerationService (150 行) |
| Repository 创建 | ❌ 每个端点创建 | ✅ DI 时创建，请求复用 |
| 业务逻辑位置 | ❌ API 层 | ✅ Service 层 |

**影响**:
- 代码重复 (4 个端点重复创建 Repository)
- 难以测试 (需要 mock 多个组件)
- 难以扩展 (业务逻辑散落在 API 层)
- 不符合 DDD 架构标准

**评分**: 55/100

---

### ⭐ Star 3: Security Complete (100/100)

**v2.1.0 安全改进** (全部完成):
- ✅ **EX-P0-1/2**: SSRF 防护 (URL 域名白名单)
- ✅ **EX-HIGH-1**: UUID 格式验证 (project_id)
- ✅ **EX-HIGH-2**: 文件名注入防护 (Content-Disposition)
- ✅ **EX-MEDIUM-1**: URL 数量限制 (max 20, DoS 防护)
- ✅ **EX-MEDIUM-2**: Pydantic 验证 (ZipExportRequest)
- ✅ **EX-LOW-1**: 日志脱敏 (user_id 只记录前 8 位)

**安全机制完整**:
- ✅ SSRF Protection (whitelist validation)
- ✅ UUID Validation (regex pattern)
- ✅ Filename Sanitization (remove special chars)
- ✅ URL Count Limit (max 20)
- ✅ Rate Limiting (5-20/minute)
- ✅ Tier Verification (ZIP requires Pro)
- ✅ Project Ownership Check (user["id"] verification)
- ✅ Error Message Sanitization (no internal details)

**测试覆盖**:
- 25 个测试全部通过 ✅
- 安全测试完整 (SSRF, UUID, filename, URL count)

**评分**: 100/100

---

### ⭐ Star 4: Call Chain Complete (85/100)

**调用链** (v2.1.0):
```
PDF Export:
API → export_project_pdf()
  → SupabaseProjectRepository (手动创建)
  → _extract_project_data() (helper)
  → create_foldable_book() (external)
  → log_activity() (external)

Preview Export:
API → export_project_preview()
  → SupabaseProjectRepository (手动创建)
  → _extract_project_data() (helper)
  → create_foldable_book() (external)
  → fitz (PyMuPDF, external)
  → log_activity() (external)

ZIP Export (Deprecated):
API → export_zip()
  → Tier verification
  → ZipExportRequest.validate_urls() (Pydantic)
  → create_assets_zip() (external)
  → log_activity() (external)

Project ZIP Export:
API → export_project_zip()
  → Tier verification
  → SupabaseProjectRepository (手动创建)
  → _extract_project_data() (helper)
  → _is_allowed_url() (SSRF filter)
  → create_assets_zip() (external)
  → log_activity() (external)
```

**优点**:
- ✅ 所有调用存在
- ✅ 参数传递正确
- ✅ 错误处理完整 (404/400/403/500)
- ✅ SSRF 防护到位 (URL 过滤)

**问题**:
- 🟡 **EX-CHAIN-1**: 缺少事务管理 (activity log 可能失败)
- 🟡 **EX-CHAIN-2**: 缺少幂等性保证 (重复请求可能重复生成)
- 🟡 **EX-CHAIN-3**: Preview 错误处理过于宽泛 (`except Exception`)

**评分**: 85/100

---

### ⭐ Star 5: Test Coverage Complete (95/100)

**测试统计**:
- **Total**: 28 tests (25 passed, 3 skipped)
- **Coverage**: ~85-90% (推测)

**测试分类**:
- PDF Export (5 tests): Success, 404, 401, Invalid UUID, Filename Sanitization
- Preview Export (3 tests, 2 skipped): Invalid UUID, Success (skipped), 404 (skipped)
- ZIP Deprecated (6 tests): Pro tier, Success, 401, SSRF, URL limit, Empty URLs
- Project ZIP (7 tests): Invalid UUID, Pro tier, Success, 404, 401, SSRF filter, No valid URLs
- Helper Functions (9 tests): _is_allowed_url (6), _sanitize_filename (4)

**测试质量**:
- ✅ 完整的安全测试 (SSRF, UUID, filename, URL count)
- ✅ 完整的权限测试 (401, 403, Pro tier)
- ✅ 完整的边界测试 (empty URLs, invalid UUID, malicious filename)
- ✅ 完整的 Helper 函数测试 (edge cases covered)

**问题**:
- 🟡 **EX-TEST-1**: Preview 测试被跳过 (需要 PyMuPDF)
- 🟡 **EX-TEST-2**: 使用 `@patch` 而非 `app.dependency_overrides` (旧模式)
  ```python
  # ❌ 旧模式
  @patch('api.user.export.SupabaseProjectRepository')
  @patch('api.user.export.create_foldable_book')
  def test_export_pdf_success(self, mock_repo_class, mock_create_pdf, ...):

  # ✅ FastAPI 最佳实践 (Generation PDF v3.26)
  app.dependency_overrides[get_pdf_service] = lambda: mock_service
  ```

**评分**: 95/100

---

## 📈 总分计算

| 维度 | 分数 | 权重 | 加权分 |
|------|------|------|--------|
| Code Standards | 90/100 | 20% | 18 |
| **Architecture** | **55/100** | 30% | **16.5** |
| Security | 100/100 | 20% | 20 |
| Call Chain | 85/100 | 15% | 12.75 |
| Test Coverage | 95/100 | 15% | 14.25 |
| **总分** | | | **78/100** |

**当前评级**: ⭐⭐⭐⭐ (4 星)

---

## 🚨 必须修复的问题 (达到 5 星)

### 1. EX-CRITICAL-1: 创建 Service 层 + 依赖注入 (+40 架构分)

**需要创建**:

#### ExportService (新文件: `domains/export/export_service.py`)

```python
"""Export Service - PDF, Preview, ZIP export functionality."""

from io import BytesIO
from typing import Dict, List, Optional
from infrastructure.repositories.project_repository import ProjectRepository
from infrastructure.logging.activity_logger import log_activity
from shared.ai.zine_generator import create_foldable_book, create_assets_zip

class ProjectNotFoundException(Exception):
    """Raised when project is not found or user doesn't have access."""
    pass

class ExportException(Exception):
    """Base exception for export failures."""
    pass

class ExportService:
    """Service for project export functionality."""

    def __init__(self, project_repository: ProjectRepository):
        self.project_repository = project_repository

    async def export_pdf(
        self,
        user_id: str,
        project_id: str,
    ) -> BytesIO:
        """
        Export project as PDF.

        Returns:
            BytesIO: PDF buffer

        Raises:
            ProjectNotFoundException: If project not found
            ExportException: If PDF generation fails
        """
        # Get project
        proj = await self._get_user_project(user_id, project_id)

        # Extract data
        image_urls, texts, paper_size = self._extract_project_data(proj)

        # Generate PDF
        buf = BytesIO()
        try:
            create_foldable_book(image_urls, texts, buf, paper_type=paper_size)
            buf.seek(0)
        except Exception as e:
            raise ExportException(f"PDF generation failed: {str(e)}")

        # Log activity
        log_activity(user_id, "download_pdf", {"project_id": project_id})

        return buf

    async def export_preview(
        self,
        user_id: str,
        project_id: str,
    ) -> BytesIO:
        """
        Export project preview image.

        Returns:
            BytesIO: PNG image buffer

        Raises:
            ProjectNotFoundException: If project not found
            ExportException: If preview generation fails
        """
        import fitz

        # Get project
        proj = await self._get_user_project(user_id, project_id)

        # Extract data
        image_urls, texts, paper_size = self._extract_project_data(proj)

        # Generate PDF first
        pdf_buffer = BytesIO()
        create_foldable_book(image_urls, texts, pdf_buffer, paper_type=paper_size)
        pdf_buffer.seek(0)

        # Convert to image
        try:
            pdf_doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
            page = pdf_doc[0]

            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            img_buffer = BytesIO(pix.tobytes("png"))
            pdf_doc.close()

            # Log activity
            log_activity(user_id, "preview_pdf", {"project_id": project_id})

            return img_buffer

        except Exception as e:
            raise ExportException(f"Preview generation failed: {type(e).__name__}")

    async def export_project_zip(
        self,
        user_id: str,
        project_id: str,
        tier: str,
    ) -> BytesIO:
        """
        Export project assets as ZIP.

        Args:
            user_id: User ID
            project_id: Project ID
            tier: User tier (must be "pro")

        Returns:
            BytesIO: ZIP buffer

        Raises:
            PermissionError: If tier is not "pro"
            ProjectNotFoundException: If project not found
            ExportException: If no valid URLs or ZIP generation fails
        """
        if tier.lower() != "pro":
            raise PermissionError("ZIP export requires Pro plan")

        # Get project
        proj = await self._get_user_project(user_id, project_id)

        # Extract URLs
        canvas_data = proj.get("canvas_data", {})
        image_urls, _, _ = self._extract_project_data(proj)

        # Filter allowed URLs (SSRF protection)
        from api.user.export import _is_allowed_url
        valid_urls = [url for url in image_urls if _is_allowed_url(url)]

        if not valid_urls:
            raise ExportException("No valid image URLs found in project")

        # Create ZIP
        buf = BytesIO()
        try:
            create_assets_zip(valid_urls, buf)
            buf.seek(0)
        except Exception as e:
            raise ExportException(f"ZIP generation failed: {str(e)}")

        # Log activity
        log_activity(user_id, "export_zip", {"project_id": project_id})

        return buf

    async def export_custom_zip(
        self,
        user_id: str,
        image_urls: List[str],
        tier: str,
        project_id: Optional[str] = None,
    ) -> BytesIO:
        """
        Export custom URLs as ZIP (deprecated endpoint).

        Args:
            user_id: User ID
            image_urls: List of image URLs (already validated by Pydantic)
            tier: User tier (must be "pro")
            project_id: Optional project ID for logging

        Returns:
            BytesIO: ZIP buffer

        Raises:
            PermissionError: If tier is not "pro"
            ExportException: If ZIP generation fails
        """
        if tier.lower() != "pro":
            raise PermissionError("ZIP export requires Pro plan")

        # Create ZIP
        buf = BytesIO()
        try:
            create_assets_zip(image_urls, buf)
            buf.seek(0)
        except Exception as e:
            raise ExportException(f"ZIP generation failed: {str(e)}")

        # Log activity
        log_activity(user_id, "export_zip", {"project_id": project_id})

        return buf

    # Private methods

    async def _get_user_project(self, user_id: str, project_id: str) -> Dict:
        """Get project and verify ownership."""
        proj = await self.project_repository.get_project_detail(project_id, user_id)
        if not proj:
            raise ProjectNotFoundException("Project not found or access denied")
        return proj

    def _extract_project_data(self, proj: Dict) -> tuple[list, list, str]:
        """Extract pages data and paper size from project."""
        canvas_data = proj.get("canvas_data", {})

        if isinstance(canvas_data, list):
            pages = canvas_data
            paper_size = "US_LETTER"
        else:
            pages = canvas_data.get("pages", [])
            paper_size_raw = canvas_data.get("paperSize", "Letter")
            paper_size = "A4" if paper_size_raw == "A4" else "US_LETTER"

        image_urls = []
        texts = []
        for page in pages:
            if isinstance(page, dict):
                image_urls.append(page.get("previewImage", "") or "")
                texts.append(page.get("prompt", "") or "")
            else:
                image_urls.append("")
                texts.append("")

        # Pad to 8 pages
        while len(image_urls) < 8:
            image_urls.append("")
            texts.append("")

        return image_urls, texts, paper_size
```

#### 更新 API 层 (`api/user/export.py`)

```python
# 添加 DI 工厂
def get_export_service() -> ExportService:
    """Dependency injection factory for ExportService."""
    db = get_database_client()
    project_repo = SupabaseProjectRepository(db)
    return ExportService(project_repository=project_repo)

# 重写端点
@router.get("/projects/{project_id}/pdf")
@limiter.limit("10/minute")
async def export_project_pdf(
    request: Request,
    project_id: str,
    user: dict = Depends(get_current_user),
    export_service: ExportService = Depends(get_export_service),  # v3.0.0: DI
):
    """Generate a PDF from stored project data."""
    # v3.0.0: Validate project_id format
    if not UUID_PATTERN.match(project_id):
        raise HTTPException(400, "Invalid project ID format")

    try:
        buf = await export_service.export_pdf(user["id"], project_id)
    except ProjectNotFoundException:
        raise HTTPException(404, "Project not found")
    except ExportException as e:
        logger.error(f"PDF export failed: {e}")
        raise HTTPException(500, "PDF generation failed")

    # Get project title for filename (lightweight call)
    # ... (simplified, title can be passed from service if needed)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="export.pdf"'},
    )
```

**预期改进**:
- 架构评分: 55 → 95 (+40)
- 总分: 78 → 95 (+17)
- 星级: ⭐⭐⭐⭐ → ⭐⭐⭐⭐⭐

---

## 🎯 修复优先级

| 优先级 | 问题 | 影响 | 工作量 |
|--------|------|------|--------|
| **P0** | EX-CRITICAL-1 | 架构 +40 | 2-3 hours |
| P1 | EX-TEST-2 | 测试质量 +3 | 1 hour |
| P2 | EX-CODE-1/2 | 代码质量 +5 | 30 mins |
| P3 | EX-CHAIN-1/2/3 | 调用链 +5 | 1 hour |

**总工作量**: 4-5 hours

---

## 📝 修复后预期评分

| 维度 | 当前 | 修复后 | 提升 |
|------|------|--------|------|
| Code Standards | 90/100 | 95/100 | +5 |
| **Architecture** | **55/100** | **95/100** | **+40** |
| Security | 100/100 | 100/100 | 0 |
| Call Chain | 85/100 | 90/100 | +5 |
| Test Coverage | 95/100 | 98/100 | +3 |
| **总分** | **78/100** | **95/100** | **+17** |
| **星级** | **⭐⭐⭐⭐** | **⭐⭐⭐⭐⭐** | **+1 星** |

---

## 🎯 结论

**Export v2.1.0 当前为 4 星 (78/100)**

### 优点:
- ✅ 安全措施完整 (SSRF, UUID, filename, rate limiting)
- ✅ 测试覆盖良好 (25/28 tests passing)
- ✅ 代码质量高 (清晰、注释完整)

### 核心问题:
- ❌ **架构不合规** (无 Service 层，无 DI)
- 与 Generation PDF v3.25 相同的问题（已在 v3.26 修复）

### 修复路径:
1. 创建 ExportService (~200 行)
2. 添加 DI 工厂 (get_export_service)
3. 重写 4 个端点使用 Service
4. 更新测试使用 app.dependency_overrides
5. 运行测试验证 (预期 25/25 passing)

**修复后可达 5 星 (95/100)** ✨

---

**审核人**: Claude (AI Assistant)
**审核日期**: 2026-01-10
**下一步**: 等待用户确认是否立即修复
