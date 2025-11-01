# Multi-Drive Storage & Advanced Metadata

**Copyright © 2025 Alexandru Emanuel Vasile. All Rights Reserved.**  
**Proprietary Software - 200-Key Limited Release License**

## Overview

AI File Organiser now includes **intelligent multi-drive storage management** and **advanced metadata extraction** to organize files even more effectively. These features help you:

- **Optimize storage** across multiple drives (C:, D:, E:, etc.)
- **Extract rich metadata** from images, PDFs, videos, audio, and documents
- **Make smarter decisions** based on file content, not just names
- **Prevent drive space issues** with intelligent space checking
- **Organize by location, author, date taken, and more**

---

## Multi-Drive Storage Management

### Features

✅ **Automatic Drive Detection**: Scans all available drives (A-Z)  
✅ **Space Monitoring**: Real-time free space tracking  
✅ **Intelligent Selection**: Chooses optimal drive based on strategy  
✅ **Multiple Strategies**: Same drive, most space, balanced, user choice  
✅ **Archive Separation**: Dedicated drive for old files  
✅ **Space Warnings**: Alerts when drives are running low  

### Storage Strategies

#### 1. **SAME_DRIVE** (Default)
Keeps files on their current drive if sufficient space available.

```json
{
  "storage_strategy": "same_drive",
  "min_free_space_gb": 10
}
```

**Use When**:
- You want minimal file movement
- Current drive has plenty of space
- Files are already organized by drive

**Example**:
```
C:\Downloads\invoice.pdf → C:\Finance\Invoices\2025\March\invoice.pdf
(Stays on C: drive)
```

#### 2. **MOST_SPACE**
Automatically selects drive with most available space.

```json
{
  "storage_strategy": "most_space",
  "min_free_space_gb": 20
}
```

**Use When**:
- System drive (C:) is getting full
- You have multiple data drives
- Want to balance storage automatically

**Example**:
```
C:\Downloads\large_video.mp4 → D:\Videos\Personal\2025\large_video.mp4
(Moved to D: which has 500GB free vs C: with 50GB free)
```

#### 3. **BALANCED**
Distributes files evenly across drives to maintain ~50% usage on each.

```json
{
  "storage_strategy": "balanced",
  "min_free_space_gb": 10
}
```

**Use When**:
- You have multiple drives of similar size
- Want even wear/usage across drives
- Prefer organized distribution

**Example**:
```
Drive C: 60% full → Files go to D: (40% full)
Drive D: 55% full → Files go to E: (35% full)
```

#### 4. **USER_CHOICE**
User specifies preferred drive for organization.

```json
{
  "storage_strategy": "user_choice",
  "preferred_drive": "D",
  "min_free_space_gb": 10
}
```

**Use When**:
- You have a dedicated data drive
- Want all user files on specific drive
- Clear preference for drive organization

**Example**:
```
All files → D:\[organized structure]
(Unless D: is full, then falls back to most_space)
```

#### 5. **ARCHIVE_SEPARATE**
Old files (>1 year) go to separate archive drive.

```json
{
  "storage_strategy": "archive_separate",
  "preferred_drive": "D",
  "archive_drive": "E",
  "min_free_space_gb": 10
}
```

**Use When**:
- You have a dedicated archive/backup drive
- Want to separate active vs historical files
- Need to keep system drive fast

**Example**:
```
Active files: D:\Documents\2025\...
Old files: E:\Archives\2024\...
```

### Configuration Example

```python
# config.json
{
  "storage": {
    "strategy": "most_space",           # or: same_drive, balanced, user_choice, archive_separate
    "preferred_drive": "D",             # Optional: preferred drive letter
    "archive_drive": "E",               # Optional: drive for old files
    "min_free_space_gb": 10,           # Minimum free space to consider drive viable
    "check_space_before_move": true,   # Verify space before operations
    "warn_threshold_gb": 20             # Warn when drive has less than this
  }
}
```

### Storage Summary

The system provides real-time storage visualization:

```
======================================================================
STORAGE SUMMARY
======================================================================

Drive C: (system)
  [████████████████████████░░░░░░░░░░░░░░░░] 60.5% used
  Total: 476.9GB  |  Used: 288.6GB  |  Free: 188.3GB

Drive D: (data)
  [██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 25.3% used
  Total: 931.5GB  |  Used: 235.7GB  |  Free: 695.8GB

Drive E: (data)
  [████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 10.2% used
  Total: 1863.0GB  |  Used: 190.0GB  |  Free: 1673.0GB

======================================================================
Storage Strategy: most_space
Preferred Drive: D:
Archive Drive: E:
======================================================================
```

