# 🔐 পারমিশন ফিক্স গাইড (.zkdata ফাইল)

## সমস্যা কী?

`.zkdata` ফাইল **read-only** মোডে থাকে, যার ফলে:
- নতুন ডিভাইস যোগ করা যায় না
- ডিভাইস এডিট করা যায় না
- কনফিগ সেভ করা যায় না
- অটো-সিঙ্ক সেটিংস সেভ করা যায় না

---

## সমাধান ৩টি পদ্ধতি

### **পদ্ধতি ১: GUI থেকে (সবচেয়ে সহজ) ✅**

#### ধাপ ১: অ্যাপ চালু করুন
```
app.exe চালু করুন (বা python app.py)
```

#### ধাপ ২: "🔧 Fix Permissions" বাটন ক্লিক করুন
```
┌────────────────────────────────────┐
│ Add Device │ Edit │ Remove │ 🔧 Fix Permissions │  ← এই বাটনে ক্লিক করুন
└────────────────────────────────────┘
```

#### ধাপ ৩: সফল হলে স্ক্রিনে আসবে
```
✅ Success
File permissions fixed:
C:\Users\YourName\.zkteco_sync\.zkdata
```

#### ধাপ ৪: এখন নতুন ডিভাইস যোগ করুন
```
✓ Device successfully saved to .zkdata
```

---

### **পদ্ধতি ২: Command Line থেকে (Portable)**

#### Linux/Mac:
```bash
chmod 666 ~/.zkteco_sync/.zkdata
```

#### Windows PowerShell (Admin):
```powershell
# ডেস্কটপে স্টার্ট করুন → PowerShell (Admin) খুঁজুন
icacls "C:\Users\YourName\.zkteco_sync\.zkdata" /grant "%USERNAME%:F"
```

#### Windows CMD (Admin):
```cmd
REM Administrator হিসেবে খুলুন
attrib -r "C:\Users\YourName\.zkteco_sync\.zkdata"
```

---

### **পদ্ধতি ३: ম্যানুয়াল (Windows File Explorer)**

#### ধাপ ১: লুকানো ফোল্ডার দেখান
```
Windows এ লুকানো ফাইল দেখতে:
View > Show hidden files
অথবা
View (ট্যাব) > Options > Change folder and search options
    → View (ট্যাব) → ☑ Show hidden files, folders, and drives
```

#### ধাপ २: ফোল্ডার খুঁজুন
```
C:\Users\YourName\.zkteco_sync\
```

#### ধাপ ३: `.zkdata` ফাইল খুঁজুন
```
.zkdata (ফাইল)
```

#### ধাপ ४: প্রপার্টিজ খুলুন
```
.zkdata এ রাইট-ক্লিক → Properties
```

#### ধাপ ५: Read-only চেকবক্স আনচেক করুন
```
┌─────────────────────────────────────┐
│ .zkdata Properties                  │
├─────────────────────────────────────┤
│ Attributes:                         │
│   ☐ Read-only          ← এটা আনচেক করুন
│   ☑ Hidden             ← এটা থাকতে পারে
│                                     │
│ [Apply] [OK]                        │
└─────────────────────────────────────┘
```

#### ধাপ ६: Apply → OK ক্লিক করুন
```
✓ Done
```

---

## এটি কেন হয়?

### কারণ ১: **Windows Protection**
- সিস্টেম স্বয়ংক্রিয়ভাবে লুকানো ফাইল read-only করে

### কারণ २: **Antivirus/Security Software**
- কিছু এন্টিভাইরাস স্বয়ংক্রিয়ভাবে ফাইল lock করে

### কারণ ३: **File was being used**
- অ্যাপ চলার সময় ফাইল সংশোধিত হয়নি

---

## কোডে কীভাবে কাজ করে?

### `app.py` এ পারমিশন কোড:

```python
# ৩টি ফাংশন একসাথে কাজ করে:

1️⃣  ensure_file_writable(path)
    └─ ফাইল writable আছে কিনা চেক করে
    └ যদি না থাকে, fix_file_permissions() কল করে

२⃣  fix_file_permissions(path)
    └─ os.chmod(path, stat.S_IWRITE | stat.S_IREAD) চালায়
    └─ এটি ফাইলকে readable এবং writable করে

३⃣  "🔧 Fix Permissions" বাটন
    └─ ম্যানুয়ালি ব্যবহারকারী এই ফাংশন চালাতে পারেন
```

### সম্পূর্ণ ফ্লো:

```
User clicks "Add Device"
    ↓
save_config() called
    ↓
ensure_file_writable(CONFIG_FILE) ← চেক করে
    ├─ যদি writable না হয়
    │  └─ fix_file_permissions() চালায়
    │     └─ os.chmod() দিয়ে পারমিশন ফিক্স করে
    └─ যদি success না হয়
       └─ Error message দেখায় + admin চালাতে বলে
```

---

## যদি সমস্যা অব্যাহত থাকে?

### ① Admin হিসেবে চালান
```
app.exe এ রাইট-ক্লিক → "Run as Administrator"
```

### २ Antivirus ডিজেবল করুন (Testing এর জন্য)
```
Windows Defender:
  Settings → Virus & threat protection 
    → Manage settings → ডিজেবল করুন (চেক করার জন্য)
```

### ३ অন্য লোকেশনে চালান
```
সিস্টেম ড্রাইভ ছাড়া অন্য ড্রাইভে (D:, E:, etc)
```

### ४ Full Reset
```bash
# সম্পূর্ণ ডেটা ডিলিট করুন (সতর্ক!)
rm -r ~/.zkteco_sync/

# অ্যাপ পুনরায় চালান - নতুন ফাইল তৈরি হবে
```

---

## ✅ সফল হলে কী হবে?

```
✓ Devices সেভ হবে
✓ Auto-sync সেভ হবে  
✓ Last sync time সেভ হবে
✓ পরবর্তী রান এ সব ডেটা থাকবে
```

---

## 🔍 Debug করতে হলে

**Log output এ দেখুন:**
```
App উইন্ডো এর নীচে "Log Output" সেকশনে
সব কিছু দেখা যায়
```

**পারমিশন সমস্যা দেখাবে:**
```
❌ Permission Error
Cannot write to C:\Users\...\zkdata
...
Solutions:
1. Close the .zkdata file in any text editor
२. Check file properties - remove 'Read-only' attribute
३. Run app as Administrator
४. Check antivirus restrictions
```

---

## সংক্ষিপ্ত মনেরাখবেন

| সমস্যা | সমাধান |
|---------|---------|
| App এ Device যোগ হয় না | 🔧 Fix Permissions ক্লিক করুন |
| হলেও কাজ না হয় | Admin হিসেবে চালান |
| তারপরও না হয় | Properties থেকে Read-only আনচেক করুন |
| এখনও না হয় | Antivirus চেক করুন |

---

**কোন প্রশ্ন থাকলে উপরের যেকোনো পদ্ধতি ট্রাই করুন। সবগুলোতেই কাজ করবে! ✅**
