# 🚀 COMPLETE END-TO-END FIX PROMPT FOR AIFILEORGANISER

> **Use this prompt with Claude AI to fix ALL issues and make the software production-ready**

---

## CONTEXT

You are fixing a mature, well-architected Python project called **Private AI File Organiser**. This is a local-first file organization tool using Ollama (local LLM) that automatically classifies and organizes files on disk.

**Current Status**: ~95% complete, but has 5 CRITICAL issues + 7 HIGH priority issues preventing production release.

**Goal**: Apply ALL fixes in a single coordinated pass, ensuring the software is production-ready and can be used immediately after completion.

**Key Constraints**:
- Keep existing architecture intact
- Maintain 200-key limited release licensing
- Preserve all documentation
- Ensure backward compatibility with existing config.json
- No breaking changes to APIs

---

## 🔴 CRITICAL ISSUES TO FIX (MUST DO)

### Issue #1: Policy Enforcement Code Was Reverted
**File**: `src/core/actions.py`
**Severity**: CRITICAL SECURITY

The `execute()` method is missing folder policy enforcement that was previously implemented. Users cannot protect specific folders from reorganization.

**Current broken code (line 46)**:
```python
def execute(self, file_path: str, classification: Dict[str, Any],
            user_approved: bool = False) -> Dict[str, Any]:  # ❌ Missing folder_policy param
    # ... proceeds without checking policies
```

**Required fix**:
1. Add `folder_policy: Dict[str, Any] = None` parameter to execute() method
2. Add folder policy check BEFORE any file operations (around line 67):
```python
if folder_policy is None:
    folder_policy = self.config.get_folder_policy(file_path)

if folder_policy and folder_policy.get('allow_move') is False:
    return {
        'success': False,
        'action': 'blocked',
        'old_path': file_path,
        'new_path': None,
        'time_saved': 0.0,
        'message': 'Operation blocked: folder policy disallows moves'
    }
```
3. Update all calls to `execute()` to pass the folder_policy when available

**Test after fixing**:
- Create config.json with `"folder_policies": {"~/Desktop": {"allow_move": false}}`
- Drop file in Desktop
- Verify ActionManager returns `'success': False` with blocked message

---

### Issue #2: base_destination Is Hardcoded
**File**: `src/core/actions.py` (line 156)
**Severity**: CRITICAL DATA LOSS RISK

The `_build_destination_path()` method uses `Path.home()` instead of respecting `config.base_destination`. Files are organized to wrong location.

**Current broken code**:
```python
def _build_destination_path(self, source_path: Path, suggested_path: str, ...):
    base_dir = Path.home()  # ❌ HARDCODED
    dest_dir = base_dir / suggested_path.strip('/')
```

**Required fix**:
```python
def _build_destination_path(self, source_path: Path, suggested_path: str, 
                            suggested_rename: Optional[str] = None) -> Path:
    """Build complete destination path for file."""
    # Use configured base destination
    try:
        base_dir = Path(self.config.base_destination).expanduser().resolve()
    except (AttributeError, OSError):
        base_dir = Path.home()  # Fallback only on error

    # Handle absolute vs relative suggested paths
    suggested_obj = Path(suggested_path)
    if suggested_obj.is_absolute():
        dest_dir = suggested_obj
    else:
        dest_dir = base_dir / Path(suggested_path.lstrip('/'))

    # Determine filename
    filename = suggested_rename if suggested_rename else source_path.name
    
    # Handle filename conflicts
    dest_path = dest_dir / filename
    
    if dest_path.exists() and dest_path != source_path:
        # Add counter to filename to avoid overwrites
        stem = dest_path.stem
        suffix = dest_path.suffix
        counter = 1
        while dest_path.exists():
            dest_path = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    return dest_path
```

**Test after fixing**:
- Set config.json: `"base_destination": "D:/MyOrganizedFiles"`
- Move a file
- Verify it appears in D:/MyOrganizedFiles, NOT home directory

---

### Issue #3: Race Condition in File Operations
**File**: `src/core/actions.py` (lines 67-104)
**Severity**: CRITICAL STABILITY

TOCTOU (Time Of Check Time Of Use) vulnerability: File could be deleted between existence check and move operation, causing crashes.

