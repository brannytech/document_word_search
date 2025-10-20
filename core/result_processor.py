"""Process and merge search results - FIXED INFINITE LOOP"""

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
    """Process search results to merge nearby matches"""
    
    def __init__(self):
        self.max_sentence_gap = Config.MAX_SENTENCES_TO_MERGE
        self.ellipsis = Config.ELLIPSIS_TEXT
    
    def process_results(self, all_results: Dict[str, List[SearchResult]], 
                       full_texts: Dict[str, str] = None) -> Dict[str, List[MergedMatch]]:
        """
        Process all results and merge nearby matches on same pages
        
        FIXED: Added safety limits to prevent infinite loops
        """
        processed = {}
        
        for file_path, results in all_results.items():
            if not results:
                continue
            
            # SAFETY: Limit results per file
            if len(results) > 1000:
                results = results[:1000]
            
            # Group by page number
            by_page = self._group_by_page(results)
            
            # Process each page
            merged_results = []
            for page_num, page_matches in sorted(by_page.items()):
                # SAFETY: Limit matches per page
                if len(page_matches) > 100:
                    page_matches = page_matches[:100]
                
                # Sort by position
                page_matches.sort(key=lambda x: x.absolute_position)
                
                # Merge nearby matches - FIXED VERSION
                merged = self._merge_page_matches_safe(page_matches)
                merged_results.extend(merged)
            
            processed[file_path] = merged_results
        
        return processed
    
    def _group_by_page(self, results: List[SearchResult]) -> Dict[int, List[SearchResult]]:
        """Group search results by page number"""
        by_page = {}
        for result in results:
            page = result.page_number
            if page not in by_page:
                by_page[page] = []
            by_page[page].append(result)
        return by_page
    
    def _merge_page_matches_safe(self, matches: List[SearchResult]) -> List[MergedMatch]:
        """
        Merge matches on same page - SAFE VERSION with loop protection
        """
        if not matches:
            return []
        
        if len(matches) == 1:
            # Single match, return as-is
            return [self._create_single_match(matches[0])]
        
        # Group nearby matches - FIXED: Added safety counter
        groups = []
        current_group = [matches[0]]
        
        # SAFETY: Iterate only once through matches
        for i in range(1, min(len(matches), 100)):  # LIMIT: Max 100 matches
            prev_match = matches[i-1]
            curr_match = matches[i]
            
            # Simple distance check (avoid complex calculations)
            char_distance = curr_match.absolute_position - prev_match.absolute_position
            
            # If close enough (within 1000 chars), group together
            if char_distance < 1000 and char_distance > 0:
                current_group.append(curr_match)
            else:
                # Start new group
                groups.append(current_group)
                current_group = [curr_match]
            
            # SAFETY: Limit group size
            if len(current_group) > 20:
                groups.append(current_group)
                current_group = []
        
        # Add last group
        if current_group:
            groups.append(current_group)
        
        # SAFETY: Limit number of groups
        if len(groups) > 50:
            groups = groups[:50]
        
        # Create merged matches from groups
        merged_results = []
        for group in groups:
            if group:  # Extra safety check
                merged_results.append(self._create_merged_match_simple(group))
        
        return merged_results
    
    def _create_single_match(self, match: SearchResult) -> MergedMatch:
        """Create MergedMatch from single SearchResult"""
        return MergedMatch(
            file_path=match.file_path,
            file_name=match.file_name,
            page_number=match.page_number,
            merged_context=match.context,
            match_positions=[(match.match_start, match.match_end)],
            match_count=1,
            matched_texts=[match.matched_text]
        )
    
    def _create_merged_match_simple(self, matches: List[SearchResult]) -> MergedMatch:
        """
        Create a MergedMatch from a group of matches - SIMPLIFIED
        """
        if len(matches) == 1:
            return self._create_single_match(matches[0])
        
        # SAFETY: Limit matches in group
        if len(matches) > 20:
            matches = matches[:20]
        
        first_match = matches[0]
        
        # Simple concatenation of contexts
        contexts = []
        positions = []
        current_pos = 0
        
        for match in matches:
            # SAFETY: Limit context length
            context = match.context[:500] if len(match.context) > 500 else match.context
            contexts.append(context)
            
            # Track position for highlighting
            rel_start = current_pos + match.match_start
            rel_end = current_pos + match.match_end
            positions.append((rel_start, rel_end))
            
            current_pos += len(context) + 3  # Add separator space
        
        # Join contexts with separator
        merged_context = " ... ".join(contexts)
        
        # SAFETY: Limit merged context length
        if len(merged_context) > 5000:
            merged_context = merged_context[:5000] + "..."
        
        return MergedMatch(
            file_path=first_match.file_path,
            file_name=first_match.file_name,
            page_number=first_match.page_number,
            merged_context=merged_context,
            match_positions=positions,
            match_count=len(matches),
            matched_texts=[m.matched_text for m in matches]
        )
    
    