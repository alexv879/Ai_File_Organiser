"""
Safety Guardian Module - Final Evaluation Layer

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module implements a comprehensive multi-layered safety system that acts as
the FINAL checkpoint before any file operation. It uses reasoning AI to evaluate
the entire operation context and prevent any potentially harmful actions.

SAFETY LAYERS:
1. Path Security - Prevents path traversal, escapes, system file access
2. Business Logic - Validates classification makes sense
3. Consequence Analysis - Predicts and prevents negative outcomes
4. User Data Protection - Prevents accidental data loss
5. System Integrity - Protects OS and application files
6. Reasoning Evaluation - Final AI check with detailed reasoning

NOTICE: This software is proprietary and confidential.
See LICENSE.txt for full terms and conditions.

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import json


logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for file operations"""
    SAFE = "safe"                # Operation is safe to proceed
    CAUTION = "caution"          # Proceed with user confirmation
    HIGH_RISK = "high_risk"      # Strongly recommend against
    CRITICAL = "critical"        # Block operation immediately
    

class ThreatType(Enum):
    """Types of threats the guardian can detect"""
    PATH_TRAVERSAL = "path_traversal"
    SYSTEM_FILE = "system_file"
    APPLICATION_FILE = "application_file"
    DATA_LOSS = "data_loss"
    PERMISSION_ISSUE = "permission_issue"
    INVALID_DESTINATION = "invalid_destination"
    LOGIC_ERROR = "logic_error"
    CIRCULAR_REFERENCE = "circular_reference"
    DESTRUCTIVE_OPERATION = "destructive_operation"


