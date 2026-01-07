"""
Platform Domain Exceptions.

@module domains.platform.exceptions
@version 1.0.0
"""

from core.exceptions import DomainException


class PlatformException(DomainException):
    """Base exception for platform domain."""

    def __init__(self, message: str, code: str = "PLATFORM_ERROR"):
        super().__init__(message, code)


class FeatureFlagNotFoundException(PlatformException):
    """Raised when a feature flag is not found."""

    def __init__(self, flag_key: str):
        super().__init__(
            message=f"Feature flag not found: {flag_key}",
            code="FEATURE_FLAG_NOT_FOUND"
        )
        self.flag_key = flag_key
        self.status_code = 404


class ExperimentNotFoundException(PlatformException):
    """Raised when an experiment is not found."""

    def __init__(self, experiment_id: str):
        super().__init__(
            message=f"Experiment not found: {experiment_id}",
            code="EXPERIMENT_NOT_FOUND"
        )
        self.experiment_id = experiment_id
        self.status_code = 404


class InvalidConfigurationException(PlatformException):
    """Raised when configuration is invalid."""

    def __init__(self, config_type: str, reason: str):
        super().__init__(
            message=f"Invalid {config_type} configuration: {reason}",
            code="INVALID_CONFIGURATION"
        )
        self.config_type = config_type
        self.reason = reason
        self.status_code = 400


class FeatureFlagEvaluationException(PlatformException):
    """Raised when feature flag evaluation fails."""

    def __init__(self, flag_key: str, reason: str):
        super().__init__(
            message=f"Failed to evaluate feature flag '{flag_key}': {reason}",
            code="FLAG_EVALUATION_FAILED"
        )
        self.flag_key = flag_key
        self.reason = reason
        self.status_code = 500


class ExperimentAssignmentException(PlatformException):
    """Raised when experiment assignment fails."""

    def __init__(self, experiment_id: str, reason: str):
        super().__init__(
            message=f"Failed to assign experiment '{experiment_id}': {reason}",
            code="EXPERIMENT_ASSIGNMENT_FAILED"
        )
        self.experiment_id = experiment_id
        self.reason = reason
        self.status_code = 500
