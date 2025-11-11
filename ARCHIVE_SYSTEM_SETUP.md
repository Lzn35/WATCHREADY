# 📦 WATCH Archive System - Setup Guide

## ✅ What We Implemented

### **Complete Archive System for Cases**

A user-friendly archive system that:
1. **Soft Deletes Cases** - When users delete a case, it's marked as deleted but NOT removed from database
2. **View Deleted Cases** - "View Archive" button on all case pages shows soft-deleted cases
3. **Restore from Archive** - Users can restore accidentally deleted cases within 60 days
4. **Auto-Purge After 60 Days** - Cases older than 60 days are automatically permanently deleted
5. **CSV Backups** - Before permanent deletion, CSV backups are created
6. **Countdown Timers** - Shows "Days Remaining" before permanent deletion

---

## 🎯 Features

### **1. Archive Button on All Case Pages**
- ✅ Minor Cases - Student
- ✅ Minor Cases - Staff  
- ✅ Minor Cases - Faculty
- ✅ Major Cases - Student
- ✅ Major Cases - Staff
- ✅ Major Cases - Faculty

### **2. Archive View Page**
- Shows all soft-deleted cases for each case type
- Color-coded countdown timer:
  - 🟢 **Green** (>30 days remaining) - Safe
  - 🟡 **Yellow** (8-30 days remaining) - Warning
  - 🔴 **Red** (≤7 days remaining) - Critical
  
- Statistics dashboard:
  - Total archived cases
  - Cases expiring soon (≤7 days)
  - Safe cases (>7 days)

### **3. Restore Functionality**
- **Restore Button** - Click to restore case from archive
- Case is immediately restored to active cases
- Activity log entry created
- Archive page updates automatically

### **4. Permanent Delete (Manual)**
- **Delete Now Button** - Admin can immediately delete without waiting 60 days
- Creates CSV backup before deletion
- Requires double confirmation
- Irreversible action

### **5. Automatic Purge (Daily)**
- Runs automatically every day
- Finds cases older than 60 days
- Creates CSV backup automatically
- Permanently deletes old cases
- No manual intervention needed!

---

## 🛠️ Setup Instructions

### **Step 1: Deploy Changes to Railway**

1. Commit and push all changes:
```bash
git add .
git commit -m "FEATURE: Complete Archive System with Auto-Purge

IMPLEMENTED:
- Archive button on all case pages (Minor/Major Student/Staff/Faculty)
- Archive view page with countdown timers and restore functionality
- Permanent delete API with CSV backup
- Automatic daily purge for cases older than 60 days
- CSV backups created before all permanent deletions

USER FLOW:
1. Delete case → Goes to Archive (soft delete)
2. View Archive → See deleted cases with days remaining
3. Restore or wait → Can restore within 60 days
4. Auto-purge → After 60 days, automatically deleted with CSV backup

PANEL REQUIREMENT SATISFIED:
✅ Purging of database within school year cycle
✅ Data recovery system (60-day restore window)
✅ CSV archives for audit trail"

git push origin main
```

2. Wait for Railway to deploy (check Deploy Logs)

---

### **Step 2: Setup Daily Auto-Purge (CRITICAL!)**

Railway doesn't have built-in cron support, so we need to use an external cron service:

#### **Option A: cron-job.org (FREE & RECOMMENDED)**

1. Go to **https://cron-job.org**
2. Create a free account
3. Click **"Create Cron Job"**
4. Configure:
   - **Title:** "WATCH Auto-Purge Old Cases"
   - **URL:** `https://www.sti-watch.com/cron/purge-old-cases`
   - **Schedule:** Daily at 2:00 AM (or your preferred time)
     - Every day
     - Time: 02:00
   - **Timezone:** Asia/Manila
5. Click **"Create"**
6. Test by clicking **"Run Now"** - should see success message

#### **Option B: EasyCron (FREE)**

1. Go to **https://www.easycron.com**
2. Create free account
3. Add new cron job:
   - **URL:** `https://www.sti-watch.com/cron/purge-old-cases`
   - **Cron Expression:** `0 2 * * *` (Daily at 2 AM)
   - **HTTP Method:** GET
4. Save and test

#### **Option C: UptimeRobot (FREE)**

1. Go to **https://uptimerobot.com**
2. Add New Monitor:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** WATCH Auto-Purge
   - **URL:** `https://www.sti-watch.com/cron/purge-old-cases`
   - **Monitoring Interval:** Every 24 hours
3. Save

---

### **Step 3: Test the Archive System**

1. **Create Test Case:**
   - Go to Cases → Minor Cases → Student
   - Add a student case