class SafetyGuardian:
    """
    Final safety checkpoint - evaluates every file operation before execution.
    
    This acts as the last line of defense against any potentially harmful
    file operations. It uses multiple validation layers and AI reasoning
    to ensure no mistakes slip through.
    """
    
    # Critical system paths that should NEVER be modified
    CRITICAL_PATHS_WINDOWS = [
        "C:\\Windows",
        "C:\\Windows\\System32",
        "C:\\Windows\\SysWOW64",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\ProgramData\\Microsoft",
        "C:\\Users\\Default",
        "C:\\Users\\Public",
        "C:\\System Volume Information",
        "C:\\$Recycle.Bin",
        "C:\\Recovery",
        "C:\\Boot",
        "C:\\bootmgr",
        "C:\\hiberfil.sys",
        "C:\\pagefile.sys",
        "C:\\swapfile.sys",
    ]
    
    CRITICAL_PATHS_UNIX = [
        "/bin",
        "/sbin",
        "/usr/bin",
        "/usr/sbin",
        "/lib",
        "/lib64",
        "/usr/lib",
        "/usr/lib64",
        "/etc",
        "/boot",
        "/sys",
        "/proc",
        "/dev",
        "/root",
        "/var/log",
        "/var/lib/dpkg",
        "/var/lib/rpm",
    ]
    
    # Application-related paths to protect
    APP_PATHS_WINDOWS = [
        "AppData\\Local",
        "AppData\\Roaming",
        "AppData\\LocalLow",
        ".config",
        ".cache",
        ".local",
    ]
    
    # Extensions that should never be moved from their location
    CRITICAL_EXTENSIONS = [
        ".sys", ".dll", ".exe", ".drv", ".ocx",  # System/executable files
        ".so", ".dylib", ".a",  # Unix libraries
        ".ini", ".cfg", ".conf",  # Configuration files in wrong context
    ]
    
    # Minimum confidence threshold for auto-approval
    MIN_CONFIDENCE_THRESHOLD = 0.75
    
    def __init__(self, config, ollama_client=None):
        """
        Initialize Safety Guardian.
        
        Args:
            config: Application configuration
            ollama_client: Optional Ollama client for AI reasoning evaluation
        """
        self.config = config
        self.ollama_client = ollama_client
        self.blocked_operations = []  # Track blocked operations for audit
        
    def evaluate_operation(self, 
                          source_path: str,
                          destination_path: str,
                          operation: str,
                          classification: Dict[str, Any],
                          user_approved: bool = False) -> Dict[str, Any]:
        """
        Comprehensive evaluation of a file operation before execution.
        
        This is the FINAL checkpoint. If this returns risk_level != SAFE,
        the operation MUST NOT proceed without explicit user override.
        
        Args:
            source_path: Original file location
            destination_path: Proposed new location
            operation: Type of operation (move, rename, delete, etc.)
            classification: Classification result from AI/rules
            user_approved: Whether user has explicitly approved
            
        Returns:
            Dict with evaluation result:
                - approved: bool (safe to proceed)
                - risk_level: RiskLevel enum
                - threats: List of detected threats
                - warnings: List of warning messages
                - reasoning: Detailed explanation
                - requires_confirmation: bool
                - recommended_action: str
        """
        logger.info(f"[SAFETY GUARDIAN] Evaluating {operation}: {source_path} -> {destination_path}")
        
        threats = []
        warnings = []
        
        # LAYER 1: Path Security Validation
        path_threats = self._check_path_security(source_path, destination_path)
        threats.extend(path_threats)
        
        # LAYER 2: System File Protection
        system_threats = self._check_system_file_protection(source_path, destination_path)
        threats.extend(system_threats)
        
        # LAYER 3: Application Integrity
        app_threats = self._check_application_integrity(source_path, destination_path)
        threats.extend(app_threats)
        
        # LAYER 4: Data Loss Prevention
        data_threats = self._check_data_loss_prevention(source_path, destination_path, operation)
        threats.extend(data_threats)
        
        # LAYER 5: Logic Validation
        logic_warnings = self._check_logic_validation(source_path, destination_path, classification)
        warnings.extend(logic_warnings)
        
        # LAYER 6: Permission & Access Checks
        permission_threats = self._check_permissions(source_path, destination_path)
        threats.extend(permission_threats)
        
        # Determine risk level based on threats
        risk_level = self._calculate_risk_level(threats, warnings)
        
        # LAYER 7: AI Reasoning Evaluation (if available and needed)
        ai_evaluation = None
        if self.ollama_client and risk_level in [RiskLevel.CAUTION, RiskLevel.HIGH_RISK]:
            ai_evaluation = self._ai_reasoning_check(
                source_path, destination_path, operation, 
                classification, threats, warnings
            )
            
            # AI can upgrade or downgrade risk
            if ai_evaluation and ai_evaluation.get('success'):
                ai_risk = ai_evaluation.get('final_risk_level')
                if ai_risk == 'critical':
                    risk_level = RiskLevel.CRITICAL
                elif ai_risk == 'high_risk' and risk_level == RiskLevel.CAUTION:
                    risk_level = RiskLevel.HIGH_RISK
                elif ai_risk == 'safe' and risk_level == RiskLevel.CAUTION and not threats:
                    risk_level = RiskLevel.SAFE
        
        # Build result
        result = {
            'approved': self._should_approve(risk_level, user_approved, threats),
            'risk_level': risk_level.value,
            'threats': [self._threat_to_dict(t) for t in threats],
            'warnings': warnings,
            'reasoning': self._build_reasoning(risk_level, threats, warnings, ai_evaluation),
            'requires_confirmation': risk_level in [RiskLevel.CAUTION, RiskLevel.HIGH_RISK],
            'recommended_action': self._get_recommended_action(risk_level, user_approved),
            'ai_evaluation': ai_evaluation
        }
        
        # Log blocked operations for audit
        if not result['approved']:
            self._log_blocked_operation(source_path, destination_path, operation, result)
        
        logger.info(f"[SAFETY GUARDIAN] Evaluation result: {risk_level.value} - {'APPROVED' if result['approved'] else 'BLOCKED'}")
        
        return result
    
    def _check_path_security(self, _source: str, destination: str) -> List[Tuple[ThreatType, str, str]]:
        """Check for path traversal and security issues"""
        threats = []
        
        # Check for path traversal patterns
        if ".." in destination:
            threats.append((
                ThreatType.PATH_TRAVERSAL,
                "critical",
                f"Destination contains '..' (path traversal attack pattern): {destination}"
            ))
        
        # Check for absolute paths escaping base destination
        dest_path = Path(destination)
        if dest_path.is_absolute():
            try:
                base_dest = Path(self.config.base_destination).expanduser().resolve()
                dest_resolved = dest_path.resolve()
                
                # Verify destination is within base_destination
                try:
                    dest_resolved.relative_to(base_dest)
                except ValueError:
                    threats.append((
                        ThreatType.PATH_TRAVERSAL,
                        "critical",
                        f"Destination escapes base directory: {destination} is outside {base_dest}"
                    ))
            except Exception as e:
                threats.append((
                    ThreatType.INVALID_DESTINATION,
                    "high",
                    f"Cannot validate destination path: {e}"
                ))
        
        # Check for suspicious characters in paths
        suspicious_chars = ['\\x00', '\n', '\r', '\t']
        for char in suspicious_chars:
            if char in destination:
                threats.append((
                    ThreatType.PATH_TRAVERSAL,
                    "critical",
                    f"Destination contains suspicious character: {repr(char)}"
                ))
        
        return threats
    
    def _check_system_file_protection(self, source: str, _destination: str) -> List[Tuple[ThreatType, str, str]]:
        """Protect critical system files"""
        threats = []
        
        try:
            source_resolved = str(Path(source).resolve())
            
            # Check Windows system paths
            if os.name == 'nt':
                for critical_path in self.CRITICAL_PATHS_WINDOWS:
                    try:
                        if source_resolved.startswith(critical_path.lower()) or \
                           source_resolved.lower().startswith(critical_path.lower()):
                            threats.append((
                                ThreatType.SYSTEM_FILE,
                                "critical",
                                f"CRITICAL: File is in system directory {critical_path}. "
                                f"Moving system files will break Windows!"
                            ))
                            break
                    except:
                        pass
            
            # Check Unix system paths
            else:
                for critical_path in self.CRITICAL_PATHS_UNIX:
                    if source_resolved.startswith(critical_path):
                        threats.append((
                            ThreatType.SYSTEM_FILE,
                            "critical",
                            f"CRITICAL: File is in system directory {critical_path}. "
                            f"Moving system files will break the OS!"
                        ))
                        break
            
            # Check for critical file extensions in wrong context
            source_path = Path(source)
            if source_path.suffix.lower() in self.CRITICAL_EXTENSIONS:
                # Only threat if in system/program directories
                parent_str = str(source_path.parent).lower()
                if any(x in parent_str for x in ['windows', 'system32', 'program files', 'bin', 'lib', 'sbin']):
                    threats.append((
                        ThreatType.SYSTEM_FILE,
                        "critical",
                        f"CRITICAL: File {source_path.suffix} in system/application directory. "
                        f"Moving will likely break software!"
                    ))
        
        except Exception as e:
            logger.error(f"Error checking system file protection: {e}")
        
        return threats
    
    def _check_application_integrity(self, source: str, _destination: str) -> List[Tuple[ThreatType, str, str]]:
        """Protect application files and configurations"""
        threats = []
        
        try:
            source_path = Path(source)
            source_str = str(source_path).lower()
            
            # Check if file is in an application installation directory
            app_indicators = [
                'program files', 'program files (x86)', 'programdata',
                '.app/contents', '/applications/', '/opt/',
                'appdata\\local\\programs', 'appdata\\roaming'
            ]
            
            for indicator in app_indicators:
                if indicator in source_str:
                    # Check if it's an executable or library
                    if source_path.suffix.lower() in ['.exe', '.dll', '.so', '.dylib', '.app']:
                        threats.append((
                            ThreatType.APPLICATION_FILE,
                            "critical",
                            f"CRITICAL: Executable/library in application directory. "
                            f"Moving will break the application!"
                        ))
                        break
                    
                    # Check if it's a config file in app directory
                    if source_path.suffix.lower() in ['.ini', '.cfg', '.conf', '.plist']:
                        threats.append((
                            ThreatType.APPLICATION_FILE,
                            "high",
                            f"WARNING: Configuration file in application directory. "
                            f"Moving may break application settings."
                        ))
                        break
        
        except Exception as e:
            logger.error(f"Error checking application integrity: {e}")
        
        return threats
    
    def _check_data_loss_prevention(self, source: str, destination: str, operation: str) -> List[Tuple[ThreatType, str, str]]:
        """Prevent accidental data loss"""
        threats = []
        
        try:
            dest_path = Path(destination)
            
            # Check if destination already exists
            if dest_path.exists():
                source_path = Path(source)
                
                # If sizes differ significantly, could be overwriting important file
                if dest_path.is_file() and source_path.exists():
                    source_size = source_path.stat().st_size
                    dest_size = dest_path.stat().st_size
                    
                    if dest_size > source_size * 2:  # Destination is 2x+ larger
                        threats.append((
                            ThreatType.DATA_LOSS,
                            "high",
                            f"WARNING: Destination file is significantly larger ({dest_size} vs {source_size} bytes). "
                            f"Overwriting may cause data loss!"
                        ))
            
            # Check for destructive operations
            if operation == 'delete':
                source_path = Path(source)
                if source_path.is_file():
                    size = source_path.stat().st_size
                    # Flag deletion of large files
                    if size > 100 * 1024 * 1024:  # > 100MB
                        threats.append((
                            ThreatType.DESTRUCTIVE_OPERATION,
                            "high",
                            f"WARNING: Deleting large file ({size / (1024*1024):.1f} MB). "
                            f"This cannot be undone!"
                        ))
            
            # Check for moving to same location (circular reference)
            try:
                if Path(source).resolve() == Path(destination).resolve():
                    threats.append((
                        ThreatType.CIRCULAR_REFERENCE,
                        "medium",
                        "File is already at destination location (no-op)."
                    ))
            except:
                pass
        
        except Exception as e:
            logger.error(f"Error in data loss prevention check: {e}")
        
        return threats
    
    def _check_logic_validation(self, source: str, destination: str, classification: Dict[str, Any]) -> List[str]:
        """Validate the logic of the classification"""
        warnings = []
        
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            # Check confidence level
            confidence = classification.get('confidence', 'unknown')
            if confidence == 'low':
                warnings.append(
                    f"Classification confidence is LOW. Recommendation may not be accurate."
                )
            
            # Check if file extension matches destination category
            extension = source_path.suffix.lower()
            dest_str = str(dest_path).lower()
            
            # Example: moving .pdf to Pictures folder is suspicious
            suspicious_combinations = [
                (['pdf', 'doc', 'docx', 'txt'], ['pictures', 'images', 'photos']),
                (['jpg', 'png', 'gif', 'bmp'], ['documents', 'text']),
                (['exe', 'msi', 'app'], ['documents', 'pictures']),
                (['mp4', 'avi', 'mkv'], ['documents', 'pictures']),
            ]
            
            for extensions, wrong_dest in suspicious_combinations:
                if any(ext in extension for ext in extensions):
                    if any(cat in dest_str for cat in wrong_dest):
                        warnings.append(
                            f"Logic warning: {extension} file being moved to {dest_str}. "
                            f"This seems unusual - verify classification is correct."
                        )
            
            # Check if suggested path seems reasonable length
            if len(str(dest_path)) > 250:  # Windows MAX_PATH is 260
                warnings.append(
                    f"Destination path is very long ({len(str(dest_path))} chars). "
                    f"May cause issues on Windows systems."
                )
        
        except Exception as e:
            logger.error(f"Error in logic validation: {e}")
        
        return warnings
    
    def _check_permissions(self, source: str, _destination: str) -> List[Tuple[ThreatType, str, str]]:
        """Check file permissions and access rights"""
        threats = []

        try:
            _source_path = Path(source)
            
            # Check if we have read access to source
            if not os.access(source, os.R_OK):
                threats.append((
                    ThreatType.PERMISSION_ISSUE,
                    "critical",
                    f"No read permission for source file: {source}"
                ))
            
            # Check if file is writable (needed for move/delete)
            if not os.access(source, os.W_OK):
                threats.append((
                    ThreatType.PERMISSION_ISSUE,
                    "high",
                    f"No write permission for source file: {source}. Cannot move/delete."
                ))
            
            # Check if destination directory exists and is writable
            dest_path = Path(destination)
            dest_dir = dest_path.parent
            
            if dest_dir.exists():
                if not os.access(dest_dir, os.W_OK):
                    threats.append((
                        ThreatType.PERMISSION_ISSUE,
                        "critical",
                        f"No write permission for destination directory: {dest_dir}"
                    ))
        
        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
        
        return threats
    
    def _ai_reasoning_check(self, source: str, destination: str, operation: str,
                           classification: Dict[str, Any], threats: List, warnings: List) -> Optional[Dict]:
        """
        Final AI reasoning check - asks AI to evaluate the entire operation context.
        """
        if not self.ollama_client or not self.ollama_client.is_available():
            return None
        
        # Build comprehensive prompt for final evaluation
        prompt = f"""You are a safety evaluation AI. Your job is to perform a FINAL SAFETY CHECK
before a file operation is executed. Analyze the entire context and determine if this operation
is safe or if it could cause problems.

OPERATION DETAILS:
- Operation Type: {operation}
- Source: {source}
- Destination: {destination}

CLASSIFICATION RESULT:
{json.dumps(classification, indent=2)}

THREATS DETECTED:
{json.dumps([{'type': t[0].value, 'severity': t[1], 'message': t[2]} for t in threats], indent=2)}

WARNINGS:
{json.dumps(warnings, indent=2)}

YOUR TASK:
Carefully analyze this operation and provide a final safety evaluation.

Consider:
1. Could this operation break the operating system or applications?
2. Could this cause data loss or file corruption?
3. Is the destination logical for this file type?
4. Are there any security concerns?
5. Could this operation have unintended consequences?
6. Is the classification reasoning sound?

Provide your evaluation in JSON format:
{{
  "final_risk_level": "safe|caution|high_risk|critical",
  "should_proceed": true/false,
  "reasoning": "Your detailed analysis (3-5 sentences)",
  "concerns": ["List specific concerns if any"],
  "recommendations": ["Suggestions to make operation safer"],
  "confidence": 0.0 to 1.0
}}

IMPORTANT: Be conservative. If you have ANY doubt, recommend caution or rejection.

Your evaluation:"""
        
        try:
            import requests
            
            response = requests.post(
                f"{self.ollama_client.base_url}/api/generate",
                json={
                    "model": self.ollama_client.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                # Parse JSON
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                evaluation = json.loads(response_text)
                evaluation['success'] = True
                return evaluation
        
        except Exception as e:
            logger.error(f"AI reasoning check failed: {e}")
        
        return None
    
    def _calculate_risk_level(self, threats: List, warnings: List) -> RiskLevel:
        """Calculate overall risk level from threats and warnings"""
        
        if not threats and not warnings:
            return RiskLevel.SAFE
        
        # Check for critical threats
        for threat in threats:
            severity = threat[1] if len(threat) > 1 else "unknown"
            if severity == "critical":
                return RiskLevel.CRITICAL
        
        # Check for high severity threats
        high_count = sum(1 for t in threats if len(t) > 1 and t[1] == "high")
        if high_count >= 2:
            return RiskLevel.HIGH_RISK
        elif high_count == 1:
            return RiskLevel.CAUTION
        
        # Medium severity or warnings only
        if threats or len(warnings) >= 3:
            return RiskLevel.CAUTION
        
        return RiskLevel.SAFE
    
    def _should_approve(self, risk_level: RiskLevel, user_approved: bool, threats: List) -> bool:
        """Determine if operation should be approved"""
        
        # CRITICAL threats are NEVER auto-approved
        if risk_level == RiskLevel.CRITICAL:
            return False
        
        # HIGH_RISK requires explicit user approval
        if risk_level == RiskLevel.HIGH_RISK:
            return user_approved
        
        # CAUTION can proceed with user approval or if no critical threats
        if risk_level == RiskLevel.CAUTION:
            # Check if any threats are actually critical despite risk level
            has_critical_threat = any(
                t[1] == "critical" for t in threats if len(t) > 1
            )
            if has_critical_threat:
                return False
            return user_approved or self.config.get('auto_approve_caution', False)
        
        # SAFE operations can proceed
        return True
    
    def _build_reasoning(self, risk_level: RiskLevel, threats: List, warnings: List, 
                        ai_eval: Optional[Dict]) -> str:
        """Build human-readable reasoning for the decision"""
        
        parts = [f"Risk Level: {risk_level.value.upper()}"]
        
        if threats:
            parts.append(f"\n\nThreats Detected ({len(threats)}):")
            for threat in threats[:5]:  # Show first 5
                parts.append(f"  - [{threat[1].upper()}] {threat[2]}")
        
        if warnings:
            parts.append(f"\n\nWarnings ({len(warnings)}):")
            for warning in warnings[:5]:
                parts.append(f"  - {warning}")
        
        if ai_eval and ai_eval.get('reasoning'):
            parts.append(f"\n\nAI Evaluation:\n{ai_eval['reasoning']}")
        
        if risk_level == RiskLevel.CRITICAL:
            parts.append("\n\n⛔ OPERATION BLOCKED: Critical safety concerns detected.")
        elif risk_level == RiskLevel.HIGH_RISK:
            parts.append("\n\n⚠️ HIGH RISK: Explicit user approval required.")
        elif risk_level == RiskLevel.CAUTION:
            parts.append("\n\n⚠️ CAUTION: Review recommended before proceeding.")
        else:
            parts.append("\n\n✅ Operation appears safe to proceed.")
        
        return "\n".join(parts)
    
    def _get_recommended_action(self, risk_level: RiskLevel, user_approved: bool) -> str:
        """Get recommended action based on risk level"""
        
        if risk_level == RiskLevel.CRITICAL:
            return "BLOCK_OPERATION"
        elif risk_level == RiskLevel.HIGH_RISK:
            return "REQUIRE_EXPLICIT_APPROVAL" if not user_approved else "PROCEED_WITH_CAUTION"
        elif risk_level == RiskLevel.CAUTION:
            return "REQUEST_CONFIRMATION"
        else:
            return "PROCEED"
    
    def _threat_to_dict(self, threat: Tuple) -> Dict:
        """Convert threat tuple to dictionary"""
        return {
            'type': threat[0].value if len(threat) > 0 else "unknown",
            'severity': threat[1] if len(threat) > 1 else "unknown",
            'message': threat[2] if len(threat) > 2 else "Unknown threat"
        }
    
    def _log_blocked_operation(self, source: str, destination: str, operation: str, result: Dict):
        """Log blocked operations for security audit"""
        blocked_entry = {
            'timestamp': str(Path(source).stat().st_mtime) if Path(source).exists() else "unknown",
            'operation': operation,
            'source': source,
            'destination': destination,
            'risk_level': result['risk_level'],
            'threats': result['threats']
        }
        
        self.blocked_operations.append(blocked_entry)
        
        logger.warning(f"[SECURITY AUDIT] Blocked operation: {operation} {source} -> {destination}")
        logger.warning(f"[SECURITY AUDIT] Risk: {result['risk_level']}, Threats: {len(result['threats'])}")
    
    def get_blocked_operations(self) -> List[Dict]:
        """Get history of blocked operations for security review"""
        return self.blocked_operations.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get guardian statistics"""
        return {
            'total_blocked': len(self.blocked_operations),
            'threat_types': self._count_threat_types(),
            'risk_levels': self._count_risk_levels()
        }
    
    def _count_threat_types(self) -> Dict[str, int]:
        """Count threats by type"""
        counts = {}
        for entry in self.blocked_operations:
            for threat in entry.get('threats', []):
                threat_type = threat.get('type', 'unknown')
                counts[threat_type] = counts.get(threat_type, 0) + 1
        return counts
    
    def _count_risk_levels(self) -> Dict[str, int]:
        """Count blocked operations by risk level"""
        counts = {}
        for entry in self.blocked_operations:
            risk = entry.get('risk_level', 'unknown')
            counts[risk] = counts.get(risk, 0) + 1
        return counts


# Convenience function
def evaluate_operation_safety(source: str, destination: str, operation: str,
                             classification: Dict, config, ollama_client=None,
                             user_approved: bool = False) -> Dict[str, Any]:
    """
    Evaluate safety of a file operation.
    
    This should be called before EVERY file operation to ensure safety.
    """
    guardian = SafetyGuardian(config, ollama_client)
    return guardian.evaluate_operation(
        source, destination, operation, classification, user_approved
    )


if __name__ == "__main__":
    # Test Safety Guardian
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from config import get_config
    
    config = get_config()
    guardian = SafetyGuardian(config)
    
    # Test Case 1: Safe operation
    print("="*70)
    print("TEST 1: Safe operation")
    print("="*70)
    result = guardian.evaluate_operation(
        source_path="C:\\Users\\alex\\Downloads\\invoice.pdf",
        destination_path="C:\\Users\\alex\\Documents\\Finance\\Invoices\\invoice.pdf",
        operation="move",
        classification={'category': 'Finance', 'confidence': 'high'},
        user_approved=False
    )
    print(json.dumps(result, indent=2))
    
    # Test Case 2: System file (CRITICAL)
    print("\n" + "="*70)
    print("TEST 2: System file (should be BLOCKED)")
    print("="*70)
    result = guardian.evaluate_operation(
        source_path="C:\\Windows\\System32\\kernel32.dll",
        destination_path="C:\\Users\\alex\\Documents\\Files\\kernel32.dll",
        operation="move",
        classification={'category': 'System', 'confidence': 'high'},
        user_approved=False
    )
    print(json.dumps(result, indent=2))
    
    # Test Case 3: Path traversal attempt (CRITICAL)
    print("\n" + "="*70)
    print("TEST 3: Path traversal (should be BLOCKED)")
    print("="*70)
    result = guardian.evaluate_operation(
        source_path="C:\\Users\\alex\\Downloads\\file.txt",
        destination_path="C:\\Users\\alex\\Documents\\../../Windows/System32/malware.exe",
        operation="move",
        classification={'category': 'Documents', 'confidence': 'high'},
        user_approved=False
    )
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*70)
    print("Guardian Statistics:")
    print(json.dumps(guardian.get_statistics(), indent=2))
