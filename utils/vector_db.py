import os
import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np
import hashlib
from datetime import datetime

class SimpleVectorDB:
    """
    Simple vector database implementation for agricultural knowledge storage
    """
    
    def __init__(self, db_path: str = "agricultural_vectordb.json"):
        self.db_path = db_path
        self.documents = []
        self.embeddings = []
        self.load_db()
    
    def generate_simple_embedding(self, text: str, dimension: int = 384) -> List[float]:
        """Generate simple hash-based embedding for text"""
        try:
            # Normalize text
            text = text.lower().strip()
            
            # Create multiple hashes for better representation
            hash1 = hashlib.md5(text.encode()).hexdigest()
            hash2 = hashlib.sha1(text.encode()).hexdigest()
            hash3 = hashlib.sha256(text.encode()).hexdigest()
            
            # Combine hashes
            combined_hash = hash1 + hash2 + hash3[:32]  # Total 104 characters
            
            # Convert to numeric values
            embedding = []
            for i in range(0, len(combined_hash), 2):
                try:
                    # Convert hex pairs to integers
                    val = int(combined_hash[i:i+2], 16)
                    embedding.append(val)
                except:
                    embedding.append(0)
            
            # Pad or truncate to desired dimension
            if len(embedding) < dimension:
                embedding.extend([0] * (dimension - len(embedding)))
            else:
                embedding = embedding[:dimension]
            
            # Normalize to unit vector
            embedding = np.array(embedding, dtype=np.float32)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding.tolist()
            
        except Exception as e:
            logging.error(f"Error generating embedding: {str(e)}")
            # Return random normalized vector as fallback
            embedding = np.random.rand(dimension).astype(np.float32)
            return (embedding / np.linalg.norm(embedding)).tolist()
    
    def add_document(self, title: str, content: str, category: str = "", 
                    keywords: List[str] = None, metadata: Dict = None):
        """Add a document to the vector database"""
        try:
            if keywords is None:
                keywords = []
            if metadata is None:
                metadata = {}
            
            # Create document
            doc = {
                'id': len(self.documents),
                'title': title,
                'content': content,
                'category': category,
                'keywords': keywords,
                'metadata': metadata,
                'created_at': datetime.now().isoformat()
            }
            
            # Generate embedding for full text
            full_text = f"{title} {content} {' '.join(keywords)}"
            embedding = self.generate_simple_embedding(full_text)
            
            # Add to storage
            self.documents.append(doc)
            self.embeddings.append(embedding)
            
            # Save to file
            self.save_db()
            
            logging.info(f"Added document: {title}")
            return doc['id']
            
        except Exception as e:
            logging.error(f"Error adding document: {str(e)}")
            return None
    
    def search(self, query: str, limit: int = 5, threshold: float = 0.1) -> List[Dict]:
        """Search for similar documents"""
        try:
            if not self.documents:
                return []
            
            # Generate query embedding
            query_embedding = np.array(self.generate_simple_embedding(query))
            
            # Calculate similarities
            similarities = []
            for i, doc_embedding in enumerate(self.embeddings):
                doc_embedding = np.array(doc_embedding)
                
                # Cosine similarity
                similarity = np.dot(query_embedding, doc_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
                )
                similarities.append((i, similarity))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Filter by threshold and limit
            results = []
            for doc_idx, similarity in similarities[:limit]:
                if similarity >= threshold:
                    doc = self.documents[doc_idx].copy()
                    doc['similarity'] = float(similarity)
                    results.append(doc)
            
            # Fallback to keyword search if no good matches
            if not results:
                results = self.keyword_search(query, limit)
            
            return results
            
        except Exception as e:
            logging.error(f"Error searching documents: {str(e)}")
            return self.keyword_search(query, limit)
    
    def keyword_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Fallback keyword-based search"""
        try:
            query_words = query.lower().split()
            matches = []
            
            for doc in self.documents:
                score = 0
                text_to_search = f"{doc['title']} {doc['content']} {' '.join(doc['keywords'])}".lower()
                
                # Score based on word matches
                for word in query_words:
                    if word in doc['title'].lower():
                        score += 3  # Title matches are more important
                    if word in doc['content'].lower():
                        score += 2  # Content matches
                    if word in ' '.join(doc['keywords']).lower():
                        score += 1  # Keyword matches
                
                if score > 0:
                    doc_copy = doc.copy()
                    doc_copy['similarity'] = score / len(query_words)  # Normalize score
                    matches.append(doc_copy)
            
            # Sort by score and return top results
            matches.sort(key=lambda x: x['similarity'], reverse=True)
            return matches[:limit]
            
        except Exception as e:
            logging.error(f"Error in keyword search: {str(e)}")
            return []
    
    def get_by_category(self, category: str) -> List[Dict]:
        """Get all documents in a specific category"""
        try:
            return [doc for doc in self.documents if doc.get('category') == category]
        except Exception as e:
            logging.error(f"Error getting documents by category: {str(e)}")
            return []
    
    def get_by_id(self, doc_id: int) -> Optional[Dict]:
        """Get document by ID"""
        try:
            for doc in self.documents:
                if doc['id'] == doc_id:
                    return doc
            return None
        except Exception as e:
            logging.error(f"Error getting document by ID: {str(e)}")
            return None
    
    def update_document(self, doc_id: int, **kwargs):
        """Update an existing document"""
        try:
            for i, doc in enumerate(self.documents):
                if doc['id'] == doc_id:
                    # Update document fields
                    for key, value in kwargs.items():
                        if key in doc:
                            doc[key] = value
                    
                    # Regenerate embedding if content changed
                    if 'title' in kwargs or 'content' in kwargs or 'keywords' in kwargs:
                        full_text = f"{doc['title']} {doc['content']} {' '.join(doc.get('keywords', []))}"
                        self.embeddings[i] = self.generate_simple_embedding(full_text)
                    
                    self.save_db()
                    logging.info(f"Updated document: {doc_id}")
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error updating document: {str(e)}")
            return False
    
    def delete_document(self, doc_id: int):
        """Delete a document"""
        try:
            for i, doc in enumerate(self.documents):
                if doc['id'] == doc_id:
                    self.documents.pop(i)
                    self.embeddings.pop(i)
                    self.save_db()
                    logging.info(f"Deleted document: {doc_id}")
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error deleting document: {str(e)}")
            return False
    
    def save_db(self):
        """Save database to file"""
        try:
            db_data = {
                'documents': self.documents,
                'embeddings': self.embeddings,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(db_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logging.error(f"Error saving database: {str(e)}")
    
    def load_db(self):
        """Load database from file"""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    db_data = json.load(f)
                
                self.documents = db_data.get('documents', [])
                self.embeddings = db_data.get('embeddings', [])
                
                logging.info(f"Loaded {len(self.documents)} documents from database")
            else:
                logging.info("No existing database found, starting fresh")
                
        except Exception as e:
            logging.error(f"Error loading database: {str(e)}")
            self.documents = []
            self.embeddings = []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            categories = {}
            for doc in self.documents:
                cat = doc.get('category', 'Unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            return {
                'total_documents': len(self.documents),
                'categories': categories,
                'db_size_mb': os.path.getsize(self.db_path) / 1024 / 1024 if os.path.exists(self.db_path) else 0
            }
            
        except Exception as e:
            logging.error(f"Error getting database stats: {str(e)}")
            return {'total_documents': 0, 'categories': {}, 'db_size_mb': 0}
    
    def bulk_add_documents(self, documents: List[Dict]):
        """Add multiple documents at once"""
        try:
            added_count = 0
            for doc_data in documents:
                doc_id = self.add_document(
                    title=doc_data.get('title', ''),
                    content=doc_data.get('content', ''),
                    category=doc_data.get('category', ''),
                    keywords=doc_data.get('keywords', []),
                    metadata=doc_data.get('metadata', {})
                )
                if doc_id is not None:
                    added_count += 1
            
            logging.info(f"Bulk added {added_count} documents")
            return added_count
            
        except Exception as e:
            logging.error(f"Error in bulk add: {str(e)}")
            return 0
