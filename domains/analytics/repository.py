"""
Analytics Repository Interface - Domain repository interface.

@module domains.analytics.repository
@version 1.0.0

Defines the repository interface for analytics event persistence.
Implementation is in infrastructure layer.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from datetime import datetime

from .entities import AnalyticsEvent


class IAnalyticsRepository(ABC):
    """
    Analytics Repository Interface.
    
    Defines data access contract for analytics events.
    Infrastructure layer provides concrete implementations.
    """
    
    # ========================================
    # Single Event Operations
    # ========================================
    
    @abstractmethod
    async def save(self, event: AnalyticsEvent) -> None:
        """
        Save a single analytics event.
        
        Args:
            event: AnalyticsEvent entity to save
            
        Raises:
            RepositoryException: If save fails
        """
        pass
    
    @abstractmethod
    async def save_batch(self, events: List[AnalyticsEvent]) -> int:
        """
        Save multiple analytics events in batch.
        
        Args:
            events: List of AnalyticsEvent entities
            
        Returns:
            Number of events successfully saved
            
        Raises:
            RepositoryException: If batch save fails
        """
        pass
    
    # ========================================
    # Query Operations
    # ========================================
    
    @abstractmethod
    async def get_by_id(self, event_id: str) -> Optional[AnalyticsEvent]:
        """
        Get an analytics event by ID.
        
        Args:
            event_id: Event ID (UUID or custom ID)
            
        Returns:
            AnalyticsEvent if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_user_events(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        event_types: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[AnalyticsEvent], int]:
        """
        Get analytics events for a specific user.
        
        Args:
            user_id: User ID
            start_date: Start date for query
            end_date: End date for query
            event_types: Optional list of event types to filter
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            Tuple of (events, total_count)
        """
        pass
    
    @abstractmethod
    async def count_events(
        self,
        event_type: str,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> int:
        """
        Count analytics events by type and date range.
        
        Args:
            event_type: Event type to count
            start_date: Start date for query
            end_date: End date for query
            user_id: Optional user ID filter
            
        Returns:
            Number of events
        """
        pass
    
    # ========================================
    # Batch Operations (for frontend events)
    # ========================================
    
    @abstractmethod
    async def batch_insert_user_events(
        self,
        event_rows: List[dict]
    ) -> int:
        """
        Batch insert events to user_events table.
        
        Args:
            event_rows: List of event dictionaries
            
        Returns:
            Number of events successfully inserted
        """
        pass
    
    @abstractmethod
    async def batch_insert_analytics_events(
        self,
        event_rows: List[dict]
    ) -> int:
        """
        Batch insert events to analytics_events table.
        
        Args:
            event_rows: List of event dictionaries
            
        Returns:
            Number of events successfully inserted
        """
        pass
    
    @abstractmethod
    async def batch_insert_activity_logs(
        self,
        activity_rows: List[dict]
    ) -> int:
        """
        Batch insert events to activity_logs table.
        
        Args:
            activity_rows: List of activity dictionaries
            
        Returns:
            Number of activities successfully inserted
        """
        pass
    
    @abstractmethod
    async def batch_insert_all(
        self,
        user_event_rows: List[dict],
        analytics_event_rows: List[dict],
        activity_rows: List[dict]
    ) -> Tuple[int, int, int]:
        """
        Batch insert events to all three tables.
        
        Args:
            user_event_rows: List of user events
            analytics_event_rows: List of analytics events
            activity_rows: List of activity logs
            
        Returns:
            Tuple of (user_events_inserted, analytics_events_inserted, activity_logs_inserted)
        """
        pass
