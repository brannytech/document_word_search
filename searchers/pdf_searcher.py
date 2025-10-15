"""PDF document searcher with highlighting"""

import os
import PyPDF2
import fitz
from typing import List
from .base import BaseSearcher, SearchResult
from utils.helpers import create_context
from config import Config


class PDFSearcher(BaseSearcher):
    """Search and highlight PDF documents"""
    
    def search(self, file_path: str, keyword: str, 
               case_sensitive: bool = False,
               whole_word: bool = False) -> List[SearchResult]:
        """Search for keyword in PDF"""
        results = []
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    
                    if not text:
                        continue
                    
                    pattern = self._build_pattern(keyword, case_sensitive, whole_word)
                    
                    for match in pattern.finditer(text):
                        context, rel_start, rel_end = create_context(
                            text, match.start(), match.end(), 
                            Config.DEFAULT_CONTEXT_LENGTH
                        )
                        
                        results.append(SearchResult(
                            file_path=file_path,
                            file_name=os.path.basename(file_path),
                            page_number=page_num + 1,
                            context=context,
                            match_start=rel_start,
                            match_end=rel_end,
                            absolute_position=match.start(),
                            matched_text=match.group()
                        ))
                        
        except Exception as e:
            print(f"Error reading PDF {file_path}: {str(e)}")
            
        return results
    
    def highlight_document(self, file_path: str, keyword: str, 
                          output_path: str, case_sensitive: bool = False) -> bool:
        """Create PDF with highlighted keywords"""
        try:
            doc = fitz.open(file_path)
            pattern = self._build_pattern(keyword, case_sensitive, False)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                for match in pattern.finditer(text):
                    text_instances = page.search_for(match.group())
                    
                    for inst in text_instances:
                        highlight = page.add_highlight_annot(inst)
                        highlight.set_colors(stroke=Config.HIGHLIGHT_COLOR_RGB)
                        highlight.update()
            
            doc.save(output_path)
            doc.close()
            return True
            
        except Exception as e:
            print(f"Error highlighting PDF: {str(e)}")
            return False