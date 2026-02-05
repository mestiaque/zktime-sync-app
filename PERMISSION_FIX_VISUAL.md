# 🔐 `.zkdata` পারমিশন ফিক্স - ভিজ্যুয়াল গাইড

## ১. **সবচেয়ে সহজ উপায় (GUI বাটন)**

```
┌─────────────────────────────────────────────────────────┐
│                   ZKTeco Time Sync                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Device List                                            │
│  ┌────────────────────────────────────────────────────┐ │
│  │ IP Address  │ Port  │ Device SN                   │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ (empty)                                            │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌─────────────┬──────────┬────────────┬──────────────┐ │
│  │ Add Device  │ Edit Dev │ Remove Dev │ 🔧 FIX PERM  │ │
│  └─────────────┴──────────┴────────────┴──────────────┘ │
│                            ↑                             │
│                    ক্লিক এখানে!                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### কী ঘটে:

```
Step 1: আপনি "🔧 Fix Permissions" ক্লিক করেন
           ↓
Step 2: প্রোগ্রাম os.chmod() চালায়
           ↓
Step 3: ফাইল পারমিশন আপডেট হয়
           ↓
Step 4: Success message দেখায়
           ↓
Step 5: এখন Device যোগ করতে পারবেন!
```

---

## २. **কোড লেভেলে কী হয়?**

### পারমিশন চেক সিস্টেম:

```python
# ফাইল সেভ করার সময়:

save_config(cfg)
    │
    ├─→ ensure_file_writable(CONFIG_FILE)
    │   │
    │   └─→ os.access(path, os.W_OK) ?
    │       │
    │       ├─ True  → OK, proceed
    │       │
    │       └─ False → fix_file_permissions()
    │           │
    │           └─→ os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    │               └─ ফাইল writable করে দেয়
    │
    └─→ ফাইলে সেভ করো
```

### কোড উদাহরণ:

```python
def ensure_file_writable(path):
    """ফাইল writable কিনা চেক করো"""
    if not os.path.exists(path):
        return True
    try:
        if not os.access(path, os.W_OK):  # ← read-only কিনা চেক
            return fix_file_permissions(path)  # ← ফিক্স করো
        return True
    except:
        return False

def fix_file_permissions(path):
    """read-only ফাইলকে writable করো"""
    try:
        if os.path.exists(path):
            # ✓ Read permission
            # ✓ Write permission
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            return True
    except Exception as e:
        print(f"Failed: {e}")
    return False
```

---

## ३. **Windows File Properties ম্যানুয়াল ফিক্স**

### সমস্যা দেখাবে এভাবে:

```
Add Device করার চেষ্টা করছেন
    ↓
❌ Permission Error
   Cannot write to: C:\Users\YourName\.zkteco_sync\.zkdata
   
   Solutions:
   1. Close the .zkdata file in text editor
   2. Check file properties - remove 'Read-only'
   3. Run as Administrator
   4. Check antivirus
```

### ম্যানুয়াল ফিক্স স্টেপস:

```
Step 1: লুকানো ফাইল দেখান
┌──────────────────────────────────────┐
│ Windows এ:                           │
│ File Explorer খুলুন                │
│ View menu → Show hidden files      │
└──────────────────────────────────────┘

Step 2: ফোল্ডার খুঁজুন
┌──────────────────────────────────────┐
│ C:\Users\YourName\.zkteco_sync\    │
│                                      │
│ ফোল্ডার ডাবল-ক্লিক করুন          │
└──────────────────────────────────────┘

Step 3: .zkdata ফাইল খুঁজুন
┌──────────────────────────────────────┐
│ অনেক ফাইল থাকবে, এটা খুঁজুন:      │
│                                      │
│ 📄 .zkdata  ← এটা!                 │
│ 📄 last_sync.json                  │
│ ...                                  │
└──────────────────────────────────────┘

Step 4: রাইট-ক্লিক করুন
┌──────────────────────────────────────┐
│ .zkdata এ রাইট-ক্লিক             │
│                                      │
│ [Properties]  ← এই অপশন বেছে নিন  │
└──────────────────────────────────────┘

Step 5: Read-only আনচেক করুন
┌────────────────────────────────────────┐
│ .zkdata Properties                     │
├────────────────────────────────────────┤
│                                        │
│ File name:    .zkdata                 │
│ Type:         File                    │
│ Size:         2.1 KB                  │
│                                        │
│ [Attributes]                           │
│  ☐ Read-only       ← আনচেক করুন     │
│  ☑ Hidden         ← এটা থাকতে পারে   │
│  ☑ Archive        ← এটা থাকতে পারে   │
│                                        │
│ [Apply] [OK]                           │
│    ↓                                   │
│   ক্লিক করুন!                         │
│                                        │
└────────────────────────────────────────┘