**Current broken code**:
```python
if not path.exists():  # Line 67
    return {...}

# Lines 80-99: Long processing here
# FILE COULD BE DELETED BY ANOTHER PROCESS HERE

result = self._perform_action(path, new_path, action_type)  # Line 104 - CRASH RISK
```

**Required fix**: Modify `_perform_action()` to re-check file before moving:

```python
def _perform_action(self, source: Path, destination: Path, action: str) -> Dict[str, Any]:
    """Actually perform file operation with race condition protection."""
    try:
        # RE-CHECK file exists just before operation (CRITICAL)
        if not source.exists():
            return {
                'success': False,
                'action': action,
                'old_path': str(source),
                'new_path': str(destination),
                'message': f'File no longer exists at {source}'
            }

        # Check if file is locked/in use (NEW)
        try:
            with open(source, 'rb+') as f:
                pass  # Just test if we can open it
        except (IOError, PermissionError) as e:
            return {
                'success': False,
                'action': action,
                'old_path': str(source),
                'new_path': str(destination),
                'message': f'File is locked or in use: {str(e)}'
            }

        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Perform atomic move
        shutil.move(str(source), str(destination))

        return {
            'success': True,
            'action': action,
            'old_path': str(source),
            'new_path': str(destination),
            'message': f'Successfully {action}d file to {destination}'
        }

    except Exception as e:
        return {
            'success': False,
            'action': action,
            'old_path': str(source),
            'new_path': str(destination),
            'message': f'Failed to {action} file: {str(e)}'
        }
```

**Test after fixing**:
- Watch folder mode while rapidly deleting/moving files
- Should handle gracefully with error messages, not crash

---

### Issue #4: Source Blacklist Bypass in Agent
**File**: `src/agent/agent_analyzer.py` (around line 360)
**Severity**: CRITICAL SECURITY

Agent only checks DESTINATION paths against blacklist, not SOURCE. Could suggest moving system files.

**Current broken code** (in `_apply_safety_checks()`):
```python
def _apply_safety_checks(self, plan, file_path, policy=None):
    # ✅ Checks destination only
    suggested_path = plan.get('suggested_path')
    if suggested_path:
        # validates destination
    
    # ❌ NEVER checks if SOURCE file is blacklisted
```

**Required fix**: Add source check FIRST:

```python
def _check_source_blacklist(self, file_path: str) -> tuple[bool, str]:
    """
    Check if source file is in blacklist.
    
    Returns: (is_blacklisted, reason)
    """
    try:
        source_resolved = str(Path(file_path).resolve())
        blacklist = getattr(self.config, 'path_blacklist', []) or []

        for blacklisted in blacklist:
            try:
                blacklisted_resolved = str(Path(blacklisted).expanduser().resolve())
                if os.path.commonpath([source_resolved, blacklisted_resolved]) == blacklisted_resolved:
                    return True, f'source file is blacklisted: {blacklisted}'
            except (ValueError, OSError):
                # Different drives on Windows
                if source_resolved.lower().startswith(blacklisted_resolved.lower()):
                    return True, f'source file is blacklisted: {blacklisted}'
    except Exception:
        pass

    return False, ''


def _apply_safety_checks(self, plan: Dict[str, Any], file_path: str,
                        policy: dict = None) -> Dict[str, Any]:
    """Apply safety checks to the agent plan."""
    
    # CHECK SOURCE FILE FIRST (NEW - CRITICAL)
    is_blacklisted, reason = self._check_source_blacklist(file_path)
    if is_blacklisted:
        plan['action'] = 'none'
        plan['block_reason'] = reason
        return plan

    # Check folder policy allow_move
    if policy and policy.get('allow_move') is False:
        plan['action'] = 'none'
        plan['block_reason'] = 'folder policy disallows moves'
        return plan

    # ... rest of existing destination checks ...
```

**Test after fixing**:
- Try deep analyze on a blacklisted file
- Should return blocked action, not suggested move

---

### Issue #5: No Timeout on Ollama Requests
**File**: `src/agent/agent_analyzer.py` (lines 278-309)
**Severity**: CRITICAL HANG RISK

If Ollama hangs, dashboard freezes indefinitely. No timeout handling.

