"""Anthropic Claude model integration."""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic package not installed. Run: pip install anthropic")

from .base import AIModel, ClassificationResult, ModelType, ModelTier

logger = logging.getLogger(__name__)


class ClaudeModel(AIModel):
    """Anthropic Claude model for file classification.

    Supports Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku.

    Pricing (as of 2025):
    - Claude 3.5 Sonnet: $0.003/1K input tokens, $0.015/1K output tokens
    - Claude 3 Opus: $0.015/1K input tokens, $0.075/1K output tokens
    - Claude 3 Haiku: $0.00025/1K input tokens, $0.00125/1K output tokens
    """

    MODELS = {
        "claude-3-5-sonnet-20250122": {
            "input_cost": 0.003 / 1000,
            "output_cost": 0.015 / 1000,
            "context_window": 200000,
            "tier": ModelTier.PRO
        },
        "claude-3-opus-20240229": {
            "input_cost": 0.015 / 1000,
            "output_cost": 0.075 / 1000,
            "context_window": 200000,
            "tier": ModelTier.PRO
        },
        "claude-3-haiku-20240307": {
            "input_cost": 0.00025 / 1000,
            "output_cost": 0.00125 / 1000,
            "context_window": 200000,
            "tier": ModelTier.STARTER
        }
    }

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20250122", config: Dict[str, Any] = None):
        """Initialize Claude model.

        Args:
            api_key: Anthropic API key
            model: Model name
            config: Additional configuration
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic package required. Install: pip install anthropic")

        super().__init__(model, config)

        self.api_key = api_key
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_type = ModelType.CLOUD
        self.model_tier = self.MODELS.get(model, {}).get("tier", ModelTier.PRO)

    def is_available(self) -> bool:
        """Check if Anthropic API is accessible."""
        try:
            # Simple API call to verify connectivity
            self.client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception as e:
            logger.error(f"Anthropic API not accessible: {e}")
            return False

    def classify_file(
        self,
        file_path: str,
        file_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ClassificationResult:
        """Classify file using Claude."""
        start_time = time.time()

        # Build prompt
        prompt = self._build_classification_prompt(file_path, file_content, metadata)

        try:
            # Call Anthropic API
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=1000,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Parse response
            import json
            result_text = message.content[0].text

            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]

            result_data = json.loads(result_text.strip())

            # Calculate costs
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            cost = (
                input_tokens * self.MODELS[self.model_name]["input_cost"] +
                output_tokens * self.MODELS[self.model_name]["output_cost"]
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            return ClassificationResult(
                category=result_data.get("category", "Uncategorized"),
                subcategory=result_data.get("subcategory"),
                confidence=result_data.get("confidence", 0.85),
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
            logger.error(f"Claude classification failed: {e}")
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

        prompt = f"""You are an expert file organization assistant. Analyze the following file and provide detailed classification information.

File Information:
- Filename: {filename}
- Extension: {extension}
"""

        if metadata:
            prompt += f"- Metadata: {metadata}\n"

        if file_content:
            # Truncate content if too long
            max_content_length = 3000  # Claude has larger context window
            if len(file_content) > max_content_length:
                file_content = file_content[:max_content_length] + "... (truncated)"
            prompt += f"\nContent Preview:\n{file_content}\n"

        prompt += """
Based on this information, provide a comprehensive classification in JSON format:

```json
{
    "category": "Primary category (Documents, Photos, Videos, Audio, Code, Archives, Spreadsheets, Presentations, etc.)",
    "subcategory": "More specific subcategory (e.g., 'Contracts', 'Family Photos', 'Python Scripts')",
    "confidence": 0.95,
    "suggested_path": "Documents/Work/Contracts/2025",
    "suggested_name": "Better filename if current is unclear (optional)",
    "tags": ["relevant", "descriptive", "tags"],
    "summary": "Brief 1-2 sentence summary of file content",
    "entities": {
        "dates": ["2025-01-15", "Q1 2025"],
        "names": ["Company Name", "Person Name"],
        "amounts": ["$1,000", "€500"],
        "locations": ["New York", "Remote"]
    },
    "reasoning": "Brief explanation of why this categorization was chosen"
}
```

Provide your response in JSON format only."""

        return prompt
