# 🚀 Getting Started Guide

Complete step-by-step instructions for setting up the Legal Document Comparator.

---

## 📋 Prerequisites

Before you begin, ensure you have:

- [ ] **Python 3.7 or higher** installed
  ```bash
  python --version  # Should show 3.7+
  ```

- [ ] **Git** installed (for deployment)
  ```bash
  git --version
  ```

- [ ] **10GB free disk space** (for models and dependencies)

- [ ] **Internet connection** (to download models)

---

## 🏃 Quick Start (5 Minutes)

### Step 1: Create Project

Save all the provided code files in this structure:

```
legal-comparator/
├── setup_project.py
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── requirements.txt
│   └── comparison_engine/
│       ├── __init__.py
│       ├── text_extractor.py
│       ├── smart_chunker.py
│       ├── semantic_matcher.py
│       └── report_generator.py
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── scripts/
    └── start_local.py
```

### Step 2: Run Setup

```bash
# Navigate to project directory
cd legal-comparator

# Run the automated setup
python setup_project.py
```

This will create all necessary folders and files.

### Step 3: Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Install packages
cd backend
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### Step 4: Install Tesseract (Optional, for OCR)

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**Windows:**
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run installer
3. Add to PATH

**Skip if you only need to compare digital PDFs**

### Step 5: Copy Frontend Files

```bash
# From project root
cp frontend/* backend/static/
```

### Step 6: Start Server

```bash
cd backend
python app.py
```

Or use the quick start script:
```bash
python scripts/start_local.py
```

### Step 7: Open Browser

Navigate to: **http://localhost:8000**

You should see the upload interface!

---

## 🧪 Test the Application

### Test 1: Create Two Text Files

**file1.txt:**
```
This is the first sentence. This is the second sentence.
This is the third sentence.
```

**file2.txt:**
```
This is the first sentence. This is the seccond sentence.
This is the third sentence.
```

### Test 2: Upload and Compare

1. Open http://localhost:8000
2. Drag file1.txt to "Document 1"
3. Drag file2.txt to "Document 2"
4. Click "Compare with AI"
5. Wait 5-10 seconds
6. View results!

**Expected Result:**
- Overall match: ~95%
- 1 difference found: "second" vs "seccond"
- Classification: Minor difference (OCR typo)

---

## 📁 File-by-File Setup Instructions

If you're creating files manually, here's what each file does:

### 1. `setup_project.py`
Creates the complete directory structure. Run this first.

### 2. `backend/requirements.txt`
Lists all Python packages needed. Install with `pip install -r requirements.txt`

### 3. `backend/config.py`
Configuration management. Handles environment variables and paths.

### 4. `backend/app.py`
Main FastAPI application. The web server.

### 5. `backend/comparison_engine/` (4 files)
The core AI engine:
- `text_extractor.py` - Extracts text from PDFs and images
- `smart_chunker.py` - Splits text into sentences
- `semantic_matcher.py` - AI matching logic
- `report_generator.py` - Creates comparison reports

### 6. `frontend/` (3 files)
User interface:
- `index.html` - Main page structure
- `styles.css` - Visual styling
- `app.js` - Interactive functionality

### 7. `scripts/start_local.py`
Automated startup script. Handles all setup steps.

---

## 🔍 Verification Checklist

After setup, verify everything works:

- [ ] **Server starts without errors**
  ```bash
  cd backend
  python app.py
  # Should see: "Server ready at http://0.0.0.0:8000"
  ```

- [ ] **Frontend loads**
  - Open http://localhost:8000
  - See upload interface
  - No console errors

- [ ] **API responds**
  ```bash
  curl http://localhost:8000/api/health
  # Should return: {"status": "healthy", ...}
  ```

- [ ] **Models loaded**
  - Check server logs
  - Should see: "✓ Loaded spaCy model"
  - Should see: "✓ Loaded embedding model" (on first comparison)

- [ ] **File upload works**
  - Drag a file to upload zone
  - File name appears
  - No errors in console

- [ ] **Comparison works**
  - Upload two text files
  - Click compare
  - See results page
  - Verify match percentage

---

## 🐛 Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
pip install -r backend/requirements.txt
```

### Issue: `OSError: [E050] Can't find model 'en_core_web_sm'`

**Solution:**
```bash
python -m spacy download en_core_web_sm
```

### Issue: `TesseractNotFoundError`

**Solution:** Either:
1. Install Tesseract (see Step 4)
2. Or only use digital PDFs (OCR not required)

### Issue: Port 8000 already in use

**Solution:**
```bash
# Use different port
uvicorn app:app --port 8001
```

### Issue: Models take forever to download

**Solution:**
- Be patient (first time takes 2-5 minutes)
- Check internet connection
- Models are ~100MB total

### Issue: Server starts but frontend doesn't load

**Solution:**
```bash
# Make sure frontend files are in backend/static/
cp frontend/* backend/static/

# Or check server logs for file paths
```

---

## 🌐 Next Steps

### For Local Development:
1. ✅ Edit code in your favorite editor
2. ✅ Server auto-reloads on changes (`--reload` flag)
3. ✅ Test with different documents
4. ✅ Check logs for debugging

### For Production Deployment:
1. 📦 Push code to GitHub
2. 🚀 Deploy to Render.com (see README.md)
3. ⚙️ Configure environment variables
4. 🎉 Share your live URL!

### For Feature Development:
1. 🧪 Write tests in `tests/` directory
2. 📝 Update documentation
3. 🔄 Submit pull requests
4. 💡 Suggest improvements

---

## 📚 Additional Resources

### Learn More About:

- **FastAPI**: https://fastapi.tiangolo.com/tutorial/
- **spaCy**: https://spacy.io/usage
- **Sentence Transformers**: https://www.sbert.net/
- **Tesseract OCR**: https://github.com/tesseract-ocr/tesseract/wiki

### Example Documents to Test:

1. **Simple Text Files**
   - Create two versions with minor changes
   - Test exact matching

2. **PDF Documents**
   - Find sample contracts online
   - Test PDF text extraction

3. **Scanned Images**
   - Take a photo of printed text
   - Test OCR capabilities

---

## 💬 Get Help

If you're stuck:

1. **Check the logs**
   ```bash
   # Server logs show detailed errors
   cd backend
   python app.py
   ```

2. **Test each component**
   ```bash
   # Test text extraction
   cd backend/comparison_engine
   python text_extractor.py sample.pdf
   
   # Test chunking
   python smart_chunker.py
   
   # Test matching
   python semantic_matcher.py
   ```

3. **Verify installation**
   ```bash
   # Check all packages installed
   pip list
   
   # Check spaCy model
   python -c "import spacy; spacy.load('en_core_web_sm')"
   
   # Check Tesseract
   tesseract --version
   ```

4. **Start fresh**
   ```bash
   # Delete and recreate venv
   rm -rf venv
   python -m venv venv
   source venv/bin/activate
   pip install -r backend/requirements.txt
   ```

---

## ✅ Success Checklist

You're ready to use the app when:

- [x] Server starts without errors
- [x] http://localhost:8000 loads the interface
- [x] You can upload two files
- [x] Comparison completes successfully
- [x] Results page shows match percentage
- [x] Differences are displayed correctly

---

## 🎉 Congratulations!

You now have a working AI-powered document comparator!

**What you can do:**
- ✅ Compare contract versions
- ✅ Verify physical documents match digital copies
- ✅ Detect OCR errors automatically
- ✅ Get detailed difference reports
- ✅ Deploy to the cloud for free

**Next: Try comparing real documents!**

---

*Need help? Check README.md for more details or create an issue on GitHub.*
