"""
Safe Multi-Model Classifier Module

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module implements a two-stage AI classification system with reasoning
and validation to ensure safe file organization decisions.

Stage 1: Reasoning Model analyzes file and provides detailed reasoning
Stage 2: Validator Model checks decision for safety and correctness
Stage 3: Hierarchical Organizer generates optimal 3-4 level folder structure

NOTICE: This software is proprietary and confidential.
See LICENSE.txt for full terms and conditions.

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import json
import requests
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """Classification safety levels"""
    SAFE = "safe"  # Confident and validated
    UNCERTAIN = "uncertain"  # Needs manual review
    DANGEROUS = "dangerous"  # Could cause data loss


class SafeClassifier:
    """
    Two-stage AI classifier with reasoning and validation.
    
    Stage 1 (Reasoning): Uses a reasoning model (e.g., deepseek-r1:14b or qwen2.5:14b)
                         to analyze file with explicit chain-of-thought
    
    Stage 2 (Validation): Uses a validation model to check for safety issues,
                          logical errors, or potential data loss
    
    Stage 3 (Hierarchical): Uses HierarchicalOrganizer to generate optimal
                           3-4 level folder structure based on research
    
    This ensures files are organized safely with human-like reasoning and
    intelligent folder hierarchies.
    """

    def __init__(self, 
                 base_url: str = "http://localhost:11434",
                 reasoning_model: str = "qwen2.5:14b",
                 validator_model: str = "deepseek-r1:14b",
                 timeout: int = 60,
                 config=None):
        """
        Initialize safe classifier with two models and hierarchical organizer.
        
        Args:
            base_url: Ollama API endpoint
            reasoning_model: Model for initial analysis (should be good at reasoning)
            validator_model: Model for validation (should catch errors)
            timeout: Request timeout in seconds
            config: Configuration object (for HierarchicalOrganizer)
        
        Recommended model combinations:
        - reasoning_model: "qwen2.5:14b" or "deepseek-r1:14b" or "llama3.1:70b"
        - validator_model: "deepseek-r1:14b" or "qwen2.5:14b"
        
        Note: Using two different models helps catch biases and errors
        """
        self.base_url = base_url.rstrip('/')
        self.reasoning_model = reasoning_model
        self.validator_model = validator_model
        self.timeout = timeout
        self.config = config
        
        # Import HierarchicalOrganizer here to avoid circular imports
        try:
            from ..core.hierarchy_organizer import HierarchicalOrganizer
            self.hierarchy_organizer = HierarchicalOrganizer(config)
            logger.info("HierarchicalOrganizer initialized successfully")
        except ImportError as e:
            logger.warning(f"Could not import HierarchicalOrganizer: {e}")
            self.hierarchy_organizer = None

    def is_available(self) -> Dict[str, bool]:
        """
        Check if Ollama and required models are available.
        
        Returns:
            Dict with 'service', 'reasoning_model', 'validator_model' availability
        """
        status = {
            "service": False,
            "reasoning_model": False,
            "validator_model": False
        }
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                status["service"] = True
                models = [m['name'] for m in response.json().get('models', [])]
                status["reasoning_model"] = self.reasoning_model in models
                status["validator_model"] = self.validator_model in models
        except requests.exceptions.RequestException:
            pass
        
        return status

    def _construct_reasoning_prompt(self, filename: str, extension: str,
                                   text_snippet: Optional[str] = None,
                                   file_size: Optional[int] = None,
                                   current_location: Optional[str] = None) -> str:
        """Construct detailed reasoning prompt"""
        size_info = f"\nSize: {file_size:,} bytes ({file_size / 1024:.1f} KB)" if file_size else ""
        snippet_info = f"\n\nContent Preview:\n{text_snippet[:800]}" if text_snippet else ""
        location_info = f"\nCurrent Location: {current_location}" if current_location else ""
        
        prompt = f"""You are an expert file organization AI with deep reasoning capabilities. 
Your task is to carefully analyze this file and suggest where it should be organized.

**THINK STEP-BY-STEP AND SHOW YOUR REASONING**

File Information:
- Filename: {filename}
- Extension: {extension}{size_info}{location_info}{snippet_info}

REASONING PROCESS:
1. First, analyze the filename - what does it tell you?
2. Look at the file extension - what type of file is this?
3. If content is available, what is this file about?
4. What is the PRIMARY PURPOSE of this file? (personal, work, financial, creative, etc.)
5. Is this a temporary file, or long-term important document?
6. What date/time information can you extract (if any)?
7. Are there any RISKS in moving this file? (system file, application file, etc.)

SAFETY CHECKS - CRITICAL:
- Is this a system file? (DO NOT MOVE if in C:/Windows, C:/Program Files, etc.)
- Is this an application file? (DO NOT MOVE executables from their install location)
- Is this a configuration file? (BE CAUTIOUS with .ini, .conf, .cfg files)
- Could moving this break something? (dependencies, shortcuts, etc.)