### Benefits by Drive Type

#### **System Drive (C:)**
- ✅ Automatically avoided for user files when alternatives exist
- ✅ System performance maintained
- ✅ Warnings when <20GB free
- ✅ Critical alerts when <10GB free

#### **Data Drives (D:, E:, etc.)**
- ✅ Optimal for user file organization
- ✅ Large video/media files automatically placed here
- ✅ Balanced distribution prevents any single drive from filling
- ✅ Flexible strategies adapt to available space

#### **External/Network Drives**
- ✅ Detected and can be used for archives
- ✅ Slower drives used for cold storage
- ✅ Automatic backup locations

---

## Advanced Metadata Extraction

### Why Metadata Matters

Instead of organizing solely by **filename**, we extract **rich metadata** from files:

| File Type | Basic Info | **+ Metadata** | **Organization Improvement** |
|-----------|------------|----------------|------------------------------|
| **Image** | Extension | **Date taken, GPS location, camera** | Organize by event date, not file date |
| **PDF** | Size | **Author, subject, keywords** | Categorize by author or subject |
| **Audio** | Extension | **Artist, album, genre, year** | Music library organization |
| **Video** | Size | **Resolution, duration** | Separate 4K, HD, SD content |
| **Document** | Extension | **Author, company, keywords** | Organize by project/author |

### Extracted Metadata by Type

#### **Images (JPG, PNG, etc.)**
```python
{
  'dimensions': '4032x3024',
  'format': 'JPEG',
  'date_taken': datetime(2025, 3, 15, 14, 30, 0),  # EXIF date
  'camera_make': 'Canon',
  'camera_model': 'EOS 5D Mark IV',
  'gps': {
    'GPSLatitude': (40, 45, 12.5),
    'GPSLongitude': (-73, 58, 45.2)
  },
  'has_location': True,
  'organization_hints': {
    'date_based': True,
    'suggested_date_folder': '2025/March',
    'location_based': True
  }
}
```

**Organization Impact**:
```
Instead of:   Photos/IMG_20250315_143000.jpg
You get:      Photos/Events/2025/March/Family-Gathering/IMG_20250315_143000.jpg
              (Based on EXIF date taken, not file date)
```

#### **PDFs**
```python
{
  'pages': 15,
  'title': 'Q1 2025 Financial Report',
  'author': 'John Smith',
  'subject': 'Quarterly Financial Analysis',
  'keywords': 'finance, report, Q1, 2025',
  'creation_date': datetime(2025, 3, 28),
  'detected_type': 'report',  # From content analysis
  'organization_hints': {
    'type_detected': 'report',
    'author_based': True,
    'suggested_author_folder': 'Author-John-Smith'
  }
}
```

**Organization Impact**:
```
Instead of:   Documents/report.pdf
You get:      Work/Reports/2025/Q1/Financial/report.pdf
              (Based on PDF metadata and content detection)
```

#### **Audio Files (MP3, FLAC, etc.)**
```python
{
  'duration_seconds': 245,
  'duration_formatted': '04:05',
  'bitrate': 320000,
  'sample_rate': 44100,
  'artist': 'The Beatles',
  'album': 'Abbey Road',
  'title': 'Come Together',
  'genre': 'Rock',
  'date': '1969',
  'organization_hints': {
    'music_organization': True,
    'suggested_path': 'Music/The Beatles/Abbey Road',
    'genre_based': True
  }
}
```

**Organization Impact**:
```
Instead of:   Music/song.mp3
You get:      Music/The Beatles/Abbey Road/01 - Come Together.mp3
              (Perfect iTunes-style organization)
```

#### **Videos (MP4, AVI, etc.)**
```python
{
  'duration_seconds': 3620,
  'duration_formatted': '01:00:20',
  'resolution': '3840x2160',
  'fps': 60,
  'bitrate': 50000000,
  'organization_hints': {
    'resolution_based': True,
    'quality_folder': '4K-Ultra-HD',
    'duration_category': 'Long-Videos'
  }
}
```

**Organization Impact**:
```
Instead of:   Videos/vid.mp4
You get:      Videos/Personal/2025/4K-Ultra-HD/Long-Videos/vid.mp4
              (Organized by quality and length)
```

