"""
Billing Domain Exceptions - Business-specific errors.

@module domains.billing.exceptions
@version 1.0.0
"""

from core.exceptions import AppException, ErrorCode


class BillingException(AppException):
    """Base exception for billing domain."""
    pass


class InsufficientCreditsException(BillingException):
    """User doesn't have enough credits for the operation."""
    status_code = 402  # Payment Required
    default_code = ErrorCode.PAYMENT_REQUIRED
    default_message = "Insufficient credits"

    def __init__(
        self,
        required: int = None,
        available: int = None,
        **kwargs
    ):
        message = "Insufficient credits for this operation"
        if required is not None and available is not None:
            message = f"Insufficient credits: need {required}, have {available}"

        super().__init__(
            message=message,
            context={
                "required": required,
                "available": available,
            },
            details={
                "required": required,
                "available": available,
            },
            **kwargs
        )


class InvalidAmountException(BillingException):
    """Credit amount is invalid (negative, zero, etc.)."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Invalid credit amount"

    def __init__(self, amount: int = None, reason: str = None, **kwargs):
        message = reason or "Credit amount must be a positive integer"
        if amount is not None:
            message = f"Invalid amount {amount}: {reason or 'must be positive'}"

        super().__init__(
            message=message,
            context={"amount": amount, "reason": reason},
            **kwargs
        )


class CreditOperationFailedException(BillingException):
    """Credit operation failed (database error, etc.)."""
    status_code = 500
    default_code = ErrorCode.SERVER_ERROR
    default_message = "Credit operation failed"

    def __init__(
        self,
        operation: str = None,
        reason: str = None,
        **kwargs
    ):
        message = "Credit operation failed"
        if operation and reason:
            message = f"Failed to {operation}: {reason}"
        elif reason:
            message = reason

        super().__init__(
            message=message,
            context={"operation": operation, "reason": reason},
            **kwargs
        )


class TransactionNotFoundException(BillingException):
    """Credit transaction not found."""
    status_code = 404
    default_code = ErrorCode.NOT_FOUND
    default_message = "Transaction not found"

    def __init__(self, transaction_id: str = None, **kwargs):
        message = "Credit transaction not found"
        if transaction_id:
            message = f"Transaction {transaction_id} not found"

        super().__init__(
            message=message,
            context={"transaction_id": transaction_id},
            **kwargs
        )