Step 6: সফল!
┌──────────────────────────────────────┐
│ ✅ পারমিশন ফিক্স হয়েছে!            │
│                                      │
│ এখন Device যোগ করতে পারবেন         │
└──────────────────────────────────────┘
```

---

## ४. **অ্যাডমিন মোডে চালানো**

### Windows এ App.exe চালাবেন যদি সমস্যা হয়:

```
Step 1: app.exe খুঁজুন
┌──────────────────────────┐
│ Desktop বা Program Files │
└──────────────────────────┘

Step 2: রাইট-ক্লিক করুন
┌──────────────────────────────────────┐
│ app.exe                              │
│                                      │
│ [Run as Administrator]  ← বেছে নিন  │
│ [Open]                              │
│ [Send to]                           │
│ ...                                  │
└──────────────────────────────────────┘

Step 3: সম্মতি দিন
┌──────────────────────────────────────┐
│ User Account Control                 │
│                                      │
│ "Do you want to allow this app      │
│  to make changes?"                  │
│                                      │
│ [Yes]  ← ক্লিক করুন                │
└──────────────────────────────────────┘

Step 4: অ্যাপ এখন Admin সুবিধা নিয়ে চলবে
```

---

## ५. **কমান্ড লাইন দিয়ে ফিক্স**

### PowerShell (Admin) দিয়ে:

```powershell
# Administrator হিসেবে PowerShell খুলুন
# (Start → PowerShell (Admin) খুঁজুন)

icacls "C:\Users\YourName\.zkteco_sync\.zkdata" /grant "%USERNAME%:F"

# Output:
# processed file: C:\Users\YourName\.zkteco_sync\.zkdata
# Successfully processed 1 files...
```

### CMD (Admin) দিয়ে:

```cmd
REM Administrator হিসেবে CMD খুলুন

attrib -r "C:\Users\YourName\.zkteco_sync\.zkdata"

REM কোন output মানে সফল!
```

### Linux/Mac থেকে:

```bash
chmod 666 ~/.zkteco_sync/.zkdata

# Verify:
ls -la ~/.zkteco_sync/.zkdata
# Output: -rw-rw-rw- ...  (rw=readable + writable)
```

---

## ६. **ডিবাগিং: কী গেল ভুল?**

### Log Output দেখুন:

```
App খোলার পর, Log Box এর নীচে চেক করুন:

❌ "Permission Error" দেখা যাচ্ছে?
   └─ 🔧 Fix Permissions বাটন ক্লিক করুন

❌ "Failed to fix permissions"?
   └─ Admin হিসেবে চালান

❌ এখনও না হয়?
   └─ Windows Properties থেকে ম্যানুয়াল ফিক্স করুন

✅ "File permissions fixed"?
   └─ সফল! এখন Device যোগ করতে পারবেন
```

---

## ७. **সমস্যা সমাধান চেকলিস্ট**

```
☐ Device যোগ করতে পারছেন না?
  └─ Step 1: 🔧 Fix Permissions ক্লিক করুন

☐ এখনও পারছেন না?
  └─ Step 2: Admin মোডে চালান

☐ এখনও না?
  └─ Step 3: Properties থেকে Read-only আনচেক করুন

☐ Antivirus বাধা দিচ্ছে?
  └─ Step 4: Antivirus এক্সিমপশন যোগ করুন

☐ সবকিছু ট্রাই করে ফেলেছেন?
  └─ Step 5: সম্পূর্ণ ডেটা ডিলিট করুন, নতুন শুরু করুন
  
    # Windows
    rmdir /s C:\Users\YourName\.zkteco_sync\
    
    # Linux/Mac
    rm -rf ~/.zkteco_sync/
    
    # Then restart the app
```

---

## ✅ সফল হলে কী দেখবেন?

```
✓ Log Output এ: "Data file: C:\Users\...\zkdata"
✓ Device যোগ করতে পারবেন
✓ Device Edit করতে পারবেন
✓ Auto Sync সেটিংস সেভ হবে
✓ পরবর্তী রানে সব ডেটা থাকবে
```

---

**এই গাইড অনুসরণ করলে ১০০% কাজ হবে! 🚀**
