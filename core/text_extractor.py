"""Parallel text extraction with caching"""

from typing import Dict, List, Optional, Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import PyPDF2
from docx import Document
import pypandoc

from core.cache_manager import TextCache


class TextExtractor:
    """Extract text from documents with caching support"""
    
    def __init__(self, cache: Optional[TextCache] = None, max_workers: int = 16):
        self.cache = cache
        self.max_workers = max_workers
        self.progress_lock = Lock()
        self.completed_count = 0
        self.stop_requested = False
    
    def extract_all(self, files: List[Path], 
                   progress_callback: Optional[Callable] = None) -> Dict[str, str]:
        """
        Extract text from all files in parallel
        
        Returns:
            Dict mapping file paths to extracted text
        """
        extracted_texts = {}
        total_files = len(files)
        self.completed_count = 0
        self.stop_requested = False
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {}
            for file_path in files:
                if self.stop_requested:
                    break
                
                future = executor.submit(self._extract_single, file_path)
                future_to_file[future] = file_path
            
            # Collect results
            for future in as_completed(future_to_file):
                if self.stop_requested:
                    break
                
                file_path = future_to_file[future]
                
                try:
                    text = future.result(timeout=30)
                    if text:
                        extracted_texts[str(file_path)] = text
                    
                    with self.progress_lock:
                        self.completed_count += 1
                        if progress_callback:
                            progress_callback(
                                self.completed_count,
                                total_files,
                                file_path.name
                            )
                except Exception as e:
                    print(f"Error extracting {file_path}: {e}")
                    with self.progress_lock:
                        self.completed_count += 1
        
        return extracted_texts
    
    def _extract_single(self, file_path: Path) -> Optional[str]:
        """Extract text from a single file"""
        file_str = str(file_path)
        
        # Check cache first
        if self.cache:
            cached = self.cache.get(file_str)
            if cached:
                return cached
        
        # Extract based on file type
        text = None
        ext = file_path.suffix.lower()
        
        try:
            if ext == '.pdf':
                text = self._extract_pdf(file_str)
            elif ext == '.docx':
                text = self._extract_docx(file_str)
            elif ext == '.doc':
                text = self._extract_doc(file_str)
            
            # Cache the result
            if text and self.cache:
                self.cache.put(file_str, text)
            
            return text
        except Exception as e:
            print(f"Error extracting {file_path}: {e}")
            return None
    
    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF"""
        text_parts = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return '\n'.join(text_parts)
    
    def _extract_docx(self, file_path: str) -> str:
        """Extract text from DOCX"""
        doc = Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    
    def _extract_doc(self, file_path: str) -> str:
        """Extract text from DOC"""
        return pypandoc.convert_file(file_path, 'plain', format='doc')
    
    def stop(self):
        """Stop extraction"""
        self.stop_requested = True