# 📄 Legal Document Comparator

**Smart Context-Aware Document Verification with AI**

Compare physical documents (via OCR) with digital versions using intelligent semantic matching. No more line-by-line comparison - this tool understands context and meaning.

---

## 🎯 What It Does

- **Smart Matching**: Compares documents by meaning, not just text position
- **Context-Aware**: Understands "sentence 3" regardless of line breaks or formatting
- **OCR Support**: Scans physical documents and matches with digital copies
- **Detailed Reports**: Shows exactly where and why documents differ
- **AI-Powered**: Uses sentence transformers for semantic understanding

---

## 🚀 Quick Start (3 Steps)

### Option 1: Automated Setup (Recommended)

```bash
# 1. Run the setup script
python setup_project.py

# 2. Start local server
python scripts/start_local.py

# 3. Open browser
# http://localhost:8000
```

### Option 2: Manual Setup

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 2. Install Tesseract (for OCR)
# macOS:
brew install tesseract

# Ubuntu/Debian:
sudo apt-get install tesseract-ocr

# Windows:
# Download from: https://github.com/UB-Mannheim/tesseract/wiki

# 3. Copy frontend files
cp frontend/* backend/static/

# 4. Start server
python app.py
# OR
uvicorn app:app --reload --port 8000
```

---

## 📦 What Gets Installed

### Python Packages (~150MB total)
- **FastAPI**: Web framework (lightweight)
- **Tesseract**: OCR engine (needs system install)
- **spaCy**: Sentence segmentation (~12MB model)
- **Sentence Transformers**: Semantic matching (~80MB model)
- **PyMuPDF**: PDF text extraction
- **Pillow**: Image processing

### System Requirements
- Python 3.7+
- 2GB RAM (recommended)
- Tesseract OCR (optional, for scanned documents)

---

## 🏗️ Project Structure

```
legal-comparator/
├── setup_project.py              # Project setup script
├── README.md                     # This file
├── Dockerfile                    # Production deployment
├── render.yaml                   # Render.com config
├── .env.example                  # Environment template
│
├── backend/
│   ├── app.py                    # Main FastAPI server
│   ├── config.py                 # Configuration
│   ├── requirements.txt          # Python dependencies
│   │
│   ├── comparison_engine/
│   │   ├── __init__.py
│   │   ├── text_extractor.py    # PDF + OCR extraction
│   │   ├── smart_chunker.py     # Sentence segmentation
│   │   ├── semantic_matcher.py  # AI matching
│   │   └── report_generator.py  # Results formatting
│   │
│   ├── static/                   # Frontend files (auto-copied)
│   └── uploads/                  # Temporary file storage
│
├── frontend/
│   ├── index.html               # Main UI
│   ├── styles.css               # Styling
│   └── app.js                   # Frontend logic
│
├── scripts/
│   └── start_local.py           # Quick start script
│
└── tests/                        # Unit tests (future)
```

---

## 💡 How It Works

### The Smart Matching Process

```
1. Text Extraction
   ↓
   [PDF/Image] → Extract Text → Clean Text

2. Smart Chunking
   ↓
   Text → Sentence Segmentation (spaCy) → List of Sentences

3. Semantic Matching
   ↓
   Sentences → AI Embeddings → Similarity Matrix → Best Matches

4. Context Validation
   ↓
   Matches → Check Ordering → Verify Context → Final Matches

5. Report Generation
   ↓
   Matches + Differences → Detailed Report
```

### Why Context-Aware Matters

**Traditional Line-by-Line:**
```
❌ Line 5 in Doc1 ≠ Line 5 in Doc2 → MISMATCH
   (Even if it's the same sentence, just different line breaks)
```

**Our Semantic Approach:**
```
✅ Sentence 3 in Doc1 ≈ Sentence 3 in Doc2 → MATCH (96% similar)
   (Understands content, ignores formatting)
```

---

## 🎨 Usage Examples

### Example 1: Digital-to-Digital Comparison
```
Document 1 (PDF): Contract v1.pdf
Document 2 (PDF): Contract v2.pdf

Result: 95.2% match
- 3 sentences reworded
- 1 clause added
- No OCR errors
```

### Example 2: Physical-to-Digital with OCR
```
Document 1 (Scan): physical_contract.jpg
Document 2 (PDF): digital_contract.pdf

Result: 89.7% match
- 2 OCR typos detected ("herby" → "hereby")
- 1 sentence missing (OCR failed to capture)
- 45 sentences matched perfectly
```

---

## 🌐 Deployment

### Deploy to Render.com (Free Tier)

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_REPO_URL
   git push -u origin main
   ```

2. **Connect to Render.com**
   - Go to https://render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Render will auto-detect `render.yaml`
   - Click "Create Web Service"

3. **Wait for deployment** (~5-10 minutes)
   - Render builds Docker image
   - Downloads ML models
   - Deploys to free tier

4. **Your app is live!**
   ```
   https://your-app-name.onrender.com
   ```

### Performance on Free Tier

- **Cold start**: 15-30 seconds (first request after idle)
- **Warm requests**: 5-10 seconds per comparison
- **RAM usage**: ~400MB (fits in 512MB limit)
- **Monthly limit**: ~1000 comparisons

### Upgrade Options

| Tier | Cost | RAM | Performance |
|------|------|-----|-------------|
| Free | $0/mo | 512MB | Good for testing |
| Starter | $7/mo | 2GB | Faster, no cold starts |
| Standard | $25/mo | 4GB | Production-ready |

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```bash
# Server
DEBUG=True
HOST=0.0.0.0
PORT=8000

# File Upload
MAX_UPLOAD_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=pdf,png,jpg,jpeg

# Models
SPACY_MODEL=en_core_web_sm
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2

# Matching
SIMILARITY_THRESHOLD=0.85  # 85% match required
CONTEXT_WINDOW=2  # Check ±2 sentences for context
```

---

## 🧪 API Documentation

Once running, visit:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

### Key Endpoints

#### `POST /api/compare`
Compare two documents

**Request:**
```bash
curl -X POST http://localhost:8000/api/compare \
  -F "file1=@document1.pdf" \
  -F "file2=@document2.pdf"
```

**Response:**
```json
{
  "summary": {
    "overall_match": 94.2,
    "matched_sentences": 47,
    "exact_matches": 45,
    "significant_differences": 3
  },
  "verdict": {
    "status": "very_similar",
    "message": "Documents are very similar with minor differences"
  },
  "differences": [
    {
      "type": "mismatch",
      "severity": "low",
      "sentence1": "The party hereby agrees...",
      "sentence2": "The party herby agrees...",
      "similarity": 0.96,
      "suggestions": ["Possible OCR error: 'hereby' → 'herby'"]
    }
  ]
}
```

---

## 📊 Features Roadmap

### ✅ Phase 1: MVP (Current)
- [x] Text extraction (PDF)
- [x] Smart sentence chunking
- [x] Semantic matching
- [x] Basic OCR support
- [x] Web interface
- [x] Detailed reports

### 🚧 Phase 2: Enhanced OCR (Next)
- [ ] Image preprocessing (deskew, enhance)
- [ ] OCR confidence scoring
- [ ] Multi-page document handling
- [ ] OCR error correction

### 🔮 Phase 3: Advanced Features (Future)
- [ ] Batch document comparison
- [ ] User accounts & history
- [ ] API authentication
- [ ] Export reports (PDF, Word)
- [ ] Custom similarity thresholds
- [ ] Legal clause detection
- [ ] Multi-language support

### 💰 Phase 4: Freemium (Later)
- [ ] Free: 10 comparisons/day
- [ ] Pro: Unlimited comparisons
- [ ] Business: API access + analytics

---

## 🐛 Troubleshooting

### Common Issues

**1. Models not downloading**
```bash
# Manually download spaCy model
python -m spacy download en_core_web_sm

# Sentence transformer will auto-download on first use
```

**2. Tesseract not found**
```bash
# macOS
brew install tesseract

# Ubuntu
sudo apt-get install tesseract-ocr

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH
```

**3. Port already in use**
```bash
# Use a different port
uvicorn app:app --port 8001
```

**4. Memory errors on free tier**
- Reduce document size
- Use smaller images
- Limit to 5-10 pages per document

**5. Slow performance**
- First request loads models (30-60 seconds)
- Subsequent requests are faster (5-10 seconds)
- Consider paid tier for production

---

## 🤝 Contributing

This is a focused tool. Keep it simple:
- ✅ Bug fixes welcome
- ✅ Performance improvements
- ✅ Documentation updates
- ❌ No feature creep
- ❌ Keep dependencies minimal

---

## 📝 License

MIT License - Free to use and modify

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [spaCy](https://spacy.io/) - NLP
- [Sentence Transformers](https://www.sbert.net/) - Semantic similarity
- [Tesseract](https://github.com/tesseract-ocr/tesseract) - OCR
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF processing

---

## 📞 Support

- 📖 **Documentation**: Check `/docs` endpoint when running
- 🐛 **Issues**: Report on GitHub
- 💬 **Questions**: Create a discussion

---

**Made with ❤️ for lawyers, paralegals, and anyone comparing documents**

*"Because nobody should manually compare documents line by line anymore"*
