"""
Application Services Layer
应用服务层 - 编排业务逻辑，调用领域层

Provides:
- AI chat orchestration
- Report generation services
- CAPI (Facebook Conversion API) integration
- Generation helpers and utilities
- Setup assistant

Services in this layer:
- Orchestrate use cases across multiple domains
- Handle external API integrations (AI, Analytics)
- Do NOT contain business rules (those belong in domains/)
- Call domain services and repositories

Architecture:
application/services/ → domains/ + infrastructure/ + shared/
"""

__all__ = []