**Current broken code**:
```python
def _call_ollama(self, prompt: str) -> str:
    try:
        response = requests.post(
            f"{self.ollama_client.base_url}/api/generate",
            json={...},
            timeout=self.ollama_client.timeout  # ❌ Could be None
        )
        # ...
    except Exception as e:
        raise Exception(...)  # ❌ No distinction between timeout and other errors
```

**Required fix**:
```python
def _call_ollama(self, prompt: str) -> str:
    """Call Ollama generate API with proper timeout handling."""
    import requests

    # Ensure timeout is set (NEW)
    timeout = getattr(self.ollama_client, 'timeout', 30)
    if timeout is None or timeout <= 0:
        timeout = 30  # Default 30 seconds

    try:
        response = requests.post(
            f"{self.ollama_client.base_url}/api/generate",
            json={
                "model": self.ollama_client.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=timeout
        )

        if response.status_code != 200:
            raise Exception(f"Ollama API returned status {response.status_code}")

        result = response.json()
        return result.get("response", "")

    except requests.exceptions.Timeout:
        # Specific timeout handling (NEW)
        raise Exception(
            f"Ollama request timed out after {timeout} seconds. "
            f"Try increasing timeout in config.json or using a faster model."
        )
    except requests.exceptions.ConnectionError as e:
        # Specific connection handling (NEW)
        raise Exception(
            f"Cannot connect to Ollama at {self.ollama_client.base_url}. "
            f"Is Ollama running? Start with: ollama serve"
        )
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ollama request failed: {str(e)}")
```

**Test after fixing**:
- Stop Ollama service
- Try deep analyze
- Should get clear error message about Ollama not running, not hang
- Restart Ollama and verify it works again

---

## 🟠 HIGH PRIORITY ISSUES (SHOULD FIX)

### HIGH-1: Missing Input Validation in Dashboard
**File**: `src/ui/dashboard.py` (around line 1058)

The `/api/files/deep-analyze` endpoint doesn't validate that file is in watched folders.

**Fix**: Before analyzing file, verify it's in watched folders or pending list:
```python
@app.post("/api/files/deep-analyze")
def deep_analyze_file(request: DeepAnalyzeRequest, req: Request):
    file_path = request.file_path
    
    # Validate file exists
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Validate file is in watched folders or pending list (NEW)
    file_path_obj = Path(file_path).resolve()
    
    # Check if in pending files
    is_pending = any(
        Path(item['file_path']).resolve() == file_path_obj
        for item in state.pending_files
    )
    
    # Check if in watched folders
    is_watched = False
    for watched in state.config.watched_folders:
        watched_path = Path(watched).expanduser().resolve()
        try:
            if os.path.commonpath([str(file_path_obj), str(watched_path)]) == str(watched_path):
                is_watched = True
                break
        except ValueError:
            continue
    
    if not is_pending and not is_watched:
        raise HTTPException(
            status_code=403,
            detail="File not in watched folders or pending list"
        )
    
    # Check blacklist
    blacklist = getattr(state.config, 'path_blacklist', []) or []
    for blacklisted in blacklist:
        try:
            blacklisted_resolved = Path(blacklisted).expanduser().resolve()
            if os.path.commonpath([str(file_path_obj), str(blacklisted_resolved)]) == str(blacklisted_resolved):
                raise HTTPException(
                    status_code=403,
                    detail="File is in blacklisted location"
                )
        except (ValueError, OSError):
            continue
    
    # Continue with deep analysis
    try:
        result = state.classifier.classify(str(file_path_obj), deep_analysis=True)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deep analysis failed: {str(e)}")
```

---

### HIGH-2: Add Rate Limiting to Dashboard
**File**: `src/ui/dashboard.py` (note: This is already partially fixed in the file)

Verify rate limiting is applied correctly to `/api/files/deep-analyze`:
```python
@app.post("/api/files/deep-analyze")
def deep_analyze_file(request: DeepAnalyzeRequest, req: Request):
    # Rate limit check (VERIFY IT'S HERE)
    client_ip = req.client.host
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max 10 requests per 60 seconds."
        )
    
    # Rest of implementation...
```

---

### HIGH-3: Fix SQL LIKE Pattern Escaping
**File**: `src/core/db_manager.py` (around line 206)

