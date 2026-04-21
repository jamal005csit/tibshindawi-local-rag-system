"""
Vector Store Module
Manages FAISS vector database for similarity search.
Handles embeddings, indexing, and persistence.
"""

import json
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
import config


class VectorStore:
    """
    FAISS-based vector store for semantic search.
    Stores embeddings with metadata persistence.
    """
    
    def __init__(self):
        self.index_path = config.VECTOR_STORE_DIR / config.FAISS_INDEX_NAME
        self.metadata_path = config.VECTOR_STORE_DIR / config.METADATA_FILE_NAME
        self.texts_path = config.VECTOR_STORE_DIR / "texts.json"
        
        # Load embedding model (local, CPU-friendly)
        print(f"Loading embedding model: {config.EMBEDDING_MODEL_NAME}")
        self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
        
        # Initialize FAISS index, metadata, and texts
        self.index = None
        self.metadata = []
        self.texts = []  # Store actual chunk texts
        
        # Load existing index if available
        self.load()
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            Numpy array of embeddings (n_texts x embedding_dim)
        """
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings
    
    def build_index(self, chunks: List[Dict]):
        """
        Build FAISS index from document chunks.
        
        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata'
        """
        if not chunks:
            print("WARNING: No chunks provided. Index not built.")
            return
        
        print(f"Building FAISS index for {len(chunks)} chunks...")
        
        # Extract texts
        texts = [chunk["text"] for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.embed_texts(texts)
        
        # Create FAISS index (L2 distance)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        
        # Add embeddings to index
        self.index.add(embeddings.astype('float32'))
        
        # Store metadata and texts
        self.metadata = [chunk["metadata"] for chunk in chunks]
        self.texts = texts  # Store chunk texts
        
        print(f"Index built with {self.index.ntotal} vectors")
        
        # Save to disk
        self.save()
    
    def search(self, query: str, top_k: int = config.TOP_K_RETRIEVAL) -> List[Dict]:
        """
        Search for similar chunks using semantic similarity.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            
        Returns:
            List of result dictionaries with text, metadata, and similarity score
        """
        if self.index is None or self.index.ntotal == 0:
            print("WARNING: Index is empty. Cannot search.")
            return []
        
        print(f"[DEBUG] Searching index with {self.index.ntotal} vectors")
        
        # Embed query
        query_embedding = self.embed_texts([query])
        
        # Search FAISS index
        distances, indices = self.index.search(
            query_embedding.astype('float32'),
            min(top_k, self.index.ntotal)
        )
        
        print(f"[DEBUG] Raw distances: {distances[0]}")
        
        # Convert L2 distances to similarity scores (0-1 range)
        # Lower distance = higher similarity
        # Using negative exponential: similarity = e^(-distance)
        similarities = np.exp(-distances[0])
        
        print(f"[DEBUG] Converted similarities: {similarities}")
        
        # Build results
        results = []
        for idx, similarity in zip(indices[0], similarities):
            if idx < len(self.metadata):  # Validate index
                result = {
                    "text": self.texts[idx] if idx < len(self.texts) else "[Text not available]",
                    "metadata": self.metadata[idx],
                    "similarity": float(similarity)
                }
                results.append(result)
        
        print(f"[DEBUG] Before filtering: {len(results)} results")
        
        # Filter by threshold
        results = [r for r in results if r["similarity"] >= config.SIMILARITY_THRESHOLD]
        
        print(f"[DEBUG] After filtering: {len(results)} results")
        
        return results
    
    def save(self):
        """Save FAISS index, metadata, and texts to disk."""
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_path))
            print(f"Index saved to {self.index_path}")
        
        if self.metadata:
            with open(self.metadata_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            print(f"Metadata saved to {self.metadata_path}")
        
        if self.texts:
            with open(self.texts_path, 'w') as f:
                json.dump(self.texts, f)
            print(f"Texts saved to {self.texts_path}")
    
    def load(self):
        """Load FAISS index, metadata, and texts from disk if they exist."""
        if self.index_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                print(f"Loaded index with {self.index.ntotal} vectors")
            except Exception as e:
                print(f"Error loading index: {e}")
        
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, 'r') as f:
                    self.metadata = json.load(f)
                print(f"Loaded metadata for {len(self.metadata)} chunks")
            except Exception as e:
                print(f"Error loading metadata: {e}")
        
        if self.texts_path.exists():
            try:
                with open(self.texts_path, 'r') as f:
                    self.texts = json.load(f)
                print(f"Loaded texts for {len(self.texts)} chunks")
            except Exception as e:
                print(f"Error loading texts: {e}")
    
    def exists(self) -> bool:
        """Check if a saved index exists."""
        return (self.index_path.exists() and 
                self.metadata_path.exists() and 
                self.texts_path.exists())


if __name__ == "__main__":
    # Test vector store
    store = VectorStore()
    
    # Test embedding
    test_texts = ["This is a test sentence.", "Another test sentence."]
    embeddings = store.embed_texts(test_texts)
    print(f"Generated embeddings shape: {embeddings.shape}")
