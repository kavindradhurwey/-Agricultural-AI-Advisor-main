"""
Persistent Storage Manager for Government Schemes
Handles SQLite database operations for scraped government schemes
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os

class SchemeStorageManager:
    """
    Manages persistent storage of government schemes in SQLite database
    """
    
    def __init__(self, db_path: str = "data/schemes.db"):
        self.db_path = db_path
        self.ensure_data_directory()
        self.init_database()
    
    def ensure_data_directory(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create schemes table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schemes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        source_url TEXT,
                        category TEXT,
                        keywords TEXT,  -- JSON string
                        relevance_score INTEGER DEFAULT 0,
                        scraped_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')
                
                # Create scraping_logs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scraping_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        scraping_started_at TIMESTAMP,
                        scraping_completed_at TIMESTAMP,
                        schemes_found INTEGER DEFAULT 0,
                        schemes_added INTEGER DEFAULT 0,
                        schemes_updated INTEGER DEFAULT 0,
                        status TEXT,  -- 'success', 'partial', 'failed'
                        error_message TEXT,
                        scraping_source TEXT DEFAULT 'manual'  -- 'manual', 'scheduled'
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_schemes_title ON schemes(title)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_schemes_category ON schemes(category)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_schemes_active ON schemes(is_active)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_date ON scraping_logs(scraping_started_at)')
                
                conn.commit()
                logging.info("Database initialized successfully")
                
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
    
    def save_schemes(self, schemes: List[Dict[str, Any]], scraping_source: str = "manual") -> Dict[str, int]:
        """
        Save scraped schemes to database
        Returns dict with counts of added/updated schemes
        """
        stats = {"added": 0, "updated": 0, "errors": 0}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for scheme in schemes:
                    try:
                        # Check if scheme already exists
                        cursor.execute(
                            "SELECT id, updated_at FROM schemes WHERE title = ? AND is_active = 1",
                            (scheme.get('title', ''),)
                        )
                        existing = cursor.fetchone()
                        
                        # Prepare data
                        keywords_json = json.dumps(scheme.get('keywords', []))
                        scraped_at = scheme.get('scraped_at', datetime.now().isoformat())
                        
                        if existing:
                            # Update existing scheme
                            cursor.execute('''
                                UPDATE schemes SET
                                    description = ?,
                                    source_url = ?,
                                    category = ?,
                                    keywords = ?,
                                    relevance_score = ?,
                                    scraped_at = ?,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', (
                                scheme.get('description', ''),
                                scheme.get('source_url', ''),
                                scheme.get('category', ''),
                                keywords_json,
                                scheme.get('relevance_score', 0),
                                scraped_at,
                                existing[0]
                            ))
                            stats["updated"] += 1
                        else:
                            # Insert new scheme
                            cursor.execute('''
                                INSERT INTO schemes (
                                    title, description, source_url, category,
                                    keywords, relevance_score, scraped_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                scheme.get('title', ''),
                                scheme.get('description', ''),
                                scheme.get('source_url', ''),
                                scheme.get('category', ''),
                                keywords_json,
                                scheme.get('relevance_score', 0),
                                scraped_at
                            ))
                            stats["added"] += 1
                    
                    except Exception as e:
                        logging.error(f"Error saving scheme '{scheme.get('title', 'Unknown')}': {e}")
                        stats["errors"] += 1
                
                conn.commit()
                
                # Log the scraping operation
                self.log_scraping_operation(
                    schemes_found=len(schemes),
                    schemes_added=stats["added"],
                    schemes_updated=stats["updated"],
                    status="success" if stats["errors"] == 0 else "partial",
                    error_message=f"{stats['errors']} errors occurred" if stats["errors"] > 0 else None,
                    scraping_source=scraping_source
                )
                
        except Exception as e:
            logging.error(f"Error saving schemes to database: {e}")
            self.log_scraping_operation(
                schemes_found=len(schemes),
                status="failed",
                error_message=str(e),
                scraping_source=scraping_source
            )
            stats["errors"] = len(schemes)
        
        return stats
    
    def get_all_schemes(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Retrieve all schemes from database"""
        schemes = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM schemes"
                if active_only:
                    query += " WHERE is_active = 1"
                query += " ORDER BY relevance_score DESC, updated_at DESC"
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                # Get column names
                columns = [desc[0] for desc in cursor.description]
                
                for row in rows:
                    scheme = dict(zip(columns, row))
                    # Parse JSON keywords
                    try:
                        scheme['keywords'] = json.loads(scheme['keywords']) if scheme['keywords'] else []
                    except:
                        scheme['keywords'] = []
                    schemes.append(scheme)
                    
        except Exception as e:
            logging.error(f"Error retrieving schemes from database: {e}")
        
        return schemes
    
    def search_schemes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search schemes by title, description, or keywords"""
        schemes = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                search_query = f"%{query.lower()}%"
                cursor.execute('''
                    SELECT * FROM schemes 
                    WHERE is_active = 1 AND (
                        LOWER(title) LIKE ? OR 
                        LOWER(description) LIKE ? OR 
                        LOWER(keywords) LIKE ?
                    )
                    ORDER BY relevance_score DESC, updated_at DESC
                    LIMIT ?
                ''', (search_query, search_query, search_query, limit))
                
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                for row in rows:
                    scheme = dict(zip(columns, row))
                    try:
                        scheme['keywords'] = json.loads(scheme['keywords']) if scheme['keywords'] else []
                    except:
                        scheme['keywords'] = []
                    schemes.append(scheme)
                    
        except Exception as e:
            logging.error(f"Error searching schemes: {e}")
        
        return schemes
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about stored schemes"""
        stats = {
            "total_schemes": 0,
            "active_schemes": 0,
            "last_update": None,
            "last_scraping": None,
            "database_size": 0
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count schemes
                cursor.execute("SELECT COUNT(*) FROM schemes")
                stats["total_schemes"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM schemes WHERE is_active = 1")
                stats["active_schemes"] = cursor.fetchone()[0]
                
                # Get last update
                cursor.execute("SELECT MAX(updated_at) FROM schemes")
                last_update = cursor.fetchone()[0]
                if last_update:
                    stats["last_update"] = last_update
                
                # Get last scraping
                cursor.execute("SELECT MAX(scraping_completed_at) FROM scraping_logs")
                last_scraping = cursor.fetchone()[0]
                if last_scraping:
                    stats["last_scraping"] = last_scraping
            
            # Get database file size
            if os.path.exists(self.db_path):
                stats["database_size"] = os.path.getsize(self.db_path)
                
        except Exception as e:
            logging.error(f"Error getting storage stats: {e}")
        
        return stats
    
    def log_scraping_operation(self, schemes_found: int = 0, schemes_added: int = 0, 
                             schemes_updated: int = 0, status: str = "success",
                             error_message: str = None, scraping_source: str = "manual"):
        """Log a scraping operation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO scraping_logs (
                        scraping_started_at, scraping_completed_at, schemes_found,
                        schemes_added, schemes_updated, status, error_message, scraping_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    schemes_found,
                    schemes_added,
                    schemes_updated,
                    status,
                    error_message,
                    scraping_source
                ))
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"Error logging scraping operation: {e}")
    
    def get_scraping_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent scraping history"""
        history = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM scraping_logs 
                    ORDER BY scraping_started_at DESC 
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                for row in rows:
                    history.append(dict(zip(columns, row)))
                    
        except Exception as e:
            logging.error(f"Error getting scraping history: {e}")
        
        return history
    
    def clear_old_schemes(self, days_old: int = 90):
        """Mark old schemes as inactive"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
                
                cursor.execute('''
                    UPDATE schemes SET is_active = 0 
                    WHERE updated_at < ? AND is_active = 1
                ''', (cutoff_date,))
                
                affected_rows = cursor.rowcount
                conn.commit()
                
                logging.info(f"Marked {affected_rows} old schemes as inactive")
                return affected_rows
                
        except Exception as e:
            logging.error(f"Error clearing old schemes: {e}")
            return 0
