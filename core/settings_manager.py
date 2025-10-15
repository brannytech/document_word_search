"""Settings management with presets and persistence"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class PerformanceSettings:
    """Performance-related settings"""
    max_workers: int = 16
    batch_size: int = 100
    min_files_for_batching: int = 50


@dataclass
class ContextSettings:
    """Context display settings"""
    sentences_before: int = 2
    sentences_after: int = 2
    max_merge_distance: int = 5


@dataclass
class CacheSettings:
    """Cache configuration"""
    enabled: bool = True
    max_size_mb: int = 500
    persistent: bool = False
    auto_preextract_threshold: int = 100


@dataclass
class UserSettings:
    """Complete user settings"""
    performance: PerformanceSettings
    context: ContextSettings
    cache: CacheSettings
    profile: str = "balanced"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'performance': asdict(self.performance),
            'context': asdict(self.context),
            'cache': asdict(self.cache),
            'profile': self.profile
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSettings':
        """Create from dictionary"""
        return cls(
            performance=PerformanceSettings(**data.get('performance', {})),
            context=ContextSettings(**data.get('context', {})),
            cache=CacheSettings(**data.get('cache', {})),
            profile=data.get('profile', 'balanced')
        )


class SettingsManager:
    """Manage user settings with presets and persistence"""
    
    SETTINGS_FILE = Path("user_settings.json")
    
    PRESETS = {
        'low_resource': UserSettings(
            performance=PerformanceSettings(max_workers=2, batch_size=50, min_files_for_batching=50),
            context=ContextSettings(sentences_before=2, sentences_after=2, max_merge_distance=5),
            cache=CacheSettings(enabled=False, max_size_mb=100, persistent=False, auto_preextract_threshold=100),
            profile='low_resource'
        ),
        'balanced': UserSettings(
            performance=PerformanceSettings(max_workers=16, batch_size=100, min_files_for_batching=50),
            context=ContextSettings(sentences_before=2, sentences_after=2, max_merge_distance=5),
            cache=CacheSettings(enabled=True, max_size_mb=500, persistent=False, auto_preextract_threshold=100),
            profile='balanced'
        ),
        'high_performance': UserSettings(
            performance=PerformanceSettings(max_workers=32, batch_size=200, min_files_for_batching=50),
            context=ContextSettings(sentences_before=2, sentences_after=2, max_merge_distance=5),
            cache=CacheSettings(enabled=True, max_size_mb=500, persistent=False, auto_preextract_threshold=100),
            profile='high_performance'
        ),
        'maximum': UserSettings(
            performance=PerformanceSettings(max_workers=64, batch_size=500, min_files_for_batching=30),
            context=ContextSettings(sentences_before=3, sentences_after=3, max_merge_distance=5),
            cache=CacheSettings(enabled=True, max_size_mb=1000, persistent=True, auto_preextract_threshold=50),
            profile='maximum'
        )
    }
    
    @classmethod
    def load_settings(cls) -> UserSettings:
        """Load settings from file or return defaults"""
        if cls.SETTINGS_FILE.exists():
            try:
                with open(cls.SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                return UserSettings.from_dict(data)
            except Exception as e:
                print(f"Error loading settings: {e}")
                return cls.get_preset('balanced')
        return cls.get_preset('balanced')
    
    @classmethod
    def save_settings(cls, settings: UserSettings):
        """Save settings to file"""
        try:
            with open(cls.SETTINGS_FILE, 'w') as f:
                json.dump(settings.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    @classmethod
    def get_preset(cls, preset_name: str) -> UserSettings:
        """Get a preset configuration"""
        return cls.PRESETS.get(preset_name, cls.PRESETS['balanced'])
    
    @classmethod
    def get_preset_names(cls):
        """Get list of preset names"""
        return list(cls.PRESETS.keys())


# ==============================================================================
# FILE: core/cache_manager.py (NEW)
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