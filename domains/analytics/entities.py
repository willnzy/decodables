"""
Analytics Entities - Domain entities for analytics tracking.

@module domains.analytics.entities
@version 1.0.0

This module defines the core AnalyticsEvent entity with business rules.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4


@dataclass
class AnalyticsEvent:
    """
    Analytics Event Domain Entity.
    
    Represents a single analytics event with all its properties.
    Includes business rules for event validation.
    """
    
    # Core fields
    event_name: str
    event_type: str
    
    # Optional identification
    id: UUID = field(default_factory=uuid4)
    event_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Event data
    properties: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    source: str = "server"  # server/web/mobile/api
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate business rules after initialization."""
        # Rule 1: event_name is required
        if not self.event_name:
            raise ValueError("event_name is required")
        
        # Rule 2: event_name length limit
        if len(self.event_name) > 100:
            raise ValueError("event_name too long (max 100 chars)")
        
        # Rule 3: event_type is required
        if not self.event_type:
            raise ValueError("event_type is required")
        
        # Rule 4: properties must be a dict
        if self.properties and not isinstance(self.properties, dict):
            raise TypeError("properties must be a dict")
        
        # Rule 5: context must be a dict
        if self.context and not isinstance(self.context, dict):
            raise TypeError("context must be a dict")
        
        # Rule 6: auto-generate event_id if not provided
        if not self.event_id:
            self.event_id = str(self.id)
        
        # Rule 7: normalize event_name (lowercase)
        self.event_name = self.event_name.lower().strip()
        self.event_type = self.event_type.lower().strip()
    
    def add_property(self, key: str, value: Any) -> None:
        """
        Add a property to the event.
        
        Business rule: Properties use __ prefix for server-side data.
        
        Args:
            key: Property key
            value: Property value
        """
        self.properties[key] = value
    
    def add_context(self, key: str, value: Any) -> None:
        """
        Add context information to the event.
        
        Args:
            key: Context key
            value: Context value
        """
        self.context[key] = value
    
    def enrich_with_server_context(
        self,
        ip: str,
        country_code: str,
        user_agent: str,
        **extra_context
    ) -> None:
        """
        Enrich event with server-side context.
        
        Business rule: Server context uses __ prefix to prevent
        client from overwriting these fields.
        
        Args:
            ip: Client IP address
            country_code: Country code from IP
            user_agent: User agent string
            extra_context: Additional context fields
        """
        server_context = {
            "__server_ip": ip,
            "__server_country": country_code,
            "__server_user_agent": user_agent,
            **{f"__server_{k}": v for k, v in extra_context.items()}
        }
        self.properties.update(server_context)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize entity to dictionary for persistence.
        
        Returns:
            Dictionary representation suitable for database insertion
        """
        return {
            'id': str(self.id),
            'event_id': self.event_id,
            'event_name': self.event_name,
            'event_type': self.event_type,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'properties': self.properties,
            'context': self.context,
            'source': self.source,
            'created_at': self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalyticsEvent':
        """
        Deserialize dictionary to entity.
        
        Args:
            data: Dictionary from database
            
        Returns:
            AnalyticsEvent instance
        """
        # Parse datetime if string
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        return cls(
            id=UUID(data['id']) if isinstance(data['id'], str) else data['id'],
            event_id=data.get('event_id'),
            event_name=data['event_name'],
            event_type=data['event_type'],
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            properties=data.get('properties', {}),
            context=data.get('context', {}),
            source=data.get('source', 'server'),
            created_at=created_at or datetime.now(timezone.utc)
        )
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"AnalyticsEvent(id={self.id}, "
            f"event_name='{self.event_name}', "
            f"user_id='{self.user_id}', "
            f"source='{self.source}')"
        )
