"""
Articles Domain - CMS for Manual, News, and Changelog.

@module domains.articles
@version 1.0.0

This domain handles content management for:
- Manual: Help documentation, FAQ, tutorials
- News: Announcements, feature updates
- Changelog: Release notes, version history
"""

from .entities import Article, ArticleCategory
from .repository import ArticleRepository
from .service import ArticleService

__all__ = [
    "Article",
    "ArticleCategory",
    "ArticleRepository",
    "ArticleService",
]
