"""Process and merge search results - OPTIMIZED VERSION"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
from searchers.base import SearchResult
from config import Config


@dataclass
class MergedMatch:
    """Represents merged matches on same page"""
    file_path: str
    file_name: str
    page_number: int
    merged_context: str
    match_positions: List[Tuple[int, int]]
    match_count: int
    matched_texts: List[str]


class ResultProcessor:
    """Process search results to merge nearby matches - OPTIMIZED"""
    
    def __init__(self):
        self.max_sentence_gap = Config.MAX_SENTENCES_TO_MERGE
        self.ellipsis = Config.ELLIPSIS_TEXT
    
    def process_results(self, all_results: Dict[str, List[SearchResult]]) -> Dict[str, List[MergedMatch]]:
        """
        Process all results and merge nearby matches - FAST VERSION
        
        Args:
            all_results: Dict mapping file paths to list of SearchResult
            
        Returns:
            Dict mapping file paths to list of MergedMatch objects
        """
        processed = {}
        
        for file_path, results in all_results.items():
            if not results:
                continue
            
            # Group by page
            by_page = {}
            for result in results:
                page = result.page_number
                if page not in by_page:
                    by_page[page] = []
                by_page[page].append(result)
            
            # Process each page - SIMPLIFIED
            merged_results = []
            for page_num in sorted(by_page.keys()):
                page_matches = sorted(by_page[page_num], key=lambda x: x.absolute_position)
                
                # Simple merging: Group close matches (within 5 sentences)
                merged = self._merge_page_matches_fast(page_matches)
                merged_results.extend(merged)
            
            processed[file_path] = merged_results
        
        return processed
    
    def _merge_page_matches_fast(self, matches: List[SearchResult]) -> List[MergedMatch]:
        """Fast merge - no complex logic"""
        if not matches:
            return []
        
        if len(matches) == 1:
            # Single match
            m = matches[0]
            return [MergedMatch(
                file_path=m.file_path,
                file_name=m.file_name,
                page_number=m.page_number,
                merged_context=m.context,
                match_positions=[(m.match_start, m.match_end)],
                match_count=1,
                matched_texts=[m.matched_text]
            )]
        
        # Multiple matches - simple grouping
        groups = []
        current_group = [matches[0]]
        
        for i in range(1, len(matches)):
            prev = matches[i-1]
            curr = matches[i]
            
            # Simple distance check
            char_distance = curr.absolute_position - (prev.absolute_position + len(prev.matched_text))
            
            # If close (< 500 chars), group together
            if char_distance < 500:
                current_group.append(curr)
            else:
                groups.append(current_group)
                current_group = [curr]
        
        groups.append(current_group)
        
        # Create merged matches
        result = []
        for group in groups:
            result.append(self._create_merged_fast(group))
        
        return result
    
    def _create_merged_fast(self, matches: List[SearchResult]) -> MergedMatch:
        """Create merged match - simplified"""
        first = matches[0]
        
        if len(matches) == 1:
            return MergedMatch(
                file_path=first.file_path,
                file_name=first.file_name,
                page_number=first.page_number,
                merged_context=first.context,
                match_positions=[(first.match_start, first.match_end)],
                match_count=1,
                matched_texts=[first.matched_text]
            )
        
        # Merge contexts - simple concatenation
        contexts = []
        positions = []
        current_pos = 0
        
        for match in matches:
            contexts.append(match.context)
            positions.append((current_pos + match.match_start, current_pos + match.match_end))
            current_pos += len(match.context) + 1
        
        merged_context = " ".join(contexts)
        
        return MergedMatch(
            file_path=first.file_path,
            file_name=first.file_name,
            page_number=first.page_number,
            merged_context=merged_context,
            match_positions=positions,
            match_count=len(matches),
            matched_texts=[m.matched_text for m in matches]
        )
    
    