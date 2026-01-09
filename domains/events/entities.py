"""
Events Domain Entities

Domain models for Events domain.

@module domains.events.entities
@version 1.0.0 (created for v3.27 refactor)
"""

from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class UserEvent:
    """User event entity."""

    id: Optional[str] = None
    user_id: str = ""
    event_type: str = ""
    event_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "event_data": self.event_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserEvent":
        """Create entity from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            user_id=data.get("user_id", ""),
            event_type=data.get("event_type", ""),
            event_data=data.get("event_data"),
            created_at=created_at,
            session_id=data.get("session_id"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
        )


@dataclass
class EventStats:
    """Event statistics entity."""

    group_key: str
    count: int
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "key": self.group_key,
            "count": self.count,
            "metadata": self.metadata,
        }


@dataclass
class AggregatedStats:
    """Aggregated statistics entity."""

    stat_type: str
    date: str
    value: int
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "stat_type": self.stat_type,
            "date": self.date,
            "value": self.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AggregatedStats":
        """Create entity from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return cls(
            stat_type=data.get("stat_type", ""),
            date=data.get("date", ""),
            value=data.get("value", 0),
            metadata=data.get("metadata"),
            created_at=created_at,
            updated_at=updated_at,
        )
