"""DOC document searcher"""

import os
from typing import List
import pypandoc
from .base import BaseSearcher, SearchResult
from utils.helpers import create_context
from config import Config


class DOCSearcher(BaseSearcher):
    """Search DOC documents"""
    
    def search(self, file_path: str, keyword: str, 
               case_sensitive: bool = False,
               whole_word: bool = False) -> List[SearchResult]:
        """Search for keyword in DOC"""
        results = []
        
        try:
            text = pypandoc.convert_file(file_path, 'plain', format='doc')
            pattern = self._build_pattern(keyword, case_sensitive, whole_word)
            
            for match in pattern.finditer(text):
                page_num = (match.start() // Config.CHARS_PER_PAGE_ESTIMATE) + 1
                
                context, rel_start, rel_end = create_context(
                    text, match.start(), match.end(),
                    Config.DEFAULT_CONTEXT_LENGTH
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
                
        except Exception as e:
            print(f"Error reading DOC {file_path}: {str(e)}")
            
        return results
    
    def highlight_document(self, file_path: str, keyword: str, 
                          output_path: str, case_sensitive: bool = False) -> bool:
        """Highlight DOC by converting to DOCX"""
        try:
            temp_docx = str(Config.TEMP_DIR / "temp.docx")
            pypandoc.convert_file(file_path, 'docx', outputfile=temp_docx, format='doc')
            
            from .docx_searcher import DOCXSearcher
            docx_searcher = DOCXSearcher()
            result = docx_searcher.highlight_document(temp_docx, keyword, output_path, case_sensitive)
            
            if os.path.exists(temp_docx):
                os.remove(temp_docx)
            
            return result
            
        except Exception as e:
            print(f"Error highlighting DOC: {str(e)}")
            return False