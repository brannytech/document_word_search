"""Ultra-fast text extraction using PyMuPDF and multiprocessing - FIXED"""

from pathlib import Path
from typing import Optional, Tuple, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# Import extractors - CRITICAL: Must be at module level for multiprocessing
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("Warning: PyMuPDF not available, falling back to PyPDF2")

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

from docx import Document
import pypandoc


class FastPDFExtractor:
    """Ultra-fast PDF extraction using PyMuPDF"""
    
    @staticmethod
    def extract_text(file_path: str) -> Tuple[str, int]:
        """
        Extract text from PDF using PyMuPDF (100x faster than PyPDF2)
        Returns: (text, page_count)
        """
        try:
            if PYMUPDF_AVAILABLE:
                doc = fitz.open(file_path)
                text_parts = []
                
                for page in doc:
                    text = page.get_text("text", sort=True)
                    if text:
                        text_parts.append(text)
                
                page_count = len(doc)
                doc.close()
                
                return '\n'.join(text_parts), page_count
            
            elif PYPDF2_AVAILABLE:
                # Fallback to PyPDF2
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text_parts = []
                    
                    for page in pdf_reader.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    
                    return '\n'.join(text_parts), len(pdf_reader.pages)
            
            else:
                print(f"No PDF extractor available for {file_path}")
                return "", 0
                
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


def extract_single_file_safe(file_path: str) -> Tuple[str, str, int]:
    """
    Extract text from a single file - SAFE VERSION for threading
    Returns: (file_path, text, page_count)
    """
    ext = Path(file_path).suffix.lower()
    
    try:
        if not os.path.exists(file_path):
            return file_path, "", 0
        
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
        import traceback
        traceback.print_exc()
        return file_path, "", 0


class MultiProcessExtractor:
    """Multi-threaded text extractor - FIXED to use threads instead of processes"""
    
    def __init__(self, max_workers: Optional[int] = None):
        if max_workers is None:
            max_workers = min(os.cpu_count() or 1, 16)  # Cap at 16
        self.max_workers = max_workers
        self.stop_requested = False
    
    def extract_batch(self, file_paths: list, progress_callback=None) -> Dict[str, Tuple[str, int]]:
        """
        Extract text from multiple files in parallel using threads
        Returns: {file_path: (text, page_count)}
        """
        results = {}
        total = len(file_paths)
        completed = 0
        
        if not file_paths:
            return results
        
        # Use ThreadPoolExecutor instead of ProcessPoolExecutor
        # This avoids multiprocessing issues with PyMuPDF
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(extract_single_file_safe, fp): fp 
                for fp in file_paths
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                if self.stop_requested:
                    # Cancel remaining futures
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    break
                
                file_path = futures[future]
                
                try:
                    result_path, text, pages = future.result(timeout=60)
                    if text:  # Only add if text was extracted
                        results[result_path] = (text, pages)
                    
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, Path(file_path).name)
                        
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    import traceback
                    traceback.print_exc()
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, Path(file_path).name)
        
        return results
    
    def stop(self):
        """Stop extraction"""
        self.stop_requested = True