#### **Office Documents (DOCX, etc.)**
```python
{
  'title': 'Project Alpha Proposal',
  'author': 'Jane Doe',
  'category': 'Business Proposal',
  'keywords': 'project, alpha, proposal, 2025',
  'last_modified_by': 'John Smith',
  'created': datetime(2025, 1, 15),
  'modified': datetime(2025, 3, 20),
  'organization_hints': {
    'author_based': True,
    'category_based': True,
    'suggested_category': 'Business Proposal'
  }
}
```

**Organization Impact**:
```
Instead of:   Documents/doc.docx
You get:      Work/Projects/2025/Project-Alpha/Proposals/doc.docx
              (Based on document properties)
```

### Organization Hints System

The metadata extractor generates **intelligent hints** for better organization:

```python
organization_hints = {
  # Date-based
  'date_based': True,
  'suggested_date_folder': '2025/March',
  
  # Location-based (from GPS)
  'location_based': True,
  'has_location': True,
  
  # Author-based
  'author_based': True,
  'suggested_author_folder': 'Author-John-Smith',
  
  # Type detection
  'type_detected': 'invoice',
  'confidence': 'high',
  
  # Archive candidate
  'is_old': True,
  'archive_candidate': True,
  'suggested_archive_year': 2023,
  
  # Quality-based (videos)
  'resolution_based': True,
  'quality_folder': '4K-Ultra-HD',
  
  # Duration-based
  'duration_category': 'Long-Videos',
  
  # Music organization
  'music_organization': True,
  'suggested_path': 'Music/Artist/Album'
}
```

### Real-World Examples

#### Example 1: Vacation Photos

**File**: `IMG_4523.jpg` (generic camera name)

**Extracted Metadata**:
```python
{
  'date_taken': datetime(2025, 7, 15, 10, 30),  # From EXIF
  'gps': {'lat': 41.8902, 'lon': 12.4922},      # Rome, Italy
  'camera_make': 'Apple',
  'camera_model': 'iPhone 14 Pro'
}
```

**Organization Result**:
```
Photos/Travel/2025/July/Italy-Rome/IMG_4523.jpg
(Detected date and location from EXIF, not filename)
```

#### Example 2: Invoice PDF

**File**: `scan_002.pdf` (generic scanner name)

**Extracted Metadata**:
```python
{
  'detected_type': 'invoice',           # From content analysis
  'creation_date': datetime(2025, 3, 15),
  'first_page_preview': 'INVOICE\nClient: Acme Corp\nDate: 03/15/2025...'
}
```

**Organization Result**:
```
Finance/Invoices/2025/March/Client-Acme/scan_002.pdf
(Detected invoice type and client from content)
```

#### Example 3: Music Library

**File**: `track03.mp3` (no useful filename)

**Extracted Metadata**:
```python
{
  'artist': 'Pink Floyd',
  'album': 'The Dark Side of the Moon',
  'title': 'Time',
  'date': '1973',
  'genre': 'Progressive Rock'
}
```

**Organization Result**:
```
Music/Pink Floyd/The Dark Side of the Moon/03 - Time.mp3
(Perfect library organization from ID3 tags)
```

---

## Combined Intelligence

### Multi-Drive + Metadata = Smart Organization

The system combines **storage management** and **metadata extraction** for optimal results:

```python
# Example: Large 4K video file

File: vacation_clip.mp4 (8GB)

Step 1: Extract Metadata
  → Resolution: 3840x2160 (4K)
  → Duration: 15 minutes
  → Date: 2025-07-15

Step 2: Select Drive
  → C: has 50GB free (system drive, avoid)
  → D: has 200GB free (good)
  → E: has 1TB free (best for large files)
  → Selected: E: (most space strategy)

Step 3: Generate Hierarchy
  → Primary: Videos
  → Secondary: Personal
  → Tertiary: 2025
  → Quaternary: 4K-Ultra-HD

Final Result:
E:\Videos\Personal\2025\4K-Ultra-HD\Italy-Vacation\vacation_clip.mp4

Benefits:
✅ Not on system drive (C:)
✅ On drive with plenty of space (E:)
✅ Organized by quality (4K)
✅ Organized by date (2025)
✅ Easy to find and browse
```

### Intelligent Archive Management

**Scenario**: Mixed collection of old and new files

