"""
Generation Router - AI content generation endpoints (Aggregator)

@module routers.generation
@version 3.24

This is the main entry point that aggregates all generation sub-routers.

Sub-modules:
- generation_images: Sync/Async image generation
- generation_story: Story and inspiration generation
- generation_pdf: PDF generation

Endpoints:
- POST /api/generate/story - Generate story JSON
- POST /api/generate/images - Sync image generation
- POST /api/generate/images/async - Async image generation (v3.23)
- POST /api/generate/inspiration - AI inspiration suggestions
- POST /api/generate/pdf - PDF generation
"""

from fastapi import APIRouter

# Import sub-routers
from .generation_images import router as images_router
from .generation_story import router as story_router
from .generation_pdf import router as pdf_router

# Main router (empty, just for grouping)
router = APIRouter(tags=["generation"])


def include_generation_routers(app):
    """
    Include all generation routers in the FastAPI app.
    
    Call this from app.py instead of including the main router.
    
    Usage:
        from routers.generation import include_generation_routers
        include_generation_routers(app)
    """
    app.include_router(images_router)
    app.include_router(story_router)
    app.include_router(pdf_router)


# For backwards compatibility - export all sub-routers
__all__ = [
    "router",
    "images_router",
    "story_router",
    "pdf_router",
    "include_generation_routers",
]
