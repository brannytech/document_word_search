"""Main search manager with parallel processing"""

from typing import Dict, List, Optional, Tuple, Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from threading import Lock
import time

from searchers import PDFSearcher, DOCXSearcher, DOCSearcher, SearchResult
from utils.helpers import get_all_files, validate_directory
from config import Config


class SearchManager:
    """Coordinate parallel searches across different file types"""
    
    def __init__(self):
        self.searchers = {
            '.pdf': PDFSearcher(),
            '.docx': DOCXSearcher(),
            '.doc': DOCSearcher()
        }
        self.stop_requested = False
        self.active_futures: List[Future] = []
        self.progress_lock = Lock()
        self.completed_count = 0
        self.results_lock = Lock()
        Config.ensure_directories()
    
    def stop_search(self):
        """Stop all ongoing searches"""
        self.stop_requested = True
        for searcher in self.searchers.values():
            searcher.stop_search = True
        
        # Cancel pending futures
        for future in self.active_futures:
            if not future.done():
                future.cancel()
    
    def reset_stop(self):
        """Reset stop flag for new search"""
        self.stop_requested = False
        self.completed_count = 0
        self.active_futures = []
        for searcher in self.searchers.values():
            searcher.stop_search = False
    
    def search_directory(self, directory: str, keyword: str, 
                        case_sensitive: bool = False,
                        whole_word: bool = False,
                        file_extensions: Optional[List[str]] = None,
                        progress_callback: Optional[Callable] = None) -> Dict[str, List[SearchResult]]:
        """
        Search for keyword in all supported documents using parallel processing
        
        Returns results from completed files even if search is stopped
        """
        # Reset stop flag at start
        self.reset_stop()
        
        is_valid, message = validate_directory(directory)
        if not is_valid:
            raise ValueError(message)
        
        if file_extensions is None:
            file_extensions = Config.SUPPORTED_EXTENSIONS
        
        # Get all files
        files = get_all_files(directory, file_extensions)
        total_files = len(files)
        
        if total_files == 0:
            return {}
        
        # Determine processing strategy
        if total_files < Config.MIN_FILES_FOR_BATCHING:
            # Small number of files: process all in parallel
            return self._search_parallel_simple(
                files, keyword, case_sensitive, whole_word, 
                total_files, progress_callback
            )
        else:
            # Large number of files: process in batches
            return self._search_parallel_batched(
                files, keyword, case_sensitive, whole_word,
                total_files, progress_callback
            )
    
    def _search_parallel_simple(self, files: List[Path], keyword: str,
                               case_sensitive: bool, whole_word: bool,
                               total_files: int, progress_callback: Optional[Callable]) -> Dict[str, List[SearchResult]]:
        """Process all files in parallel (for small file counts)"""
        all_results = {}
        
        # Use ThreadPoolExecutor for parallel processing
        max_workers = min(Config.MAX_WORKERS, total_files)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {}
            for file_path in files:
                if self.stop_requested:
                    break
                
                future = executor.submit(
                    self._search_single_file,
                    file_path, keyword, case_sensitive, whole_word
                )
                future_to_file[future] = file_path
                self.active_futures.append(future)
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                if self.stop_requested:
                    break
                
                file_path = future_to_file[future]
                
                try:
                    results = future.result(timeout=30)  # 30 second timeout per file
                    
                    if results:
                        with self.results_lock:
                            all_results[str(file_path)] = results
                    
                    # Update progress
                    with self.progress_lock:
                        self.completed_count += 1
                        if progress_callback:
                            progress_callback(
                                self.completed_count, 
                                total_files, 
                                file_path.name
                            )
                
                except Exception as e:
                    print(f"Error searching {file_path}: {str(e)}")
                    with self.progress_lock:
                        self.completed_count += 1
        
        return all_results
    
    def _search_parallel_batched(self, files: List[Path], keyword: str,
                                case_sensitive: bool, whole_word: bool,
                                total_files: int, progress_callback: Optional[Callable]) -> Dict[str, List[SearchResult]]:
        """Process files in batches (for large file counts)"""
        all_results = {}
        batch_size = Config.BATCH_SIZE
        
        # Process in batches
        for batch_start in range(0, len(files), batch_size):
            if self.stop_requested:
                break
            
            batch_end = min(batch_start + batch_size, len(files))
            batch_files = files[batch_start:batch_end]
            
            # Process this batch in parallel
            batch_results = self._search_parallel_simple(
                batch_files, keyword, case_sensitive, whole_word,
                total_files, progress_callback
            )
            
            # Merge batch results
            all_results.update(batch_results)
        
        return all_results
    
    def _search_single_file(self, file_path: Path, keyword: str,
                           case_sensitive: bool, whole_word: bool) -> List[SearchResult]:
        """Search a single file (called by worker threads)"""
        if self.stop_requested:
            return []
        
        ext = file_path.suffix.lower()
        if ext not in self.searchers:
            return []
        
        searcher = self.searchers[ext]
        
        try:
            results = searcher.search(
                str(file_path), keyword, case_sensitive, whole_word
            )
            return results
        except Exception as e:
            print(f"Error in worker thread for {file_path}: {str(e)}")
            return []
    
    def get_searcher(self, file_extension: str):
        """Get searcher for file type"""
        return self.searchers.get(file_extension.lower())
    
    def get_completion_stats(self, total_files: int) -> Tuple[int, int]:
        """Get completion statistics"""
        return self.completed_count, total_files
