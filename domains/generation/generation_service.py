"""
Generation Service - AI Image Generation Workflow Orchestration

@module domains.generation.generation_service
@version 1.0.0 (DDD Architecture - 5 Star)

Architecture: API → GenerationService → Repositories + External Services

This service orchestrates the complete AI image generation workflow:
- Credit deduction/refund via BillingService
- Image generation via external AI API
- Asset storage via AssetRepository
- Generation history tracking
- Analytics tracking
"""

import logging
import uuid
import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from core.database import get_supabase_client
from infrastructure.repositories import SupabaseAssetRepository
from shared.ai.image_generator import generate_8_images
from infrastructure.task_queue import task_queue
from domains.platform.analytics_service import track_ai_generation
from domains.billing.value_objects import TransactionType, CreditBucket
from domains.billing.exceptions import InsufficientCreditsException
from application.services.generation_helpers import (
    calculate_cost,
    get_base_cost,
    build_generation_record,
)

# Generation timeout in seconds (prevent DoS)
GENERATION_TIMEOUT_SECONDS = 120

logger = logging.getLogger(__name__)


class GenerationTimeoutException(Exception):
    """Raised when image generation times out."""
    pass


class GenerationFailedException(Exception):
    """Raised when image generation fails."""
    pass


class EmptyGenerationException(Exception):
    """Raised when generation returns no images."""
    pass


