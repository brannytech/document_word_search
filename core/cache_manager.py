# ==============================================================================
# FILE: core/cache_manager.py
# ==============================================================================
"""Text caching system for fast repeated searches"""

import hashlib
import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
from collections import OrderedDict


class TextCache:
    """LRU cache for extracted document text"""
    
    def __init__(self, max_size_mb: int = 500, persistent: bool = False):
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.persistent = persistent
        self.cache: OrderedDict[str, Tuple[str, int, datetime]] = OrderedDict()
        self.current_size = 0
        self.cache_dir = Path("cache")
        
        if persistent:
            self.cache_dir.mkdir(exist_ok=True)
            self._load_persistent_cache()
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get hash of file for cache key"""
        path = Path(file_path)
        # Use file path + modification time as key
        stat = path.stat()
        key = f"{file_path}_{stat.st_mtime}_{stat.st_size}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, file_path: str) -> Optional[str]:
        """Get cached text for file"""
        cache_key = self._get_file_hash(file_path)
        
        if cache_key in self.cache:
            # Move to end (most recently used)
            text, size, timestamp = self.cache.pop(cache_key)
            self.cache[cache_key] = (text, size, datetime.now())
            return text
        
        # Try loading from disk if persistent
        if self.persistent:
            disk_path = self.cache_dir / f"{cache_key}.pkl"
            if disk_path.exists():
                try:
                    with open(disk_path, 'rb') as f:
                        text = pickle.load(f)
                    
                    # Add to memory cache
                    size = len(text.encode('utf-8'))
                    self._ensure_space(size)
                    self.cache[cache_key] = (text, size, datetime.now())
                    self.current_size += size
                    return text
                except Exception as e:
                    print(f"Error loading cache from disk: {e}")
        
        return None
    
    def put(self, file_path: str, text: str):
        """Cache text for file"""
        cache_key = self._get_file_hash(file_path)
        size = len(text.encode('utf-8'))
        
        # Remove if already exists
        if cache_key in self.cache:
            old_text, old_size, _ = self.cache.pop(cache_key)
            self.current_size -= old_size
        
        # Ensure we have space
        self._ensure_space(size)
        
        # Add to cache
        self.cache[cache_key] = (text, size, datetime.now())
        self.current_size += size
        
        # Save to disk if persistent
        if self.persistent:
            disk_path = self.cache_dir / f"{cache_key}.pkl"
            try:
                with open(disk_path, 'wb') as f:
                    pickle.dump(text, f)
            except Exception as e:
                print(f"Error saving cache to disk: {e}")
    
    def _ensure_space(self, needed_size: int):
        """Ensure we have space for new entry (LRU eviction)"""
        while self.current_size + needed_size > self.max_size_bytes and self.cache:
            # Remove least recently used
            oldest_key = next(iter(self.cache))
            text, size, timestamp = self.cache.pop(oldest_key)
            self.current_size -= size
            
            # Remove from disk if persistent
            if self.persistent:
                disk_path = self.cache_dir / f"{oldest_key}.pkl"
                if disk_path.exists():
                    disk_path.unlink()
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.current_size = 0
        
        if self.persistent and self.cache_dir.exists():
            for file in self.cache_dir.glob("*.pkl"):
                file.unlink()
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'entries': len(self.cache),
            'size_mb': self.current_size / (1024 * 1024),
            'max_size_mb': self.max_size_mb,
            'usage_percent': (self.current_size / self.max_size_bytes) * 100 if self.max_size_bytes > 0 else 0
        }
    
    def _load_persistent_cache(self):
        """Load persistent cache from disk"""
        if not self.cache_dir.exists():
            return
        
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                with open(cache_file, 'rb') as f:
                    text = pickle.load(f)
                
                size = len(text.encode('utf-8'))
                if self.current_size + size <= self.max_size_bytes:
                    cache_key = cache_file.stem
                    self.cache[cache_key] = (text, size, datetime.now())
                    self.current_size += size
            except Exception as e:
                print(f"Error loading cache file {cache_file}: {e}")