"""
Story Generation Service - Business logic for AI story generation.

@module domains.generation.story_service
@version 1.0.0

This service orchestrates the story generation workflow:
1. Get cost from config (configurable, currently 0)
2. Deduct credits if cost > 0 (with idempotency)
3. Generate story via AI
4. Refund on failure (to correct bucket)

Changes:
- v1.0.0: Initial creation - Extracted from api/user/generation_story.py
          Implemented DDD architecture with dependency injection
          Fixed GS-CRITICAL-1: Added Service layer
          Fixed GS-CHAIN-1: Accurate refund tracking (same bucket)
"""

import logging
from typing import Dict, Any, Optional
import time
import uuid

# WS-15(SUP-7c): Use async version to avoid blocking event loop
from shared.ai.story_generator import generate_story_json_async
from domains.billing import BillingService
from domains.billing.value_objects import TransactionType, CreditBucket
from domains.billing.exceptions import InsufficientCreditsException
from application.services.generation_helpers import get_text_generation_cost

logger = logging.getLogger(__name__)


# ==========================================
# Custom Exceptions
# ==========================================

class StoryGenerationException(Exception):
    """Raised when story generation fails."""
    pass


# ==========================================
# Story Generation Service
# ==========================================

class StoryGenerationService:
    """
    Service for AI story generation workflow.

    Responsibilities:
    - Manage credit deduction/refund for story generation
    - Generate story JSON via AI
    - Handle errors with automatic refund to correct bucket

    Dependencies (Injected):
    - billing_service: Credit management
    """

    def __init__(self, billing_service: BillingService):
        """
        Initialize StoryGenerationService.

        Args:
            billing_service: BillingService for credit management
        """
        self.billing_service = billing_service

    async def generate_story(
        self,
        user_id: str,
        tier: str,
        topic: str,
    ) -> Dict[str, Any]:
        """
        Generate story JSON with credit management.

        Workflow:
        1. Get cost from config (currently 0, but configurable)
        2. Deduct credits if cost > 0 (with idempotency)
        3. Generate story via AI
        4. Return result, or refund on failure

        Args:
            user_id: User ID
            tier: User tier (t1, t3)
            topic: Story topic/theme

        Returns:
            Dict with story data (title, pages, characters, setting)

        Raises:
            InsufficientCreditsException: If user lacks credits (API returns 402)
            StoryGenerationException: If generation fails (API returns 500)
        """
        cost = await get_text_generation_cost()
        idempotency_key = None
        deduction_bucket = None  # Track which bucket was deducted

        # Step 1: Deduct credits if cost > 0
        if cost > 0:
            idempotency_key = self._generate_idempotency_key(user_id)

            try:
                tx = await self.billing_service.deduct_credits(
                    user_id=user_id,
                    amount=cost,
                    tx_type=TransactionType.AI_GENERATION,
                    description=f"Story generation: {topic[:30]}..." if len(topic) > 30 else f"Story generation: {topic}",
                    idempotency_key=idempotency_key,
                )
                # v1.0.0: Track bucket for accurate refund (GS-CHAIN-1 fix)
                deduction_bucket = tx.bucket
                logger.info(f"Deducted {cost} credits from {deduction_bucket} for user {user_id[:8]}...")
            except InsufficientCreditsException:
                # Re-raise for API layer to convert to 402
                raise

        # Step 2: Generate story via AI
        try:
            # WS-15(SUP-7c): Use async version to avoid blocking event loop
            result = await generate_story_json_async(
                topic,
                user_id=user_id,
                tier=tier,
            )
            return result
        except Exception as e:
            # Step 3: Refund on failure
            if cost > 0 and idempotency_key:
                await self._refund_credits(
                    user_id=user_id,
                    cost=cost,
                    idempotency_key=idempotency_key,
                    bucket=deduction_bucket or CreditBucket.MONTHLY,  # Fallback to MONTHLY if unknown
                    reason=str(e)[:50],
                )

            logger.error(f"Story generation failed for user {user_id[:8]}...: {e}")
            raise StoryGenerationException("Story generation failed")

    async def _refund_credits(
        self,
        user_id: str,
        cost: int,
        idempotency_key: str,
        bucket: CreditBucket,
        reason: str,
    ):
        """
        Refund credits to the same bucket that was deducted.

        v1.0.0: GS-CHAIN-1 fix - Accurate refund tracking
        """
        try:
            await self.billing_service.add_credits(
                user_id=user_id,
                amount=cost,
                bucket=bucket,  # Refund to same bucket (fixed GS-CHAIN-1)
                tx_type=TransactionType.REFUND,
                description=f"Refund: story generation failed - {reason}",
                idempotency_key=f"refund_{idempotency_key}",
            )
            logger.info(f"Refunded {cost} credits to {bucket} for user {user_id[:8]}...")
        except Exception as refund_error:
            logger.error(f"CRITICAL: Failed to refund {cost} credits: {refund_error}")

    def _generate_idempotency_key(self, user_id: str) -> str:
        """Generate unique idempotency key for credit transactions."""
        return f"gen_story_{user_id}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