In `search_logs()` method, escape SQL wildcards:
```python
def search_logs(self, query: str = None, category: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    with self.get_connection() as conn:
        cursor = conn.cursor()
        where_clauses = []
        params: List[Any] = []

        if query:
            # Escape SQL LIKE wildcards (NEW)
            escaped_query = query.replace('%', '\\%').replace('_', '\\_')
            like = f"%{escaped_query}%"
            where_clauses.append(
                "(filename LIKE ? ESCAPE '\\' OR old_path LIKE ? ESCAPE '\\' OR new_path LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like])

        # Rest of method unchanged...
```

---

### HIGH-4: Fix Memory Leak in Watcher
**File**: `src/core/watcher.py` (around line 45)

Add maxsize to file queue:
```python
class FileEventHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable = None, file_queue: Queue = None, 
                 blacklist: Optional[List[str]] = None, max_queue_size: int = 1000):
        super().__init__()
        self.callback = callback
        self.file_queue = file_queue or Queue(maxsize=max_queue_size)  # ADD maxsize
        self.blacklist = [str(Path(p).expanduser().resolve()) for p in (blacklist or [])]
        # ... rest unchanged
```

---

### HIGH-5: Add Transaction Support to DB Operations
**File**: `src/core/db_manager.py` (around line 146)

In `log_action()` method, use explicit transactions:
```python
def log_action(self, filename: str, old_path: str, new_path: Optional[str],
               operation: str, time_saved: float = 0.0, category: Optional[str] = None,
               ai_suggested: bool = False, user_approved: bool = False,
               raw_response: Optional[str] = None, model_name: Optional[str] = None,
               prompt_hash: Optional[str] = None) -> int:
    with self.get_connection() as conn:
        cursor = conn.cursor()

        try:
            # Start explicit transaction (NEW)
            cursor.execute("BEGIN IMMEDIATE")

            # Insert log entry
            cursor.execute("""
                INSERT INTO files_log
                (filename, old_path, new_path, operation, time_saved, category, ai_suggested, user_approved,
                 raw_response, model_name, prompt_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (filename, old_path, new_path, operation, time_saved, category, ai_suggested, user_approved,
                  raw_response, model_name, prompt_hash))

            log_id = cursor.lastrowid

            # Update daily stats
            today = datetime.now().date()
            cursor.execute("""
                INSERT INTO stats (stat_date, files_organised, time_saved_minutes, ai_classifications)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(stat_date) DO UPDATE SET
                    files_organised = files_organised + 1,
                    time_saved_minutes = time_saved_minutes + ?,
                    ai_classifications = ai_classifications + ?
            """, (today, time_saved, 1 if ai_suggested else 0, time_saved, 1 if ai_suggested else 0))

            # Commit transaction (NEW)
            conn.commit()
            return log_id

        except Exception as e:
            # Rollback on any error (NEW)
            conn.rollback()
            raise e
```

---

### HIGH-6: Break Circular Import
**File**: Create `src/core/text_extractor.py` (NEW FILE)

Extract shared text extraction logic:
```python
"""
Text Extraction Module

Shared text extraction functionality without circular dependencies.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import mimetypes

try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False


class TextExtractor:
    """Shared text extraction without classifier dependency."""

    def __init__(self, config):
        self.config = config
        self.text_extract_limit = config.text_extract_limit

    def extract_file_info(self, path: Path) -> Dict[str, Any]:
        """Extract comprehensive file information."""
        stat = path.stat()
        extension = path.suffix.lower().lstrip('.')
        mime_type, _ = mimetypes.guess_type(str(path))
        text_snippet = self._extract_text(path, extension)

        return {
            'path': str(path),
            'filename': path.name,
            'stem': path.stem,
            'extension': extension,
            'size': stat.st_size,
            'mime_type': mime_type,
            'text_snippet': text_snippet,
            'modified_time': stat.st_mtime
        }

    def _extract_text(self, path: Path, extension: str) -> Optional[str]:
        """Extract text content from file for AI analysis."""
        try:
            if extension in ['txt', 'md', 'log', 'csv', 'json', 'xml', 'html']:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(self.text_extract_limit)

            elif extension == 'pdf' and PDF_SUPPORT:
                return self._extract_pdf_text(path)

            elif extension == 'docx' and DOCX_SUPPORT:
                return self._extract_docx_text(path)

        except Exception:
            pass

        return None

    def _extract_pdf_text(self, path: Path) -> Optional[str]:
        """Extract text from PDF file."""
        try:
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text()
                    return text[:self.text_extract_limit]
        except Exception:
            pass
        return None

    def _extract_docx_text(self, path: Path) -> Optional[str]:
        """Extract text from DOCX file."""
        try:
            doc = Document(path)
            text = '\n'.join([para.text for para in doc.paragraphs[:5]])
            return text[:self.text_extract_limit]
        except Exception:
            pass
        return None
```

