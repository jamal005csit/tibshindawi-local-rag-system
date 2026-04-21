"""
RAG Pipeline Module
Orchestrates the complete RAG workflow: retrieval + answer synthesis.
No LLM required - uses retrieved chunks directly.
"""

from typing import List, Dict
from pdf_loader import PDFLoader
from vector_store import VectorStore
import config


class RAGPipeline:
    """
    Complete RAG pipeline for PDF question answering.
    Uses retrieval-only approach without generation LLM.
    """
    
    def __init__(self):
        self.pdf_loader = PDFLoader()
        self.vector_store = VectorStore()
        self.chunks_cache = {}  # Cache for chunk text lookup
    
    def initialize(self, force_rebuild: bool = False):
        """
        Initialize the RAG system: load PDFs and build index.
        
        Args:
            force_rebuild: If True, rebuild index even if it exists
        """
        print("=" * 60)
        print("RAG PIPELINE INITIALIZATION")
        print("=" * 60)
        
        # Check if we need to rebuild
        if not force_rebuild and self.vector_store.exists():
            print("Existing index found. Skipping rebuild.")
            print("Use force_rebuild=True to recreate index.")
            self._load_chunks_cache()
            return
        
        # Load PDFs
        print("\n[1/3] Loading PDF documents...")
        documents = self.pdf_loader.load_all_pdfs()
        
        if not documents:
            print("ERROR: No PDFs loaded. Add PDFs to data/pdfs/ directory.")
            return
        
        # Create chunks
        print("\n[2/3] Chunking documents...")
        chunks = self.pdf_loader.chunk_documents(documents)
        
        # Build cache for fast text lookup
        self._build_chunks_cache(chunks)
        
        # Build vector index
        print("\n[3/3] Building vector index...")
        self.vector_store.build_index(chunks)
        
        print("\n" + "=" * 60)
        print("INITIALIZATION COMPLETE")
        print("=" * 60)
    
    def _build_chunks_cache(self, chunks: List[Dict]):
        """Build cache mapping chunk index to text."""
        self.chunks_cache = {
            idx: chunk["text"] 
            for idx, chunk in enumerate(chunks)
        }
    
    def _load_chunks_cache(self):
        """
        Load chunks from existing metadata.
        This is a simplified version - in production, store texts separately.
        """
        # For this implementation, we'll rebuild chunks from PDFs
        documents = self.pdf_loader.load_all_pdfs()
        chunks = self.pdf_loader.chunk_documents(documents)
        self._build_chunks_cache(chunks)
    
    def ask(self, question: str) -> Dict:
        """
        Answer a question using RAG pipeline.
        
        Args:
            question: User question
            
        Returns:
            Dictionary with answer and sources
        """
        print(f"\n[DEBUG] Question: {question}")
        
        # Retrieve relevant chunks
        results = self.vector_store.search(question, top_k=config.TOP_K_RETRIEVAL)
        
        print(f"[DEBUG] Retrieved {len(results)} results")
        if results:
            print(f"[DEBUG] Top similarity: {results[0]['similarity']:.3f}")
            print(f"[DEBUG] Threshold: {config.SIMILARITY_THRESHOLD}")
        
        if not results:
            return {
                "answer": "I couldn't find relevant information about that in the available documents. Try rephrasing your question or ask about topics covered in the PDFs.",
                "sources": [],
                "question": question
            }
        
        # Synthesize answer from retrieved chunks
        answer = self._synthesize_answer(question, results)
        
        # Format sources with actual text
        sources = self._format_sources(results)
        
        return {
            "answer": answer,
            "sources": sources,
            "question": question
        }
    
    def _synthesize_answer(self, question: str, results: List[Dict]) -> str:
        """
        Synthesize a direct, conversational answer from retrieved chunks.
        Provides a clear answer first, then shows single most relevant reference.
        
        Args:
            question: Original question
            results: Retrieved chunks with similarity scores
            
        Returns:
            Synthesized answer string
        """
        if not results:
            return "I couldn't find relevant information about that in the available documents."
        
        # Sort by similarity to get best match
        results = sorted(results, key=lambda x: x["similarity"], reverse=True)
        
        # Get the most relevant chunk
        best_match = results[0]
        best_text = best_match["text"].strip()
        
        # Extract key information from top chunks
        all_context = "\n".join([r["text"] for r in results[:2]])
        
        # Synthesize direct answer based on the question type
        answer = self._generate_direct_answer(question, best_text, all_context)
        
        # Add single most relevant reference (optional)
        source_name = best_match["metadata"]["source"]
        similarity = best_match["similarity"]
        
        # Only include reference if reasonably relevant
        if similarity > 0.3:
            # Extract a concise snippet (max 150 chars)
            snippet = best_text[:150].strip()
            if len(best_text) > 150:
                snippet += "..."
            
            answer += f"\n\n**Reference:** _{source_name}_ (relevance: {similarity:.0%})\n> {snippet}"
        
        return answer
    
    def _generate_direct_answer(self, question: str, primary_text: str, context: str) -> str:
        """
        Generate a direct answer in conversational style.
        
        Args:
            question: User's question
            primary_text: Most relevant chunk
            context: Combined context from top chunks
            
        Returns:
            Direct answer string
        """
        # Detect question type
        q_lower = question.lower()
        
        # Extract key sentences from the text
        sentences = [s.strip() for s in primary_text.split('.') if s.strip()]
        key_info = '. '.join(sentences[:3]) + '.'
        
        # Handle "what is" questions
        if any(phrase in q_lower for phrase in ['what is', 'what are', 'define']):
            # Find definition-like content
            if len(sentences) > 0:
                return self._format_definition(sentences, context)
        
        # Handle "how" questions
        elif 'how' in q_lower:
            return self._format_how_answer(sentences, context)
        
        # Handle "why" questions
        elif 'why' in q_lower:
            return self._format_why_answer(sentences, context)
        
        # Handle "list" or "types" questions
        elif any(phrase in q_lower for phrase in ['types', 'kinds', 'list', 'examples']):
            return self._format_list_answer(sentences, context)
        
        # Default: provide key information directly
        return self._format_general_answer(sentences, context)
    
    def _format_definition(self, sentences: List[str], context: str) -> str:
        """Format a definition-style answer."""
        if not sentences:
            return "I found relevant information but couldn't extract a clear definition."
        
        # Use first 2 sentences for definition
        definition = '. '.join(sentences[:2]) + '.'
        
        # Add additional context if available
        if len(sentences) > 2:
            extra = sentences[2].strip()
            if extra and len(extra) > 20:
                definition += f" {extra}"
        
        return definition
    
    def _format_how_answer(self, sentences: List[str], context: str) -> str:
        """Format a how-to style answer."""
        if not sentences:
            return "I found relevant information but couldn't extract a clear explanation."
        
        # Combine relevant sentences
        answer = '. '.join(sentences[:3]) + '.'
        return answer
    
    def _format_why_answer(self, sentences: List[str], context: str) -> str:
        """Format an explanation-style answer."""
        if not sentences:
            return "I found relevant information but couldn't extract a clear explanation."
        
        # Provide reasoning from the text
        answer = '. '.join(sentences[:3]) + '.'
        return answer
    
    def _format_list_answer(self, sentences: List[str], context: str) -> str:
        """Format a list-style answer."""
        # Look for list-like patterns in the context
        items = []
        
        # Check for common list patterns
        for sentence in sentences[:5]:
            # Look for enumeration patterns
            if any(marker in sentence.lower() for marker in ['first', 'second', 'third', 'include', 'such as']):
                items.append(sentence.strip())
        
        if items:
            # Format as a coherent answer
            return ' '.join(items)
        
        # Fallback to general answer
        return '. '.join(sentences[:3]) + '.'
    
    def _format_general_answer(self, sentences: List[str], context: str) -> str:
        """Format a general answer."""
        if not sentences:
            return "I found some relevant information, but it doesn't directly answer your question."
        
        # Provide 2-3 key sentences
        answer = '. '.join(sentences[:3]) + '.'
        return answer
    
    def _format_sources(self, results: List[Dict]) -> List[Dict]:
        """
        Format source information for API response.
        Returns only the single most relevant source.
        
        Args:
            results: Retrieved chunks
            
        Returns:
            List with single most relevant source
        """
        if not results:
            return []
        
        # Sort by similarity
        results = sorted(results, key=lambda x: x["similarity"], reverse=True)
        
        # Return only the best match
        best = results[0]
        chunk_text = best["text"] if "text" in best else "[Text not available]"
        
        # Create concise preview (max 200 chars)
        preview = chunk_text[:200].strip()
        if len(chunk_text) > 200:
            preview += "..."
        
        source = {
            "rank": 1,
            "pdf_name": best["metadata"]["source"],
            "chunk_id": best["metadata"]["chunk_id"],
            "similarity_score": round(best["similarity"], 3),
            "text": chunk_text,
            "text_preview": preview
        }
        
        return [source]


if __name__ == "__main__":
    # Test RAG pipeline
    rag = RAGPipeline()
    rag.initialize()
    
    # Test query
    if rag.vector_store.index is not None:
        test_query = "What is machine learning?"
        result = rag.ask(test_query)
        print(f"\nQuestion: {result['question']}")
        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nSources: {len(result['sources'])}")
