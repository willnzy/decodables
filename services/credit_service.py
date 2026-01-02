"""
Credit Service
Handles credit-related business logic

@module services/credit_service
"""

from typing import Optional, Tuple, Literal
from config import CREDITS_PER_IMAGE, CREDITS_PER_OCR

# Default timezone for transactions
DEFAULT_TIMEZONE = "UTC"


class CreditService:
    """
    Service for managing user credits.
    
    Credit Types (PRD v3.2):
    - Monthly Credits: Reset monthly, no rollover
    - Permanent Credits: Never expire
    
    Deduction Priority: Monthly first, then Permanent
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
        timezone: str = DEFAULT_TIMEZONE
    ) -> Tuple[bool, str]:
        """
        Deduct credits from user's account.
        
        Deduction priority: Monthly first, then Permanent.
        
        NOTE: For production, this should use a database transaction (RPC function)
        to ensure atomicity. Current implementation does a best-effort approach.
        
        PRD requirement: ": "
        
        Args:
            user_id: User ID
            amount: Amount to deduct (positive number)
            tx_type: Transaction type (e.g., 'generation', 'ocr', 'market_purchase')
            description: Optional description
            timezone: IANA timezone for transaction snapshot (e.g., 'Asia/Shanghai')
        
        Returns:
            Tuple of (success, message)
        """
        if amount <= 0:
            return (True, "No credits needed")
        
        # Re-fetch balance to minimize race condition window
        monthly, permanent = self.get_balance(user_id)
        total = monthly + permanent
        
        if total < amount:
            return (False, f"Insufficient credits. Need {amount}, have {total}")
        
        # Calculate deduction from each bucket (Monthly first per PRD)
        deduct_monthly = min(monthly, amount)
        deduct_permanent = amount - deduct_monthly
        
        new_monthly = monthly - deduct_monthly
        new_permanent = permanent - deduct_permanent
        
        # Determine which bucket was primarily used for logging
        bucket = "monthly" if deduct_monthly > 0 else "permanent"
        
        try:
            # TODO: Replace with RPC transaction for production
            # Example: self.supabase.rpc("deduct_credits", {...}).execute()
            
            # Update balances with optimistic locking check
            result = self.supabase.table("profiles").update({
                "credits_monthly": new_monthly,
                "credits_permanent": new_permanent
            }).eq("id", user_id).eq(
                "credits_monthly", monthly  # Optimistic lock
            ).eq(
                "credits_permanent", permanent  # Optimistic lock
            ).execute()
            
            # Check if update actually happened (optimistic lock failed if no rows updated)
            if not result.data:
                return (False, "Balance changed during transaction, please retry")
            
            # Record transaction with timezone snapshot
            self.supabase.table("credit_transactions").insert({
                "user_id": user_id,
                "amount": -amount,
                "bucket": bucket,
                "balance_monthly_after": new_monthly,
                "balance_permanent_after": new_permanent,
                "type": tx_type,
                "description": description,
                "timezone": timezone
            }).execute()
            
            return (True, f"Deducted {amount} credits")
        except Exception as e:
            # Log error for debugging
            print(f"Credit deduction error for user {user_id}: {str(e)}")
            return (False, str(e))
    
    def add(
        self, 
        user_id: str, 
        amount: int, 
        bucket: Literal["monthly", "permanent"],
        tx_type: str,
        description: Optional[str] = None,
        timezone: str = DEFAULT_TIMEZONE
    ) -> Tuple[bool, str]:
        """
        Add credits to user's account.
        
        Args:
            user_id: User ID
            amount: Amount to add (positive number)
            bucket: Which bucket to add to ('monthly' or 'permanent')
            tx_type: Transaction type
            description: Optional description
            timezone: IANA timezone for transaction snapshot (e.g., 'Asia/Shanghai')
        
        Returns:
            Tuple of (success, message)
        """
        if amount <= 0:
            return (False, "Amount must be positive")
        
        monthly, permanent = self.get_balance(user_id)
        
        if bucket == "monthly":
            new_monthly = monthly + amount
            new_permanent = permanent
        else:
            new_monthly = monthly
            new_permanent = permanent + amount
        
        try:
            # Update balances
            self.supabase.table("profiles").update({
                "credits_monthly": new_monthly,
                "credits_permanent": new_permanent
            }).eq("id", user_id).execute()
            
            # Record transaction with timezone snapshot
            self.supabase.table("credit_transactions").insert({
                "user_id": user_id,
                "amount": amount,
                "bucket": bucket,
                "balance_monthly_after": new_monthly,
                "balance_permanent_after": new_permanent,
                "type": tx_type,
                "description": description,
                "timezone": timezone
            }).execute()
            
            return (True, f"Added {amount} credits to {bucket}")
        except Exception as e:
            return (False, str(e))
    
    def reset_monthly(
        self, 
        user_id: str, 
        amount: int,
        timezone: str = DEFAULT_TIMEZONE
    ) -> Tuple[bool, str]:
        """
        Reset monthly credits (subscription cycle).
        
        Args:
            user_id: User ID
            amount: New monthly credit amount (based on tier)
            timezone: IANA timezone for transaction snapshot
        
        Returns:
            Tuple of (success, message)
        """
        monthly, permanent = self.get_balance(user_id)
        
        try:
            # Set monthly to new amount (not add, replace)
            self.supabase.table("profiles").update({
                "credits_monthly": amount
            }).eq("id", user_id).execute()
            
            # Record transaction with timezone snapshot
            self.supabase.table("credit_transactions").insert({
                "user_id": user_id,
                "amount": amount - monthly,  # Net change
                "bucket": "monthly",
                "balance_monthly_after": amount,
                "balance_permanent_after": permanent,
                "type": "sub_grant",
                "description": "Monthly credits reset",
                "timezone": timezone
            }).execute()
            
            return (True, f"Monthly credits reset to {amount}")
        except Exception as e:
            return (False, str(e))
    
    def is_first_generation(self, user_id: str) -> bool:
        """
        Check if this is user's first AI generation.
        PRD:  0 Credits  onboarding 
        
        Args:
            user_id: User ID
        
        Returns:
            True if user has never generated before
        """
        result = self.supabase.table("credit_transactions").select(
            "id"
        ).eq("user_id", user_id).eq("type", "generation").limit(1).execute()
        
        return not result.data or len(result.data) == 0
    
    def get_generation_cost(self, user_id: str) -> int:
        """
        Get cost for AI image generation.
        PRD: 5 Credits/Image,  0 Credits
        
        Args:
            user_id: User ID
        
        Returns:
            Cost in credits (0 for first generation)
        """
        if self.is_first_generation(user_id):
            return 0
        return CREDITS_PER_IMAGE
    
    @staticmethod
    def get_ocr_cost() -> int:
        """Get cost for OCR."""
        return CREDITS_PER_OCR

