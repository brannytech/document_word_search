"""Configuration settings for the Document Search Tool"""

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
    
    # Parallel processing settings
    MIN_FILES_FOR_BATCHING = 50
    BATCH_SIZE = 150
    MAX_WORKERS = min(64, (os.cpu_count() or 1) * 4)  # Cap at 32 threads
    
    # Context merging settings
    MAX_SENTENCES_TO_MERGE = 5  # Merge matches within 5 sentences
    ELLIPSIS_TEXT = "... [gap] ..."
    
    # UI settings
    PAGE_TITLE = "📄 Document Keyword Search Tool"
    PAGE_ICON = "🔍"
    LAYOUT = "wide"
    
    # Highlighting colors
    HIGHLIGHT_COLOR_RGB = (1.0, 1.0, 0.0)  # Yellow
    HIGHLIGHT_COLOR_WORD = 7  # Word highlight color code
    
    # Export settings
    OUTPUT_DIR = Path("search_results")
    TEMP_DIR = Path("temp")
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist"""
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        cls.TEMP_DIR.mkdir(exist_ok=True)
        return cls.OUTPUT_DIR, cls.TEMP_DIR