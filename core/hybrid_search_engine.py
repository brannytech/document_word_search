"""Hybrid search engine combining indexing and fast extraction"""

from typing import Dict, List, Optional, Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import os

from core.document_index import DocumentIndex
from core.fast_extractors import MultiProcessExtractor
from searchers.base import SearchResult
from config import Config


class HybridSearchEngine:
    """
    Hybrid search engine with three modes:
    1. hybrid: Use index + fast extraction for new files (DEFAULT)
    2. fast_extract: Always extract (no index) - Phase 1
    3. indexed_only: Only search indexed files - Phase 2
    """
    
    def __init__(self, search_mode: str = "hybrid", index_enabled: bool = True):
        self.search_mode = search_mode
        self.index = DocumentIndex() if index_enabled else None
        self.extractor = MultiProcessExtractor(max_workers=Config.MAX_WORKERS)
        self.stop_requested = False
    
    def stop(self):
        """Stop all ongoing operations"""
        self.stop_requested = True
        if self.extractor:
            self.extractor.stop()
    
    def reset_stop(self):
        """Reset stop flag"""
        self.stop_requested = False
        if self.extractor:
            self.extractor.stop_requested = False
    
    def search_files(self, files: List[Path], keyword: str, 
                    case_sensitive: bool = False, whole_word: bool = False,
                    progress_callback: Optional[Callable] = None) -> Dict[str, List[SearchResult]]:
        """
        Search files using hybrid approach
        
        Returns: {file_path: [SearchResult, ...]}
        """
        self.reset_stop()
        
        if self.search_mode == "hybrid":
            return self._search_hybrid(files, keyword, case_sensitive, whole_word, progress_callback)
        elif self.search_mode == "fast_extract":
            return self._search_fast_extract(files, keyword, case_sensitive, whole_word, progress_callback)
        elif self.search_mode == "indexed_only":
            return self._search_indexed_only(files, keyword, case_sensitive, whole_word, progress_callback)
        else:
            return self._search_hybrid(files, keyword, case_sensitive, whole_word, progress_callback)
    
    def _search_hybrid(self, files: List[Path], keyword: str, 
                      case_sensitive: bool, whole_word: bool,
                      progress_callback: Optional[Callable]) -> Dict[str, List[SearchResult]]:
        """
        Hybrid mode: Check index first, extract only new/changed files
        FASTEST for repeated searches
        """
        results = {}
        
        # Separate indexed and non-indexed files
        indexed_files = []
        files_to_extract = []
        
        if self.index:
            for file in files:
                if self.stop_requested:
                    break
                file_str = str(file)
                if self.index.is_indexed(file_str):
                    indexed_files.append(file)
                else:
                    files_to_extract.append(file)
        else:
            files_to_extract = files
        
        total_files = len(files)
        processed = 0
        
        # 1. Search indexed files (instant)
        if indexed_files and not self.stop_requested:
            for file in indexed_files:
                if self.stop_requested:
                    break
                
                file_str = str(file)
                text = self.index.get_text(file_str)
                
                if text:
                    file_results = self._search_text(file_str, text, keyword, case_sensitive, whole_word)
                    if file_results:
                        results[file_str] = file_results
                
                processed += 1
                if progress_callback:
                    progress_callback(processed, total_files, file.name)
        
        # 2. Extract and search new files (fast multiprocessing)
        if files_to_extract and not self.stop_requested:
            extraction_results = self.extractor.extract_batch(
                [str(f) for f in files_to_extract],
                lambda c, t, n: progress_callback(processed + c, total_files, n) if progress_callback else None
            )
            
            # Index extracted files
            if self.index:
                for file_path, (text, page_count) in extraction_results.items():
                    if text and not self.stop_requested:
                        self.index.add_document(file_path, text, page_count)
            
            # Search extracted text
            for file_path, (text, page_count) in extraction_results.items():
                if self.stop_requested:
                    break
                
                if text:
                    file_results = self._search_text(file_path, text, keyword, case_sensitive, whole_word)
                    if file_results:
                        results[file_path] = file_results
                
                processed += 1
                if progress_callback:
                    progress_callback(processed, total_files, Path(file_path).name)
        
        return results
    
    def _search_fast_extract(self, files: List[Path], keyword: str,
                            case_sensitive: bool, whole_word: bool,
                            progress_callback: Optional[Callable]) -> Dict[str, List[SearchResult]]:
        """
        Phase 1 mode: Always extract, no indexing
        FAST for single searches, no persistence
        """
        results = {}
        total_files = len(files)
        
        # Extract all files in parallel
        extraction_results = self.extractor.extract_batch(
            [str(f) for f in files],
            progress_callback
        )
        
        # Search extracted text
        processed = 0
        for file_path, (text, page_count) in extraction_results.items():
            if self.stop_requested:
                break
            
            if text:
                file_results = self._search_text(file_path, text, keyword, case_sensitive, whole_word)
                if file_results:
                    results[file_path] = file_results
            
            processed += 1
            if progress_callback:
                progress_callback(processed, total_files, Path(file_path).name)
        
        return results
    
    def _search_indexed_only(self, files: List[Path], keyword: str,
                            case_sensitive: bool, whole_word: bool,
                            progress_callback: Optional[Callable]) -> Dict[str, List[SearchResult]]:
        """
        Phase 2 mode: Only search pre-indexed files
        INSTANT but requires pre-indexing
        """
        results = {}
        
        if not self.index:
            return results
        
        total_files = len(files)
        processed = 0
        
        for file in files:
            if self.stop_requested:
                break
            
            file_str = str(file)
            if self.index.is_indexed(file_str):
                text = self.index.get_text(file_str)
                if text:
                    file_results = self._search_text(file_str, text, keyword, case_sensitive, whole_word)
                    if file_results:
                        results[file_str] = file_results
            
            processed += 1
            if progress_callback:
                progress_callback(processed, total_files, file.name)
        
        return results
    
    def _search_text(self, file_path: str, text: str, keyword: str,
                    case_sensitive: bool, whole_word: bool) -> List[SearchResult]:
        """Search text for keyword matches"""
        from utils.helpers import create_sentence_context, normalize_keyword
        
        results = []
        
        # Build fuzzy pattern
        normalized = normalize_keyword(keyword)
        words = normalized.split()
        
        pattern_parts = []
        for i, word in enumerate(words):
            escaped_word = re.escape(word)
            if i == len(words) - 1:
                escaped_word = escaped_word + r'(?:e?s)?'
            pattern_parts.append(escaped_word)
        
        pattern = r'[-\s]*'.join(pattern_parts)
        if whole_word:
            pattern = r'\b' + pattern + r'\b'
        
        flags = re.IGNORECASE
        regex = re.compile(pattern, flags)
        
        # Find all matches
        for match in regex.finditer(text):
            if self.stop_requested:
                break
            
            page_num = (match.start() // Config.CHARS_PER_PAGE_ESTIMATE) + 1
            context, rel_start, rel_end = create_sentence_context(
                text, match.start(), match.end(),
                Config.SENTENCES_BEFORE, Config.SENTENCES_AFTER
            )
            
            results.append(SearchResult(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                page_number=page_num,
                context=context,
                match_start=rel_start,
                match_end=rel_end,
                absolute_position=match.start(),
                matched_text=match.group()
            ))
        
        return results
    
    def index_files(self, files: List[Path], progress_callback: Optional[Callable] = None):
        """Pre-index files (for Phase 2 mode or building initial index)"""
        if not self.index:
            return
        
        files_to_index = [f for f in files if not self.index.is_indexed(str(f))]
        
        if not files_to_index:
            return
        
        # Extract all files
        extraction_results = self.extractor.extract_batch(
            [str(f) for f in files_to_index],
            progress_callback
        )
        
        # Add to index
        for file_path, (text, page_count) in extraction_results.items():
            if text and not self.stop_requested:
                self.index.add_document(file_path, text, page_count)
    
    def get_index_stats(self) -> Dict:
        """Get indexing statistics"""
        if self.index:
            return self.index.get_stats()
        return {'indexed_files': 0, 'total_size_mb': 0, 'db_size_mb': 0}
    
    def clear_index(self):
        """Clear all indexed data"""
        if self.index:
            self.index.clear_index()