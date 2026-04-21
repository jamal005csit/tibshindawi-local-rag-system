"""
FastAPI Server
Main entry point for the RAG PDF API.
Provides REST endpoints for question answering.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from rag_pipeline import RAGPipeline
import config


# Pydantic Models for API
class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str
    sources: list
    question: str


# Initialize FastAPI app
app = FastAPI(
    title="Zero Cost Local RAG PDF System",
    description="Local RAG system for PDF question answering - No paid APIs required",
    version="1.0.0"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG pipeline (global instance)
rag_pipeline = RAGPipeline()


@app.on_event("startup")
async def startup_event():
    """Initialize RAG pipeline on server startup."""
    print("\n" + "=" * 60)
    print("SERVER STARTUP")
    print("=" * 60)
    rag_pipeline.initialize()
    print(f"\nServer ready at http://{config.API_HOST}:{config.API_PORT}")
    print("=" * 60 + "\n")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "system": "Zero Cost Local RAG PDF System",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check with system status."""
    index_status = "ready" if rag_pipeline.vector_store.index is not None else "not_initialized"
    
    return {
        "status": "healthy",
        "index_status": index_status,
        "total_vectors": rag_pipeline.vector_store.index.ntotal if rag_pipeline.vector_store.index else 0,
        "embedding_model": config.EMBEDDING_MODEL_NAME
    }


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """
    Answer a question using RAG pipeline.
    
    Args:
        request: QuestionRequest with question field
        
    Returns:
        AnswerResponse with answer, sources, and original question
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    # Check if index is ready
    if rag_pipeline.vector_store.index is None:
        raise HTTPException(
            status_code=503,
            detail="Vector index not initialized. Add PDFs to data/pdfs/ and restart server."
        )
    
    try:
        # Get answer from RAG pipeline
        result = rag_pipeline.ask(request.question)
        return result
    
    except Exception as e:
        print(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/rebuild")
async def rebuild_index():
    """
    Rebuild the vector index from PDFs.
    Useful when PDFs are added/removed.
    """
    try:
        print("\nRebuilding index...")
        rag_pipeline.initialize(force_rebuild=True)
        
        return {
            "status": "success",
            "message": "Index rebuilt successfully",
            "total_vectors": rag_pipeline.vector_store.index.ntotal if rag_pipeline.vector_store.index else 0
        }
    
    except Exception as e:
        print(f"Error rebuilding index: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rebuild index: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unexpected errors."""
    print(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"}
    )


if __name__ == "__main__":
    # Run server
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=False,  # Disable in production
        log_level="info"
    )
