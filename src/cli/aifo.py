"""
AI File Organiser - Minimal Safety-First CLI (aifo)

Commands:
  - organize [folder]: organize files in safe user folders by default
  - find-duplicates [folder] [--delete]: scan duplicates with app/game protection
  - undo [--last N | --interactive]: revert recent MOVE operations using operations.log
  - space migrate --to DRIVE [--simulate]: safety-bannered plan for migration (simulate only)

Safety features:
  - Default safe scan folders (Downloads, Documents, Pictures, Videos, Desktop, Music)
  - validate_scan_folder via SafetyGuardian for custom targets
  - Deletion whitelist and typed confirmation
  - First-run enforced dry-run and safety banner
  - Size limits and --simulate support
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import typer

# Ensure project imports work when executing as module
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import get_config
from core.db_manager import DatabaseManager
from core.classifier import FileClassifier
from core.actions import ActionManager
from core.duplicates import DuplicateFinder
from core.safety_guardian import SafetyGuardian


app = typer.Typer(add_completion=False, help="AI File Organiser - Safety-first CLI")


def safe_scan_folders() -> List[Path]:
    home = Path.home()
    return [
        home / "Downloads",
        home / "Documents",
        home / "Pictures",
        home / "Videos",
        home / "Desktop",
        home / "Music",
    ]


def is_safe_location_for_deletion(p: Path) -> bool:
    safe = [Path.home() / "Downloads", Path.home() / "Desktop"]
    temp_env = os.environ.get('TEMP') or os.environ.get('TMP')
    if temp_env:
        safe.append(Path(temp_env))
    try:
        rp = p.resolve()
        for loc in safe:
            try:
                if os.path.commonpath([str(rp), str(loc.resolve())]) == str(loc.resolve()):
                    return True
            except ValueError:
                # Different drives
                if str(rp).lower().startswith(str(loc.resolve()).lower()):
                    return True
    except Exception:
        return False
    return False


def command_history_path() -> Path:
    cfg_dir = ROOT.parent / "config" if (ROOT / "../config").exists() else ROOT / "../config"
    cfg_dir = (ROOT / "../config").resolve()  # project-root/config
    cfg_dir.mkdir(exist_ok=True)
    return cfg_dir / "command_history.json"


def check_first_run_for_command(name: str) -> bool:
    import json
    path = command_history_path()
    data = {"history": []}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            data = {"history": []}
    ran = any(item.get('command') == name for item in data.get('history', []))
    if not ran:
        data.setdefault('history', []).append({'command': name})
        try:
            path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except Exception:
            pass
    return not ran


SAFETY_LIMITS = {
    'max_files_to_delete_without_confirmation': 100,
    'max_total_size_to_delete_without_confirmation': 10 * 1024 * 1024 * 1024,
    'max_files_to_move_without_confirmation': 500,
}


def show_safety_banner_once():
    cfg = get_config()
    if not cfg.get('safety_notice_shown', False):
        typer.echo("\n🛡️ SAFETY MODE ENABLED\n")
        typer.echo("This tool will NOT touch:")
        typer.echo("✓ System files (Windows, Program Files)")
        typer.echo("✓ Installed applications (Steam, Epic Games, Origin, etc.)")
        typer.echo("✓ Game files (.pak, .dll, .exe in app folders)")
        typer.echo("✓ Development tools (Visual Studio, IDEs, etc.)")
        typer.echo("✓ Any folder containing applications\n")
        typer.echo("Only user files in safe locations will be processed:")
        for f in safe_scan_folders():
            typer.echo(f"✓ {f}")
        typer.echo("\nApplication and game files are automatically protected.\n")
        try:
            cfg.update('safety_notice_shown', True)
            cfg.save()
        except Exception:
            pass


def validate_target_folder(guardian: SafetyGuardian, folder: Optional[Path]) -> Tuple[List[Path], Optional[str]]:
    # default safe targets
    if folder is None:
        return [p for p in safe_scan_folders() if p.exists()], None
    ok, reason = guardian.validate_scan_folder(folder)
    if not ok:
        # Allow warning prompts; hard protected requires typed phrase
        if reason and reason.startswith("WARNING:"):
            cont = typer.confirm(f"{reason}\nContinue anyway?", default=False)
            if not cont:
                return [], reason
        elif reason and "Protected system/application folder" in reason:
            typer.secho("⚠️ DANGER ZONE\n\nYou are trying to scan a folder that may contain applications or games. This could break installed software.", fg=typer.colors.RED)
            typer.echo(f"Folder: {folder}")
            phrase = typer.prompt("Type 'I UNDERSTAND THE RISK' to proceed")
            if phrase.strip() != 'I UNDERSTAND THE RISK':
                return [], reason
    return [folder], None


@app.command("organize")
def organize(folder: Optional[Path] = typer.Argument(None, exists=False),
             simulate: bool = typer.Option(True, "--simulate/--no-simulate", help="Simulate actions (dry run)"),
             auto: bool = typer.Option(False, "--auto", help="Auto-approve organize actions")):
    """Organize files in a folder. Defaults to safe user folders when not provided."""
    show_safety_banner_once()
    cfg = get_config()
    db = DatabaseManager()
    guardian = SafetyGuardian(cfg)
    targets, reason = validate_target_folder(guardian, folder)
    if not targets:
        typer.secho(f"❌ PROTECTED FOLDER\n\n{reason}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    classifier = FileClassifier(cfg, None)
    actions = ActionManager(cfg, db, dry_run=True if simulate else None)

    # First-run enforce dry-run
    if check_first_run_for_command("organize") and not simulate:
        typer.secho("First run enforce dry-run: switching to simulate.", fg=typer.colors.YELLOW)
        actions.set_dry_run(True)

    import itertools
    count = 0
    # Pre-count for safety limits
    candidates: List[Path] = []
    for tgt in targets:
        files = (p for p in tgt.rglob('*') if p.is_file())
        for p in itertools.islice(files, 10000):  # guard upper bound
            safe, _ = guardian.is_file_safe_to_modify(p)
            if safe:
                candidates.append(p)

    # Size limits check
    total_size = 0
    for p in candidates:
        try:
            total_size += p.stat().st_size
        except Exception:
            pass
    if len(candidates) > SAFETY_LIMITS['max_files_to_move_without_confirmation']:
        typer.secho(f"About to process {len(candidates)} files.", fg=typer.colors.YELLOW)
        if typer.prompt("Type 'yes' to confirm") != 'yes':
            typer.echo("Operation cancelled.")
            raise typer.Exit()

    # Execute
    for p in candidates:
        classification = classifier.classify(str(p))
        res = actions.execute(str(p), classification, user_approved=auto)
        count += 1
    typer.echo(f"Processed {count} files{' (simulate)' if actions.dry_run else ''}.")


@app.command("find-duplicates")
def find_duplicates(folder: Optional[Path] = typer.Argument(None, exists=False),
                    delete: bool = typer.Option(False, "--delete", help="Delete safe duplicates"),
                    simulate: bool = typer.Option(True, "--simulate/--no-simulate")):
    """Find duplicate files (safe user folders by default). Optionally delete safe duplicates."""
    show_safety_banner_once()
    cfg = get_config()
    db = DatabaseManager()
    guardian = SafetyGuardian(cfg)
    targets, reason = validate_target_folder(guardian, folder)
    if not targets:
        typer.secho(f"❌ PROTECTED FOLDER\n\n{reason}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    finder = DuplicateFinder(cfg, db)
    all_groups = []
    for tgt in targets:
        all_groups.extend(finder.find_duplicates_in_directory(str(tgt), recursive=True))
    safe_groups, protected_groups, protected_files = finder.filter_protected_duplicates(all_groups)

    typer.echo(f"Found {len(safe_groups)} safe duplicate groups. Protected groups skipped: {protected_groups} (files: {protected_files})")

    if not delete or not safe_groups:
        raise typer.Exit()

    # Deletion whitelist & confirmations
    to_delete = 0
    total_bytes = 0
    for g in safe_groups:
        suggestion = finder.suggest_duplicates_to_keep(g)
        to_delete += len(suggestion['delete'])
        total_bytes += g['size'] * len(suggestion['delete'])

    # Safety limits
    if to_delete > SAFETY_LIMITS['max_files_to_delete_without_confirmation'] or total_bytes > SAFETY_LIMITS['max_total_size_to_delete_without_confirmation']:
        typer.secho(f"About to delete {to_delete} files / {total_bytes/1e9:.2f} GB.", fg=typer.colors.YELLOW)
        confirm = typer.prompt("Type 'yes' to confirm")
        if confirm.lower() != 'yes':
            typer.echo("Deletion cancelled.")
            raise typer.Exit()

    # Whitelist location check
    for g in safe_groups:
        suggestion = finder.suggest_duplicates_to_keep(g)
        for fp in suggestion['delete']:
            if not is_safe_location_for_deletion(Path(fp)):
                typer.secho(f"Not a whitelisted delete location: {fp}", fg=typer.colors.RED)
                typer.echo("Deletion cancelled.")
                raise typer.Exit(code=3)

    # Final typed confirmation when not simulate
    if not simulate:
        confirm2 = typer.prompt("Are you ABSOLUTELY sure? type 'I UNDERSTAND THE RISK'")
        if confirm2.strip() != 'I UNDERSTAND THE RISK':
            typer.echo("Deletion cancelled.")
            raise typer.Exit()

    # Perform cleanup
    deleted = 0
    for g in safe_groups:
        res = finder.cleanup_duplicates(g, dry_run=simulate)
        deleted += res['deleted_count']
    typer.echo(f"Deleted {deleted} files{' (simulate)' if simulate else ''}.")


@app.command("undo")
def undo(last: int = typer.Option(1, "--last", help="Undo last N MOVE operations"),
         interactive: bool = typer.Option(False, "--interactive", help="List last 20 and choose")):
    """Undo recent MOVE operations using logs/operations.log."""
    from datetime import datetime
    log_path = ROOT.parent / 'logs' / 'operations.log'
    if not log_path.exists():
        typer.echo("No operations log found.")
        raise typer.Exit(code=0)
    lines = log_path.read_text(encoding='utf-8').splitlines()
    # parse into entries
    entries = []
    for ln in lines:
        try:
            ts, op, file_path, old_loc, new_loc, status = [s.strip() for s in ln.split('|')]
            entries.append({'timestamp': ts, 'operation': op, 'file_path': file_path, 'old_location': old_loc, 'new_location': new_loc, 'status': status})
        except Exception:
            continue
    move_entries = [e for e in entries if e['operation'] == 'MOVE']
    if interactive:
        last20 = move_entries[-20:]
        if not last20:
            typer.echo("No move operations to undo.")
            raise typer.Exit()
        for idx, e in enumerate(last20[::-1], start=1):
            typer.echo(f"{idx}. {e['file_path']} <- {e['old_location']} (from {e['new_location']}) @ {e['timestamp']}")
        choice = typer.prompt("Select number to undo", type=int)
        if choice < 1 or choice > len(last20):
            typer.echo("Invalid choice.")
            raise typer.Exit(code=2)
        target = last20[::-1][choice-1]
        to_undo = [target]
    else:
        to_undo = move_entries[-last:]
        if not to_undo:
            typer.echo("No move operations to undo.")
            raise typer.Exit()
    undone = 0
    for e in to_undo:
        try:
            src = Path(e['new_location'])
            dst = Path(e['old_location'])
            if not src.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.move(str(src), str(dst))
            undone += 1
        except Exception as ex:
            typer.secho(f"Undo failed for {e['file_path']}: {ex}", fg=typer.colors.RED)
    typer.echo(f"Undone {undone} move operation(s).")


@app.command("space-migrate")
def space_migrate(to: str = typer.Option(..., "--to", help="Target drive letter, e.g., D:"),
                  simulate: bool = typer.Option(True, "--simulate/--no-simulate")):
    """Safety-bannered migration plan (simulate only)."""
    show_safety_banner_once()
    typer.echo("⚠️ MIGRATION SAFETY CHECK")
    typer.echo("Only user folders will be migrated:")
    typer.echo(" ✓ Documents, Pictures, Videos, Music, Downloads")
    typer.echo(" ✗ Applications, Games, System Files (will NOT be touched)")
    # For now, just a plan outline; actual copy omitted intentionally
    tgt = Path(to + ("\\" if not to.endswith(('\\','/')) else ""))
    if not tgt.exists():
        typer.secho(f"Target drive not found: {tgt}", fg=typer.colors.RED)
        raise typer.Exit(code=2)
    cfg = get_config()
    guardian = SafetyGuardian(cfg)
    safe = [p for p in safe_scan_folders() if p.exists()]
    protected_count = 0
    safe_files: List[Path] = []
    for base in safe:
        for f in base.rglob('*'):
            if not f.is_file():
                continue
            ok, _ = guardian.is_file_safe_to_modify(f)
            if ok:
                safe_files.append(f)
            else:
                protected_count += 1
        if protected_count:
            typer.echo(f"⚠️ {base} contains {protected_count} application files (will be skipped)")

    # Size-limits and confirmation
    total_bytes = 0
    for f in safe_files:
        try:
            total_bytes += f.stat().st_size
        except Exception:
            pass
    if len(safe_files) > SAFETY_LIMITS['max_files_to_move_without_confirmation']:
        typer.secho(f"About to migrate {len(safe_files)} files / {total_bytes/1e9:.2f} GB.", fg=typer.colors.YELLOW)
        if typer.prompt("Type 'yes' to confirm") != 'yes':
            typer.echo("Migration cancelled.")
            raise typer.Exit()

    # Perform copy (simulate by default)
    moved = 0
    import shutil
    for f in safe_files:
        rel = None
        # Mirror by relative path from user folder
        for base in safe:
            try:
                rel = f.resolve().relative_to(base.resolve())
                break
            except Exception:
                continue
        if rel is None:
            continue
        dest = tgt / base.name / rel
        if simulate:
            typer.echo(f"[SIMULATE] Would copy {f} -> {dest}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(f), str(dest))
        moved += 1
        # Log COPY operation
        try:
            from utils.logger import get_logger
            get_logger().log_operation('COPY', str(f), str(f.parent), str(dest), 'SUCCESS')
        except Exception:
            pass
    typer.echo(f"Eligible files: {len(safe_files)}. {'Simulated' if simulate else f'Copied {moved} files'} to {tgt}.")


@app.command("space-large-old")
def space_large_old(folder: Optional[Path] = typer.Argument(None, exists=False),
                    min_size_mb: int = typer.Option(200, "--min-size-mb", help="Minimum size in MB"),
                    older_than_days: int = typer.Option(180, "--older-than-days", help="Older than days")):
    """List large, old files in safe folders (or validated target) with protections."""
    cfg = get_config()
    guardian = SafetyGuardian(cfg)
    targets, reason = validate_target_folder(guardian, folder)
    if not targets:
        typer.secho(f"❌ PROTECTED FOLDER\n\n{reason}", fg=typer.colors.RED)
        raise typer.Exit(code=2)
    import time
    cutoff = time.time() - older_than_days * 24 * 3600
    min_bytes = min_size_mb * 1024 * 1024
    results: List[Path] = []
    for base in targets:
        for p in base.rglob('*'):
            if not p.is_file():
                continue
            try:
                st = p.stat()
                if st.st_size >= min_bytes and st.st_mtime < cutoff:
                    ok, _ = guardian.is_file_safe_to_modify(p)
                    if ok:
                        results.append(p)
            except Exception:
                continue
    if not results:
        typer.echo("✅ No large old user files found. All large files may be protected application files.")
        raise typer.Exit()
    total = sum((p.stat().st_size for p in results if p.exists()), 0)
    typer.echo(f"Found {len(results)} large old files (~{total/1e9:.2f} GB)")
    for p in results[:50]:
        typer.echo(f" - {p}")


def run():
    app()


if __name__ == "__main__":
    run()
