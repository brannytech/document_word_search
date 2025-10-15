"""Process and merge search results for optimal display"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
from searchers.base import SearchResult
from utils.helpers import count_sentences_between
from config import Config


@dataclass
class MergedMatch:
    """Represents merged matches on same page"""
    file_path: str
    file_name: str
    page_number: int
    merged_context: str
    match_positions: List[Tuple[int, int]]  # List of (start, end) for highlighting
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
        
        Args:
            all_results: Dict mapping file paths to list of SearchResult
            full_texts: Optional dict of full text content per file for better merging
            
        Returns:
            Dict mapping file paths to list of MergedMatch objects
        """
        processed = {}
        
        for file_path, results in all_results.items():
            if not results:
                continue
            
            # Group by page number
            by_page = self._group_by_page(results)
            
            # Process each page
            merged_results = []
            for page_num, page_matches in sorted(by_page.items()):
                # Sort matches by position on page
                page_matches.sort(key=lambda x: x.absolute_position)
                
                # Merge nearby matches
                merged = self._merge_page_matches(page_matches, full_texts.get(file_path) if full_texts else None)
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
    
    def _merge_page_matches(self, matches: List[SearchResult], 
                           full_text: str = None) -> List[MergedMatch]:
        """
        Merge matches on same page that are close together
        
        Strategy:
        - If matches are <= 5 sentences apart: merge into one context
        - If matches are > 5 sentences apart: use ellipsis
        - If all matches far apart: return separately
        """
        if not matches:
            return []
        
        if len(matches) == 1:
            # Single match, no merging needed
            return [self._create_merged_match([matches[0]])]
        
        # Group matches that should be merged together
        groups = []
        current_group = [matches[0]]
        
        for i in range(1, len(matches)):
            prev_match = matches[i-1]
            curr_match = matches[i]
            
            # Calculate distance between matches
            if full_text:
                sentence_gap = count_sentences_between(
                    full_text, 
                    prev_match.absolute_position + len(prev_match.matched_text),
                    curr_match.absolute_position
                )
            else:
                # Estimate based on character distance
                char_distance = curr_match.absolute_position - (prev_match.absolute_position + len(prev_match.matched_text))
                sentence_gap = char_distance // 100  # Rough estimate: ~100 chars per sentence
            
            if sentence_gap <= self.max_sentence_gap:
                # Close enough to merge
                current_group.append(curr_match)
            else:
                # Too far, start new group
                groups.append(current_group)
                current_group = [curr_match]
        
        # Add last group
        groups.append(current_group)
        
        # Create merged matches for each group
        merged_results = []
        for group in groups:
            merged_results.append(self._create_merged_match(group, full_text))
        
        return merged_results
    
    def _create_merged_match(self, matches: List[SearchResult], 
                            full_text: str = None) -> MergedMatch:
        """
        Create a MergedMatch from a group of matches
        """
        if len(matches) == 1:
            # Single match
            match = matches[0]
            return MergedMatch(
                file_path=match.file_path,
                file_name=match.file_name,
                page_number=match.page_number,
                merged_context=match.context,
                match_positions=[(match.match_start, match.match_end)],
                match_count=1,
                matched_texts=[match.matched_text]
            )
        
        # Multiple matches - need to merge contexts
        first_match = matches[0]
        last_match = matches[-1]
        
        # Build merged context
        if full_text and all(m.absolute_position for m in matches):
            # Use full text to build proper merged context
            merged_context, positions = self._build_merged_context_from_full_text(
                matches, full_text
            )
        else:
            # Fall back to concatenating contexts
            merged_context, positions = self._build_merged_context_from_contexts(matches)
        
        return MergedMatch(
            file_path=first_match.file_path,
            file_name=first_match.file_name,
            page_number=first_match.page_number,
            merged_context=merged_context,
            match_positions=positions,
            match_count=len(matches),
            matched_texts=[m.matched_text for m in matches]
        )
    
    def _build_merged_context_from_full_text(self, matches: List[SearchResult], 
                                            full_text: str) -> Tuple[str, List[Tuple[int, int]]]:
        """Build merged context from full text"""
        # Find start and end positions
        first_match = matches[0]
        last_match = matches[-1]
        
        # Get 2 sentences before first match
        start_pos = max(0, first_match.absolute_position - 200)  # Rough estimate
        # Get 2 sentences after last match
        end_pos = min(len(full_text), last_match.absolute_position + len(last_match.matched_text) + 200)
        
        # Extract context
        context = full_text[start_pos:end_pos].strip()
        
        # Calculate relative positions for all matches
        positions = []
        for match in matches:
            rel_start = match.absolute_position - start_pos
            rel_end = rel_start + len(match.matched_text)
            if 0 <= rel_start < len(context):
                positions.append((rel_start, rel_end))
        
        return context, positions
    
    def _build_merged_context_from_contexts(self, matches: List[SearchResult]) -> Tuple[str, List[Tuple[int, int]]]:
        """Build merged context by combining individual contexts"""
        # Simple concatenation with match tracking
        parts = []
        positions = []
        current_pos = 0
        
        for i, match in enumerate(matches):
            if i > 0:
                # Add space or ellipsis between contexts
                parts.append(" ")
                current_pos += 1
            
            # Add context
            parts.append(match.context)
            
            # Track match position
            positions.append((
                current_pos + match.match_start,
                current_pos + match.match_end
            ))
            
            current_pos += len(match.context)
        
        return "".join(parts), positions