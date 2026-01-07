"""
Platform Domain Exceptions.

@module domains.platform.exceptions
@version 1.0.0
"""

from core.exceptions import AppException, ErrorCode


class PlatformException(AppException):
    """Base exception for platform domain."""
    pass


class FeatureFlagNotFoundException(PlatformException):
    """Raised when a feature flag is not found."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Feature flag not found"

    def __init__(self, flag_key: str = None, **kwargs):
        message = "Feature flag not found"
        if flag_key:
            message = f"Feature flag not found: {flag_key}"

        super().__init__(
            message=message,
            context={"flag_key": flag_key},
            **kwargs
        )


class ExperimentNotFoundException(PlatformException):
    """Raised when an experiment is not found."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Experiment not found"

    def __init__(self, experiment_id: str = None, **kwargs):
        message = "Experiment not found"
        if experiment_id:
            message = f"Experiment not found: {experiment_id}"

        super().__init__(
            message=message,
            context={"experiment_id": experiment_id},
            **kwargs
        )


class InvalidConfigurationException(PlatformException):
    """Raised when configuration is invalid."""
    status_code = 400
    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Invalid configuration"

    def __init__(self, config_type: str = None, reason: str = None, **kwargs):
        message = "Invalid configuration"
        if config_type and reason:
            message = f"Invalid {config_type} configuration: {reason}"

        super().__init__(
            message=message,
            context={"config_type": config_type, "reason": reason},
            **kwargs
        )


class FeatureFlagEvaluationException(PlatformException):
    """Raised when feature flag evaluation fails."""
    status_code = 500
    default_code = ErrorCode.SERVER_ERROR
    default_message = "Feature flag evaluation failed"

    def __init__(self, flag_key: str = None, reason: str = None, **kwargs):
        message = "Feature flag evaluation failed"
        if flag_key:
            message = f"Failed to evaluate feature flag '{flag_key}'"
            if reason:
                message += f": {reason}"

        super().__init__(
            message=message,
            context={"flag_key": flag_key, "reason": reason},
            **kwargs
        )


class ExperimentAssignmentException(PlatformException):
    """Raised when experiment assignment fails."""
    status_code = 500
    default_code = ErrorCode.SERVER_ERROR
    default_message = "Experiment assignment failed"

    def __init__(self, experiment_id: str = None, reason: str = None, **kwargs):
        message = "Experiment assignment failed"
        if experiment_id:
            message = f"Failed to assign experiment '{experiment_id}'"
            if reason:
                message += f": {reason}"

        super().__init__(
            message=message,
            context={"experiment_id": experiment_id, "reason": reason},
            **kwargs
        )
