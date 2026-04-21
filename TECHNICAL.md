# Technical Documentation

Deep dive into the architecture, implementation details, and design decisions of the Zero Cost Local RAG PDF System.

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface Layer                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Frontend (Vanilla HTML/CSS/JS)                        │ │
│  │  - Dark mode chat interface                            │ │
│  │  - Message history management                          │ │
│  │  - Source visualization                                │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │ HTTP/JSON
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                       API Layer (FastAPI)                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Endpoints: /ask, /health, /rebuild                    │ │
│  │  - Request validation (Pydantic)                       │ │
│  │  - CORS middleware                                     │ │
│  │  - Error handling                                      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG Pipeline Layer                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  RAGPipeline                                           │ │
│  │  - Query orchestration                                 │ │
│  │  - Answer synthesis                                    │ │
│  │  - Source formatting                                   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
              │                              │
              ▼                              ▼
┌────────────────────────┐      ┌────────────────────────────┐
│   Document Processing  │      │   Vector Store (FAISS)     │
│  ┌──────────────────┐  │      │  ┌──────────────────────┐ │
│  │  PDFLoader       │  │      │  │  Embedding Model     │ │
│  │  - pypdf         │  │      │  │  all-MiniLM-L6-v2    │ │
│  │  - Text chunking │  │      │  │  (384 dimensions)    │ │
│  │  - Metadata      │  │      │  └──────────────────────┘ │
│  └──────────────────┘  │      │  ┌──────────────────────┐ │
└────────────────────────┘      │  │  FAISS Index         │ │
                                │  │  - L2 distance       │ │
                                │  │  - Disk persistence  │ │
                                │  └──────────────────────┘ │
                                └────────────────────────────┘
                                            │
                                            ▼
                                ┌────────────────────────┐
                                │  Persistent Storage    │
                                │  - pdf_index.faiss     │
                                │  - metadata.json       │
                                │  - texts.json          │
                                └────────────────────────┘
```

## 📦 Component Details

### 1. PDF Loader (`pdf_loader.py`)

**Purpose:** Extract and chunk text from PDF documents

**Key Classes:**
- `PDFDocument`: Represents a loaded PDF with metadata
- `PDFLoader`: Handles PDF loading and chunking

**Processing Pipeline:**
```python
PDF File → pypdf.PdfReader → Text Extraction → RecursiveCharacterTextSplitter → Chunks
```

**Chunking Strategy:**
```python
Chunk Size: 800 characters (~200 tokens)
Overlap: 150 characters (~37 tokens)
Separators: ["\n\n", "\n", ". ", " ", ""]
```

**Why these values?**
- 800 chars: Large enough for context, small enough for precision
- 150 overlap: Prevents losing context at chunk boundaries
- Recursive separators: Tries to split on paragraphs first, then sentences

**Metadata per chunk:**
```json
{
  "source": "filename.pdf",
  "chunk_id": 5,
  "total_chunks": 42,
  "page_count": 10
}
```

### 2. Vector Store (`vector_store.py`)

**Purpose:** Manage embeddings and similarity search

**Key Components:**

#### Embedding Model
- **Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Output dimension:** 384
- **Max sequence length:** 256 tokens
- **Speed:** ~2000 sentences/sec (CPU)
- **Size:** ~80MB
- **Quality:** Strong for semantic similarity

**Why all-MiniLM-L6-v2?**
1. Optimized for CPU inference
2. Small memory footprint
3. Good performance on STS benchmarks
4. Widely used and well-tested
5. Free and open source

#### FAISS Index
- **Type:** `IndexFlatL2`
- **Distance metric:** L2 (Euclidean)
- **Search complexity:** O(n) where n = number of vectors

**Why IndexFlatL2?**
- Exact search (no approximation)
- Simple and reliable
- Fast for small-medium datasets (<100K vectors)
- No parameter tuning needed

**Similarity Scoring:**
```python
# L2 distance → Similarity score
similarity = exp(-distance)

# Range: 0 to 1
# Higher = more similar
```

**Persistence:**
```python
FAISS Index → binary file (pdf_index.faiss)
Metadata → JSON file (metadata.json)
Chunk texts → JSON file (texts.json)
```

### 3. RAG Pipeline (`rag_pipeline.py`)

**Purpose:** Orchestrate end-to-end question answering

**Query Flow:**
```
User Question
    ↓
Embed Question (sentence-transformers)
    ↓
Search FAISS (top-K retrieval)
    ↓
Filter by Similarity Threshold
    ↓
Synthesize Answer (template-based)
    ↓
