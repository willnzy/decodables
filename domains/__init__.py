"""
Domains Layer - Business logic organized by domain.

This layer contains:
- billing/: Credit management and transactions
- identity/: User profiles and authentication
- creation/: Projects and assets
- marketplace/: Asset listings and purchases
- platform/: Feature flags, experiments, configs
- content/: System resources and content library
- workspace/: User workspace management (v3.33)
- tag/: Tag system for organizing projects and assets (v3.33)

@package domains
@version 1.1.0

Design Principles:
- Each domain is independent and self-contained
- Cross-domain communication via application layer
- No direct imports between domains
- Business rules encapsulated in aggregates
"""

__all__ = [
    'billing',
    'identity',
    'creation',
    'marketplace',
    'platform',
    'content',
    'workspace',
    'tag',
]
