# OneDrive Integration Setup Guide

Complete guide to setting up Microsoft OneDrive integration for AI File Organizer.

## Prerequisites

- Microsoft account
- Azure account (free tier works)
- Python 3.8+ with requests library installed

## Step 1: Register Application in Azure

### 1.1 Create Azure Account

1. Go to https://portal.azure.com
2. Sign in with your Microsoft account
3. Click "Create a resource" if prompted (free tier is sufficient)

### 1.2 Register New Application

1. In Azure Portal, search for "Azure Active Directory"
2. Click "App registrations" in left menu
3. Click "+ New registration"

**Fill in details:**
- **Name**: AI File Organizer
- **Supported account types**: "Accounts in any organizational directory and personal Microsoft accounts"
- **Redirect URI**:
  - Platform: Web
  - URI: `http://localhost:8000/auth/onedrive/callback`

4. Click "Register"

### 1.3 Note Your Application ID

After registration, you'll see:
- **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Directory (tenant) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

**Copy the Application (client) ID** - this is your `ONEDRIVE_CLIENT_ID`

### 1.4 Create Client Secret

1. Click "Certificates & secrets" in left menu
2. Click "+ New client secret"
3. Add description: "AI File Organizer Secret"
4. Expires: Choose "24 months" (or "Never" for development)
5. Click "Add"
6. **IMMEDIATELY COPY THE VALUE** - you won't see it again!
   - This is your `ONEDRIVE_CLIENT_SECRET`

### 1.5 Configure API Permissions

1. Click "API permissions" in left menu
2. Click "+ Add a permission"
3. Select "Microsoft Graph"
4. Select "Delegated permissions"
5. Add these permissions:
   - `Files.ReadWrite.All` - Read and write all files
   - `User.Read` - Sign in and read user profile
   - `offline_access` - Maintain access to data

6. Click "Add permissions"
7. Click "Grant admin consent for [Your Organization]" (if available)

## Step 2: Update Environment Configuration

### 2.1 Edit .env File

```bash
# Open .env file
nano .env  # or your preferred editor
```

### 2.2 Add OneDrive Credentials

```bash
# Microsoft OneDrive
ONEDRIVE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
ONEDRIVE_CLIENT_SECRET=your-secret-value-from-azure
ONEDRIVE_REDIRECT_URI=http://localhost:8000/auth/onedrive/callback
```

**Important**: Never commit `.env` to version control!

## Step 3: Test OneDrive Integration

### 3.1 Create Test Script

Create `test_onedrive.py`:

