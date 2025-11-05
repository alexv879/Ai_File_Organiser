# AI File Organiser - Quick Start

**Copyright © 2025 Alexandru Emanuel Vasile. All Rights Reserved.**

## One Command to Do Everything

Just installed? Start here:

```bash
aifo space      # Free up space (most common)
aifo organize   # Organize Downloads
aifo find       # Find duplicates
```

---

## Common Scenarios

### "My C: drive is almost full!"

```bash
aifo space
```

Interactive menu guides you through:
1. Find and remove duplicates (SAFEST)
2. Find large old files
3. Analyze what's using space
4. Migrate to another drive

### "My Downloads is a mess!"

```bash
aifo organize
```

Organizes your Downloads folder automatically.

### "I have duplicate photos!"

```bash
aifo find
```

Shows duplicate files and wasted space.

---

## All Commands

### `aifo space` - Free Disk Space

**Purpose**: Free up space on C: drive

**Examples**:
```bash
aifo space                  # Interactive menu
aifo space --duplicates     # Find and remove duplicates
aifo space --large-old      # Find large old files (>100MB, 6+ months)
aifo space --analyze        # Show what's using space
aifo space --migrate D:     # Move files to D: drive
```

**What it does**:
- Finds duplicate files (safest way to free space)
- Finds large old files you might not need
- Analyzes C: drive usage
- Migrates files to another drive safely

### `aifo organize` - Organize Files

**Purpose**: Intelligently organize files into folders

**Examples**:
```bash
aifo organize               # Organize Downloads
aifo organize ~/Documents   # Organize specific folder
aifo organize --preview     # Preview changes first (dry run)
aifo organize --auto        # Auto-approve without confirmation
aifo organize --deep        # Deep AI analysis (slower, better)
```

**What it does**:
- Scans folder for files
- Classifies files by type and content
- Organizes into categories (Documents, Pictures, Videos, etc.)
- Shows preview before moving files

### `aifo find` - Find Duplicates

**Purpose**: Find and optionally delete duplicate files

**Examples**:
```bash
aifo find                   # Find duplicates in Downloads
aifo find ~/Pictures        # Find duplicates in Pictures
aifo find --delete          # Find and delete (keeps newest)
aifo find --min-size 10MB   # Only large files
```

**What it does**:
- Finds exact duplicate files (same content)
- Shows duplicate groups and space wasted
- Optionally deletes duplicates (keeps newest copy)
- Safe - requires confirmation before deleting

### `aifo scan` - Quick Inventory

**Purpose**: Scan folder and show what's inside

**Examples**:
```bash
aifo scan                   # Scan Downloads
aifo scan ~/Documents       # Scan specific folder
aifo scan --detailed        # Detailed breakdown by file type
```

**What it does**:
- Counts files and calculates total size
- Shows file type breakdown
- Helps you understand what you have

### `aifo stats` - Show Statistics

**Purpose**: View organization progress

**Example**:
```bash
aifo stats                  # Show all-time statistics
```

**What it shows**:
- Files organized
- Space saved
- Top categories
- Last organization date

### `aifo ask` - Natural Language

**Purpose**: Ask what you want in plain English

**Examples**:
```bash
aifo ask "I need to free up space on C drive"
aifo ask "organize my photos"
aifo ask "find duplicate files"
```

**What it does**:
- Understands your intent
- Suggests 3-4 relevant actions
- Shows commands to run
- Explains what each action does

---

## Safety Features

### 1. Preview First (Dry Run Default)
```bash
aifo organize --preview     # See plan before executing
```

### 2. Confirmation Required
All destructive actions ask for confirmation:
```
Delete 45 duplicate files (2.3 GB)?
[y/N]:
```

### 3. Keeps Newest
When deleting duplicates, always keeps the newest file:
```
Keeping: photo.jpg (modified 2024-11-01)
Deleting: photo_copy.jpg (modified 2024-10-15)
```

### 4. System Files Protected
Never touches:
- Windows system folders
- Program Files
- AppData (except Downloads)

### 5. Undo Available
Database tracks all operations (future feature).

---

## Installation

### Windows
```cmd
install.bat
```

### Linux/macOS
```bash
chmod +x install.sh
./install.sh
```

**That's it!** The installer handles everything.

---

## First-Time Setup

### 1. Install (5-10 minutes)
Run installer - it sets up:
- Python dependencies
- Ollama (local AI)
- AI model (deepseek-r1:1.5b)
- MCP integration (optional)

### 2. Verify Installation
```bash
aifo --help
```

You should see the command list.

### 3. Test with Scan
```bash
aifo scan
```

Quick, safe way to test.

---

## Real-World Examples

### Example 1: Free Up 5GB on C: Drive

**Scenario**: C: drive is 95% full, need space urgently

**Solution**:
```bash
aifo space --duplicates
```

**Result**:
```
Found 127 duplicate files
Space wasted: 5.2 GB

Delete duplicates? [y/N]: y

✅ Deleted 127 files
💾 Freed 5.2 GB
```

**Time**: 2-3 minutes

### Example 2: Organize Messy Downloads

**Scenario**: Downloads folder has 500+ files, total chaos

**Solution**:
```bash
aifo organize --preview
```

