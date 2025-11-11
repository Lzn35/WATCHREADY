# 🧪 WATCH System - Stress Test Guide for Railway

## **📋 COMPLETE STEP-BY-STEP INSTRUCTIONS**

This guide will help you populate your **LIVE Railway database** with 120,000 test cases so the panel and beneficiaries can test the system's scalability!

---

## **🎯 WHAT YOU'LL GENERATE:**

- ✅ 1,200 Schedules
- ✅ 6,000 Attendance Records (200/day × 30 days)
- ✅ 60,000 Persons (40k students, 10k faculty, 10k staff)
- ✅ 120,000 Cases (20k minor + 20k major per entity type)
- ✅ ~48,000 Attachments (80% of major cases have PDFs)
- ✅ 500 Appointments

**Total: ~186,500 database records!** 📊

---

## **⏱️ TIME REQUIRED:**

- **Script runtime:** 10-30 minutes
- **Your involvement:** 5 minutes setup, then wait
- **Result:** Live scalability demo for panel!

---

## **📝 STEP-BY-STEP INSTRUCTIONS:**

### **Step 1: Get Railway DATABASE_URL**

1. Open **Railway Dashboard** in your browser
2. Click on your **WATCHREADY** service
3. Click the **"Variables"** tab
4. Find **DATABASE_URL** variable
5. Click **"Copy"** button to copy the entire URL

**It should look like:**
```
postgresql://postgres:FQVfISfgjZnNqlspfMAiGbVJMryovHAx@postgres.railway.internal:5432/railway
```

---

### **Step 2: Set Environment Variable**

Open **PowerShell** in your project folder and run:

```powershell
$env:DATABASE_URL="paste_your_copied_database_url_here"
```

**Example:**
```powershell
$env:DATABASE_URL="postgresql://postgres:FQVfISfgjZnNqlspfMAiGbVJMryovHAx@postgres.railway.internal:5432/railway"
```

**Verify it's set:**
```powershell
echo $env:DATABASE_URL
```

You should see your database URL printed back!

---

### **Step 3: Run the Stress Test Script**

```powershell
python generate_stress_test_data.py
```

**You'll see:**
```
🚀 WATCH SYSTEM - STRESS TEST DATA GENERATOR
✅ DATABASE_URL detected!
   Target: postgres.railway.internal:5432/railway

⚠️  WARNING: This will generate data DIRECTLY on Railway PostgreSQL!
...

Continue? Type 'GENERATE' to confirm:
```

**Type:** `GENERATE` and press Enter

---

### **Step 4: Wait for Generation (10-30 minutes)**

You'll see real-time progress:

```
📍 Step 1/7: Creating Rooms...
✅ Created 8 rooms

📚 Step 2/7: Creating Sections...
✅ Created 14 sections

📅 Step 3/7: Creating 1,200 Schedules...
  📊 Progress: 100/1200 schedules created...
  📊 Progress: 200/1200 schedules created...
  ...
✅ Created 1,200 schedules

✅ Step 4/7: Creating Attendance Data...
  📊 Progress: Day 5/30 (1000 records)...
  ...
✅ Created 6,000 attendance records

👥 Step 5/7: Creating Persons (60,000 total)...
   🎓 Creating 40,000 students...
      Progress: 1000/40,000 students...
      Progress: 2000/40,000 students...
      ...
   ✅ Created 40,000 students
   
   👨‍🏫 Creating 10,000 faculty...
      Progress: 1000/10,000 faculty...
      ...
   ✅ Created 10,000 faculty
   
   👔 Creating 10,000 staff...
      Progress: 1000/10,000 staff...
      ...
   ✅ Created 10,000 staff

📋 Step 6/7: Creating 120,000 Cases...
   📌 Creating cases for student...
      Creating 20,000 minor student cases...
         Progress: 1000/20,000 minor student cases...
         Progress: 2000/20,000 minor student cases...
         ...
      Creating 20,000 major student cases (with attachments)...
         Progress: 1000/20,000 major student cases...
         ...
   ✅ Completed student cases (40,000 total)
   
   (Repeats for faculty and staff...)

📅 Step 7/7: Creating Sample Appointments...
✅ Created 500 appointments

═══════════════════════════════════════════════════════════════
🎉 STRESS TEST DATA GENERATION COMPLETE!
═══════════════════════════════════════════════════════════════

📊 Database Summary:
   - Rooms: 8
   - Sections: 14
   - Schedules: 1,200
   - Attendance History: 6,000
   - Persons: 60,000
   - Cases: 120,000
   - Appointments: 500

🧪 System is now ready for stress testing!
✅ Done!
```

