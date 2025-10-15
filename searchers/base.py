"""Abstract base class for document searchers"""

import re
from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass
from utils.helpers import normalize_keyword


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
    
    def __init__(self):
        self.stop_search = False
    
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
    
    def _build_fuzzy_pattern(self, keyword: str, case_sensitive: bool, whole_word: bool) -> re.Pattern:
        """
        Build regex pattern for fuzzy searching
        Handles variations like 'low-resource', 'low resource', 'low resources'
        """
        # Normalize the keyword
        normalized = normalize_keyword(keyword)
        words = normalized.split()
        
        # Build pattern that allows:
        # 1. Optional hyphens between words
        # 2. Optional 's' suffix on last word
        pattern_parts = []
        
        for i, word in enumerate(words):
            escaped_word = re.escape(word)
            
            # Add optional 's' or 'es' suffix to last word
            if i == len(words) - 1:
                escaped_word = escaped_word + r'(?:e?s)?'
            
            pattern_parts.append(escaped_word)
        
        # Join with optional hyphen/space pattern
        pattern = r'[-\s]*'.join(pattern_parts)
        
        # Add word boundary if whole_word is True
        if whole_word:
            pattern = r'\b' + pattern + r'\b'
        
        # Always case insensitive for better matching
        flags = re.IGNORECASE
        
        return re.compile(pattern, flags)