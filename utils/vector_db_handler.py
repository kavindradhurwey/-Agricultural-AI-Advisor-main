import os
import chromadb
from chromadb.config import Settings
# IMPORTANT: Avoid importing sentence_transformers here to prevent PyTorch/torchvision C-extension (_C) errors
# from sentence_transformers import SentenceTransformer  # Not used; disabled to keep Streamlit image slim
try:
    import pypdf as PyPDF2  # New pypdf library
except ImportError:
    try:
        import PyPDF2  # Fallback to old PyPDF2
    except ImportError:
        PyPDF2 = None
import streamlit as st
from typing import List, Dict, Any
import hashlib
import json
from datetime import datetime

class VectorDBHandler:
    """Handler for ChromaDB vector database operations with PDF processing"""
    
    def __init__(self, persist_directory: str = "chroma_db"):
        """Initialize the vector database handler"""
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB with robust error handling and fallbacks
        try:
            # Ensure directory exists
            os.makedirs(persist_directory, exist_ok=True)
            
            # Initialize with safer settings for Docker environments
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )
            )
            
            # Test client connection
            collections = self.client.list_collections()
            
            # Get or create collection with proper error handling
            try:
                self.collection = self.client.get_collection(name="agricultural_documents")
            except Exception:
                # Create new collection if doesn't exist
                self.collection = self.client.create_collection(
                    name="agricultural_documents",
                    metadata={"description": "Agricultural knowledge base documents", "_type": "collection"}
                )
            
            st.success("✅ ChromaDB initialized successfully")
            
        except Exception as e:
            st.error(f"❌ Vector DB initialization failed: {e}")
            st.info("💡 PDF Q&A will be disabled. Other features will work normally.")
            self.client = None
            self.collection = None
        
        # Use Chroma's built-in ONNX embeddings; avoid loading sentence-transformers
        # This prevents PyTorch SDPA version requirements and speeds up startup
        self.embedding_model = None
    
    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text content from PDF file with enhanced error handling"""
        try:
            # Reset file pointer to beginning
            pdf_file.seek(0)
            
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            
            # Check if PDF has pages
            if len(pdf_reader.pages) == 0:
                st.warning("📄 PDF appears to be empty (no pages found)")
                return ""
            
            st.info(f"📄 Found {len(pdf_reader.pages)} pages in PDF")
            
            total_chars = 0
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        cleaned_text = page_text.strip()
                        text += f"\n--- Page {page_num + 1} ---\n{cleaned_text}"
                        total_chars += len(cleaned_text)
                        st.info(f"📄 Page {page_num + 1}: extracted {len(cleaned_text)} characters")
                    else:
                        st.warning(f"⚠️ Page {page_num + 1}: no text content found (might be scanned image)")
                        
                except Exception as e:
                    st.warning(f"⚠️ Could not extract text from page {page_num + 1}: {str(e)}")
            
            if total_chars == 0:
                st.error("❌ No text content found in any PDF pages. This might be a scanned document.")
                st.info("💡 Try using OCR tools for scanned PDFs, or ensure the PDF contains selectable text.")
            
            return text.strip()
            
        except PyPDF2.errors.PdfReadError as e:
            st.error(f"❌ PDF Read Error: {str(e)}")
            st.info("💡 The PDF file might be corrupted or password-protected")
            return ""
        except Exception as e:
            st.error(f"❌ Error processing PDF: {str(e)}")
            st.info("💡 Try a different PDF file or check if the file is readable")
            return ""
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for better retrieval"""
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundaries
            if end < len(text):
                last_period = chunk.rfind('.')
                if last_period > chunk_size * 0.8:  # If period found in last 20%
                    end = start + last_period + 1
                    chunk = text[start:end]
            
            chunks.append(chunk.strip())
            start = end - overlap
        
        return chunks
    
    def add_document(self, filename: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add document to vector database with enhanced error handling and batch processing"""
        try:
            if not self.collection:
                st.error("❌ Vector database not properly initialized")
                return False
                
            if not content or not content.strip():
                st.error("❌ No content to add to database")
                return False
            
            # Check if document already exists
            try:
                existing = self.collection.get(where={"filename": filename})
                if existing['ids']:
                    st.warning(f"⚠️ Document {filename} already exists. Skipping.")
                    return True
            except Exception:
                pass  # Continue if check fails
            
            # Chunk the content using improved chunking
            chunks = self.chunk_text(content, chunk_size=1500, overlap=200)
            
            if not chunks:
                st.error("❌ Failed to create text chunks")
                return False
            
            st.info(f"📊 Processing {len(chunks)} chunks for {filename}")
            
            # Prepare batch data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            
            base_metadata = metadata or {}
            base_metadata.update({
                'filename': filename,
                'upload_date': datetime.now().isoformat(),
                'total_chunks': len(chunks)
            })
            
            for i, chunk in enumerate(chunks):
                chunk_id = hashlib.md5(f"{filename}_{i}_{chunk[:50]}".encode()).hexdigest()
                chunk_metadata = base_metadata.copy()
                chunk_metadata.update({
                    'chunk_index': i,
                    'chunk_id': chunk_id
                })
                
                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append(chunk_metadata)
            
            # Add documents in batches (ChromaDB handles embeddings automatically)
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch_ids = ids[i:i + batch_size]
                batch_docs = documents[i:i + batch_size]
                batch_metas = metadatas[i:i + batch_size]
                
                self.collection.add(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_metas
                )
                
                st.info(f"✅ Added batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")
            
            st.success(f"✅ Successfully added {len(chunks)} chunks from {filename}")
            return True
            
        except Exception as e:
            st.error(f"❌ Error adding document to vector database: {str(e)}")
            return False
    
    def search_documents(self, query: str, top_k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search for relevant documents in the vector database with optional filtering"""
        try:
            if not self.collection:
                return []
            
            # Prepare query parameters
            query_params = {
                "query_texts": [query],
                "n_results": min(top_k, 20),  # Limit to reasonable number
                "include": ["documents", "metadatas", "distances"]
            }
            
            # Add metadata filtering if provided
            if filter_metadata:
                query_params["where"] = filter_metadata
            
            # Perform similarity search
            results = self.collection.query(**query_params)
            
            # Format results with better scoring
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    # Convert distance to similarity score (0-1, higher is better)
                    distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else 1.0
                    similarity_score = max(0, 1 - distance)  # Ensure non-negative
                    
                    formatted_results.append({
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                        'score': similarity_score,
                        'distance': distance
                    })
            
            # Sort by score (highest first)
            formatted_results.sort(key=lambda x: x['score'], reverse=True)
            
            return formatted_results
            
        except Exception as e:
            st.error(f"❌ Error searching documents: {str(e)}")
            return []
    
    def get_document_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the vector database"""
        try:
            if not self.collection:
                return {
                    'total_chunks': 0, 
                    'unique_documents': 0, 
                    'filenames': [],
                    'total_size': 0,
                    'avg_chunk_size': 0
                }
            
            # Get all documents with content for size calculation
            all_docs = self.collection.get(include=["metadatas", "documents"])
            
            if not all_docs['metadatas']:
                return {
                    'total_chunks': 0, 
                    'unique_documents': 0, 
                    'filenames': [],
                    'total_size': 0,
                    'avg_chunk_size': 0
                }
            
            # Extract comprehensive statistics
            filenames = set()
            total_content_size = 0
            
            for i, metadata in enumerate(all_docs['metadatas']):
                if metadata and 'filename' in metadata:
                    filenames.add(metadata['filename'])
                
                # Calculate content size
                if all_docs['documents'] and i < len(all_docs['documents']):
                    total_content_size += len(all_docs['documents'][i])
            
            total_chunks = len(all_docs['metadatas'])
            avg_chunk_size = total_content_size // total_chunks if total_chunks > 0 else 0
            
            return {
                'total_chunks': total_chunks,
                'unique_documents': len(filenames),
                'filenames': list(filenames),
                'total_size': total_content_size,
                'avg_chunk_size': avg_chunk_size
            }
            
        except Exception as e:
            st.error(f"❌ Error getting document stats: {str(e)}")
            return {
                'total_chunks': 0, 
                'unique_documents': 0, 
                'filenames': [],
                'total_size': 0,
                'avg_chunk_size': 0
            }
    
    def delete_document(self, filename: str) -> bool:
        """Delete all chunks of a specific document"""
        try:
            # Find all chunks for this document
            results = self.collection.get(
                where={"filename": filename}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                return True
            
            return False
            
        except Exception as e:
            st.error(f"Error deleting document: {str(e)}")
            return False
    
    def clear_all_documents(self) -> bool:
        """Clear all documents from the database"""
        try:
            self.client.delete_collection("agricultural_documents")
            self.collection = self.client.get_or_create_collection(
                name="agricultural_documents",
                metadata={"hnsw:space": "cosine"}
            )
            return True
        except Exception as e:
            st.error(f"Error clearing documents: {str(e)}")
            return False