```python
Files to organize:
- recent_report.pdf (2025, 2MB) → D:\Work\Reports\2025\Q1\
- old_project.zip (2022, 500MB) → E:\Archives\2022\Projects\
- family_photo.jpg (2025, 5MB) → D:\Photos\Family\2025\
- backup_2020.tar (2020, 5GB) → E:\Archives\2020\Backups\

Strategy: archive_separate
D: = Active files (fast access)
E: = Archives (cold storage)

Result:
✅ D: drive stays fast and organized (recent files only)
✅ E: drive holds historical data (old files)
✅ System automatically separates by age
✅ Archive drive used for large old files
```

---

## Installation

### Required Dependencies

```bash
pip install Pillow          # Image EXIF extraction
pip install PyPDF2          # PDF metadata
pip install mutagen         # Audio/video metadata
pip install python-docx     # Office document properties
```

Or install all at once:

```bash
pip install -r requirements.txt
```

### Verify Installation

```python
from src.core.storage_manager import StorageManager
from src.core.metadata_extractor import AdvancedMetadataExtractor

# Check storage
storage = StorageManager()
print(storage.format_storage_summary())

# Check metadata extraction
extractor = AdvancedMetadataExtractor()
print(f"Supported: {', '.join(extractor.supported_types)}")
```

Expected output:
```
======================================================================
STORAGE SUMMARY
======================================================================
Drive C: (system) ...
Drive D: (data) ...
...
Supported: basic, images, pdf, audio, video, docx
```

---

## Configuration

### Full Configuration Example

```json
{
  "storage": {
    "strategy": "most_space",
    "preferred_drive": "D",
    "archive_drive": "E",
    "min_free_space_gb": 10,
    "check_space_before_move": true,
    "warn_threshold_gb": 20
  },
  
  "metadata": {
    "extract_exif": true,
    "extract_gps": true,
    "extract_pdf_metadata": true,
    "extract_audio_tags": true,
    "extract_video_info": true,
    "extract_document_properties": true,
    "use_hints_for_organization": true
  },
  
  "hierarchy": {
    "max_depth": 4,
    "preferred_depth": 3,
    "use_temporal_organization": true,
    "temporal_pattern": "monthly",
    "use_metadata_hints": true
  }
}
```

---

## Benefits Summary

### Multi-Drive Storage
✅ **Prevent system drive slowdown** - Keep C: fast  
✅ **Optimize space usage** - Use drives efficiently  
✅ **Automatic drive selection** - No manual decisions  
✅ **Archive separation** - Old files to cold storage  
✅ **Space warnings** - Never run out unexpectedly  

### Advanced Metadata
✅ **Accurate dating** - Use EXIF date, not file date  
✅ **Content-aware** - Detect document types  
✅ **Music library** - Perfect iTunes-style organization  
✅ **Location-based** - GPS from photos  
✅ **Quality sorting** - Separate 4K, HD, SD  
✅ **Author tracking** - Organize by creator  

### Combined Power
✅ **Intelligent placement** - Right files, right drives  
✅ **Meaningful hierarchies** - Context-aware folders  
✅ **Future-proof** - Scales with storage needs  
✅ **Time-saving** - Fully automated decisions  
✅ **Professional** - Enterprise-grade organization  

---

## Comparison: Before vs After

### Before (Basic Organization)
```
C:\Downloads\
├── IMG_4523.jpg (no idea what this is)
├── scan_002.pdf (generic scanner name)
├── track03.mp3 (no context)
└── vacation_clip.mp4 (8GB eating C: drive space)

Problems:
❌ System drive filling up
❌ Generic filenames
❌ No organization
❌ Hard to find anything
```

### After (Multi-Drive + Metadata)
```
D:\
├── Photos\
│   └── Travel\
│       └── 2025\
│           └── July\
│               └── Italy-Rome\
│                   └── IMG_4523.jpg (EXIF: date + GPS)
│
├── Finance\
│   └── Invoices\
│       └── 2025\
│           └── March\
│               └── Client-Acme\
│                   └── scan_002.pdf (Content: detected invoice)
│
└── Music\
    └── Pink Floyd\
        └── The Dark Side of the Moon\
            └── 03 - Time.mp3 (ID3: artist + album)

E:\
└── Videos\
    └── Personal\
        └── 2025\
            └── 4K-Ultra-HD\
                └── Italy-Vacation\
                    └── vacation_clip.mp4 (8GB on spacious drive)

Benefits:
✅ C: drive fast and clean
✅ Meaningful file locations
✅ Perfect organization
✅ Instantly findable
✅ Metadata-driven hierarchy
```

---

**© 2025 Alexandru Emanuel Vasile - All Rights Reserved**  
**Proprietary Software - 200-Key Limited Release License**
