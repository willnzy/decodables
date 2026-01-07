"""
Task Handlers
任务处理器

Contains the actual task execution logic for background workers.
"""

import os
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Supabase client for database operations
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL and not SUPABASE_URL.endswith('/'):
    SUPABASE_URL = SUPABASE_URL + '/'

_supabase: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """Get Supabase client (lazy initialization)."""
    global _supabase
    if _supabase is None and SUPABASE_URL and SUPABASE_KEY:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


class ImageGenerationHandler:
    """
    Handles image generation tasks.
    
    Executes in background worker process.
    """
    
    def __init__(self, task_data: Dict[str, Any]):
        self.task_id = task_data.get("task_id")
        self.user_id = task_data.get("user_id")
        self.tier = task_data.get("tier", "free")
        self.params = task_data.get("params", {})
        self.worker_id = f"worker_{os.getpid()}"
        
        # Import progress tracker (avoid circular import)
        from .progress_tracker import progress_tracker
        self.progress = progress_tracker
    
    async def execute(self) -> Dict[str, Any]:
        """
        Execute image generation task.
        
        Returns:
            Result dict with image_urls and metadata
        """
        # Mark task as started
        self.progress.mark_started(self.task_id, self.worker_id)
        
        try:
            # Import image generator (avoid circular import at module level)
            from shared.ai.image_generator import generate_and_upload_single
            import aiohttp
            
            # Extract parameters
            prompts = self.params.get("prompts", [])
            num_images = self.params.get("num_images", 1)
            reference_image = self.params.get("reference_image")
            reference_strength = self.params.get("reference_strength", 0.7)
            image_size = self.params.get("image_size", "landscape_4_3")
            generation_mode = self.params.get("generation_mode", "guided")
            creativity_level = self.params.get("creativity_level", 0.3)
            negative_prompt = self.params.get("negative_prompt")
            model = self.params.get("model", "flux-schnell")
            
            # Calculate total steps
            total_steps = len(prompts) * num_images
            self.progress.update(
                self.task_id,
                total_steps=total_steps,
                message=f"Starting generation of {total_steps} images..."
            )
            
            # Process reference image if provided
            reference_image_url = None
            if reference_image:
                from shared.ai.image_generator import upload_reference_image
                async with aiohttp.ClientSession() as session:
                    reference_image_url = await upload_reference_image(
                        session, reference_image, self.task_id, self.user_id
                    )
                    if not reference_image_url:
                        logger.warning(f"[Task:{self.task_id}] Reference image upload failed, continuing without")
            
            # Generate images one by one with progress updates
            image_urls = []
            async with aiohttp.ClientSession() as session:
                for prompt_idx, prompt in enumerate(prompts):
                    for variation in range(num_images):
                        image_index = prompt_idx * num_images + variation
                        
                        try:
                            # Generate single image
                            url = await generate_and_upload_single(
                                session=session,
                                prompt=prompt,
                                index=image_index,
                                task_id=self.task_id,
                                model=model,
                                reference_image_url=reference_image_url,
                                reference_strength=reference_strength,
                                image_size=image_size,
                                generation_mode=generation_mode,
                                creativity_level=creativity_level,
                                negative_prompt=negative_prompt,
                                user_id=self.user_id,
                                tier=self.tier
                            )
                            
                            image_urls.append(url)
                            
                            # Update progress with step result
                            self.progress.increment_step(
                                self.task_id,
                                step_result={"url": url, "index": image_index},
                                message=f"Generated {image_index + 1}/{total_steps} images"
                            )
                            
                        except Exception as e:
                            logger.error(f"[Task:{self.task_id}] Image {image_index} failed: {e}")
                            image_urls.append(None)
                            self.progress.increment_step(
                                self.task_id,
                                step_result={"error": str(e), "index": image_index},
                                message=f"Image {image_index + 1} failed, continuing..."
                            )
            
            # Build result
            successful_urls = [url for url in image_urls if url]
            result = {
                "image_urls": successful_urls,
                "total_requested": total_steps,
                "total_generated": len(successful_urls),
                "model_used": model,
                "task_id": self.task_id,
            }
            
            # Save to database
            await self._save_generation_records(successful_urls, prompts, num_images)
            
            # Mark completed
            self.progress.mark_completed(self.task_id, result)
            
            # Update database task record
            self._update_db_task("completed", result)
            
            return result
            
        except Exception as e:
            logger.error(f"[Task:{self.task_id}] Generation failed: {e}")
            self.progress.mark_failed(self.task_id, str(e), "GENERATION_ERROR")
            self._update_db_task("failed", error=str(e))
            raise
    
    async def _save_generation_records(
        self,
        urls: List[str],
        prompts: List[str],
        num_images: int
    ):
        """Save generation records to database."""
        supabase = get_supabase()
        if not supabase:
            return
        
        try:
            for idx, url in enumerate(urls):
                if not url:
                    continue
                
                prompt_idx = idx // num_images if num_images > 1 else idx
                prompt_used = prompts[prompt_idx] if prompt_idx < len(prompts) else prompts[0]
                
                # Save to assets table
                supabase.table("assets").insert({
                    "user_id": self.user_id,
                    "file_url": url,
                    "source": "ai_generated",
                    "description": prompt_used,
                }).execute()
                
                # Save to user_generations table
                supabase.table("user_generations").insert({
                    "user_id": self.user_id,
                    "image_url": url,
                    "original_prompt": prompt_used,
                    "generation_mode": self.params.get("generation_mode", "guided"),
                    "creativity_level": self.params.get("creativity_level", 0.3),
                    "has_reference": bool(self.params.get("reference_image")),
                    "batch_id": self.task_id,
                    "batch_index": idx,
                    "model_used": self.params.get("model", "flux-schnell"),
                }).execute()
                
        except Exception as e:
            logger.warning(f"[Task:{self.task_id}] Failed to save records: {e}")
    
    def _update_db_task(
        self,
        status: str,
        result: Dict = None,
        error: str = None
    ):
        """Update task record in database."""
        supabase = get_supabase()
        if not supabase:
            return
        
        try:
            update_data = {
                "status": status,
                "worker_id": self.worker_id,
            }
            
            if result:
                update_data["result"] = result
            if error:
                update_data["error_message"] = error
            
            if status in ("completed", "failed"):
                update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            supabase.table("generation_tasks").update(update_data).eq(
                "task_id", self.task_id
            ).execute()
            
        except Exception as e:
            logger.warning(f"[Task:{self.task_id}] Failed to update DB task: {e}")


def execute_image_generation(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point for RQ worker.
    
    This function is called by RQ workers to execute image generation.
    It wraps the async handler in an event loop.
    """
    handler = ImageGenerationHandler(task_data)
    
    # Run async code in sync context (RQ doesn't support async natively)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(handler.execute())
        return result
    finally:
        loop.close()
