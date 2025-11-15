# 🚀 Render.com Deployment Guide

Complete guide to deploying the Legal Document Comparator on Render.com.

---

## 📋 Pre-Deployment Checklist

Before deploying, ensure:

- [ ] All code is committed to Git
- [ ] GitHub repository is created and code is pushed
- [ ] `Dockerfile` is in project root
- [ ] `render.yaml` is in project root
- [ ] `.dockerignore` is in project root
- [ ] All fixes from this guide are applied

---

## 🎯 Step-by-Step Deployment

### **Step 1: Push to GitHub**

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial deployment to Render"

# Add remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/legal-comparator.git

# Push to main branch
git push -u origin main
```

### **Step 2: Sign Up for Render**

1. Go to https://render.com
2. Click "Get Started for Free"
3. Sign up with GitHub (recommended)
4. Authorize Render to access your repositories

### **Step 3: Create New Web Service**

1. Click **"New +"** button (top right)
2. Select **"Web Service"**
3. Choose **"Build and deploy from a Git repository"**
4. Click **"Next"**

### **Step 4: Connect Repository**

1. Find your `legal-comparator` repository
2. Click **"Connect"**
3. Render will scan your repo and detect `render.yaml`

### **Step 5: Configure Service**

Render should auto-detect settings from `render.yaml`, but verify:

**Basic Settings:**
- **Name**: `legal-document-comparator` (or your choice)
- **Region**: Choose closest to you (e.g., Oregon, Frankfurt)
- **Branch**: `main`
- **Root Directory**: `.` (leave blank)

**Build Settings:**
- **Environment**: `Docker`
- **Dockerfile Path**: `./Dockerfile`

**Plan:**
- **Free** (for testing) or **Starter** ($7/month, recommended)

**Environment Variables** (should be auto-set from render.yaml):
```
DEBUG=false
HOST=0.0.0.0
PORT=10000
RENDER=true
SIMILARITY_THRESHOLD=0.85
CONTEXT_WINDOW=2
```

### **Step 6: Deploy**

1. Click **"Create Web Service"**
2. Render will start building your Docker image
3. **Wait 5-10 minutes** for first deployment

**Build Process:**
```
📦 Cloning repository...
🐳 Building Docker image...
📥 Installing system packages...
🐍 Installing Python packages...
🧠 Downloading AI models...
🚀 Starting server...
✅ Deploy succeeded!
```

### **Step 7: Verify Deployment**

Once deployed, you'll see:
- **URL**: `https://legal-document-comparator-xxxx.onrender.com`
- **Status**: `Live` (green)

**Test the deployment:**

1. **Visit the URL** - Should see the upload interface
2. **Test health endpoint**: `https://YOUR-URL.onrender.com/api/health`
3. **Upload test files** - Try comparing two documents

---

## 🐛 Common Render Issues & Fixes

### **Issue 1: Build Fails - Out of Memory**

**Error:**
```
Killed
Error: failed to build
```

**Fix:**
Upgrade to Starter plan ($7/month) - Free tier has limited build resources.

---

### **Issue 2: Deploy Succeeds but App Doesn't Load**

**Check:**
1. Click on your service in Render dashboard
2. Go to **"Logs"** tab
3. Look for Python errors

**Common causes:**
- Models failed to download
- Port mismatch
- Import errors

**Fix:**
Check logs for specific error, then redeploy:
```bash
# Make fix in code
git add .
git commit -m "Fix deployment issue"
git push

# Render auto-deploys on push
```

---

### **Issue 3: First Request Times Out (Cold Start)**

**Symptom:**
- First request after idle takes 30+ seconds
- Shows "Unexpected end of JSON input"

**This is NORMAL on free tier!**

**Solutions:**

**A. Wait it out** (30-60 seconds)
- Render spins down free services after 15 minutes of inactivity
- First request wakes it up

**B. Keep service warm** (free hack)
Use a service like UptimeRobot to ping your app every 14 minutes:
- Sign up at https://uptimerobot.com (free)
- Add monitor for your Render URL
- Check interval: 14 minutes

**C. Upgrade to Starter** ($7/month)
- No cold starts
- Always running
- Faster responses

---

### **Issue 4: "Cannot find module" Errors**

**Check:**
1. Verify all Python files are in correct locations
2. Check `__init__.py` files exist in `comparison_engine/`
3. Ensure `frontend/` files copied to `static/`