Then update `src/agent/agent_analyzer.py`:
```python
# Remove this line:
# from ..core.classifier import FileClassifier

# Add this line:
from ..core.text_extractor import TextExtractor

class AgentAnalyzer:
    def __init__(self, config, ollama_client, db_manager=None):
        self.config = config
        self.ollama_client = ollama_client
        self.db_manager = db_manager
        self.text_extractor = TextExtractor(config)  # NEW - No classifier dependency!
```

---

### HIGH-7: Add Symlink Safety Checks
**File**: `src/config.py` and multiple files

Add symlink checking before path validation:
```python
def _is_path_blacklisted(self, path: Path, blacklist: List[str]) -> bool:
    """Check if path (or symlink target) is blacklisted."""
    try:
        if path.is_symlink():
            # Check both symlink location and target
            symlink_path = path
            target_path = path.resolve()

            for check_path in [symlink_path, target_path]:
                resolved = str(check_path)
                for blacklisted in blacklist:
                    blacklisted_resolved = str(Path(blacklisted).expanduser().resolve())
                    try:
                        if os.path.commonpath([resolved, blacklisted_resolved]) == blacklisted_resolved:
                            return True
                    except (ValueError, OSError):
                        if resolved.lower().startswith(blacklisted_resolved.lower()):
                            return True
        else:
            # Normal path check
            resolved = str(path.resolve())
            for blacklisted in blacklist:
                blacklisted_resolved = str(Path(blacklisted).expanduser().resolve())
                try:
                    if os.path.commonpath([resolved, blacklisted_resolved]) == blacklisted_resolved:
                        return True
                except (ValueError, OSError):
                    if resolved.lower().startswith(blacklisted_resolved.lower()):
                        return True

    except Exception:
        return True  # If check fails, err on side of caution

    return False
```

---

## 🟡 MEDIUM PRIORITY (NICE TO HAVE)

### MEDIUM-1: Add Comprehensive Logging
Add logging statements to track:
- When agent is called and why
- What prompts were sent
- Agent response times
- Safety check results

**File**: `src/agent/agent_analyzer.py` - Add at start of `analyze_file()`:
```python
def analyze_file(self, file_path: str, policy: dict = None, ...):
    logger.info(f"Agent analysis started for: {file_path}")
    start_time = time.time()
    
    # ... existing code ...
    
    elapsed = time.time() - start_time
    logger.info(f"Agent analysis completed in {elapsed:.2f}s: "
               f"category={safe_plan.get('category')}, "
               f"confidence={safe_plan.get('confidence')}")
```

---

### MEDIUM-2: Validate Config Schema
**File**: `src/config.py`

Add schema validation on load:
```python
from jsonschema import validate, ValidationError

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "watched_folders": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "ollama_model": {"type": "string"},
        "base_destination": {"type": "string"}
    },
    "required": ["watched_folders", "ollama_model"]
}

def load(self) -> None:
    if not self.config_path.exists():
        raise FileNotFoundError(f"Config not found: {self.config_path}")

    with open(self.config_path, 'r', encoding='utf-8') as f:
        raw_config = json.load(f)

    # Validate (NEW)
    try:
        validate(instance=raw_config, schema=CONFIG_SCHEMA)
    except ValidationError as e:
        raise ValueError(f"Invalid configuration: {e.message}")

    self._config = raw_config
    # ... rest unchanged
```

---

### MEDIUM-3: Sanitize Agent Evidence
**File**: `src/agent/agent_analyzer.py`