```python
"""Test OneDrive integration."""

import os
from pathlib import Path
from dotenv import load_dotenv
from src.cloud.onedrive import OneDriveProvider

# Load environment variables
load_dotenv()

def test_onedrive():
    """Test OneDrive authentication and file operations."""

    # Initialize provider
    provider = OneDriveProvider(
        client_id=os.getenv('ONEDRIVE_CLIENT_ID'),
        client_secret=os.getenv('ONEDRIVE_CLIENT_SECRET'),
        redirect_uri=os.getenv('ONEDRIVE_REDIRECT_URI')
    )

    # Step 1: Get authorization URL
    auth_url = provider.get_authorization_url()
    print("\n" + "="*60)
    print("STEP 1: AUTHORIZE APPLICATION")
    print("="*60)
    print("\nVisit this URL in your browser:")
    print(f"\n{auth_url}\n")
    print("After authorizing, you'll be redirected to:")
    print(f"{os.getenv('ONEDRIVE_REDIRECT_URI')}?code=...")
    print("\nCopy the 'code' parameter from the URL")
    print("="*60 + "\n")

    # Step 2: Exchange code for token
    auth_code = input("Paste the authorization code here: ").strip()

    try:
        tokens = provider.exchange_code_for_token(auth_code)
        print("\n✅ Successfully authenticated!")
        print(f"Access token received (expires in {tokens.get('expires_in', 0)} seconds)")

        # Step 3: Get user info
        print("\n" + "="*60)
        print("STEP 2: USER INFORMATION")
        print("="*60)
        user_info = provider.get_user_info()
        print(f"\nUser: {user_info.get('displayName')}")
        print(f"Email: {user_info.get('userPrincipalName')}")

        # Step 4: Get quota
        print("\n" + "="*60)
        print("STEP 3: STORAGE QUOTA")
        print("="*60)
        quota = provider.get_quota()
        print(f"\nTotal: {provider.format_size(quota['total'])}")
        print(f"Used: {provider.format_size(quota['used'])}")
        print(f"Remaining: {provider.format_size(quota['remaining'])}")

        # Step 5: List files
        print("\n" + "="*60)
        print("STEP 4: LIST FILES")
        print("="*60)
        files = provider.list_files()
        print(f"\nFound {len(files)} files in root folder:")
        for i, file in enumerate(files[:10], 1):  # Show first 10
            icon = "📁" if file.is_folder else "📄"
            print(f"{i}. {icon} {file.name} ({provider.format_size(file.size)})")

        if len(files) > 10:
            print(f"... and {len(files) - 10} more files")

        # Step 6: Create test folder
        print("\n" + "="*60)
        print("STEP 5: CREATE TEST FOLDER")
        print("="*60)
        folder = provider.create_folder("AI_File_Organizer_Test")
        print(f"\n✅ Created folder: {folder.name}")
        print(f"Folder ID: {folder.id}")

        # Step 7: Upload test file
        print("\n" + "="*60)
        print("STEP 6: UPLOAD TEST FILE")
        print("="*60)

        # Create a test file
        test_file = Path("test_upload.txt")
        test_file.write_text("Hello from AI File Organizer!\n\nThis is a test file.")

        uploaded = provider.upload_file(
            local_path=test_file,
            cloud_folder_id=folder.id,
            cloud_filename="test_upload.txt"
        )
        print(f"\n✅ Uploaded: {uploaded.name}")
        print(f"Size: {provider.format_size(uploaded.size)}")
        print(f"File ID: {uploaded.id}")

        # Cleanup
        test_file.unlink()

        # Step 8: Search files
        print("\n" + "="*60)
        print("STEP 7: SEARCH FILES")
        print("="*60)
        search_results = provider.search_files("test")
        print(f"\nSearch for 'test' found {len(search_results)} results:")
        for file in search_results[:5]:
            print(f"- {file.name}")

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nOneDrive integration is working correctly!")
        print("You can now use OneDrive features in the application.")

        # Save tokens for reuse
        print("\n💡 TIP: Save these tokens for future use:")
        print(f"Access Token: {tokens.get('access_token')[:50]}...")
        print(f"Refresh Token: {tokens.get('refresh_token')[:50]}...")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("1. Client ID and Secret are correct")
        print("2. Redirect URI matches Azure configuration")
        print("3. API permissions are granted")
        return False

    return True


if __name__ == "__main__":
    print("\n" + "="*60)
    print("ONEDRIVE INTEGRATION TEST")
    print("="*60)
    test_onedrive()
```

### 3.2 Run Test

```bash
# Install python-dotenv if not already installed
pip install python-dotenv

# Run test
python test_onedrive.py
```

### 3.3 Expected Output

```
============================================================
ONEDRIVE INTEGRATION TEST
============================================================

============================================================
STEP 1: AUTHORIZE APPLICATION
============================================================

Visit this URL in your browser:

https://login.microsoftonline.com/common/oauth2/v2.0/authorize?...

After authorizing, you'll be redirected to:
http://localhost:8000/auth/onedrive/callback?code=...

Copy the 'code' parameter from the URL
============================================================

Paste the authorization code here: [YOUR CODE]

✅ Successfully authenticated!
Access token received (expires in 3600 seconds)

============================================================
STEP 2: USER INFORMATION
============================================================

User: John Doe
Email: john@example.com

============================================================
STEP 3: STORAGE QUOTA
============================================================

Total: 5.0 GB
Used: 1.2 GB
Remaining: 3.8 GB

[... more test output ...]

✅ ALL TESTS PASSED!
```

## Step 4: Integrate with Secure Dashboard

### 4.1 Add OAuth Callback Route

Add to `src/ui/dashboard_secure.py`:

