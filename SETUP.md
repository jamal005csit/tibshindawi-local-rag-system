# Setup and Testing Guide

Complete step-by-step guide to set up and test the Zero Cost Local RAG PDF System.

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] Python 3.8 or higher installed
- [ ] pip package manager available
- [ ] At least 8GB RAM (16GB recommended)
- [ ] ~2GB free disk space
- [ ] Internet connection (for initial setup only)

Check versions:
```bash
python3 --version  # Should be 3.8+
pip3 --version     # Should be installed
```

## 🔧 Installation Steps

### Step 1: Navigate to Project Directory

```bash
cd rag-pdf-local-zero-cost
```

### Step 2: Install Dependencies

```bash
cd backend
pip3 install -r requirements.txt --break-system-packages
```

**What gets installed:**
- `fastapi` - Web framework for the API
- `uvicorn` - ASGI server
- `pypdf` - PDF text extraction
- `sentence-transformers` - Embedding model
- `faiss-cpu` - Vector database
- `langchain` - Text processing utilities
- `pydantic` - Data validation
- `numpy` - Numerical operations

**Installation time:** 2-5 minutes (downloads ~500MB)

### Step 3: Verify Installation

```bash
python3 -c "import fastapi, pypdf, sentence_transformers, faiss; print('All dependencies installed successfully!')"
```

You should see: `All dependencies installed successfully!`

## 📁 Directory Structure After Setup

```
rag-pdf-local-zero-cost/
├── backend/
│   ├── main.py
│   ├── rag_pipeline.py
│   ├── pdf_loader.py
│   ├── vector_store.py
│   ├── config.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/
│   ├── pdfs/
│   │   └── sample_ml_guide.pdf  ← Sample PDF included
│   └── vector_store/             ← Will be created on first run
└── README.md
```

## 🚀 First Run

### Step 1: Start Backend Server

```bash
cd backend
python3 main.py
```

**Expected output:**
```
============================================================
SERVER STARTUP
============================================================
Loading embedding model: sentence-transformers/all-MiniLM-L6-v2
Downloading (on first run)... 100%
Found 1 PDF file(s)
Loading PDF: sample_ml_guide.pdf
Created 8 chunks from 1 document(s)
Building FAISS index for 8 chunks...
Batches: 100%|████████████████████████████████| 1/1
Index built with 8 vectors
Index saved to ...
Metadata saved to ...
Texts saved to ...

Server ready at http://0.0.0.0:8000
============================================================

INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**First run notes:**
- Model download: ~30-60 seconds (only happens once)
- Index building: ~5-10 seconds
- Subsequent runs: ~2-3 seconds (loads from disk)

### Step 2: Test API Health

In a **new terminal**:

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "index_status": "ready",
  "total_vectors": 8,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

### Step 3: Test Query via API

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is machine learning?"}'
```

**Expected response:** JSON with answer and sources

### Step 4: Open Frontend

Open `frontend/index.html` in your browser:

```bash
# macOS
open frontend/index.html

# Linux
xdg-open frontend/index.html

# Windows
start frontend/index.html

# Or manually navigate to:
# file:///path/to/rag-pdf-local-zero-cost/frontend/index.html
```

The interface will automatically connect to `http://localhost:8000`.

## ✅ Testing Workflow

### Test 1: Basic Question

**Question:** "What is machine learning?"

**Expected behavior:**
1. Message appears in chat immediately
2. Loading indicator shows
3. Response appears in ~200ms
4. Sources section shows 3-5 relevant chunks
5. Similarity scores are displayed

**What to check:**
- Answer includes relevant information about ML
- Sources reference `sample_ml_guide.pdf`
- Similarity scores are > 0.3

### Test 2: Specific Topic

**Question:** "Explain neural networks"

**Expected behavior:**
- Should retrieve chunks from Section 3 of the PDF
- Higher similarity scores for neural network content
- Answer should be focused and relevant

### Test 3: Types Question

**Question:** "What are the types of machine learning?"

**Expected behavior:**
- Should mention supervised, unsupervised, reinforcement learning
- Multiple relevant chunks retrieved
- Well-structured answer

### Test 4: No Match Query

**Question:** "What is quantum physics?"

