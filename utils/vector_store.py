import json
import numpy as np
from typing import Dict, List, Any
from datetime import datetime
import logging

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
    print("INFO: ChromaDB successfully imported")
except ImportError as e:
    CHROMADB_AVAILABLE = False
    print(f"WARNING: ChromaDB not available - PDF Q&A will be disabled. Error: {e}")
    # Create mock chromadb for graceful degradation
    class MockChromaDB:
        def __init__(self):
            pass
        def get_or_create_collection(self, *args, **kwargs):
            return MockCollection()
        def Client(self, *args, **kwargs):
            return self
    
    class MockCollection:
        def add(self, *args, **kwargs):
            pass
        def query(self, *args, **kwargs):
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
    
    chromadb = MockChromaDB()

class SimpleVectorStore:
    """
    Simple vector storage implementation for agricultural knowledge
    """
    
    def __init__(self, knowledge_file: str = "data/agricultural_knowledge.json"):
        self.knowledge_file = knowledge_file
        self.documents = []
        self.embeddings = []
        self.load_knowledge()
    
    def load_knowledge(self):
        """Load agricultural knowledge from JSON file"""
        try:
            with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.documents = data.get('agricultural_knowledge', [])
            logging.info(f"Loaded {len(self.documents)} documents from knowledge base")
            
        except FileNotFoundError:
            logging.warning(f"Knowledge file {self.knowledge_file} not found")
            self.documents = []
        except json.JSONDecodeError:
            logging.error("Error decoding JSON knowledge file")
            self.documents = []
    
    def simple_text_similarity(self, query: str, document: Dict) -> float:
        """Simple text similarity using keyword matching"""
        query_words = set(query.lower().split())
        doc_text = f"{document.get('title', '')} {document.get('content', '')}"
        doc_words = set(doc_text.lower().split())
        
        # Keyword matching
        keyword_score = 0
        if 'keywords' in document:
            keywords = set([kw.lower() for kw in document['keywords']])
            keyword_score = len(query_words.intersection(keywords)) * 2
        
        # Content matching
        content_score = len(query_words.intersection(doc_words))
        
        return keyword_score + content_score
    
    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search for relevant documents"""
        if not self.documents:
            return []
        
        # Calculate similarity scores
        scored_docs = []
        for doc in self.documents:
            score = self.simple_text_similarity(query, doc)
            if score > 0:
                scored_docs.append((score, doc))
        
        # Sort by score and return top results
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs[:max_results]]
    
    def search_by_category(self, category: str) -> List[Dict]:
        """Search documents by category"""
        # Remove emoji prefix from category for matching
        clean_category = category
        if ' ' in category:
            # Extract the text part after the emoji (e.g., "🌱 Crop Cultivation" -> "Crop Cultivation")
            clean_category = category.split(' ', 1)[1] if len(category.split(' ', 1)) > 1 else category
        
        return [doc for doc in self.documents if doc.get('category', '').lower() == clean_category.lower()]
    
    def get_all_categories(self) -> List[str]:
        """Get all available categories"""
        categories = set()
        for doc in self.documents:
            if 'category' in doc:
                categories.add(doc['category'])
        return list(categories)
    
    def add_document(self, document: Dict):
        """Add a new document to the knowledge base"""
        self.documents.append(document)
    
    def save_knowledge(self):
        """Save knowledge base to file"""
        try:
            data = {
                "agricultural_knowledge": self.documents,
                "metadata": {
                    "version": "1.0",
                    "last_updated": datetime.now().isoformat(),
                    "total_documents": len(self.documents)
                }
            }
            
            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logging.info(f"Saved {len(self.documents)} documents to knowledge base")
            
        except Exception as e:
            logging.error(f"Error saving knowledge base: {e}")

class AgricultureKnowledgeBase:
    """
    Agricultural knowledge management system
    """
    
    def __init__(self):
        self.vector_store = SimpleVectorStore()
    
    def search_knowledge(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search agricultural knowledge"""
        return self.vector_store.search(query, max_results)
    
    def get_relevant_context(self, query: str) -> str:
        """Get relevant context for a query"""
        results = self.search_knowledge(query, 3)
        context = ""
        
        for i, doc in enumerate(results, 1):
            context += f"\n{i}. {doc.get('title', 'Unknown Title')}\n"
            context += f"   {doc.get('content', 'No content available')}\n"
            context += f"   Category: {doc.get('category', 'Unknown')}\n"
        
        return context
    
    def get_category_information(self, category: str) -> List[Dict]:
        """Get all information for a specific category"""
        return self.vector_store.search_by_category(category)
    
    def get_available_categories(self) -> List[str]:
        """Get all available knowledge categories"""
        return self.vector_store.get_all_categories()