**Fix in Dockerfile:**
Make sure this line exists:
```dockerfile
COPY frontend/ ./static/
```

---

### **Issue 5: Models Not Loading**

**Error in logs:**
```
OSError: [E050] Can't find model 'en_core_web_sm'
```

**Fix:**
The Dockerfile should have:
```dockerfile
RUN python -m spacy download en_core_web_sm
```

If missing, add it and redeploy.

---

### **Issue 6: CORS Errors**

**Error in browser console:**
```
Access to fetch at '...' has been blocked by CORS policy
```

**Fix:**
Ensure `app.py` has proper CORS settings (already fixed in code above).

---

### **Issue 7: File Upload Fails**

**Check:**
1. File size < 10MB
2. Correct file types (PDF, PNG, JPG)
3. Render logs for specific errors

**Common issue on free tier:**
- Memory limit (512MB) can cause crashes with large files
- **Solution**: Upgrade to Starter (2GB RAM)

---

## 📊 Monitoring Your Deployment

### **Check Logs**

1. Go to Render dashboard
2. Click your service
3. Click **"Logs"** tab
4. Real-time logs appear here

**What to look for:**
```
✅ Good:
✓ Server ready on port 10000
✓ Loaded spaCy model
✓ Loaded embedding model

❌ Bad:
ModuleNotFoundError: ...
OSError: ...
Killed
```

### **Check Metrics**

1. Click **"Metrics"** tab
2. Monitor:
   - **CPU usage** (should be <50% when idle)
   - **Memory** (should be <400MB on free tier)
   - **Response times** (5-10 seconds for comparison)

---

## 🔄 Updating Your Deployment

Render auto-deploys on every push to main branch:

```bash
# Make changes locally
# Edit files...

# Commit and push
git add .
git commit -m "Update feature X"
git push

# Render automatically rebuilds and deploys
# Takes 3-5 minutes
```

**Manual deploy:**
1. Go to Render dashboard
2. Click your service
3. Click **"Manual Deploy"** → **"Deploy latest commit"**

---

## 💰 Cost Breakdown

### **Free Tier**
- ✅ Good for: Testing, personal use, demos
- ❌ Limitations:
  - 512MB RAM
  - Cold starts (15-30 seconds)
  - Service sleeps after 15 minutes idle
  - 750 hours/month (enough for one service)

### **Starter - $7/month** (Recommended)
- ✅ Always on (no cold starts)
- ✅ 2GB RAM (handles larger files)
- ✅ Faster performance
- ✅ Good for production use

### **Standard - $25/month**
- ✅ 4GB RAM
- ✅ Multiple workers
- ✅ For high traffic

---

## 🎯 Production Checklist

Before going live with real users:

- [ ] Test with real documents (contracts, agreements)
- [ ] Verify OCR quality with scanned images
- [ ] Test file size limits
- [ ] Check response times
- [ ] Set up custom domain (optional)
- [ ] Consider upgrading to Starter tier
- [ ] Set up monitoring (UptimeRobot)
- [ ] Add error tracking (Sentry, optional)

---

## 🔗 Useful Links

- **Render Dashboard**: https://dashboard.render.com
- **Render Docs**: https://render.com/docs
- **Status Page**: https://status.render.com
- **Support**: help@render.com

---

## 🆘 Still Having Issues?

If deployment fails after trying all fixes:

1. **Check Render Status**: https://status.render.com
2. **View Logs**: Render Dashboard → Your Service → Logs
3. **Copy Error Message**: Share full error for help
4. **Try Manual Deploy**: Sometimes auto-deploy fails, manual works

**Quick Debug Commands:**

Add these to Dockerfile for debugging:
```dockerfile
# Before CMD, add:
RUN python -c "import spacy; spacy.load('en_core_web_sm')"
RUN python -c "from sentence_transformers import SentenceTransformer"
RUN ls -la /app/static/
```

This will catch errors during build instead of runtime.

---

## ✅ Success Indicators

Your deployment is working when:

- ✅ Render shows status: **Live** (green)
- ✅ URL loads the interface
- ✅ Health endpoint returns JSON: `/api/health`
- ✅ Can upload and compare two files
- ✅ Results page shows match percentage
- ✅ No errors in Render logs

---

**🎉 Once deployed, your app is live and accessible worldwide!**

Share your URL: `https://YOUR-APP-NAME.onrender.com`
