"""Ollama local model integration."""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
import requests

from .base import AIModel, ClassificationResult, ModelType, ModelTier

logger = logging.getLogger(__name__)


class OllamaModel(AIModel):
    """Ollama local model for file classification.

    Supports any Ollama model (qwen2.5, llama3, phi-3, etc.)
    Free to use - runs locally, no API costs.
    """

    def __init__(
        self,
        model: str = "qwen2.5:7b-instruct",
        base_url: str = "http://localhost:11434",
        timeout: int = 60,
        config: Dict[str, Any] = None
    ):
        """Initialize Ollama model.

        Args:
            model: Ollama model name
            base_url: Ollama server URL
            timeout: Request timeout in seconds
            config: Additional configuration
        """
        super().__init__(model, config)

        self.base_url = base_url
        self.timeout = timeout
        self.model_type = ModelType.LOCAL
        self.model_tier = ModelTier.FREE

    def is_available(self) -> bool:
        """Check if Ollama server is accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                # Check if our model is available
                models = response.json().get("models", [])
                return any(model["name"] == self.model_name for model in models)
            return False
        except Exception as e:
            logger.error(f"Ollama server not accessible: {e}")
            return False

    def classify_file(
        self,
        file_path: str,
        file_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ClassificationResult:
        """Classify file using Ollama."""
        start_time = time.time()

        # Build prompt
        prompt = self._build_classification_prompt(file_path, file_content, metadata)

        try:
            # Call Ollama API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 500
                    }
                },
                timeout=self.timeout
            )

            response.raise_for_status()
            result = response.json()

            # Parse response
            import json
            result_data = json.loads(result["response"])

            processing_time_ms = int((time.time() - start_time) * 1000)

            return ClassificationResult(
                category=result_data.get("category", "Uncategorized"),
                subcategory=result_data.get("subcategory"),
                confidence=result_data.get("confidence", 0.7),
                suggested_path=result_data.get("suggested_path", ""),
                suggested_name=result_data.get("suggested_name"),
                tags=result_data.get("tags", []),
                summary=result_data.get("summary"),
                entities=result_data.get("entities", {}),
                reasoning=result_data.get("reasoning"),
                model_used=self.model_name,
                processing_time_ms=processing_time_ms,
                tokens_used=0,  # Ollama doesn't report token usage
                cost_usd=0.0    # Free!
            )

        except Exception as e:
            logger.error(f"Ollama classification failed: {e}")
            # Return fallback result
            return ClassificationResult(
                category="Error",
                confidence=0.0,
                model_used=self.model_name,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

    def get_cost_estimate(self, input_tokens: int) -> float:
        """Ollama is free - no cost."""
        return 0.0

    def _build_classification_prompt(
        self,
        file_path: str,
        file_content: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Build classification prompt."""
        filename = Path(file_path).name
        extension = Path(file_path).suffix

        prompt = f"""Analyze this file and provide classification in JSON format.

File: {filename}
Extension: {extension}
"""

        if metadata:
            prompt += f"Metadata: {metadata}\n"

        if file_content:
            # Truncate for local models
            max_content_length = 1000
            if len(file_content) > max_content_length:
                file_content = file_content[:max_content_length] + "..."
            prompt += f"\nContent:\n{file_content}\n"

        prompt += """
Provide JSON response:
{
    "category": "Primary category",
    "subcategory": "Specific type",
    "confidence": 0.8,
    "suggested_path": "Organized/Path",
    "tags": ["tag1", "tag2"],
    "summary": "Brief summary",
    "reasoning": "Why this category"
}
"""

        return prompt
