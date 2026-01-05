"""
Credit Service
Handles credit-related business logic

@module services/credit_service

Atomic Operations (v3.22):
- Uses PostgreSQL RPC functions for atomic credit operations
- Row locking (SELECT FOR UPDATE) prevents race conditions
- Idempotency support for duplicate request handling
"""

import logging
from typing import Optional, Tuple, Literal, Dict, Any
from config import CREDITS_PER_IMAGE, CREDITS_PER_OCR

logger = logging.getLogger(__name__)

# Default timezone for transactions
DEFAULT_TIMEZONE = "UTC"


class CreditService:
    """
    Service for managing user credits.
    
    Credit Types (PRD v3.2):
    - Monthly Credits: Reset monthly, no rollover
    - Permanent Credits: Never expire
    
    Deduction Priority: Monthly first, then Permanent
    
    Atomic Operations (v3.22):
    - All credit operations use PostgreSQL RPC for atomicity
    - Row locking prevents concurrent modification issues
    """
    
    def __init__(self, supabase):
        self.supabase = supabase
    
    def get_balance(self, user_id: str) -> Tuple[int, int]:
        """
        Get user's credit balance.
        
        Returns:
            Tuple of (monthly_credits, permanent_credits)
        """
        result = self.supabase.table("profiles").select(
            "credits_monthly, credits_permanent"
        ).eq("id", user_id).single().execute()
        
        if result.data:
            return (
                result.data.get("credits_monthly", 0),
                result.data.get("credits_permanent", 0)
            )
        return (0, 0)
    
    def get_total(self, user_id: str) -> int:
        """Get total credits (monthly + permanent)."""
        monthly, permanent = self.get_balance(user_id)
        return monthly + permanent
    
    def has_enough(self, user_id: str, required: int) -> bool:
        """Check if user has enough credits."""
        return self.get_total(user_id) >= required
    
    def deduct(
        self, 
        user_id: str, 
        amount: int, 
        tx_type: str,
        description: Optional[str] = None,
        timezone: str = DEFAULT_TIMEZONE,
        idempotency_key: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Deduct credits from user's account using atomic RPC.
        
        Deduction priority: Monthly first, then Permanent.
        
        Uses PostgreSQL RPC function for:
        - Row locking (SELECT FOR UPDATE) to prevent race conditions
        - Atomic balance update and transaction logging
        - Idempotency support for duplicate request handling
        
        PRD requirement: Monthly-first deduction
        
        Args:
            user_id: User ID
            amount: Amount to deduct (positive number)
            tx_type: Transaction type (e.g., 'generation', 'ocr', 'market_purchase')
            description: Optional description
            timezone: IANA timezone for transaction snapshot (e.g., 'Asia/Shanghai')
            idempotency_key: Optional key to prevent duplicate processing
        
        Returns:
            Tuple of (success, message)
        """
        if amount <= 0:
            return (True, "No credits needed")
        
        try:
            # Call atomic RPC function
            result = self.supabase.rpc("deduct_credits_atomic", {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_tx_type": tx_type,
                "p_description": description,
                "p_timezone": timezone,
                "p_idempotency_key": idempotency_key
            }).execute()
            
            data = result.data
            
            if not data:
                logger.error(f"[CreditService] RPC returned no data for user {user_id}")
                return (False, "Database error: no response")
            
            if data.get("success"):
                if data.get("idempotent"):
                    logger.info(f"[CreditService] Idempotent deduction for {user_id}: {idempotency_key}")
                return (True, f"Deducted {amount} credits")
            else:
                error = data.get("error", "Unknown error")
                error_code = data.get("error_code", "")
                logger.warning(f"[CreditService] Deduction failed for {user_id}: {error} ({error_code})")
                return (False, error)
                
        except Exception as e:
            logger.error(f"[CreditService] Deduction exception for {user_id}: {e}")
            return (False, str(e))
    
    def deduct_with_details(
        self, 
        user_id: str, 
        amount: int, 
        tx_type: str,
        description: Optional[str] = None,
        timezone: str = DEFAULT_TIMEZONE,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deduct credits and return detailed result.
        
        Same as deduct() but returns full result dict including balances.
        
        Returns:
            Dict with success, balance_monthly, balance_permanent, etc.
        """
        if amount <= 0:
            monthly, permanent = self.get_balance(user_id)
            return {
                "success": True,
                "message": "No credits needed",
                "balance_monthly": monthly,
                "balance_permanent": permanent
            }
        
        try:
            result = self.supabase.rpc("deduct_credits_atomic", {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_tx_type": tx_type,
                "p_description": description,
                "p_timezone": timezone,
                "p_idempotency_key": idempotency_key
            }).execute()
            
            data = result.data or {}
            return {
                "success": data.get("success", False),
                "balance_monthly": data.get("balance_monthly", 0),
                "balance_permanent": data.get("balance_permanent", 0),
                "deducted": data.get("deducted", 0),
                "bucket": data.get("bucket", ""),
                "error": data.get("error"),
                "error_code": data.get("error_code"),
                "idempotent": data.get("idempotent", False)
            }
        except Exception as e:
            logger.error(f"[CreditService] Deduction exception for {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "EXCEPTION"
            }
    
    def add(
        self, 
        user_id: str, 
        amount: int, 
        bucket: Literal["monthly", "permanent"],
        tx_type: str,
        description: Optional[str] = None,
        timezone: str = DEFAULT_TIMEZONE,
        idempotency_key: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Add credits to user's account using atomic RPC.
        
        Uses PostgreSQL RPC function for:
        - Row locking to prevent race conditions
        - Atomic balance update and transaction logging
        - Idempotency support
        
        Args:
            user_id: User ID
            amount: Amount to add (positive number)
            bucket: Which bucket to add to ('monthly' or 'permanent')
            tx_type: Transaction type
            description: Optional description
            timezone: IANA timezone for transaction snapshot (e.g., 'Asia/Shanghai')
            idempotency_key: Optional key to prevent duplicate processing
        
        Returns:
            Tuple of (success, message)
        """
        if amount <= 0:
            return (False, "Amount must be positive")
        
        try:
            result = self.supabase.rpc("add_credits_atomic", {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_bucket": bucket,
                "p_tx_type": tx_type,
                "p_description": description,
                "p_timezone": timezone,
                "p_idempotency_key": idempotency_key
            }).execute()
            
            data = result.data
            
            if not data:
                logger.error(f"[CreditService] Add RPC returned no data for user {user_id}")
                return (False, "Database error: no response")
            
            if data.get("success"):
                if data.get("idempotent"):
                    logger.info(f"[CreditService] Idempotent add for {user_id}: {idempotency_key}")
                return (True, f"Added {amount} credits to {bucket}")
            else:
                error = data.get("error", "Unknown error")
                logger.warning(f"[CreditService] Add failed for {user_id}: {error}")
                return (False, error)
                
        except Exception as e:
            logger.error(f"[CreditService] Add exception for {user_id}: {e}")
            return (False, str(e))
    
    def reset_monthly(
        self, 
        user_id: str, 
        amount: int,
        timezone: str = DEFAULT_TIMEZONE
    ) -> Tuple[bool, str]:
        """
        Reset monthly credits (subscription cycle).
        
        Note: This is a SET operation, not an ADD. Monthly credits are replaced.
        
        Args:
            user_id: User ID
            amount: New monthly credit amount (based on tier)
            timezone: IANA timezone for transaction snapshot
        
        Returns:
            Tuple of (success, message)
        """
        monthly, permanent = self.get_balance(user_id)
        
        try:
            # Use direct update for reset (this is a replace, not add)
            # Calculate the net change for transaction logging
            net_change = amount - monthly
            
            # Update monthly to new amount
            self.supabase.table("profiles").update({
                "credits_monthly": amount
            }).eq("id", user_id).execute()
            
            # Record transaction with timezone snapshot
            self.supabase.table("credit_transactions").insert({
                "user_id": user_id,
                "amount": net_change,
                "bucket": "monthly",
                "balance_monthly_after": amount,
                "balance_permanent_after": permanent,
                "type": "sub_grant",
                "description": "Monthly credits reset",
                "timezone": timezone
            }).execute()
            
            return (True, f"Monthly credits reset to {amount}")
        except Exception as e:
            logger.error(f"[CreditService] Reset exception for {user_id}: {e}")
            return (False, str(e))
    
    @staticmethod
    def get_generation_cost() -> int:
        """
        Get cost for AI image generation.
        
        Business Rule (v3.3 Section 3.3):
        - AI 图像生成消耗 5 积分/张
        - 无特殊规则（首次免费已移除）
        
        Returns:
            Cost in credits (always CREDITS_PER_IMAGE)
        """
        return CREDITS_PER_IMAGE
    
    @staticmethod
    def get_ocr_cost() -> int:
        """Get cost for OCR."""
        return CREDITS_PER_OCR
