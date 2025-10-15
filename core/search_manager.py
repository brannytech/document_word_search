"""Main search manager with stop functionality"""

from typing import Dict, List, Optional
from pathlib import Path
from searchers import PDFSearcher, DOCXSearcher, DOCSearcher, SearchResult
from utils.helpers import get_all_files, validate_directory
from config import Config


class SearchManager:
    """Coordinate searches across different file types"""
    
    def __init__(self):
        self.searchers = {
            '.pdf': PDFSearcher(),
            '.docx': DOCXSearcher(),
            '.doc': DOCSearcher()
        }
        self.stop_requested = False
        Config.ensure_directories()
    
    def stop_search(self):
        """Stop all ongoing searches"""
        self.stop_requested = True
        for searcher in self.searchers.values():
            searcher.stop_search = True
    
    def reset_stop(self):
        """Reset stop flag for new search"""
        self.stop_requested = False
        for searcher in self.searchers.values():
            searcher.stop_search = False
    
    def search_directory(self, directory: str, keyword: str, 
                        case_sensitive: bool = False,
                        whole_word: bool = False,
                        file_extensions: Optional[List[str]] = None,
                        progress_callback = None) -> Dict[str, List[SearchResult]]:
        """Search for keyword in all supported documents"""
        
        # Reset stop flag at start
        self.reset_stop()
        
        is_valid, message = validate_directory(directory)
        if not is_valid:
            raise ValueError(message)
        
        if file_extensions is None:
            file_extensions = Config.SUPPORTED_EXTENSIONS
        
        all_results = {}
        files = get_all_files(directory, file_extensions)
        total_files = len(files)
        
        for idx, file_path in enumerate(files):
            if self.stop_requested:
                break
            
            if progress_callback:
                progress_callback(idx + 1, total_files, file_path.name)
            
            ext = file_path.suffix.lower()
            if ext not in self.searchers:
                continue
            
            searcher = self.searchers[ext]
            results = searcher.search(str(file_path), keyword, case_sensitive, whole_word)
            
            if results:
                all_results[str(file_path)] = results
        
        return all_results
    
    def get_searcher(self, file_extension: str):
        """Get searcher for file type"""
        return self.searchers.get(file_extension.lower())