2. **Delete Test Case:**
   - Click "Actions" → "Delete Case"
   - Confirm deletion

3. **View Archive:**
   - Click "📦 View Archive" button
   - You should see the deleted case
   - Check the countdown timer (should show 60 days remaining)

4. **Test Restore:**
   - Click "🔄 Restore" button
   - Case should be removed from archive
   - Go back to main case page - case should be there!

5. **Test Manual Permanent Delete (Optional):**
   - Delete another case
   - Go to Archive
   - Click "🗑️ Delete Now"
   - Confirm twice
   - Check `instance/archives/permanent_deletes/` folder - CSV backup should be there

6. **Test Auto-Purge (Manual Trigger):**
   - Visit: `https://www.sti-watch.com/cron/purge-old-cases`
   - Should return JSON: `{"success": true, "count": 0, "message": "No cases to purge"}`
   - This confirms auto-purge endpoint is working!

---

## 📋 How It Works (User Perspective)

### **For Students/Staff/Faculty:**

```
1. User clicks "Delete Case" 
   ↓
2. Case moves to Archive (not deleted from database!)
   ↓
3. User can click "View Archive" anytime
   ↓
4. User can click "Restore" within 60 days
   ↓
5. After 60 days, case is auto-purged with CSV backup
```

### **Archive Countdown Colors:**

- **🟢 60-31 days remaining** - Safe zone
- **🟡 30-8 days remaining** - Warning zone
- **🔴 7-0 days remaining** - Critical zone! Restore soon!
- **⚫ 0 days** - Will be purged tonight!

---

## 📂 CSV Backup Locations

All CSV backups are stored in `instance/archives/`:

```
instance/
  archives/
    permanent_deletes/      ← Manual "Delete Now" backups
      case_123_20251111_143022.csv
      case_124_20251111_143045.csv
    
    automatic_purge/        ← Daily auto-purge backups
      auto_purge_20251111_020000.csv
      auto_purge_20251112_020000.csv
```

---

## ⚙️ Configuration (Advanced)

### **Change Auto-Purge Days (Default: 60 days)**

Edit `watch/app/routes.py` line 359:

```python
# Change 60 to desired number of days
result = PurgeService.purge_old_cases_automatic(days_old=60)
```

Options:
- `30` - Purge after 30 days
- `90` - Purge after 90 days (3 months)
- `180` - Purge after 6 months

---

## 🐛 Troubleshooting

### **"Archive button not showing"**
- Clear browser cache (Ctrl+F5)
- Check Deploy Logs - deployment must be successful

### **"Cron job not working"**
1. Check cron service is active
2. Test manually: Visit `https://www.sti-watch.com/cron/purge-old-cases`
3. Check Railway Deploy Logs for errors

### **"Restore not working"**
- Check browser console (F12) for errors
- Ensure user is logged in
- Check Deploy Logs for backend errors

### **"CSV backups not created"**
- Check `instance/archives/` folder exists
- Check file permissions (Railway should create automatically)
- Check Deploy Logs for write errors

---

## ✅ Panel Requirements Satisfied

✅ **"Purging of data from the database within the school year"**
   - Auto-purge runs daily, removes old cases after 60 days
   - Configurable purge interval

✅ **"Student must be detected in the database after graduated"**
   - Separate graduated student purging exists (Settings → Data Purge)
   - Can mark sections as graduated and purge in bulk

✅ **"Import/Export of students"**
   - Import CSV: Settings → Student Import
   - Export CSV: Settings → Student Import → Export

✅ **"Table reference for Room and Section"**
   - Room and Section are reference tables (foreign keys)
   - Used in Schedule and Person models

---

## 📊 Database Schema

### **Case Model (Soft Delete Fields)**

```python
is_deleted = Column(Boolean, default=False, index=True)
deleted_at = Column(DateTime, nullable=True)
deleted_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
```

### **Soft Delete Flow:**

```python
# When user clicks "Delete":
case.is_deleted = True
case.deleted_at = datetime.utcnow()
case.deleted_by_id = current_user.id
db.session.commit()

# Query only shows active cases (is_deleted=False)
active_cases = Case.query.filter_by(is_deleted=False).all()

# Archive shows deleted cases (is_deleted=True)
archived_cases = Case.query.filter_by(is_deleted=True).all()
```

---

## 🎉 SUCCESS!

Your WATCH system now has a **complete archive system** that:

✅ Prevents accidental data loss (60-day restore window)  
✅ Automatically purges old data (no manual work!)  
✅ Creates CSV backups (audit trail)  
✅ User-friendly interface (countdown timers, restore buttons)  
✅ Satisfies panel requirements (purging + data recovery)  

**Great job bro! The panel will love this!** 🚀