Now provide your classification in JSON format:
{{
  "reasoning": "Your detailed step-by-step thinking (2-4 sentences)",
  "category": "Main category (e.g., Documents/Financial, Work/Projects, Personal/Photos)",
  "suggested_path": "Relative path (e.g., Documents/Invoices/2025/March/)",
  "rename": "Suggested new filename or null if current is good",
  "safety_level": "safe, uncertain, or dangerous",
  "confidence": 0.0 to 1.0,
  "warnings": ["Any potential issues or risks"],
  "requires_review": true/false
}}

**IMPORTANT**: If you're uncertain or detect ANY risk, set "requires_review": true and explain why in "warnings".

Provide your analysis:"""
        
        return prompt

    def _construct_validation_prompt(self, filename: str, extension: str,
                                    classification: Dict[str, Any],
                                    current_location: Optional[str] = None) -> str:
        """Construct validation prompt for second model"""
        
        prompt = f"""You are a safety validator AI. Your job is to CAREFULLY REVIEW a file organization decision
and check for ANY potential problems, errors, or risks.

Original File:
- Filename: {filename}
- Extension: {extension}
- Current Location: {current_location or "Unknown"}

Proposed Classification:
{json.dumps(classification, indent=2)}

VALIDATION CHECKS - Be thorough:

1. SAFETY CHECKS:
   - Will moving this file break any applications?
   - Is this a system-critical file?
   - Could this cause data loss?
   - Is the destination path appropriate?

2. LOGIC CHECKS:
   - Does the category make sense for this file type?
   - Is the path structure logical and consistent?
   - Is the proposed rename (if any) better than the original?
   - Does the reasoning provided make sense?

3. EDGE CASES:
   - Are there any special considerations?
   - Could there be unintended consequences?
   - Is this a common mistake scenario?

Provide validation result in JSON:
{{
  "validation_result": "approved", "needs_review", or "rejected",
  "safety_concerns": ["List any safety issues found"],
  "logic_issues": ["List any logical problems"],
  "recommendations": ["Suggestions to improve the classification"],
  "final_safety_level": "safe", "uncertain", or "dangerous",
  "validator_confidence": 0.0 to 1.0,
  "override_requires_review": true/false,
  "validator_reasoning": "Your analysis (2-3 sentences)"
}}

**IMPORTANT**: If you find ANY concerning issues, set "override_requires_review": true.
Be conservative - it's better to ask for human review than to cause problems.