```python
from src.cloud.onedrive import OneDriveProvider

# Global OneDrive provider instance
onedrive_provider = None

@app.get("/auth/onedrive/callback")
async def onedrive_callback(code: str, current_user: User = Depends(get_current_user)):
    """Handle OneDrive OAuth callback."""
    global onedrive_provider

    # Initialize provider
    onedrive_provider = OneDriveProvider(
        client_id=os.getenv('ONEDRIVE_CLIENT_ID'),
        client_secret=os.getenv('ONEDRIVE_CLIENT_SECRET'),
        redirect_uri=os.getenv('ONEDRIVE_REDIRECT_URI')
    )

    # Exchange code for tokens
    tokens = onedrive_provider.exchange_code_for_token(code)

    # Save tokens to user's database (implement this)
    # For now, just confirm success

    return {
        "success": True,
        "message": "OneDrive connected successfully",
        "user": current_user.username
    }

@app.get("/api/onedrive/authorize")
async def start_onedrive_auth(current_user: User = Depends(get_current_user)):
    """Start OneDrive authorization flow."""
    provider = OneDriveProvider(
        client_id=os.getenv('ONEDRIVE_CLIENT_ID'),
        client_secret=os.getenv('ONEDRIVE_CLIENT_SECRET'),
        redirect_uri=os.getenv('ONEDRIVE_REDIRECT_URI')
    )

    auth_url = provider.get_authorization_url()
    return {"auth_url": auth_url}

@app.get("/api/onedrive/files")
async def list_onedrive_files(current_user: User = Depends(get_current_user)):
    """List files in OneDrive."""
    if not onedrive_provider or not onedrive_provider.is_authenticated():
        raise HTTPException(status_code=401, detail="OneDrive not connected")

    files = onedrive_provider.list_files()
    return [
        {
            "name": f.name,
            "size": f.size,
            "is_folder": f.is_folder,
            "modified": f.modified_time.isoformat()
        }
        for f in files
    ]
```

## Troubleshooting

### Issue: "Invalid client secret"

**Solution**:
- Regenerate client secret in Azure Portal
- Make sure you copied the VALUE, not the Secret ID
- Update .env with new secret

### Issue: "Redirect URI mismatch"

**Solution**:
- Ensure redirect URI in code matches Azure configuration exactly
- Check for trailing slashes
- Use http://localhost:8000 for development, not 127.0.0.1

### Issue: "Insufficient privileges"

**Solution**:
- Grant admin consent for API permissions
- Wait 5-10 minutes after granting permissions
- Re-authenticate

### Issue: "Token expired"

**Solution**:
- Use refresh token to get new access token:
```python
new_tokens = provider.refresh_access_token()
```

## Production Deployment

### For Production:

1. **Update Redirect URI**:
   ```
   https://yourdomain.com/auth/onedrive/callback
   ```

2. **Add to Azure**:
   - Go to App registration → Authentication
   - Add production redirect URI
   - Save

3. **Update Environment**:
   ```bash
   ONEDRIVE_REDIRECT_URI=https://yourdomain.com/auth/onedrive/callback
   ```

4. **Enable HTTPS**:
   - OneDrive requires HTTPS in production
   - Use Vercel (automatic HTTPS) or configure SSL certificates

## Security Best Practices

1. **Never expose credentials**:
   - Keep .env file private
   - Add .env to .gitignore
   - Use environment variables in production

2. **Rotate secrets regularly**:
   - Change client secret every 6-12 months
   - Azure allows multiple secrets for zero-downtime rotation

3. **Use minimal permissions**:
   - Only request permissions you need
   - Remove unused API permissions

4. **Store tokens securely**:
   - Encrypt tokens in database
   - Use refresh tokens for long-lived access
   - Implement token rotation

## Resources

- [Microsoft Graph API Documentation](https://docs.microsoft.com/en-us/graph/)
- [OneDrive API Reference](https://docs.microsoft.com/en-us/graph/api/resources/onedrive)
- [Azure App Registration Guide](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)

## Support

If you encounter issues:
1. Check Azure Portal for app registration status
2. Verify all permissions are granted
3. Test with the provided test script
4. Review error messages in console

**Your OneDrive integration is now ready to use!** ✅