**Preview**:
```
📊 Organization Plan:

Documents/ (45 files)
  invoice_2024.pdf
  report.docx
  ... and 43 more

Pictures/ (89 files)
  IMG_001.jpg
  photo.png
  ... and 87 more

Videos/ (23 files)
  ...

Proceed? [Y/n]: y
```

**Result**:
```
✅ Organized 500 files into 15 folders
```

**Time**: 5-10 minutes (depending on file count)

### Example 3: Find Duplicate Photos

**Scenario**: Camera uploaded same photos multiple times

**Solution**:
```bash
aifo find ~/Pictures --delete
```

**Result**:
```
Found 45 duplicate photos
Space wasted: 892 MB

Duplicate groups:
1. IMG_001.jpg (4 copies)
2. IMG_002.jpg (3 copies)
...

Delete duplicates (keeps newest)? [y/N]: y

✅ Deleted 45 duplicate photos
💾 Freed 892 MB
```

**Time**: 3-5 minutes

### Example 4: Prepare for Backup

**Scenario**: Want to backup important files, but exclude junk

**Solution**:
```bash
# Step 1: Find duplicates (no need to backup duplicates)
aifo find --delete

# Step 2: Scan to see what's left
aifo scan ~/Documents --detailed

# Step 3: Organize to clean structure
aifo organize ~/Documents
```

**Result**: Clean, deduplicated file structure ready for backup

---

## Tips & Tricks

### Tip 1: Always Preview First

For new commands, use `--preview` or `-p`:
```bash
aifo organize -p     # See what will happen
```

### Tip 2: Start with Duplicates

Safest way to free space:
```bash
aifo space --duplicates
```

Duplicates are guaranteed safe to delete (keeps newest copy).

### Tip 3: Use `--auto` for Batch Operations

Skip confirmations when you trust the operation:
```bash
aifo organize --auto
```

### Tip 4: Check Stats Regularly

See your progress:
```bash
aifo stats
```

### Tip 5: Natural Language When Unsure

Not sure which command?
```bash
aifo ask "what you want to do"
```

### Tip 6: Combine Commands

For thorough cleanup:
```bash
aifo space --duplicates     # Remove duplicates
aifo space --large-old      # Review large old files
aifo organize               # Organize remaining files
```

---

## Troubleshooting

### "Command not found: aifo"

**Solution**: Run installer again
```bash
python install.bat    # Windows
./install.sh         # Linux/macOS
```

### "Ollama not running"

**Solution**: Start Ollama
```bash
# Windows: Should start automatically
# Linux/macOS:
ollama serve
```

### "Permission denied"

**Solution**: Run with appropriate permissions
```bash
# Windows: Run as Administrator
# Linux/macOS:
sudo aifo space --migrate /media/external
```

### "Files not organizing correctly"

**Solution**: Use deep analysis
```bash
aifo organize --deep
```

Slower but more accurate.

### "Can't delete files"

**Solution**: Check if files are in use
- Close programs using the files
- Try again

---

## Command Cheat Sheet

| Command | Purpose | Quick Example |
|---------|---------|---------------|
| `aifo space` | Free disk space | `aifo space --duplicates` |
| `aifo organize` | Organize files | `aifo organize -p` |
| `aifo find` | Find duplicates | `aifo find -d` |
| `aifo scan` | Quick inventory | `aifo scan -d` |
| `aifo stats` | Show progress | `aifo stats` |
| `aifo ask` | Natural language | `aifo ask "free space"` |

---

## Common Flags

| Flag | Purpose | Example |
|------|---------|---------|
| `-p`, `--preview` | Preview without executing | `aifo organize -p` |
| `-a`, `--auto` | Auto-approve | `aifo organize -a` |
| `-d`, `--deep` | Deep AI analysis | `aifo organize -d` |
| `-d`, `--delete` | Delete duplicates | `aifo find -d` |
| `-s`, `--min-size` | Minimum file size | `aifo find -s 10MB` |
| `-l`, `--large-old` | Large old files | `aifo space -l` |
| `-m`, `--migrate` | Migrate to drive | `aifo space -m D:` |

---

## Next Steps

After getting comfortable with basics:

1. **Read Full Guide**: [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md)
2. **Try MCP Integration**: "Claude, organize my files"
3. **Customize Settings**: Edit configuration files
4. **Explore Dashboard**: Web UI at http://localhost:5000

---

## Getting Help

### Documentation
- **This guide**: QUICK_START.md
- **Full guide**: docs/MCP_INTEGRATION.md
- **Installation**: INSTALLATION_GUIDE.md

### Command Help
```bash
aifo --help              # General help
aifo COMMAND --help      # Specific command help
```

### Support
- **GitHub**: https://github.com/alexv879/Ai_File_Organiser
- **Issues**: Report bugs on GitHub
- **Contact**: Alexandru Emanuel Vasile

---

## Summary

**Three commands cover 90% of use cases:**

```bash
aifo space      # Free up disk space
aifo organize   # Organize files
aifo find       # Find duplicates
```

**Start with the safest:**
```bash
aifo space --duplicates
```

**When unsure:**
```bash
aifo ask "what you want"
```

---

**You're ready to organize!** 🚀

---

**Copyright © 2025 Alexandru Emanuel Vasile. All Rights Reserved.**