Provide your validation:"""
        
        return prompt

    def _call_ollama(self, model: str, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Ollama API with error handling"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return None
            
            result = response.json()
            response_text = result.get("response", "")
            
            # Parse JSON (handle markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            return json.loads(response_text)
            
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"Error calling {model}: {e}")
            return None

    def classify_file(self, filename: str, extension: str,
                     text_snippet: Optional[str] = None,
                     file_size: Optional[int] = None,
                     current_location: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify file using three-stage reasoning + validation + hierarchy approach.
        
        Args:
            filename: Name of the file
            extension: File extension
            text_snippet: Extracted text content
            file_size: File size in bytes
            current_location: Current file path
        
        Returns:
            Dict with classification result including:
                - All fields from reasoning model
                - validation_result: Validation outcome
                - safety_concerns: List of safety issues
                - hierarchy: Optimal folder structure (3-4 levels)
                - final_decision: Overall recommendation
                - success: Whether classification succeeded
        """
        # Default fallback
        fallback = {
            "category": "Unsorted",
            "suggested_path": None,
            "rename": None,
            "reasoning": "AI classification unavailable",
            "safety_level": "dangerous",
            "requires_review": True,
            "success": False,
            "final_decision": "manual_review_required"
        }
        
        # Check availability
        availability = self.is_available()
        if not availability["service"]:
            fallback["error"] = "Ollama service not available"
            return fallback
        
        if not availability["reasoning_model"]:
            fallback["error"] = f"Reasoning model '{self.reasoning_model}' not found"
            return fallback
        
        if not availability["validator_model"]:
            fallback["error"] = f"Validator model '{self.validator_model}' not found"
            return fallback
        
        # STAGE 1: Reasoning Model
        print(f"[Stage 1] Analyzing with {self.reasoning_model}...")
        reasoning_prompt = self._construct_reasoning_prompt(
            filename, extension, text_snippet, file_size, current_location
        )
        
        reasoning_result = self._call_ollama(self.reasoning_model, reasoning_prompt)
        if not reasoning_result:
            fallback["error"] = "Reasoning model failed"
            return fallback
        
        # STAGE 2: Validation Model
        print(f"[Stage 2] Validating with {self.validator_model}...")
        validation_prompt = self._construct_validation_prompt(
            filename, extension, reasoning_result, current_location
        )
        
        validation_result = self._call_ollama(self.validator_model, validation_prompt)
        if not validation_result:
            # If validation fails, be conservative
            reasoning_result["requires_review"] = True
            reasoning_result["validation_result"] = "validation_failed"
            reasoning_result["success"] = True
            reasoning_result["final_decision"] = "manual_review_required"
            return reasoning_result
        
        # Combine reasoning and validation results
        combined = {**reasoning_result, **validation_result}
        
        # STAGE 3: Hierarchical Organization
        if self.hierarchy_organizer:
            print(f"[Stage 3] Generating intelligent folder hierarchy...")
            try:
                file_metadata = {
                    'size': file_size,
                    'modified_time': None,  # Would come from actual file stat
                    'content_preview': text_snippet
                }
                
                hierarchy = self.hierarchy_organizer.generate_hierarchy(
                    filename=filename,
                    extension=extension,
                    file_metadata=file_metadata,
                    classification=reasoning_result
                )
                
                # Replace suggested_path with hierarchical path
                combined['hierarchy'] = hierarchy
                combined['suggested_path'] = hierarchy['full_path']
                combined['hierarchy_reasoning'] = hierarchy['reasoning']
                combined['hierarchy_depth'] = hierarchy['depth']
                combined['is_optimal_depth'] = hierarchy['is_optimal_depth']
                
                logger.info(f"Generated hierarchy: {hierarchy['full_path']} (depth: {hierarchy['depth']})")
            except Exception as e:
                logger.error(f"Hierarchy generation failed: {e}")
                # Fallback to original AI suggested path
                combined['hierarchy_error'] = str(e)
        else:
            logger.warning("HierarchicalOrganizer not available, using flat structure")
            combined['hierarchy'] = None
        
        # Determine final decision
        validation_status = validation_result.get("validation_result", "needs_review")
        safety_level = validation_result.get("final_safety_level", "uncertain")
        requires_review = (
            reasoning_result.get("requires_review", False) or
            validation_result.get("override_requires_review", False) or
            len(validation_result.get("safety_concerns", [])) > 0
        )
        
        if validation_status == "rejected" or safety_level == "dangerous":
            final_decision = "do_not_move"
        elif validation_status == "approved" and safety_level == "safe" and not requires_review:
            final_decision = "auto_approve"
        else:
            final_decision = "manual_review_required"
        
        combined.update({
            "success": True,
            "final_decision": final_decision,
            "requires_review": requires_review,
            "used_models": {
                "reasoning": self.reasoning_model,
                "validator": self.validator_model,
                "hierarchy": self.hierarchy_organizer is not None
            }
        })
        
        return combined

    def pull_models(self) -> Dict[str, bool]:
        """
        Pull both required models from Ollama registry.
        
        Returns:
            Dict with success status for each model
        """
        results = {}
        
        for model_name in [self.reasoning_model, self.validator_model]:
            print(f"Pulling {model_name}...")
            try:
                response = requests.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name, "stream": False},
                    timeout=600  # 10 minute timeout for large models
                )
                results[model_name] = response.status_code == 200
            except requests.exceptions.RequestException as e:
                print(f"Error pulling {model_name}: {e}")
                results[model_name] = False
        
        return results


# Convenience function
def create_safe_classifier(reasoning_model: str = "qwen2.5:14b",
                          validator_model: str = "deepseek-r1:14b") -> SafeClassifier:
    """
    Create a SafeClassifier with recommended models.
    
    Recommended combinations:
    - Conservative: reasoning="qwen2.5:14b", validator="deepseek-r1:14b"
    - Balanced: reasoning="deepseek-r1:14b", validator="qwen2.5:7b"
    - Fast: reasoning="qwen2.5:7b", validator="deepseek-r1:7b"
    """
    return SafeClassifier(reasoning_model=reasoning_model, validator_model=validator_model)


if __name__ == "__main__":
    # Test safe classifier
    classifier = SafeClassifier()
    
    print("Testing Safe Classifier...")
    availability = classifier.is_available()
    print(f"Service: {availability['service']}")
    print(f"Reasoning Model ({classifier.reasoning_model}): {availability['reasoning_model']}")
    print(f"Validator Model ({classifier.validator_model}): {availability['validator_model']}")
    
    if all(availability.values()):
        print("\n" + "="*60)
        print("Test Case: Invoice PDF")
        print("="*60)
        result = classifier.classify_file(
            filename="invoice_march_2025.pdf",
            extension="pdf",
            text_snippet="Invoice #12345\nDate: 2025-03-15\nAmount: $250.00\nClient: Acme Corp",
            file_size=45000,
            current_location="C:/Users/alex/Downloads/invoice_march_2025.pdf"
        )
        print(json.dumps(result, indent=2))
    else:
        print("\n⚠ Not all components available")
        print("Run: python setup_ollama.py --models qwen2.5:14b,deepseek-r1:14b")
