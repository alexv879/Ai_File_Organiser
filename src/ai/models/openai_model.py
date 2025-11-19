"""OpenAI GPT model integration."""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI package not installed. Run: pip install openai")

from .base import AIModel, ClassificationResult, ModelType, ModelTier

logger = logging.getLogger(__name__)


class OpenAIModel(AIModel):
    """OpenAI GPT model for file classification.

    Supports GPT-4 Turbo, GPT-4, GPT-3.5 Turbo.

    Pricing (as of 2025):
    - GPT-4 Turbo: $0.01/1K input tokens, $0.03/1K output tokens
    - GPT-3.5 Turbo: $0.0005/1K input tokens, $0.0015/1K output tokens
    """

    MODELS = {
        "gpt-4-turbo": {
            "input_cost": 0.01 / 1000,   # per token
            "output_cost": 0.03 / 1000,
            "context_window": 128000,
            "tier": ModelTier.PRO
        },
        "gpt-4": {
            "input_cost": 0.03 / 1000,
            "output_cost": 0.06 / 1000,
            "context_window": 8192,
            "tier": ModelTier.PRO
        },
        "gpt-3.5-turbo": {
            "input_cost": 0.0005 / 1000,
            "output_cost": 0.0015 / 1000,
            "context_window": 16384,
            "tier": ModelTier.STARTER
        }
    }

    def __init__(self, api_key: str, model: str = "gpt-4-turbo", config: Dict[str, Any] = None):
        """Initialize OpenAI model.

        Args:
            api_key: OpenAI API key
            model: Model name (gpt-4-turbo, gpt-4, gpt-3.5-turbo)
            config: Additional configuration
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package required. Install: pip install openai")

        super().__init__(model, config)

        self.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key)
        self.model_type = ModelType.CLOUD
        self.model_tier = self.MODELS.get(model, {}).get("tier", ModelTier.STARTER)

    def is_available(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI API not accessible: {e}")
            return False

    def classify_file(
        self,
        file_path: str,
        file_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ClassificationResult:
        """Classify file using GPT."""
        start_time = time.time()

        # Build prompt
        prompt = self._build_classification_prompt(file_path, file_content, metadata)

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert file organization assistant. Analyze files and provide categorization, suggested paths, and extracted metadata."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent results
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            # Parse response
            import json
            result_data = json.loads(response.choices[0].message.content)

            # Calculate costs
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = self.get_cost_estimate(input_tokens) + (
                output_tokens * self.MODELS[self.model_name]["output_cost"]
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            return ClassificationResult(
                category=result_data.get("category", "Uncategorized"),
                subcategory=result_data.get("subcategory"),
                confidence=result_data.get("confidence", 0.8),
                suggested_path=result_data.get("suggested_path", ""),
                suggested_name=result_data.get("suggested_name"),
                tags=result_data.get("tags", []),
                summary=result_data.get("summary"),
                entities=result_data.get("entities", {}),
                reasoning=result_data.get("reasoning"),
                model_used=self.model_name,
                processing_time_ms=processing_time_ms,
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost
            )

        except Exception as e:
            logger.error(f"OpenAI classification failed: {e}")
            # Return fallback result
            return ClassificationResult(
                category="Error",
                confidence=0.0,
                model_used=self.model_name,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

    def get_cost_estimate(self, input_tokens: int) -> float:
        """Estimate cost for input tokens."""
        return input_tokens * self.MODELS[self.model_name]["input_cost"]

    def _build_classification_prompt(
        self,
        file_path: str,
        file_content: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Build classification prompt."""
        filename = Path(file_path).name
        extension = Path(file_path).suffix

        prompt = f"""Analyze this file and provide classification information in JSON format.

File: {filename}
Extension: {extension}
"""

        if metadata:
            prompt += f"\nMetadata: {metadata}"

        if file_content:
            # Truncate content if too long
            max_content_length = 2000
            if len(file_content) > max_content_length:
                file_content = file_content[:max_content_length] + "... (truncated)"
            prompt += f"\n\nContent preview:\n{file_content}"

        prompt += """

Provide a JSON response with:
{
    "category": "Primary category (Documents, Photos, Videos, Audio, Code, Archives, etc.)",
    "subcategory": "More specific subcategory",
    "confidence": 0.0-1.0,
    "suggested_path": "Recommended organization path",
    "suggested_name": "Better filename if current one is poor (optional)",
    "tags": ["relevant", "tags"],
    "summary": "Brief description of file content",
    "entities": {
        "dates": ["extracted dates"],
        "names": ["extracted names"],
        "amounts": ["extracted monetary amounts"]
    },
    "reasoning": "Brief explanation of categorization"
}
"""

        return prompt
