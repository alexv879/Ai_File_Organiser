"""
Deferred Processing Service

Runs a background loop that processes files from the deferred queue once they
become eligible (e.g., after 24 hours). Honors SafetyGuardian protections and
uses ActionManager to perform moves. Keeps work non-intrusive so user can use
computer normally.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.config import get_config
from core.db_manager import DatabaseManager
from core.classifier import FileClassifier
from core.actions import ActionManager
from core.safety_guardian import SafetyGuardian


class DeferredService:
    def __init__(self, db: DatabaseManager, cfg=None,
                 poll_seconds: int = 60,
                 enabled: bool = True):
        self.db = db
        self.cfg = cfg or get_config()
        self.poll_seconds = poll_seconds
        self.enabled = enabled
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.guardian = SafetyGuardian(self.cfg)
        self.classifier = FileClassifier(self.cfg, None)
        # Use global dry_run setting for safety; user controls it in config/CLI
        self.actions = ActionManager(self.cfg, self.db, dry_run=self.cfg.dry_run)

    def start(self):
        if not self.enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def schedule_new_file(self, file_path: str, delay_hours: int | float) -> int:
        # Only enqueue if the file exists and is not clearly protected
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return -1
        safe, _ = self.guardian.is_file_safe_to_modify(p)
        if not safe:
            return -1
        eligible_at = datetime.now() + timedelta(hours=delay_hours)
        return self.db.enqueue_deferred(str(p), eligible_at)

    def schedule_existing_file(self, file_path: str, move_if_older_days: int, default_delay_hours: int | float) -> int:
        """For first-run deep scan: if the file is older than N days, enqueue as eligible now; otherwise after delay."""
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return -1
        safe, _ = self.guardian.is_file_safe_to_modify(p)
        if not safe:
            return -1
        try:
            age_days = max(0, (datetime.now().timestamp() - p.stat().st_mtime) / 86400)
        except Exception:
            age_days = 0
        if age_days >= move_if_older_days:
            eligible_at = datetime.now()
        else:
            eligible_at = datetime.now() + timedelta(hours=default_delay_hours)
        return self.db.enqueue_deferred(str(p), eligible_at)

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._sweep_once()
            except Exception:
                # Keep the loop resilient; avoid crashing background thread
                pass
            finally:
                self._stop.wait(self.poll_seconds)

    def _sweep_once(self):
        due = self.db.fetch_due_deferred(limit=100)
        if not due:
            return
        for item in due:
            item_id = item['id']
            path = Path(item['file_path'])
            if not path.exists() or not path.is_file():
                self.db.mark_deferred_status(item_id, 'skipped', error='Missing file')
                continue
            safe, reason = self.guardian.is_file_safe_to_modify(path)
            if not safe:
                self.db.mark_deferred_status(item_id, 'skipped', error=reason or 'Protected')
                continue
            try:
                # Classify and execute
                classification = self.classifier.classify(str(path))
                res = self.actions.execute(str(path), classification, user_approved=True)
                if res.get('success'):
                    self.db.mark_deferred_status(item_id, 'done', None)
                else:
                    # Keep queued on cautionary block? Mark error to avoid tight loop
                    self.db.mark_deferred_status(item_id, 'error', error=res.get('message') or 'Unknown error')
            except Exception as ex:
                self.db.mark_deferred_status(item_id, 'error', error=str(ex))
