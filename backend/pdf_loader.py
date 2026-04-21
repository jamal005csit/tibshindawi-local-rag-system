"""
PDF Loader Module
Handles PDF loading, text extraction, and chunking.
Uses pypdf for zero-cost, local PDF processing.
"""

from pathlib import Path
from typing import List, Dict
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import config


class PDFDocument:
    """Represents a loaded PDF document with metadata."""
    
    def __init__(self, file_path: Path, text: str, page_count: int):
        self.file_path = file_path
        self.file_name = file_path.name
        self.text = text
        self.page_count = page_count
        self.chunks = []


class PDFLoader:
    """Loads and processes PDF files from the data directory."""
    
    def __init__(self, pdf_directory: Path = config.PDF_DIR):
        self.pdf_directory = pdf_directory
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def load_pdf(self, file_path: Path) -> PDFDocument:
        """
        Load a single PDF file and extract text.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            PDFDocument object with extracted text
        """
        print(f"Loading PDF: {file_path.name}")
        
        reader = PdfReader(str(file_path))
        page_count = len(reader.pages)
        
        # Extract text from all pages
        text = ""
        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- Page {page_num} ---\n{page_text}"
        
        return PDFDocument(file_path, text, page_count)
    
    def load_all_pdfs(self) -> List[PDFDocument]:
        """
        Load all PDF files from the configured directory.
        
        Returns:
            List of PDFDocument objects
        """
        pdf_files = list(self.pdf_directory.glob("*.pdf"))
        
        if not pdf_files:
            print(f"WARNING: No PDF files found in {self.pdf_directory}")
            return []
        
        print(f"Found {len(pdf_files)} PDF file(s)")
        
        documents = []
        for pdf_file in pdf_files:
            try:
                doc = self.load_pdf(pdf_file)
                documents.append(doc)
            except Exception as e:
                print(f"ERROR loading {pdf_file.name}: {e}")
        
        return documents
    
    def chunk_documents(self, documents: List[PDFDocument]) -> List[Dict]:
        """
        Split documents into chunks with metadata.
        
        Args:
            documents: List of PDFDocument objects
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        all_chunks = []
        
        for doc in documents:
            # Split text into chunks
            text_chunks = self.text_splitter.split_text(doc.text)
            
            # Create chunk objects with metadata
            for idx, chunk_text in enumerate(text_chunks):
                chunk = {
                    "text": chunk_text,
                    "metadata": {
                        "source": doc.file_name,
                        "chunk_id": idx,
                        "total_chunks": len(text_chunks),
                        "page_count": doc.page_count
                    }
                }
                all_chunks.append(chunk)
        
        print(f"Created {len(all_chunks)} chunks from {len(documents)} document(s)")
        return all_chunks


if __name__ == "__main__":
    # Test the PDF loader
    loader = PDFLoader()
    docs = loader.load_all_pdfs()
    chunks = loader.chunk_documents(docs)
    
    print(f"\nSample chunk:")
    if chunks:
        print(f"Text: {chunks[0]['text'][:200]}...")
        print(f"Metadata: {chunks[0]['metadata']}")
