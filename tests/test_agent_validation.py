"""
Test Script for AgentAnalyzer Validation Pipeline

This script tests the robustness of the JSON validation pipeline including:
- Schema validation
- JSON extraction from malformed responses
- Retry logic
- Path sanitization
- Safety checks
- Logging integration

Author: AI File Organiser Team
License: Proprietary (200-key limited release)
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.agent_analyzer import AgentAnalyzer, AGENT_RESPONSE_SCHEMA
from jsonschema import validate, ValidationError


def test_json_extraction():
    """Test JSON extraction from various malformed responses."""
    print("\n=== Testing JSON Extraction ===")

    # Mock AgentAnalyzer for testing extraction
    class MockAnalyzer:
        def _extract_json_from_text(self, text):
            # Import the method from AgentAnalyzer
            from src.agent.agent_analyzer import AgentAnalyzer
            # Use a dummy instance just to call the method
            dummy = type('obj', (object,), {})()
            return AgentAnalyzer._extract_json_from_text(dummy, text)

    analyzer = MockAnalyzer()

    test_cases = [
        {
            "name": "Markdown code fence with json tag",
            "input": """```json
{
  "category": "Documents",
  "confidence": "high"
}
```""",
            "should_extract": True
        },
        {
            "name": "Markdown code fence without json tag",
            "input": """```
{
  "category": "Finance",
  "confidence": "medium"
}
```""",
            "should_extract": True
        },
        {
            "name": "JSON with surrounding text",
            "input": """Here is the classification:
{"category": "Projects", "confidence": "low"}
Hope this helps!""",
            "should_extract": True
        },
        {
            "name": "Plain JSON",
            "input": '{"category": "Photos", "confidence": "high"}',
            "should_extract": True
        },
        {
            "name": "No JSON present",
            "input": "This is just plain text with no JSON",
            "should_extract": False
        }
    ]

    passed = 0
    failed = 0

    for case in test_cases:
        result = analyzer._extract_json_from_text(case["input"])
        success = (result is not None) == case["should_extract"]

        if success:
            print(f"[PASS] {case['name']}")
            passed += 1
        else:
            print(f"[FAIL] {case['name']}")
            print(f"  Expected extraction: {case['should_extract']}, Got: {result is not None}")
            failed += 1

    print(f"\nExtraction Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_schema_validation():
    """Test JSON schema validation."""
    print("\n=== Testing Schema Validation ===")

    valid_response = {
        "category": "Documents",
        "suggested_path": "Documents/Work",
        "rename": "renamed_file.txt",
        "confidence": "high",
        "method": "agent",
        "reason": "Test reason",
        "evidence": ["evidence 1", "evidence 2"],
        "action": "move",
        "block_reason": None
    }

    invalid_responses = [
        {
            "name": "Missing required field (category)",
            "data": {
                "suggested_path": "Documents/Work",
                "confidence": "high",
                "method": "agent",
                "reason": "Test",
                "evidence": [],
                "action": "move"
            }
        },
        {
            "name": "Invalid confidence value",
            "data": {
                "category": "Documents",
                "confidence": "invalid",
                "method": "agent",
                "reason": "Test",
                "evidence": [],
                "action": "move"
            }
        },
        {
            "name": "Invalid action value",
            "data": {
                "category": "Documents",
                "confidence": "high",
                "method": "agent",
                "reason": "Test",
                "evidence": [],
                "action": "invalid_action"
            }
        }
    ]

    passed = 0
    failed = 0

    # Test valid response
    try:
        validate(instance=valid_response, schema=AGENT_RESPONSE_SCHEMA)
        print("[PASS] Valid response passes schema validation")
        passed += 1
    except ValidationError as e:
        print(f"[FAIL] Valid response failed validation: {e.message}")
        failed += 1

    # Test invalid responses
    for case in invalid_responses:
        try:
            validate(instance=case["data"], schema=AGENT_RESPONSE_SCHEMA)
            print(f"[FAIL] {case['name']} - Should have failed validation but passed")
            failed += 1
        except ValidationError:
            print(f"[PASS] {case['name']} - Correctly rejected")
            passed += 1

    print(f"\nSchema Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_path_sanitization():
    """Test path sanitization."""
    print("\n=== Testing Path Sanitization ===")

    # Mock AgentAnalyzer for testing sanitization
    class MockAnalyzer:
        def _sanitize_path(self, path):
            from src.agent.agent_analyzer import AgentAnalyzer
            dummy = type('obj', (object,), {})()
            return AgentAnalyzer._sanitize_path(dummy, path)

    analyzer = MockAnalyzer()

    test_cases = [
        {
            "name": "Path traversal attempt",
            "input": "../../../etc/passwd",
            "expected_removed": ".."
        },
        {
            "name": "Null byte injection",
            "input": "file\x00.txt",
            "expected_removed": "\x00"
        },
        {
            "name": "Tilde expansion attempt",
            "input": "~/Documents/file.txt",
            "expected_removed": "~/"
        },
        {
            "name": "Clean path",
            "input": "Documents/Work/file.txt",
            "expected_clean": True
        }
    ]

    passed = 0
    failed = 0

    for case in test_cases:
        result = analyzer._sanitize_path(case["input"])

        if "expected_removed" in case:
            if case["expected_removed"] not in result:
                print(f"[PASS] {case['name']} - Dangerous pattern removed")
                passed += 1
            else:
                print(f"[FAIL] {case['name']} - Dangerous pattern still present: {result}")
                failed += 1
        elif case.get("expected_clean"):
            if result == case["input"]:
                print(f"[PASS] {case['name']} - Clean path unchanged")
                passed += 1
            else:
                print(f"[FAIL] {case['name']} - Clean path was modified: {result}")
                failed += 1

    print(f"\nSanitization Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_logging_integration():
    """Test that logging is properly integrated."""
    print("\n=== Testing Logging Integration ===")

    try:
        from src.utils.logger import get_logger

        logger = get_logger('test_agent')

        # Test various log methods
        logger.info("Test info message", test_field="value")
        logger.agent_call("test_model", "abc123", "/test/path")
        logger.agent_response("test_model", "abc123", "def456", True, True)
        logger.agent_action("move", "/test/file", "/test/dest", approved=True)
        logger.safety_block("/test/file", "test reason", "test_check")

        print("[PASS] Logging module imported and functional")
        print("[INFO] Check logs/organiser.log for structured output")

        return True
    except Exception as e:
        print(f"[FAIL] Logging integration failed: {str(e)}")
        return False


def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("AgentAnalyzer Validation Pipeline Test Suite")
    print("=" * 60)

    results = {
        "JSON Extraction": test_json_extraction(),
        "Schema Validation": test_schema_validation(),
        "Path Sanitization": test_path_sanitization(),
        "Logging Integration": test_logging_integration()
    }

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print("\n[ERROR] Some tests failed. Review output above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
