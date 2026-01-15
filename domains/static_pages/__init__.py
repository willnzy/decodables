"""
Static Pages Domain Module

Static pages content management (legal, company, guide pages).
Separate from articles (dynamic blog/news content).
Separate from project book pages (8 pages per mini-book).
"""

from .entities import StaticPage, StaticPageSummary, StaticPageType
from .repository import StaticPageRepository
from .service import StaticPageService

__all__ = [
    'StaticPage',
    'StaticPageSummary',
    'StaticPageType',
    'StaticPageRepository',
    'StaticPageService',
]
