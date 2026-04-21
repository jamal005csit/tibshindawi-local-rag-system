"""
Configuration Module
Central config for RAG PDF system with zero external dependencies.
"""

import os
from pathlib import Path

# Project Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR = DATA_DIR / "pdfs"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"

# Ensure directories exist
PDF_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

# Embedding Model (Local CPU-friendly)
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # all-MiniLM-L6-v2 output dimension

# Text Chunking Parameters
CHUNK_SIZE = 800  # characters (approx 200 tokens)
CHUNK_OVERLAP = 150  # character overlap between chunks

# Retrieval Parameters
TOP_K_RETRIEVAL = 3  # Number of chunks to retrieve (reduced for precision)
SIMILARITY_THRESHOLD = 0.1  # Minimum similarity score (0-1) - lowered to ensure matches

# Server Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# FAISS Index Settings
FAISS_INDEX_NAME = "pdf_index.faiss"
METADATA_FILE_NAME = "metadata.json"