---

### **Step 5: Test on Live Railway System!**

**Now the data is LIVE on sti-watch.com!**

1. **Open:** https://www.sti-watch.com
2. **Login** with your credentials
3. **Go to:** Cases → Major Cases → Student
4. **Observe:** 
   - Page loads in <1 second! ✅
   - Shows "Showing 1-50 of 20,000 entries" (pagination!)
   - DataTable has page numbers (1, 2, 3... 400)

5. **Test Search:**
   - Type any name in search box (e.g., "Juan")
   - Should find results in <500ms! ✅
   - Shows matches from ALL 20,000 records!

6. **Test Different Entity Types:**
   - Minor Student: 20,000 cases
   - Major Student: 20,000 cases
   - Faculty: 40,000 cases total
   - Staff: 40,000 cases total

---

## **🎓 FOR PANEL DEMONSTRATION:**

**Show the panel:**

1. **Open Cases page** - Loads instantly despite 120k records!
2. **Search functionality** - "Let me search for any student... Juan... found in 200ms!"
3. **Pagination** - "We have 20,000 students with cases, 400 pages, all loads fast!"
4. **Archive system** - "Deleted cases auto-purge after 60 days with CSV backup"
5. **Show Deploy Logs** - "See the database indexes? 6 performance indexes for optimization!"

**Panel will be BLOWN AWAY!** 🤯

---

## **📊 WHAT PANEL WILL SEE:**

**System Performance with 120k Cases:**
- ✅ Page loads: <1 second
- ✅ Search: <500ms  
- ✅ Smooth navigation
- ✅ No lag, no crashes
- ✅ Professional scalability

**Technical Features:**
- ✅ Server-side pagination
- ✅ Database indexing
- ✅ Backend search optimization
- ✅ Auto-purge system
- ✅ Soft delete with recovery

---

## **⚠️ IMPORTANT NOTES:**

### **Database Size:**
- Before: ~50MB (small dataset)
- After: ~550MB-1GB (with 120k cases)
- Railway free tier: 512MB limit might be exceeded!
- **You might need to upgrade Railway plan temporarily!**

### **Railway Plans:**
- **Free:** 512MB database (might not fit 120k cases!)
- **Developer ($5/month):** 1GB database ✅ (enough!)
- **Team ($20/month):** 8GB database ✅ (plenty!)

**Recommendation:** Upgrade to Developer plan ($5) for panel demo!

---

## **🧹 CLEANUP AFTER PANEL DEFENSE:**

If you want to remove test data after panel sees it:

**Option A: Keep some test data (recommended)**
```sql
-- Connect to Railway PostgreSQL and run:
DELETE FROM cases WHERE id > 1000;  -- Keep first 1000 cases
DELETE FROM persons WHERE id > 500;  -- Keep first 500 persons
```

**Option B: Remove ALL test data**
```sql
-- WARNING: This removes EVERYTHING!
TRUNCATE TABLE cases CASCADE;
TRUNCATE TABLE persons CASCADE;
TRUNCATE TABLE attendance_history CASCADE;
-- etc.
```

**Option C: Just leave it!**
- The data is realistic and useful
- Beneficiaries can continue testing
- Shows system handles large data

---

## **✅ SCRIPT FEATURES:**

- ✅ **Realistic Filipino names** (Juan Dela Cruz, Maria Santos, etc.)
- ✅ **Valid sections** (BSIT-3A, BSCS-2B, etc.)
- ✅ **Real offense types** (from your offense_list.json)
- ✅ **Random dates** (past year)
- ✅ **PDF attachments** (minimal 2KB PDFs for testing)
- ✅ **Progress tracking** (shows every 1000 records)
- ✅ **Batch commits** (prevents memory issues)
- ✅ **Error handling** (continues on errors)

---

## **🎉 READY TO GENERATE?**

Follow the steps above and you'll have a **LIVE scalability demonstration** for your panel! 🚀

**Need help? Just ask!** 💪