**Expected behavior:**
- Message: "No relevant information found in the knowledge base"
- Empty sources array
- Clean error handling (no crash)

### Test 5: Add Your Own PDF

1. Add a PDF to `data/pdfs/`
2. Restart server or call rebuild endpoint:
   ```bash
   curl -X POST http://localhost:8000/rebuild
   ```
3. Ask questions about your PDF
4. Verify sources reference your file

## 🔍 Debugging Guide

### Problem: Server won't start

**Check 1:** Port 8000 is available
```bash
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

**Solution:** Kill process or change port in `config.py`

**Check 2:** Dependencies installed
```bash
pip3 list | grep fastapi
pip3 list | grep sentence-transformers
```

**Solution:** Reinstall dependencies

### Problem: No PDFs loaded

**Check:** PDFs exist in correct directory
```bash
ls data/pdfs/*.pdf
```

**Solution:** Add PDFs to `data/pdfs/`

### Problem: Empty responses

**Check:** Index was built
```bash
ls data/vector_store/
# Should show: pdf_index.faiss, metadata.json, texts.json
```

**Solution:** Restart server to rebuild index

### Problem: Frontend can't connect

**Check:** CORS and server running
```bash
curl http://localhost:8000/
```

**Solution:** Ensure backend is running on port 8000

### Problem: Slow responses

**Possible causes:**
- Large PDF corpus (>1000 pages)
- Low RAM (<8GB)
- High `TOP_K_RETRIEVAL` value

**Solutions:**
- Reduce `TOP_K_RETRIEVAL` in `config.py`
- Increase `SIMILARITY_THRESHOLD`
- Process fewer PDFs

## 📊 Performance Benchmarks

On a typical system (8GB RAM, 4-core CPU):

| Metric | Value |
|--------|-------|
| Startup (first time) | 60s |
| Startup (cached) | 3s |
| Query latency | 100-200ms |
| Embedding time | ~100ms |
| FAISS search | <1ms |
| Index build (10 PDFs) | 15-30s |

## 🔄 Updating the System

### Add New PDFs

```bash
# 1. Add PDFs to directory
cp /path/to/new/*.pdf data/pdfs/

# 2. Rebuild index (Option A: restart server)
# Ctrl+C in backend terminal, then:
python3 main.py

# 2. Rebuild index (Option B: API call)
curl -X POST http://localhost:8000/rebuild
```

### Modify Configuration

1. Edit `backend/config.py`
2. Restart server
3. Index will rebuild automatically

### Update Dependencies

```bash
cd backend
pip3 install -r requirements.txt --upgrade --break-system-packages
```

## 🧪 Advanced Testing

### Load Testing

Test with multiple concurrent queries:

```bash
# Install apache bench (macOS)
brew install httpd

# Run load test (100 requests, 10 concurrent)
ab -n 100 -c 10 -p query.json -T application/json http://localhost:8000/ask
```

Create `query.json`:
```json
{"question": "What is machine learning?"}
```

### Memory Profiling

Monitor memory usage:

```bash
# Install memory profiler
pip3 install memory-profiler

# Profile main script
python3 -m memory_profiler main.py
```

### API Testing with Python

```python
import requests

# Test query
response = requests.post(
    "http://localhost:8000/ask",
    json={"question": "What is machine learning?"}
)

print(f"Status: {response.status_code}")
print(f"Answer: {response.json()['answer'][:200]}...")
print(f"Sources: {len(response.json()['sources'])}")
```

## ✨ Next Steps

After successful setup:

1. **Add your own PDFs** - Replace sample with your documents
2. **Customize styling** - Edit `frontend/style.css`
3. **Tune parameters** - Adjust `config.py` for your use case
4. **Monitor performance** - Use `/health` endpoint
5. **Extend functionality** - Add features from README Future Improvements

## 📝 Checklist: Setup Complete

- [ ] Dependencies installed
- [ ] Backend starts without errors
- [ ] Health endpoint returns `healthy`
- [ ] Sample query works via API
- [ ] Frontend loads and connects
- [ ] Chat interface responds to queries
- [ ] Sources display correctly
- [ ] Can add and query custom PDFs

**If all checked: Setup complete! 🎉**

---

For additional help, see README.md or check troubleshooting section.
