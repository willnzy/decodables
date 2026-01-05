"""
Google Gemini Adapter
Google Gemini 适配器

Supports:
- gemini-2.0-flash (fast)
- gemini-2.0-pro (powerful)

Note: Requires GOOGLE_AI_API_KEY environment variable.
"""

import os
import logging
from typing import List, Dict, Optional

from ..base import (
    BaseTextAdapter,
    AIProviderType,
    TextCompletionResult,
    TextUsage,
    AIAdapterError,
    AIRateLimitError,
    AIAuthenticationError,
    AITimeoutError,
    AIContentFilterError,
)

logger = logging.getLogger(__name__)

# API Key
GOOGLE_AI_API_KEY = os.environ.get("GOOGLE_AI_API_KEY")


class GeminiTextAdapter(BaseTextAdapter):
    """
    Google Gemini text adapter.
    
    Supports models:
    - gemini-2.0-flash: Fast, efficient
    - gemini-2.0-pro: Most capable
    - gemini-1.5-pro: Previous gen
    """
    
    provider = AIProviderType.GEMINI
    
    SUPPORTED_MODELS = [
        "gemini-2.0-flash",
        "gemini-2.0-pro",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ]
    
    def __init__(self):
        self._client = None
        if GOOGLE_AI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=GOOGLE_AI_API_KEY)
                self._genai = genai
                self._client = True  # Mark as available
            except ImportError:
                logger.warning("[Gemini] google-generativeai package not installed")
    
    def is_available(self) -> bool:
        return self._client is not None
    
    def get_supported_models(self) -> List[str]:
        return self.SUPPORTED_MODELS.copy()
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> TextCompletionResult:
        """
        Perform chat completion using Gemini.
        """
        if not self._client:
            raise AIAuthenticationError(
                "Google AI API key not configured",
                provider="gemini"
            )
        
        try:
            import asyncio
            
            # Get model
            gemini_model = self._genai.GenerativeModel(model)
            
            # Convert messages to Gemini format
            # Gemini uses a different message format
            history = []
            current_message = None
            system_instruction = None
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    system_instruction = content
                elif role == "user":
                    current_message = content
                    if history:  # Only add to history if there's previous context
                        pass
                elif role == "assistant":
                    if current_message:
                        history.append({"role": "user", "parts": [current_message]})
                        history.append({"role": "model", "parts": [content]})
                        current_message = None
            
            # Build generation config
            generation_config = {
                "temperature": temperature,
            }
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            
            # Create chat or generate
            if history:
                chat = gemini_model.start_chat(history=history)
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: chat.send_message(
                        current_message or messages[-1].get("content", ""),
                        generation_config=generation_config
                    )
                )
            else:
                # Simple generation
                prompt = current_message or messages[-1].get("content", "")
                if system_instruction:
                    prompt = f"{system_instruction}\n\n{prompt}"
                
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: gemini_model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )
                )
            
            # Extract content
            content = response.text if response.text else ""
            
            # Gemini doesn't provide detailed token counts in all cases
            usage = TextUsage(
                input_tokens=0,  # Not always available
                output_tokens=0,
                total_tokens=0,
            )
            
            # Try to get usage metadata if available
            if hasattr(response, 'usage_metadata'):
                usage = TextUsage(
                    input_tokens=getattr(response.usage_metadata, 'prompt_token_count', 0),
                    output_tokens=getattr(response.usage_metadata, 'candidates_token_count', 0),
                    total_tokens=getattr(response.usage_metadata, 'total_token_count', 0),
                )
            
            return TextCompletionResult(
                content=content,
                usage=usage,
                model=model,
                provider="gemini",
                finish_reason="stop",
            )
            
        except Exception as e:
            error_str = str(e).lower()
            
            if "quota" in error_str or "rate" in error_str:
                raise AIRateLimitError(
                    f"Gemini rate limit: {e}",
                    provider="gemini"
                )
            elif "api key" in error_str or "auth" in error_str:
                raise AIAuthenticationError(
                    f"Gemini auth error: {e}",
                    provider="gemini"
                )
            elif "safety" in error_str or "blocked" in error_str:
                raise AIContentFilterError(
                    f"Content filtered: {e}",
                    provider="gemini"
                )
            elif "timeout" in error_str:
                raise AITimeoutError(
                    f"Gemini timeout: {e}",
                    provider="gemini"
                )
            
            logger.error(f"[Gemini] Unexpected error: {e}")
            raise AIAdapterError(
                f"Gemini error: {e}",
                provider="gemini",
                model=model,
                retryable=True
            )
