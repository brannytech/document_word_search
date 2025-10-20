"""Configuration settings - Updated for Hybrid Search"""

from pathlib import Path
from dataclasses import dataclass
import os


@dataclass
class Config:
    """Application configuration"""
    
    # Supported file types
    SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.doc']
    
    # Search settings
    DEFAULT_CONTEXT_LENGTH = 150
    CHARS_PER_PAGE_ESTIMATE = 3000
    MAX_RESULTS_PER_FILE = 1000
    
    # Parallel processing settings (default - overridden by user settings)
    MIN_FILES_FOR_BATCHING = 50
    BATCH_SIZE = 100
    MAX_WORKERS = min(8, os.cpu_count() or 1)  # For ProcessPool, cap at 8
    
    # Context merging settings
    MAX_SENTENCES_TO_MERGE = 5
    ELLIPSIS_TEXT = "... [gap] ..."
    SENTENCES_BEFORE = 2
    SENTENCES_AFTER = 2
    
    # Search mode
    SEARCH_MODE = "hybrid"  # hybrid, fast_extract, indexed_only
    
    # Index settings
    INDEX_ENABLED = True
    INDEX_PATH = "document_index.db"
    AUTO_INDEX = True
    
    # UI settings
    PAGE_TITLE = "📄 Document Keyword Search Tool"
    PAGE_ICON = "🔍"
    LAYOUT = "wide"
    
    # Highlighting colors
    HIGHLIGHT_COLOR_RGB = (1.0, 1.0, 0.0)  # Yellow
    HIGHLIGHT_COLOR_WORD = 7
    
    # Export settings
    OUTPUT_DIR = Path("search_results")
    TEMP_DIR = Path("temp")
    
    # Cache settings
    CACHE_ENABLED = True
    CACHE_MAX_SIZE_MB = 500
    CACHE_PERSISTENT = False
    AUTO_PREEXTRACT_THRESHOLD = 100
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist"""
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        cls.TEMP_DIR.mkdir(exist_ok=True)
        return cls.OUTPUT_DIR, cls.TEMP_DIR
    
    @classmethod
    def apply_user_settings(cls, settings):
        """Apply user settings to config"""
        # Performance settings
        cls.MAX_WORKERS = settings.performance.max_workers
        cls.BATCH_SIZE = settings.performance.batch_size
        cls.MIN_FILES_FOR_BATCHING = settings.performance.min_files_for_batching
        cls.SEARCH_MODE = settings.performance.search_mode
        
        # Context settings
        cls.SENTENCES_BEFORE = settings.context.sentences_before
        cls.SENTENCES_AFTER = settings.context.sentences_after
        cls.MAX_SENTENCES_TO_MERGE = settings.context.max_merge_distance
        
        # Cache settings
        cls.CACHE_ENABLED = settings.cache.enabled
        cls.CACHE_MAX_SIZE_MB = settings.cache.max_size_mb
        cls.CACHE_PERSISTENT = settings.cache.persistent
        cls.AUTO_PREEXTRACT_THRESHOLD = settings.cache.auto_preextract_threshold
        
        # Index settings
        cls.INDEX_ENABLED = settings.index.enabled
        cls.AUTO_INDEX = settings.index.auto_index
        cls.INDEX_PATH = settings.index.index_path