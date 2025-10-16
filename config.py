"""Configuration settings for the Document Search Tool"""

from pathlib import Path
from dataclasses import dataclass
import os


@dataclass
class Config:
    """Application configuration - now dynamic based on user settings"""
    
    # Supported file types
    SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.doc']
    
    # Search settings (can be overridden by user settings)
    DEFAULT_CONTEXT_LENGTH = 150
    CHARS_PER_PAGE_ESTIMATE = 3000
    MAX_RESULTS_PER_FILE = 1000
    
    # Default parallel processing settings (overridden by SettingsManager)
    MIN_FILES_FOR_BATCHING = 50
    BATCH_SIZE = 100
    MAX_WORKERS = min(32, (os.cpu_count() or 1) * 4)
    
    # Default context merging settings
    MAX_SENTENCES_TO_MERGE = 5
    ELLIPSIS_TEXT = "... [gap] ..."
    SENTENCES_BEFORE = 2
    SENTENCES_AFTER = 2
    
    # UI settings
    PAGE_TITLE = "📄 Document Keyword Search Tool"
    PAGE_ICON = "🔍"
    LAYOUT = "wide"
    
    # Highlighting colors - FIXED: RGB values must be 0-1, not 0-255
    HIGHLIGHT_COLOR_RGB = (1.0, 1.0, 0.0)  # Yellow (0-1 range for PyMuPDF)
    HIGHLIGHT_COLOR_WORD = 7  # Word highlight color code
    
    # Export settings
    OUTPUT_DIR = Path("search_results")
    TEMP_DIR = Path("temp")
    
    # Cache settings (default)
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
        """
        Apply user settings to config
        
        Args:
            settings: UserSettings object from SettingsManager
        """
        # Apply performance settings
        cls.MAX_WORKERS = settings.performance.max_workers
        cls.BATCH_SIZE = settings.performance.batch_size
        cls.MIN_FILES_FOR_BATCHING = settings.performance.min_files_for_batching
        
        # Apply context settings
        cls.SENTENCES_BEFORE = settings.context.sentences_before
        cls.SENTENCES_AFTER = settings.context.sentences_after
        cls.MAX_SENTENCES_TO_MERGE = settings.context.max_merge_distance
        
        # Apply cache settings
        cls.CACHE_ENABLED = settings.cache.enabled
        cls.CACHE_MAX_SIZE_MB = settings.cache.max_size_mb
        cls.CACHE_PERSISTENT = settings.cache.persistent
        cls.AUTO_PREEXTRACT_THRESHOLD = settings.cache.auto_preextract_threshold