Format Sources
    ↓
Return Response
```

**Answer Synthesis Strategy:**

Since we're **not using an LLM**, the answer is synthesized using:

1. **Template-based formatting**
   ```
   Based on the retrieved documents, here's what I found:
   
   [Source 1] file.pdf (Chunk 5, Relevance: 0.87)
   <actual chunk text>
   
   [Source 2] file.pdf (Chunk 12, Relevance: 0.75)
   <actual chunk text>
   
   --- Summary ---
   Found N relevant chunks across M documents.
   ```

2. **Source ranking by similarity**
   - Sort results by similarity score
   - Show top 3 chunks in answer
   - All chunks available in sources array

3. **Context preservation**
   - Each chunk shows ~300 chars preview
   - Full text available in sources
   - Metadata for traceability

**Why no LLM?**
- Zero cost requirement
- Reduces complexity
- Faster responses
- More transparent (shows actual source text)
- Sufficient for many use cases

### 4. API Server (`main.py`)

**Purpose:** Provide REST API for frontend

**Framework:** FastAPI
- Fast, modern, async-capable
- Automatic OpenAPI documentation
- Built-in validation with Pydantic
- Easy CORS configuration

**Endpoints:**

#### `POST /ask`
```python
Request:  {"question": "What is machine learning?"}
Response: {
  "answer": "...",
  "sources": [...],
  "question": "..."
}
```

**Processing:**
1. Validate request (Pydantic)
2. Check index availability
3. Call RAG pipeline
4. Format response
5. Handle errors

#### `GET /health`
```python
Response: {
  "status": "healthy",
  "index_status": "ready",
  "total_vectors": 42,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

#### `POST /rebuild`
```python
Response: {
  "status": "success",
  "message": "Index rebuilt successfully",
  "total_vectors": 42
}
```

**Startup Process:**
```python
1. Initialize FastAPI app
2. Configure CORS
3. Create RAGPipeline instance
4. Load/build vector index (on startup event)
5. Start uvicorn server
```

### 5. Frontend (`index.html`, `style.css`, `app.js`)

**Purpose:** User interface for chat interaction

**Design Principles:**
- **Dark mode only:** Reduces eye strain
- **Minimal aesthetics:** Black/white/gray palette
- **No frameworks:** Vanilla JavaScript for simplicity
- **Responsive:** Works on desktop and mobile

**Key Features:**

1. **Auto-scrolling chat**
   ```javascript
   chatContainer.scrollTop = chatContainer.scrollHeight;
   ```

2. **Expandable sources**
   ```javascript
   Click header → Toggle visibility of source details
   ```

3. **Loading states**
   ```javascript
   Overlay with spinner during API calls
   ```

4. **Error handling**
   ```javascript
   Try-catch with user-friendly error messages
   ```

**API Integration:**
```javascript
fetch('http://localhost:8000/ask', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({question})
})
```

## 🔬 Design Decisions

### Why CPU-Only?

**Pros:**
- Universal compatibility
- Lower barrier to entry
- No GPU drivers needed
- More accessible

**Cons:**
- Slower than GPU
- Limited by CPU speed

**Mitigation:**
- Use efficient model (all-MiniLM-L6-v2)
- Optimize chunking strategy
- Cache embeddings

### Why FAISS Over Alternatives?

**Alternatives considered:**
- Chroma: Too heavy, requires more setup
- Pinecone: Paid service
- Weaviate: Too complex for this use case
- Annoy: Less features than FAISS

**FAISS advantages:**
- Battle-tested (Meta AI)
- CPU and GPU support
- Multiple index types
- Excellent documentation
- Free and open source

### Why No LLM for Answer Generation?

**Reasons:**
1. **Cost:** Free LLMs (Ollama) add complexity
2. **Speed:** Template-based is faster
3. **Transparency:** Users see actual source text
4. **Simplicity:** Fewer dependencies
5. **Reliability:** No hallucination risk

**When to add LLM:**
- Need natural language synthesis
- Complex reasoning required
- Multi-hop question answering
- Abstractive summarization

### Why FastAPI Over Flask?

**FastAPI advantages:**
- Async support (better concurrency)
- Automatic OpenAPI docs
- Built-in validation (Pydantic)
- Modern, type-safe
- Better performance

## 📊 Performance Characteristics

### Time Complexity

| Operation | Complexity | Actual Time |
|-----------|------------|-------------|
| Embed text | O(n) | ~100ms for 1 sentence |
| FAISS search | O(n) | <1ms for 10K vectors |
| Chunk retrieval | O(k) | <1ms |
| Total query | O(n) | ~100-200ms |

### Space Complexity

| Component | Size per Document | Notes |
|-----------|-------------------|-------|
| PDF | Variable | Original file |
| Chunks | ~1.5x text size | With metadata |
| Embeddings | 384 * 4 bytes/vector | ~1.5KB per chunk |
| FAISS index | ~2KB per vector | Including overhead |
| Total | ~3-4KB per chunk | Approximate |

**Example:** 100-page PDF
- Pages: 100
- Text: ~500KB
- Chunks: ~625 (800 chars each)
- Embeddings: ~950KB
- Index: ~1.2MB
- **Total: ~2-3MB**

### Scalability Limits

| Metric | Small | Medium | Large |
|--------|-------|--------|-------|
| PDFs | <10 | 10-100 | 100-1000 |
| Chunks | <1K | 1K-10K | 10K-100K |
| Index size | <10MB | 10-100MB | 100MB-1GB |
| Query time | <100ms | 100-200ms | 200-500ms |
| RAM usage | <1GB | 1-4GB | 4-8GB |

## 🔧 Configuration Guide

### Chunking Parameters

```python
CHUNK_SIZE = 800        # Larger = more context, fewer chunks
CHUNK_OVERLAP = 150     # Larger = more redundancy, better context
```

**Tuning guidelines:**
- **Larger chunks:** Better for broad questions
- **Smaller chunks:** Better for specific facts
- **More overlap:** Better continuity, more storage

### Retrieval Parameters

```python
TOP_K_RETRIEVAL = 5        # More = better coverage, slower
SIMILARITY_THRESHOLD = 0.3  # Higher = more strict
```

**Tuning guidelines:**
- **Higher TOP_K:** More context, but noisier
- **Higher threshold:** More precise, but may miss results
- **Optimal range:** TOP_K=3-7, threshold=0.2-0.5

### Embedding Model Alternatives

| Model | Dimensions | Speed | Quality | Size |
|-------|------------|-------|---------|------|
| all-MiniLM-L6-v2 | 384 | Fast | Good | 80MB |
| all-mpnet-base-v2 | 768 | Medium | Better | 420MB |
| paraphrase-MiniLM-L3-v2 | 384 | Fastest | OK | 61MB |

**To change model:**
```python
# In config.py
EMBEDDING_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
EMBEDDING_DIMENSION = 768  # Update accordingly
```

## 🚀 Optimization Opportunities

### Current Bottlenecks

1. **Embedding generation:** ~80% of query time
2. **JSON serialization:** For large responses
3. **File I/O:** When rebuilding index

### Potential Optimizations

#### 1. Query Caching
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_search(query_hash):
    return vector_store.search(query)
```

**Impact:** 10-100x faster for repeated queries

#### 2. Batch Processing
```python
# Instead of:
for pdf in pdfs:
    process(pdf)

# Use:
process_batch(pdfs)  # Process all at once
```

**Impact:** 2-3x faster indexing

#### 3. Async Endpoints
```python
@app.post("/ask")
async def ask_question(request: QuestionRequest):
    result = await async_rag_pipeline.ask(request.question)
    return result
```

**Impact:** Better concurrency, handles more users

#### 4. Model Quantization
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(MODEL_NAME)
model.half()  # Use FP16 instead of FP32
```

**Impact:** 2x less memory, ~10% faster

## 🧪 Testing Strategy

### Unit Tests
```python
def test_pdf_loader():
    loader = PDFLoader()
    docs = loader.load_all_pdfs()
    assert len(docs) > 0
    
def test_vector_store():
    store = VectorStore()
    chunks = [{"text": "test", "metadata": {}}]
    store.build_index(chunks)
    results = store.search("test")
    assert len(results) > 0
```

### Integration Tests
```python
def test_end_to_end():
    rag = RAGPipeline()
    rag.initialize()
    result = rag.ask("test question")
    assert "answer" in result
    assert len(result["sources"]) >= 0
```

### Performance Tests
```python
import time

start = time.time()
result = rag.ask("What is machine learning?")
latency = time.time() - start

assert latency < 0.5  # Must respond in <500ms
```

## 📚 Further Reading

- [FAISS Documentation](https://faiss.ai/)
- [sentence-transformers Guide](https://www.sbert.net/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [RAG Paper](https://arxiv.org/abs/2005.11401)
- [pypdf Documentation](https://pypdf.readthedocs.io/)

---

**This technical documentation provides the foundation for extending and optimizing the system.**
