# ZKTeco Sync Tool

## Features
- ✅ Sync attendance logs from multiple ZK devices
- ✅ Push logs to Laravel API
- ✅ Simple Windows UI with progress log
- ✅ Thread-safe JSON backup
- ✅ Auto-sync scheduling (1h, 4h, 6h, 8h, 12h, 24h)
- ✅ Date filtering for selective sync
- ✅ Duplicate prevention system
- ✅ Rate-limit handling

## Installation

### Prerequisites
- Python 3.10+
- pip (Python package manager)

### Steps
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Or build as EXE (Windows)
pyinstaller --onefile --icon=app_icon.ico app.py
```

## Usage

### GUI Features
1. **Add Device**: Enter Device IP, Port (default 4370), Password
2. **Edit Device**: Modify device settings
3. **Remove Device**: Delete device from list
4. **🔧 Fix Permissions**: Fix `.zkdata` file permissions if read-only
5. **Date Selection**: Choose sync date (Today/Yesterday/Custom)
6. **Auto Sync**: Set automatic sync interval
7. **SYNC NOW**: Manual sync trigger

### Permission Issues
If you get "Permission Error" when adding/editing devices:
1. Click the **"🔧 Fix Permissions"** button
2. If that fails, run as Administrator
3. See [PERMISSION_FIX_GUIDE.md](PERMISSION_FIX_GUIDE.md) for detailed solutions

## Configuration

### Config File Location
```
Windows: C:\Users\YourName\.zkteco_sync\.zkdata
Linux:   ~/.zkteco_sync/.zkdata
```

### Auto File Paths
- **Last Sync Tracker**: `last_sync.json` (in app directory)
- **Device Config**: `.zkdata` (hidden file, auto-managed)

## Technical Details

### File Structure
- `app.py` - Main GUI application
- `zk_sync.py` - Device communication & sync logic
- `sync_dup.py` - Duplicate prevention (thread-safe)
- `requirements.txt` - Python dependencies
- `last_sync.json` - Sync timestamp tracking

### Thread Safety
- Lock-based synchronization in `sync_dup.py`
- Safe concurrent read/write operations
- No race conditions in file operations

### Features in Detail

**Duplicate Prevention:**
- Tracks last sync time per device
- Only syncs new records
- Prevents duplicate submissions

**Rate Limiting:**
- Handles API 429 responses
- Auto-retry with 2s delay
- 0.4s delay between requests

**Date Filtering:**
- Filter logs by selected date
- Sync historical data safely
- Reset tracker for date changes

## Troubleshooting

### Error: "Permission Error - Cannot write to .zkdata"
**Solution**: See [PERMISSION_FIX_GUIDE.md](PERMISSION_FIX_GUIDE.md)
- Method 1: Click "🔧 Fix Permissions" button (GUI)
- Method 2: Run as Administrator
- Method 3: Manual fix via Windows Properties

### Error: "Connection failed"
- Check device IP is correct
- Verify device password
- Ensure network connectivity
- Check device is not disabled

### Error: "API Failed"
- Verify API URL is correct
- Check internet connection
- Check API server status
- Review API response in logs

## Notes
- Tkinter comes with Python 3 by default
- Device password is required to connect
- First sync might take longer (fetches all logs)
- Auto-sync continues when app is running
- Config is saved in `.zkdata` (auto-hidden on Windows)

## Version
- v1.1 (Thread-safe with permission handling)

