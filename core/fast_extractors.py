"""Ultra-fast text extraction using PyMuPDF and multiprocessing"""

import fitz  # PyMuPDF - 100x faster than PyPDF2
from docx import Document
import pypandoc
from pathlib import Path
from typing import Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp


class FastPDFExtractor:
    """Ultra-fast PDF extraction using PyMuPDF"""
    
    @staticmethod
    def extract_text(file_path: str) -> Tuple[str, int]:
        """
        Extract text from PDF using PyMuPDF (100x faster than PyPDF2)
        Returns: (text, page_count)
        """
        try:
            doc = fitz.open(file_path)
            text_parts = []
            
            for page in doc:
                # Get text only (skip images for speed)
                text = page.get_text("text", sort=True)
                if text:
                    text_parts.append(text)
            
            page_count = len(doc)
            doc.close()
            
            return '\n'.join(text_parts), page_count
        except Exception as e:
            print(f"Error extracting PDF {file_path}: {e}")
            return "", 0


class FastDOCXExtractor:
    """Optimized DOCX extraction"""
    
    @staticmethod
    def extract_text(file_path: str) -> Tuple[str, int]:
        """
        Extract text from DOCX
        Returns: (text, estimated_page_count)
        """
        try:
            doc = Document(file_path)
            text = '\n'.join([para.text for para in doc.paragraphs if para.text])
            
            # Estimate page count (roughly 3000 chars per page)
            page_count = max(1, len(text) // 3000)
            
            return text, page_count
        except Exception as e:
            print(f"Error extracting DOCX {file_path}: {e}")
            return "", 0


class FastDOCExtractor:
    """DOC extraction using pypandoc"""
    
    @staticmethod
    def extract_text(file_path: str) -> Tuple[str, int]:
        """
        Extract text from DOC
        Returns: (text, estimated_page_count)
        """
        try:
            text = pypandoc.convert_file(file_path, 'plain', format='doc')
            page_count = max(1, len(text) // 3000)
            return text, page_count
        except Exception as e:
            print(f"Error extracting DOC {file_path}: {e}")
            return "", 0


def extract_single_file(file_path: str) -> Tuple[str, str, int]:
    """
    Extract text from a single file (used in multiprocessing)
    Returns: (file_path, text, page_count)
    """
    ext = Path(file_path).suffix.lower()
    
    try:
        if ext == '.pdf':
            text, pages = FastPDFExtractor.extract_text(file_path)
        elif ext == '.docx':
            text, pages = FastDOCXExtractor.extract_text(file_path)
        elif ext == '.doc':
            text, pages = FastDOCExtractor.extract_text(file_path)
        else:
            return file_path, "", 0
        
        return file_path, text, pages
    except Exception as e:
        print(f"Error extracting {file_path}: {e}")
        return file_path, "", 0


class MultiProcessExtractor:
    """Multi-process text extractor for maximum speed"""
    
    def __init__(self, max_workers: Optional[int] = None):
        if max_workers is None:
            max_workers = min(mp.cpu_count(), 8)  # Cap at 8 processes
        self.max_workers = max_workers
        self.stop_requested = False
    
    def extract_batch(self, file_paths: list, progress_callback=None) -> dict:
        """
        Extract text from multiple files in parallel
        Returns: {file_path: (text, page_count)}
        """
        results = {}
        total = len(file_paths)
        completed = 0
        
        # Use ProcessPoolExecutor for true parallelism
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(extract_single_file, fp): fp 
                for fp in file_paths
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                if self.stop_requested:
                    # Cancel remaining futures
                    for f in futures:
                        f.cancel()
                    break
                
                file_path = futures[future]
                
                try:
                    result_path, text, pages = future.result(timeout=30)
                    results[result_path] = (text, pages)
                    
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, Path(file_path).name)
                        
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    completed += 1
        
        return results
    
    def stop(self):
        """Stop extraction"""
        self.stop_requested = True