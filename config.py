from pathlib import Path
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration"""
    
    # Supported file types
    SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.doc']
    
    # Search settings
    DEFAULT_CONTEXT_LENGTH = 150
    CHARS_PER_PAGE_ESTIMATE = 3000
    MAX_RESULTS_PER_FILE = 1000
    
    # UI settings
    PAGE_TITLE = "📄 Document Keyword Search Tool"
    PAGE_ICON = "🔍"
    LAYOUT = "wide"
    
    # Highlighting colors
    HIGHLIGHT_COLOR_RGB = (255, 255, 0)  # Yellow
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