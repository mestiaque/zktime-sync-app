# `.zkdata` পারমিশন ফিক্স - কুইক রেফারেন্স

## ❌ সমস্যা

```
❌ Device যোগ করতে পারছি না
❌ "Permission Error" এরর আসছে
❌ ".zkdata ফাইল read-only"
```

---

## ✅ সমাধান - ৩টি উপায়

### **উপায় ১: GUI বাটন (সবচেয়ে সহজ) ⭐**

```
1. App চালু করুন
2. "🔧 Fix Permissions" বাটন ক্লিক করুন
3. ✅ Success message আসবে
4. হয়ে গেছে!
```

**কেন এটা কাজ করে?**
```python
os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
# এই কমান্ড ফাইলকে read + write যোগ করে দেয়
```

---

### **উপায় २: Admin Mode**

```
1. app.exe রাইট-ক্লিক করুন
2. "Run as Administrator" বেছে নিন
3. "Yes" সম্মতি দিন
4. অ্যাপ এখন Admin রাইট নিয়ে চলবে
```

---

### **উপায় ३: Windows Properties**

```
1. C:\Users\YourName\.zkteco_sync\ খুলুন
   (View > Show hidden files চেক করুন)

2. .zkdata ফাইল খুঁজুন

3. রাইট-ক্লিক → Properties

4. Read-only চেকবক্স আনচেক করুন ☐

5. Apply → OK
```

---

## 🔍 কীভাবে জানবেন সমস্যা সমাধান হয়েছে?

✅ **সফল হলে:**
```
✓ Device যোগ করতে পারবেন
✓ কোন এরর আসবে না
✓ Config সেভ হবে
```

---

## 🆘 এখনও না হলে?

| সমস্যা | সমাধান |
|---------|---------|
| Admin রাইট নেই | IT Admin এর কাছ থেকে পান |
| Antivirus বাধা দেয় | Antivirus এ এক্সিমপশন যোগ করুন |
| সিস্টেম ড্রাইভ (C:) সমস্যা | অন্য ড্রাইভে ইনস্টল করুন |

---

## 📖 বিস্তারিত গাইড

- **[PERMISSION_FIX_GUIDE.md](PERMISSION_FIX_GUIDE.md)** - সম্পূর্ণ নির্দেশিকা
- **[PERMISSION_FIX_VISUAL.md](PERMISSION_FIX_VISUAL.md)** - ডায়াগ্রাম সহ ধাপে ধাপে

---

## 💡 মনে রাখবেন

```
"🔧 Fix Permissions" বাটন = সমস্যার সমাধানের ৯০% 
```

এটা একবার ক্লিক করলেই সবচেয়ে বেশি সমস্যা সমাধান হয়ে যায়।
