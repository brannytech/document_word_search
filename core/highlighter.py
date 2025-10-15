"""Document highlighting functionality"""

import os
from pathlib import Path
from typing import Dict, List
from searchers.base import SearchResult
from config import Config


class DocumentHighlighter:
    """Handle document highlighting"""
    
    def __init__(self, search_manager):
        self.search_manager = search_manager
        self.output_dir = Config.OUTPUT_DIR
    
    def highlight_all_results(self, results: Dict[str, List[SearchResult]], 
                             keyword: str, case_sensitive: bool = False) -> Dict[str, str]:
        """
        Create highlighted versions of all documents with matches
        
        Returns:
            Dict mapping original file paths to highlighted file paths
        """
        highlighted_files = {}
        
        for file_path in results.keys():
            try:
                output_path = self._generate_output_path(file_path, keyword)
                
                ext = Path(file_path).suffix.lower()
                searcher = self.search_manager.get_searcher(ext)
                
                if searcher:
                    success = searcher.highlight_document(
                        file_path, keyword, output_path, case_sensitive
                    )
                    
                    if success:
                        highlighted_files[file_path] = output_path
                        
            except Exception as e:
                print(f"Error highlighting {file_path}: {str(e)}")
        
        return highlighted_files
    
    def _generate_output_path(self, file_path: str, keyword: str) -> str:
        """Generate output path for highlighted document"""
        path = Path(file_path)
        clean_keyword = "".join(c for c in keyword if c.isalnum())[:20]
        new_name = f"{path.stem}_highlighted_{clean_keyword}{path.suffix}"
        return str(self.output_dir / new_name)