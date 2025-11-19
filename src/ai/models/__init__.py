"""Multi-model AI support for file classification.

This package provides support for multiple AI models:
- Local: Ollama (qwen2.5, llama3, phi-3)
- Cloud: OpenAI GPT-4, Anthropic Claude, Gemini
"""

from .base import AIModel, ClassificationResult
from .ollama_model import OllamaModel
from .openai_model import OpenAIModel
from .claude_model import ClaudeModel
from .model_selector import ModelSelector

__all__ = [
    'AIModel',
    'ClassificationResult',
    'OllamaModel',
    'OpenAIModel',
    'ClaudeModel',
    'ModelSelector',
]
