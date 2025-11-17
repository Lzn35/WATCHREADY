# Railway Deployment Troubleshooting Guide

## 🔧 Common Issues After Plan Upgrade

When upgrading from free trial to paid plan, Railway may reset some configurations. Follow these steps:

### 1. ✅ Check Environment Variables

Go to **Railway Dashboard → Your Service → Variables** and ensure these are set:

#### **REQUIRED Variables:**
```
SECRET_KEY=your-secret-key-here (generate a new one if missing)
DATABASE_URL=postgresql://... (should be auto-set if Postgres service is connected)
PORT=5000 (Railway sets this automatically)
FLASK_ENV=production
```

#### **How to Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. ✅ Verify Database Connection

1. Go to **Railway Dashboard → Postgres Service**
2. Click **Variables** tab
3. Copy the `DATABASE_URL` value
4. Go to **WATCHREADY Service → Variables**
5. Ensure `DATABASE_URL` is set (it should auto-link, but verify)

### 3. ✅ Check Build Logs

1. Go to **Railway Dashboard → WATCHREADY Service → Deployments**
2. Click on the **FAILED** deployment
3. Click **View Logs** or **Build Logs**
4. Look for specific error messages:
   - `ModuleNotFoundError` → Missing dependency
   - `Connection refused` → Database connection issue
   - `Environment variable not set` → Missing env var
   - `Build timeout` → Build taking too long

### 4. ✅ Force Redeploy

If build fails:
1. Go to **Deployments** tab
2. Click **Redeploy** on the latest deployment
3. Or push a new commit to trigger rebuild

### 5. ✅ Verify Service Connection

1. Ensure **Postgres** service is connected to **WATCHREADY** service
2. In Railway dashboard, you should see a connection line between them
3. If not connected:
   - Go to **WATCHREADY Service → Settings**
   - Under **Service Connections**, add **Postgres** service

### 6. ✅ Check Build Configuration

The project uses:
- **Build Command**: Auto-detected (pip install from requirements.txt)
- **Start Command**: `gunicorn -w 2 -b 0.0.0.0:$PORT --timeout 120 wsgi:app`
- **Python Version**: 3.11.9 (specified in runtime.txt)

### 7. ✅ Common Build Errors & Fixes

#### Error: "Failed to build an image"
- **Cause**: Missing dependencies or build timeout
- **Fix**: Check build logs for specific package errors

#### Error: "DATABASE_URL not found"
- **Cause**: Database service not connected
- **Fix**: Connect Postgres service to WATCHREADY service

#### Error: "SECRET_KEY not set"
- **Cause**: Missing environment variable
- **Fix**: Add SECRET_KEY to environment variables

#### Error: "Module not found"
- **Cause**: requirements.txt not installing correctly
- **Fix**: Check nixpacks.toml and requirements.txt are in root

### 8. ✅ Quick Fix Checklist

- [ ] SECRET_KEY is set in environment variables
- [ ] DATABASE_URL is set (auto-linked from Postgres)
- [ ] Postgres service is connected to WATCHREADY service
- [ ] Build logs show no errors
- [ ] Service is in "Running" state (not "Failed")
- [ ] Domain is properly configured (www.sti-watch.com)

### 9. ✅ Manual Redeploy Steps

1. **Via Git Push:**
   ```bash
   git commit --allow-empty -m "Trigger Railway rebuild"
   git push origin main
   ```

2. **Via Railway Dashboard:**
   - Go to **Deployments** tab
   - Click **Redeploy** on latest deployment

### 10. ✅ Verify Deployment

After successful deployment:
1. Check service status is **"Running"** (green)
2. Visit your domain: `https://www.sti-watch.com`
3. Check logs for any runtime errors

---

## 🆘 Still Having Issues?

1. **Check Railway Status**: https://status.railway.app
2. **View Full Logs**: Railway Dashboard → Service → Logs
3. **Contact Railway Support**: If issue persists after checking all above

---

## 📝 Environment Variables Reference

```env
# Required
SECRET_KEY=your-generated-secret-key
DATABASE_URL=postgresql://... (auto-set by Railway)
PORT=5000 (auto-set by Railway)

# Optional (with defaults)
FLASK_ENV=production
DEBUG=False
SESSION_COOKIE_SECURE=True
```

---

**Last Updated**: After plan upgrade troubleshooting