class GenerationService:
    """
    Generation Service - Handles AI image generation workflow.

    Responsibilities:
    - Coordinate generation process
    - Deduct/refund credits via BillingService
    - Save assets via AssetRepository
    - Save generation history to database
    - Track analytics
    - Handle errors and timeouts with automatic refunds

    Architecture: API → GenerationService → (BillingService, AssetRepository, AI API)

    v1.0.0: Created for DDD compliance (GI-CRITICAL-1 fix)
    """

    def __init__(
        self,
        billing_service,  # BillingService (injected via DI)
        asset_repository: SupabaseAssetRepository,  # Asset storage
    ):
        """
        Initialize Generation Service.

        Args:
            billing_service: BillingService for credit operations
            asset_repository: Repository for asset storage
        """
        self.billing_service = billing_service
        self.asset_repo = asset_repository
        self.supabase = get_supabase_client()

    async def generate_images_sync(
        self,
        user_id: str,
        prompts: List[str],
        num_images: int,
        model: str,
        tier: str,
        reference_image: Optional[str] = None,
        reference_strength: float = 0.7,
        image_size: str = "landscape_4_3",
        generation_mode: str = "guided",
        creativity_level: str = "balanced",
        negative_prompt: Optional[str] = None,
        project_id: Optional[str] = None,
        theme: Optional[str] = None,
        prompts_to_use: Optional[List[str]] = None,
        enhanced_prompt_text: Optional[str] = None,
        timezone: str = "UTC",
    ) -> Dict[str, Any]:
        """
        Generate images synchronously with full workflow orchestration.

        Workflow:
        1. Calculate cost and deduct credits
        2. Generate images with timeout protection
        3. Filter successful results
        4. Save assets and generation history
        5. Track analytics
        6. Return results with updated balance

        On any failure (timeout, error, empty result), credits are automatically refunded.

        Args:
            user_id: User ID
            prompts: Original prompts
            num_images: Number of images per prompt (1-4)
            model: AI model to use (flux-schnell, flux-dev)
            tier: User tier (free, starter, pro)
            reference_image: Optional reference image URL
            reference_strength: Reference influence (0-1)
            image_size: Image aspect ratio
            generation_mode: guided or flexible
            creativity_level: low, balanced, high
            negative_prompt: Optional negative prompt
            project_id: Optional project to attach images to
            theme: Optional theme for prompt enhancement
            prompts_to_use: Enhanced prompts (if already processed)
            enhanced_prompt_text: Enhanced prompt result
            timezone: User timezone

        Returns:
            Dict with:
                - image_urls: List of generated image URLs
                - balance: Total credits remaining
                - balance_monthly: Monthly credits
                - balance_permanent: Permanent credits
                - model_used: Model name
                - used_reference: Boolean
                - generation_mode: Mode used
                - creativity_level: Level used
                - batch_id: Batch identifier
                - num_images: Count of successful images
                - generation_time_ms: Generation time
                - (optional) enhanced_prompt: Enhanced prompt text
                - (optional) key_elements: Key elements extracted

        Raises:
            InsufficientCreditsException: If user has insufficient credits
            GenerationTimeoutException: If generation exceeds timeout
            GenerationFailedException: If generation fails
            EmptyGenerationException: If no images generated
        """
        # Use enhanced prompts if provided, otherwise use original
        final_prompts = prompts_to_use or prompts

        # Calculate cost using config-driven pricing
        has_reference = bool(reference_image)
        cost = calculate_cost(len(final_prompts), has_reference, num_images)
        base_cost = get_base_cost(has_reference)

        # Deduct credits using DDD BillingService with atomic operation
        idempotency_key = f"gen_sync_{user_id}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

        tx = await self.billing_service.deduct_credits(
            user_id=user_id,
            amount=cost,
            tx_type=TransactionType.GENERATION,
            description=f"Gen {len(final_prompts)} images" + (" with ref" if has_reference else ""),
            idempotency_key=idempotency_key,
        )

        # Get balance after deduction
        user_credits = await self.billing_service.get_user_credits(user_id)
        balance_monthly = user_credits.monthly_credits if user_credits else 0
        balance_permanent = user_credits.permanent_credits if user_credits else 0
        balance_total = balance_monthly + balance_permanent

        # Generate unique batch ID
        batch_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
        generation_start = time.time()

        # Generate images with timeout protection
        try:
            urls, task_id = await asyncio.wait_for(
                generate_8_images(
                    final_prompts,
                    model=model,
                    reference_image=reference_image,
                    reference_strength=reference_strength,
                    image_size=image_size,
                    generation_mode=generation_mode,
                    creativity_level=creativity_level,
                    negative_prompt=negative_prompt,
                    num_images=num_images,
                    user_id=user_id,
                    tier=tier
                ),
                timeout=GENERATION_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            # Generation timed out - refund credits
            logger.error(f"Image generation timed out after {GENERATION_TIMEOUT_SECONDS}s, refunding {cost} credits")
            await self._refund_credits(user_id, cost, "timeout", idempotency_key)
            raise GenerationTimeoutException("Image generation timed out")
        except Exception as e:
            # Generation failed - refund credits atomically
            logger.error(f"Image generation failed, refunding {cost} credits: {e}")
            await self._refund_credits(user_id, cost, "failed", idempotency_key)
            raise GenerationFailedException(str(e))

        generation_time_ms = int((time.time() - generation_start) * 1000)

        # Filter successful URLs
        successful_urls = [url for url in urls if url]

        # If no images generated, refund
        if not successful_urls:
            logger.warning(f"No images generated, refunding {cost} credits")
            await self._refund_credits(user_id, cost, "empty", idempotency_key)
            raise EmptyGenerationException("No images were generated")

        # Save assets and generation history
        await self._save_generation_results(
            user_id=user_id,
            urls=successful_urls,
            prompts=final_prompts,
            original_prompts=prompts,
            enhanced_prompt_text=enhanced_prompt_text,
            batch_id=batch_id,
            cost=cost,
            base_cost=base_cost,
            num_images=num_images,
            model=model,
            generation_mode=generation_mode,
            creativity_level=creativity_level,
            has_reference=has_reference,
            reference_strength=reference_strength if has_reference else None,
            negative_prompt=negative_prompt,
            theme=theme,
            project_id=project_id,
            generation_time_ms=generation_time_ms,
            timezone=timezone,
        )

        # Track analytics
        track_ai_generation(
            user_id=user_id,
            success=True,
            model=model,
            cost_credits=cost,
            duration_ms=generation_time_ms,
            extra_properties={
                "batch_id": batch_id,
                "num_images": len(successful_urls),
                "generation_mode": generation_mode,
                "has_reference": has_reference,
                "prompt_enhanced": bool(enhanced_prompt_text),
            }
        )

        return {
            "image_urls": successful_urls,
            "balance": balance_total,
            "balance_monthly": balance_monthly,
            "balance_permanent": balance_permanent,
            "model_used": model,
            "used_reference": has_reference,
            "generation_mode": generation_mode,
            "creativity_level": creativity_level,
            "batch_id": batch_id,
            "num_images": len(successful_urls),
            "generation_time_ms": generation_time_ms,
        }

    async def generate_images_async(
        self,
        user_id: str,
        prompts: List[str],
        num_images: int,
        model: str,
        tier: str,
        reference_image: Optional[str] = None,
        reference_strength: float = 0.7,
        image_size: str = "landscape_4_3",
        generation_mode: str = "guided",
        creativity_level: str = "balanced",
        negative_prompt: Optional[str] = None,
        project_id: Optional[str] = None,
        prompts_to_use: Optional[List[str]] = None,
        enhanced_prompt_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate images asynchronously via task queue.

        Workflow:
        1. Calculate cost and deduct credits immediately
        2. Generate task ID
        3. Save task to database
        4. Enqueue task for background processing
        5. Return task_id for progress tracking

        On queue failure, credits are automatically refunded.

        Args:
            user_id: User ID
            prompts: Original prompts
            num_images: Number of images per prompt
            model: AI model to use
            tier: User tier
            (other params same as generate_images_sync)

        Returns:
            Dict with:
                - task_id: Task identifier
                - status: "queued"
                - message: Status message
                - credits_charged: Credits deducted
                - balance: Total credits remaining
                - balance_monthly: Monthly credits
                - balance_permanent: Permanent credits
                - websocket_url: WebSocket endpoint for live updates
                - poll_url: Polling endpoint for status
                - model_used: Model name
                - priority: Queue priority (high/normal/low)
                - (optional) enhanced_prompt: Enhanced prompt text

        Raises:
            InsufficientCreditsException: If user has insufficient credits
            Exception: If task queue fails (after refund)
        """
        # Use enhanced prompts if provided
        final_prompts = prompts_to_use or prompts

        # Calculate cost using config-driven pricing
        has_reference = bool(reference_image)
        cost = calculate_cost(len(final_prompts), has_reference, num_images)

        # Generate task ID first (for idempotency)
        task_id = f"gen_{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:8]}"

        # Deduct credits using DDD BillingService with atomic operation
        tx = await self.billing_service.deduct_credits(
            user_id=user_id,
            amount=cost,
            tx_type=TransactionType.GENERATION,
            description=f"Async gen {len(final_prompts)} images" + (" with ref" if has_reference else ""),
            idempotency_key=f"gen_async_{task_id}",
        )

        # Get balance after deduction
        user_credits = await self.billing_service.get_user_credits(user_id)
        balance_monthly = user_credits.monthly_credits if user_credits else 0
        balance_permanent = user_credits.permanent_credits if user_credits else 0
        balance_total = balance_monthly + balance_permanent

        task_params = {
            "prompts": final_prompts,
            "model": model,
            "reference_image": reference_image,
            "reference_strength": reference_strength,
            "image_size": image_size,
            "generation_mode": generation_mode,
            "creativity_level": creativity_level,
            "negative_prompt": negative_prompt,
            "num_images": num_images,
            "project_id": project_id,
            "credits_charged": cost,
        }

        # Save task to database
        try:
            self.supabase.rpc("create_generation_task", {
                "p_task_id": task_id,
                "p_user_id": user_id,
                "p_task_type": "image_generation",
                "p_params": task_params,
                "p_priority": 2 if tier == "pro" else (1 if tier == "starter" else 0),
                "p_total_steps": len(final_prompts) * num_images,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save task to DB: {e}")

        # Enqueue task
        enqueued_task_id = task_queue.enqueue_image_generation(
            user_id=user_id,
            params=task_params,
            tier=tier,
            idempotency_key=task_id
        )

        if not enqueued_task_id:
            logger.error(f"[AsyncGen] Failed to enqueue task {task_id}")
            # Refund credits atomically
            await self._refund_credits(user_id, cost, "queue_failed", task_id)
            raise Exception("Generation service temporarily unavailable")

        # Track analytics
        track_ai_generation(
            user_id=user_id,
            success=True,
            model=model,
            cost_credits=cost,
            duration_ms=0,
            extra_properties={
                "async": True,
                "task_id": task_id,
                "num_images": num_images,
                "generation_mode": generation_mode,
                "has_reference": has_reference,
            }
        )

        response = {
            "task_id": task_id,
            "status": "queued",
            "message": f"Task queued for {len(final_prompts) * num_images} images",
            "credits_charged": cost,
            "balance": balance_total,
            "balance_monthly": balance_monthly,
            "balance_permanent": balance_permanent,
            "websocket_url": f"/ws/task/{task_id}",
            "poll_url": f"/api/tasks/{task_id}",
            "model_used": model,
            "priority": "high" if tier == "pro" else ("normal" if tier == "starter" else "low"),
        }

        if enhanced_prompt_text:
            response["enhanced_prompt"] = enhanced_prompt_text

        return response

    async def _refund_credits(
        self,
        user_id: str,
        amount: int,
        reason: str,
        original_key: str
    ):
        """
        Refund credits on generation failure.

        Args:
            user_id: User ID
            amount: Credits to refund
            reason: Reason for refund (timeout, failed, empty, queue_failed)
            original_key: Original idempotency key
        """
        try:
            await self.billing_service.add_credits(
                user_id=user_id,
                amount=amount,
                bucket=CreditBucket.PERMANENT,  # Refund to permanent as conservative choice
                tx_type=TransactionType.REFUND,
                description=f"Refund: generation {reason}",
                idempotency_key=f"refund_{reason}_{original_key}",
            )
            logger.info(f"Refunded {amount} credits to user {user_id} after {reason}")
        except Exception as refund_error:
            logger.error(f"CRITICAL: Failed to refund credits after {reason}: {refund_error}")
            # Re-raise to ensure caller knows refund failed
            raise

    async def _save_generation_results(
        self,
        user_id: str,
        urls: List[str],
        prompts: List[str],
        original_prompts: List[str],
        enhanced_prompt_text: Optional[str],
        batch_id: str,
        cost: int,
        base_cost: int,
        num_images: int,
        model: str,
        generation_mode: str,
        creativity_level: str,
        has_reference: bool,
        reference_strength: Optional[float],
        negative_prompt: Optional[str],
        theme: Optional[str],
        project_id: Optional[str],
        generation_time_ms: int,
        timezone: str,
    ):
        """
        Save generated images as assets and generation history.

        Args:
            urls: List of successful image URLs
            prompts: Final prompts used (may be enhanced)
            original_prompts: Original user prompts
            enhanced_prompt_text: Enhanced prompt result
            batch_id: Batch identifier
            cost: Total credits used
            base_cost: Base cost per image
            num_images: Number of images per prompt
            model: Model used
            generation_mode: Mode used
            creativity_level: Creativity level
            has_reference: Whether reference image was used
            reference_strength: Reference strength (if used)
            negative_prompt: Negative prompt (if provided)
            theme: Theme (if provided)
            project_id: Project ID (if provided)
            generation_time_ms: Total generation time
            timezone: User timezone
        """
        # Calculate per-image cost correctly
        # Total cost = prompts * base_cost * num_images
        # Per-image cost = total_cost / total_images
        total_images_expected = len(prompts) * num_images
        per_image_cost = cost / total_images_expected if total_images_expected > 0 else base_cost

        for idx, url in enumerate(urls):
            if not url:
                continue

            prompt_idx = idx // num_images if num_images > 1 else idx
            prompt_used = prompts[prompt_idx] if prompt_idx < len(prompts) else prompts[0]
            asset_prompt = f"[{theme}] {prompt_used}" if theme else prompt_used

            # Save to assets table via Repository
            await self.asset_repo.save_asset(
                user_id,
                url,
                "ai_generated",
                project_id,
                asset_prompt,
                tz=timezone
            )

            # Save to user_generations table
            try:
                generation_record = build_generation_record(
                    user_id=user_id,
                    image_url=url,
                    original_prompt=original_prompts[0] if original_prompts else None,
                    enhanced_prompt=enhanced_prompt_text,
                    negative_prompt=negative_prompt,
                    style=None,  # Not used in current implementation
                    moods=None,  # Not used in current implementation
                    aspect_ratio=None,  # Placeholder
                    generation_mode=generation_mode,
                    creativity_level=creativity_level,
                    who=None,  # Not used in current implementation
                    what=None,  # Not used in current implementation
                    where=None,  # Not used in current implementation
                    has_reference=has_reference,
                    reference_strength=reference_strength,
                    batch_id=batch_id,
                    batch_index=idx,
                    credits_used=per_image_cost,
                    model_used=model,
                    generation_time_ms=generation_time_ms // len(urls) if len(urls) > 1 else generation_time_ms,
                    timezone=timezone,
                )
                self.supabase.table("user_generations").insert(generation_record).execute()
            except Exception as e:
                logger.warning(f"Failed to save generation history: {e}")
