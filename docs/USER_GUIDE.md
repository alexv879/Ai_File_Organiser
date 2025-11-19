# AI File Organizer - Complete User Guide

Your comprehensive guide to using AI File Organizer for intelligent file management.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Desktop Application](#desktop-application)
3. [Web Application](#web-application)
4. [AI Models](#ai-models)
5. [Cloud Storage](#cloud-storage)
6. [Organization Features](#organization-features)
7. [Pricing & Plans](#pricing--plans)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Getting Started

### What is AI File Organizer?

AI File Organizer uses advanced artificial intelligence to automatically categorize, rename, and organize your files. It supports multiple AI models (GPT-4, Claude, Ollama) and integrates with popular cloud storage services.

### Key Features

- 🤖 **Multi-Model AI**: Intelligent selection between GPT-4, Claude, and local Ollama
- 📁 **Smart Organization**: Automatic categorization and file naming
- ☁️ **Cloud Integration**: OneDrive, Google Drive, Dropbox support
- 💻 **Desktop & Web**: Use locally or access from anywhere
- 🔒 **Privacy First**: Local-only option available (FREE tier)
- 💰 **Flexible Pricing**: Free tier available, paid plans start at $5/month

### Quick Start

1. **Choose Your Platform:**
   - Desktop app (Windows, macOS, Linux) - Best for local files
   - Web app (any browser) - Best for cloud access

2. **Select Your Plan:**
   - FREE - Local AI only, desktop app
   - STARTER ($5/mo) - Fast cloud AI, web access
   - PRO ($12/mo) - Advanced AI, all features
   - ENTERPRISE (custom) - Team features, API access

3. **Start Organizing:**
   - Select a folder
   - Let AI analyze and categorize
   - Review suggestions
   - Organize with one click

---

## Desktop Application

### Installation

#### Windows
1. Download `AI-File-Organizer-Setup.exe` from [releases page]
2. Run the installer
3. Follow installation wizard
4. Launch from Start Menu

#### macOS
1. Download `AI-File-Organizer.dmg` from [releases page]
2. Open DMG file
3. Drag app to Applications folder
4. Right-click and select "Open" (first time only)

#### Linux
1. Download `.AppImage` or `.deb` from [releases page]
2. For AppImage: `chmod +x AI-File-Organizer.AppImage && ./AI-File-Organizer.AppImage`
3. For Debian/Ubuntu: `sudo dpkg -i ai-file-organizer.deb`

### Basic Usage

#### 1. Select a Folder

Click **"Choose Folder"** button and navigate to the folder you want to organize.

Recommended folders:
- Downloads
- Documents
- Desktop
- Pictures

#### 2. Configure AI Settings

Navigate to **Settings** tab:

- **Use Multi-Model AI**: Toggle on for intelligent model selection
- **Subscription Tier**: Select your plan (FREE, STARTER, PRO, ENTERPRISE)

**Model Selection Logic:**
- Simple files (images, videos) → Fastest available model
- Medium complexity → Balanced model (GPT-3.5, Claude Haiku)
- Complex files (documents, code) → Advanced model (GPT-4, Claude Sonnet)

#### 3. Organize Files

1. Click **"Organize Now"** button
2. AI analyzes each file:
   - Reads file name
   - Analyzes content (for text files)
   - Extracts metadata
   - Determines category
3. Review suggestions in file list
4. Files are automatically organized into categorized folders

### Classification Details

Each file receives:
- **Category**: Primary classification (Documents, Photos, Code, etc.)
- **Subcategory**: Specific type (Contracts, Family Photos, etc.)
- **Confidence**: How certain the AI is (0-100%)
- **Suggested Path**: Recommended folder structure
- **Tags**: Descriptive keywords
- **Summary**: Brief content description (for documents)

### Keyboard Shortcuts

- `Ctrl/Cmd + O` - Open folder
- `Ctrl/Cmd + R` - Refresh file list
- `Ctrl/Cmd + ,` - Open settings
- `Ctrl/Cmd + Q` - Quit application

---

## Web Application

### Sign Up

1. Visit https://app.aifileorganizer.com
2. Click **"Get Started"**
3. Sign up with:
   - Email address
   - Google account
   - Microsoft account

### Dashboard Overview

#### Main Sections:

1. **Inbox**: Newly uploaded files awaiting classification
2. **Organized**: Files already categorized
3. **Analytics**: Usage statistics and AI costs
4. **Settings**: Account and AI configuration

### Uploading Files

#### Drag & Drop:
1. Drag files from your computer
2. Drop onto upload area
3. Files automatically queue for classification

#### File Browser:
1. Click **"Upload Files"** button
2. Select files from dialog
3. Click "Open"

**Supported Formats:**
- Documents: PDF, DOCX, TXT, MD
- Images: JPG, PNG, GIF, SVG
- Videos: MP4, AVI, MOV
- Audio: MP3, WAV, FLAC
- Archives: ZIP, RAR, 7Z
- Code: PY, JS, TS, JAVA, CPP, etc.

**File Size Limits:**
- FREE: 10 MB per file
- STARTER: 50 MB per file
- PRO: 200 MB per file
- ENTERPRISE: 1 GB per file

### Organizing Files

1. **Auto-Organize**: AI automatically categorizes on upload
2. **Manual Review**: Review and approve suggestions
3. **Batch Operations**: Organize multiple files at once
4. **Custom Rules**: Create your own organization rules

### Cloud Storage Integration

Connect your cloud accounts for seamless organization:

#### OneDrive
1. Go to Settings → Cloud Storage
2. Click "Connect OneDrive"
3. Sign in with Microsoft account
4. Grant permissions
5. Files from OneDrive appear in dashboard

#### Google Drive
1. Go to Settings → Cloud Storage
2. Click "Connect Google Drive"
3. Sign in with Google account
4. Grant permissions
5. Access Drive files from dashboard

#### Dropbox
1. Go to Settings → Cloud Storage
2. Click "Connect Dropbox"
3. Sign in with Dropbox account
4. Grant permissions
5. Dropbox files available for organization

---

## AI Models

### Model Overview

AI File Organizer supports three types of AI models:

#### 1. Ollama (Local Models)
- **Availability**: FREE tier
- **Models**: Qwen2.5, Llama 3, Phi-3
- **Cost**: Free (runs on your computer)
- **Speed**: Fast (no network delay)
- **Privacy**: 100% local, data never leaves your device
- **Accuracy**: Good for most files

**Best for:**
- Privacy-conscious users
- Simple file organization
- Offline usage
- No API costs

#### 2. OpenAI GPT Models
- **Availability**: STARTER, PRO tiers
- **Models**:
  - GPT-3.5 Turbo (STARTER) - Fast, economical
  - GPT-4 Turbo (PRO) - Most accurate, best for complex files
- **Cost**: ~$0.0005-0.01 per file
- **Speed**: 500-2000ms per file
- **Accuracy**: Excellent

**Best for:**
- Complex documents
- Code files
- Detailed metadata extraction
- Professional use

#### 3. Anthropic Claude Models
- **Availability**: STARTER, PRO tiers
- **Models**:
  - Claude 3 Haiku (STARTER) - Fast, affordable
  - Claude 3.5 Sonnet (PRO) - Advanced reasoning
- **Cost**: ~$0.0003-0.003 per file
- **Speed**: 500-2000ms per file
- **Accuracy**: Excellent

**Best for:**
- Legal documents
- Technical specifications
- Detailed analysis
- Long documents (200K context)

### Intelligent Model Selection

AI File Organizer automatically chooses the best model based on:

1. **File Complexity**:
   - SIMPLE: Images, videos, archives → Fastest model
   - MEDIUM: Basic documents → Balanced model
   - COMPLEX: Legal docs, code, specifications → Advanced model

2. **User Tier**:
   - FREE: Always uses Ollama (local)
   - STARTER: GPT-3.5, Claude Haiku, or local
   - PRO: GPT-4, Claude Sonnet, with fallbacks
   - ENTERPRISE: Custom models + all above

3. **Cost Optimization**:
   - Prefers local models when accuracy is sufficient
   - Uses cloud models only when needed
   - Tracks and reports costs per file

### Cost Tracking

View your AI usage costs:
- **Desktop App**: See cost after organization completes
- **Web App**: Analytics → AI Usage → Cost breakdown

**Average Costs:**
- Simple file (local): $0.000
- Medium file (GPT-3.5): $0.001
- Complex file (GPT-4): $0.010
- Per 1000 files: $2-10 depending on complexity

---

## Cloud Storage

### Setting Up OneDrive

See detailed guide: [ONEDRIVE_SETUP_GUIDE.md](./ONEDRIVE_SETUP_GUIDE.md)

**Quick Steps:**
1. Register app in Azure Portal
2. Configure OAuth 2.0
3. Set redirect URI
4. Copy credentials to `.env`
5. Test connection

### Setting Up Google Drive

1. **Create Project** in Google Cloud Console
2. **Enable** Google Drive API
3. **Configure** OAuth consent screen
4. **Create** OAuth 2.0 credentials
5. **Download** credentials JSON
6. **Add to** environment variables

### Setting Up Dropbox

1. **Create App** at https://www.dropbox.com/developers/apps
2. Choose **Scoped Access** (recommended)
3. Set permissions:
   - files.metadata.read
   - files.content.read
   - files.content.write
4. **Copy** App key and App secret
5. **Configure** redirect URI
6. **Add to** environment variables

### Syncing Files

#### Auto-Sync (PRO tier)
- Monitors cloud folders
- Auto-organizes new files
- Keeps cloud storage organized

#### Manual Sync
- Import files from cloud
- Organize locally
- Upload back to cloud

---

## Organization Features

### Categories

Default categories:
- **Documents**: Contracts, reports, letters, invoices
- **Photos**: Personal, family, professional, screenshots
- **Videos**: Recordings, movies, tutorials
- **Music**: Albums, singles, playlists
- **Code**: Source files, projects, scripts
- **Archives**: Compressed files, backups
- **Spreadsheets**: Excel, CSV, data files
- **Presentations**: PowerPoint, Keynote, slides

### Naming Conventions

AI suggests better file names:
- `document (1).pdf` → `Q4_2024_Financial_Report.pdf`
- `IMG_1234.jpg` → `Family_Vacation_Beach_2024.jpg`
- `file.txt` → `Project_Notes_Meeting_2024_01_15.txt`

### Folder Structure

AI creates logical folder hierarchies:

```
Documents/
├── Work/
│   ├── Contracts/
│   │   └── 2024/
│   └── Reports/
│       └── Q4_2024/
├── Personal/
│   ├── Finance/
│   └── Medical/
└── Projects/
    └── AI_File_Organizer/
```

### Custom Rules

Create your own organization rules:

1. **Pattern Matching**: "Move all files with 'invoice' to Finance"
2. **Date-Based**: "Organize by year and month"
3. **Size-Based**: "Move files >100MB to Archives"
4. **Extension-Based**: "All .py files to Code/Python"

---

## Pricing & Plans

### FREE Tier

**$0/month**

✓ Desktop application
✓ Local AI models (Ollama)
✓ Unlimited files
✓ Basic organization
✓ No credit card required

**Limitations:**
- No web access
- Local models only
- No cloud storage sync
- No team features

**Best for:**
- Individual users
- Privacy-focused users
- Offline usage
- Testing the software

### STARTER Tier

**$5/month** (billed annually: $50/year, save $10)

✓ Everything in FREE
✓ Web application access
✓ GPT-3.5 Turbo
✓ Claude 3 Haiku
✓ Cloud storage integration (OneDrive, Google Drive, Dropbox)
✓ 1 GB cloud storage included
✓ Email support

**Limitations:**
- No advanced AI models
- Single user only
- Standard processing speed

**Best for:**
- Individuals needing cloud access
- Light business use
- Budget-conscious users

### PRO Tier

**$12/month** (billed annually: $120/year, save $24)

✓ Everything in STARTER
✓ GPT-4 Turbo
✓ Claude 3.5 Sonnet
✓ Priority processing
✓ 10 GB cloud storage
✓ Advanced analytics
✓ API access
✓ Priority support
✓ Custom categories
✓ Webhook integrations

**Best for:**
- Professional users
- Businesses
- Power users with complex needs
- Those needing best accuracy

### ENTERPRISE Tier

**Custom pricing**

✓ Everything in PRO
✓ Custom fine-tuned models
✓ Team collaboration (unlimited users)
✓ Unlimited cloud storage
✓ SSO (Single Sign-On)
✓ Dedicated support
✓ SLA guarantee
✓ On-premise deployment option
✓ Custom integrations
✓ Training & onboarding

**Contact sales**: sales@aifileorganizer.com

**Best for:**
- Large organizations
- Teams (5+ users)
- Enterprise security requirements
- Custom needs

---

## Troubleshooting

### Desktop App Issues

#### App Won't Launch (Windows)
**Problem**: Double-clicking does nothing
**Solution**:
1. Right-click app → "Run as administrator"
2. Check Windows Defender didn't block it
3. Install Visual C++ Redistributable
4. Reinstall the app

#### App Won't Launch (macOS)
**Problem**: "App is damaged and can't be opened"
**Solution**:
```bash
sudo xattr -rd com.apple.quarantine /Applications/AI\ File\ Organizer.app
```

#### Python Not Found
**Problem**: "Python not found" error
**Solution**:
1. Install Python 3.8+ from python.org
2. Add Python to PATH
3. Restart app

#### Ollama Not Available
**Problem**: "Ollama not available" in FREE tier
**Solution**:
1. Install Ollama: `curl https://ollama.ai/install.sh | sh`
2. Pull a model: `ollama pull qwen2.5:7b-instruct`
3. Restart app

### Web App Issues

#### Login Problems
**Problem**: Can't sign in
**Solution**:
1. Clear browser cache
2. Try incognito mode
3. Check email for verification link
4. Reset password if needed

#### Upload Fails
**Problem**: Files won't upload
**Solution**:
1. Check file size limits
2. Verify file type is supported
3. Check internet connection
4. Try different browser

#### Slow Performance
**Problem**: App is slow
**Solution**:
1. Close unnecessary tabs
2. Clear browser cache
3. Check internet speed
4. Try different time (peak hours)

### AI Classification Issues

#### Low Confidence Scores
**Problem**: AI confidence < 50%
**Solution**:
- Use deeper analysis (slow but more accurate)
- Upgrade to PRO tier for better models
- Manually review and correct
- Provide more descriptive file names

#### Wrong Categories
**Problem**: Files categorized incorrectly
**Solution**:
- Review and manually correct
- Add to custom rules
- Report issue to support
- Use more descriptive file names

#### High Costs
**Problem**: AI costs too high
**Solution**:
- Use FREE tier with local models
- Disable deep analysis
- Organize in batches during off-peak
- Set monthly budget limit

---

## FAQ

### General

**Q: Is my data private?**
A: Yes. FREE tier processes everything locally. Paid tiers only send file metadata (name, type, small content sample) to AI APIs. Full files never leave your device unless you explicitly upload them.

**Q: Do I need an internet connection?**
A: FREE tier (desktop app with Ollama) works 100% offline. Paid tiers need internet for cloud AI models.

**Q: Can I cancel anytime?**
A: Yes. Cancel from dashboard Settings → Billing. Access continues until end of billing period.

**Q: What happens to my files if I cancel?**
A: Your files remain on your device/cloud storage. You can export organization settings before canceling.

### Technical

**Q: Which AI model should I use?**
A: Let the app choose automatically. It selects based on file complexity and your tier.

**Q: How accurate is the AI?**
A:
- Ollama (local): 75-85% accuracy
- GPT-3.5: 85-90% accuracy
- GPT-4/Claude: 90-95% accuracy

**Q: Can I train custom models?**
A: Yes, on ENTERPRISE tier. Contact sales for custom model training.

**Q: What about very large files?**
A:
- FREE/STARTER: Up to 50 MB
- PRO: Up to 200 MB
- ENTERPRISE: Up to 1 GB

**Q: Does it work with network drives?**
A: Yes. Desktop app can access any drive your computer can access.

### Billing

**Q: How are AI costs calculated?**
A: Based on tokens processed. Simple files: $0.001, Complex files: $0.01. All prices shown before organizing.

**Q: What payment methods do you accept?**
A: Credit cards (Visa, Mastercard, Amex), PayPal, bank transfer (ENTERPRISE).

**Q: Can I get a refund?**
A: Yes, within 30 days if you're not satisfied.

**Q: Do you offer discounts?**
A: Yes:
- Annual billing: 2 months free
- Students/educators: 50% off
- Non-profits: 50% off
- Enterprise: Volume discounts

### Support

**Q: How do I get help?**
A:
- FREE: Community forum, documentation
- STARTER: Email support (24-48h response)
- PRO: Priority email support (12h response)
- ENTERPRISE: Dedicated support + phone

**Q: Do you offer training?**
A: Yes:
- Video tutorials (all tiers)
- Webinars (PRO+)
- Onsite training (ENTERPRISE)

**Q: Where can I report bugs?**
A: GitHub issues: https://github.com/yourusername/ai-file-organizer/issues

---

## Additional Resources

- **Documentation**: https://docs.aifileorganizer.com
- **Video Tutorials**: https://youtube.com/aifileorganizer
- **Community Forum**: https://community.aifileorganizer.com
- **Blog**: https://blog.aifileorganizer.com
- **Status Page**: https://status.aifileorganizer.com
- **API Docs**: https://api.aifileorganizer.com/docs

## Contact

- **Support**: support@aifileorganizer.com
- **Sales**: sales@aifileorganizer.com
- **General**: hello@aifileorganizer.com
- **Twitter**: @aifileorg
- **GitHub**: github.com/yourusername/ai-file-organizer

---

**Last Updated**: January 2025
**Version**: 1.0.0
**Copyright © 2025 Alexandru Emanuel Vasile. All rights reserved.**
