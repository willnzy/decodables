"""
Content Domain Exceptions.

@module domains.content.exceptions
@version 1.0.0
"""


class ContentDomainException(Exception):
    """Base exception for content domain."""
    pass


class ResourceNotFoundException(ContentDomainException):
    """Resource not found."""

    def __init__(self, resource_id: str):
        self.resource_id = resource_id
        super().__init__(f"Resource not found: {resource_id}")


class ResourceAccessDeniedException(ContentDomainException):
    """User does not have access to resource."""

    def __init__(self, resource_id: str, user_tier: str, required_tiers: list):
        self.resource_id = resource_id
        self.user_tier = user_tier
        self.required_tiers = required_tiers
        super().__init__(
            f"Access denied to resource {resource_id}. "
            f"User tier: {user_tier}, required: {required_tiers}"
        )


class InvalidResourceDataException(ContentDomainException):
    """Invalid resource data."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Invalid {field}: {message}")


class InvalidResourceTypeException(ContentDomainException):
    """Invalid resource type."""

    def __init__(self, resource_type: str):
        self.resource_type = resource_type
        super().__init__(f"Invalid resource type: {resource_type}")


class InvalidCategoryException(ContentDomainException):
    """Invalid category for resource type."""

    def __init__(self, category: str, resource_type: str):
        self.category = category
        self.resource_type = resource_type
        super().__init__(
            f"Invalid category '{category}' for resource type '{resource_type}'"
        )
