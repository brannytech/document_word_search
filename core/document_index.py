"""Persistent document index using SQLite for instant searches"""

import sqlite3
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import threading


class DocumentIndex:
    """SQLite-based persistent document index with FTS5 full-text search"""
    
    def __init__(self, db_path: str = "document_index.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Main index table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_index (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    extracted_text TEXT,
                    last_modified REAL,
                    file_size INTEGER,
                    page_count INTEGER,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Full-text search table (FTS5)
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    file_path UNINDEXED,
                    content,
                    tokenize='porter unicode61'
                )
            """)
            
            # Index for fast hash lookup
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_hash 
                ON document_index(file_hash)
            """)
            
            conn.commit()
            conn.close()
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute hash of file based on path, size, and modification time"""
        path = Path(file_path)
        if not path.exists():
            return ""
        
        stat = path.stat()
        hash_string = f"{file_path}|{stat.st_size}|{stat.st_mtime}"
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def is_indexed(self, file_path: str) -> bool:
        """Check if file is indexed and unchanged"""
        current_hash = self._compute_file_hash(file_path)
        if not current_hash:
            return False
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT file_hash FROM document_index WHERE file_path = ?",
                (file_path,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] == current_hash:
                return True
            return False
    
    def get_text(self, file_path: str) -> Optional[str]:
        """Get cached text for file"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT extracted_text FROM document_index WHERE file_path = ?",
                (file_path,)
            )
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
    
    def add_document(self, file_path: str, text: str, page_count: int = 0, 
                    metadata: Dict = None):
        """Add or update document in index"""
        file_hash = self._compute_file_hash(file_path)
        path = Path(file_path)
        
        if not path.exists():
            return
        
        stat = path.stat()
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert or replace in main index
            cursor.execute("""
                INSERT OR REPLACE INTO document_index 
                (file_path, file_hash, extracted_text, last_modified, file_size, 
                 page_count, indexed_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, (
                file_path, file_hash, text, stat.st_mtime, stat.st_size,
                page_count, json.dumps(metadata) if metadata else None
            ))
            
            # Update FTS index
            cursor.execute(
                "INSERT OR REPLACE INTO documents_fts (file_path, content) VALUES (?, ?)",
                (file_path, text)
            )
            
            conn.commit()
            conn.close()
    
    def search_fts(self, query: str, limit: int = 1000) -> List[Tuple[str, str]]:
        """Fast full-text search using FTS5"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT file_path, content, rank
                FROM documents_fts
                WHERE content MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            return [(r[0], r[1]) for r in results]
    
    def get_stats(self) -> Dict:
        """Get index statistics"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*), SUM(file_size) FROM document_index")
            count, total_size = cursor.fetchone()
            
            conn.close()
            
            db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
            
            return {
                'indexed_files': count or 0,
                'total_size_mb': (total_size or 0) / (1024 * 1024),
                'db_size_mb': db_size / (1024 * 1024)
            }
    
    def clear_index(self):
        """Clear all indexed data"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM document_index")
            cursor.execute("DELETE FROM documents_fts")
            
            conn.commit()
            conn.close()
    
    def remove_document(self, file_path: str):
        """Remove document from index"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM document_index WHERE file_path = ?", (file_path,))
            cursor.execute("DELETE FROM documents_fts WHERE file_path = ?", (file_path,))
            
            conn.commit()
            conn.close()