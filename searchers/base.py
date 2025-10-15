"""Abstract base class for document searchers"""

import re
from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Data class to store individual search results"""
    file_path: str
    file_name: str
    page_number: int
    context: str
    match_start: int
    match_end: int
    absolute_position: int
    matched_text: str


class BaseSearcher(ABC):
    """Abstract base class for document searchers"""
    
    @abstractmethod
    def search(self, file_path: str, keyword: str, 
               case_sensitive: bool = False, 
               whole_word: bool = False) -> List[SearchResult]:
        """Search for keyword in document"""
        pass
    
    @abstractmethod
    def highlight_document(self, file_path: str, keyword: str, 
                          output_path: str, case_sensitive: bool = False) -> bool:
        """Create a copy of document with highlighted matches"""
        pass
    
    def _build_pattern(self, keyword: str, case_sensitive: bool, whole_word: bool) -> re.Pattern:
        """Build regex pattern for searching"""
        if whole_word:
            pattern = r'\b' + re.escape(keyword) + r'\b'
        else:
            pattern = re.escape(keyword)
        
        flags = 0 if case_sensitive else re.IGNORECASE
        return re.compile(pattern, flags)