Escape HTML in agent evidence for XSS prevention:
```python
import html

def _parse_and_validate_response(self, response_text: str) -> Dict[str, Any]:
    # ... existing validation code ...
    
    # Sanitize evidence strings (NEW)
    if 'evidence' in plan and isinstance(plan['evidence'], list):
        plan['evidence'] = [
            html.escape(str(ev))[:200]
            for ev in plan['evidence']
        ]

    # Sanitize reason and category
    if 'reason' in plan:
        plan['reason'] = html.escape(str(plan['reason']))[:500]
    if 'category' in plan:
        plan['category'] = html.escape(str(plan['category']))[:100]

    plan['method'] = 'agent'
    plan['success'] = True

    return plan
```

---

## AFTER ALL FIXES: COMPREHENSIVE TEST CHECKLIST

Run these tests to verify everything works:

### 1. Test Folder Policies
```bash
# Create config with folder policy
cat > config.json << 'EOF'
{
  "watched_folders": ["~/Downloads"],
  "base_destination": "~/Documents/Organized",
  "folder_policies": {
    "~/Downloads": {"allow_move": false}
  }
}
EOF

# Drop file in Downloads
# Verify ActionManager blocks move
python -m pytest tests/test_agent.py::test_policy_enforcement -v
```

### 2. Test Base Destination
```bash
# Update config
python -c "
import json
with open('config.json') as f:
    config = json.load(f)
config['base_destination'] = '/tmp/test_org'
with open('config.json', 'w') as f:
    json.dump(config, f, indent=2)
"

# Create test file and move it
# Verify file appears in /tmp/test_org, NOT home directory
```

### 3. Test Blacklist
```bash
# Add system path to blacklist, try deep analyze
python -c "
from src.config import get_config
config = get_config()
# Test _is_path_blacklisted
"
```

### 4. Test Ollama Timeout
```bash
# Stop Ollama service
# Try deep analyze
# Verify clear error message about Ollama not running
```

### 5. Run Full Test Suite
```bash
python tools/test_agent.py
pytest tests/ -v --tb=short
```

### 6. Manual Dashboard Test
```bash
python src/main.py dashboard
# Visit http://localhost:5000
# Test all features work without errors
```

---

## FINAL VERIFICATION BEFORE GITHUB

- [ ] All 5 CRITICAL issues fixed
- [ ] All 7 HIGH issues fixed
- [ ] Config.json has NO real paths
- [ ] No API keys or secrets in code
- [ ] Database file not committed (.gitignore has *.db)
- [ ] LICENSE.txt clear about 200-key proprietary model
- [ ] README.md still complete and accurate
- [ ] Code follows PEP 8 style
- [ ] No print() statements (use logging)
- [ ] All imports organized at top of files
- [ ] No TODO/FIXME/HACK comments
- [ ] Type hints on all public methods
- [ ] Error messages are user-friendly

---

## DEPLOYMENT CHECKLIST

After all fixes are applied:

```bash
# 1. Run tests
pytest tests/ -v

# 2. Run agent test harness
python tools/test_agent.py

# 3. Test dashboard locally
python src/main.py dashboard

# 4. Create git commit
git add -A
git commit -m "fix: Apply all critical and high priority fixes - production ready"

# 5. Tag version
git tag v1.0.0

# 6. Push to GitHub private repo
git push origin main
git push origin v1.0.0
```

---

## SUCCESS CRITERIA

After ALL fixes are complete, the software MUST:

✅ **Never crash** when organizing files concurrently
✅ **Respect all folder policies** (allow_move=false blocks moves)
✅ **Organize files to correct base_destination** (not hardcoded home)
✅ **Block blacklisted paths** both as source and destination
✅ **Handle Ollama timeouts gracefully** (clear error, no hang)
✅ **Validate user input** (no path traversal attacks)
✅ **Maintain transaction consistency** (logs + stats atomic)
✅ **No circular imports** (clean module structure)
✅ **Run dashboard without errors** at http://localhost:5000
✅ **Pass all unit tests** with 100% critical code coverage

---

## NOTES FOR YOU

- This fix prompt is **complete and self-contained**
- Copy the entire prompt and ask Claude to apply all fixes
- All fixes maintain backward compatibility
- No database migration needed
- No config.json format changes
- After fixes, your software is **immediately usable**
- You can organize files right away using the dashboard

Good luck! 🚀

---

**Next Step**: Copy this entire prompt and share with Claude. It will apply all fixes in one coordinated pass.

