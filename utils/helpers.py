"""Utility helper functions - FIXED with safety limits"""

import re
import os
from typing import Tuple, List
from pathlib import Path


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_keyword(keyword: str) -> str:
    """
    Normalize keyword for fuzzy matching
    Remove hyphens and special characters, keep only alphanumeric
    """
    normalized = re.sub(r'[-_/]', ' ', keyword)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()


def find_sentence_boundaries(text: str) -> List[int]:
    """
    Find all sentence boundary positions in text - SAFE VERSION
    Returns list of positions where sentences end
    """
    if not text or len(text) > 100000:
        # SAFETY: Don't process extremely long text
        return [0, len(text)]
    
    sentence_pattern = r'[.!?]+[\s]+'
    boundaries = [0]
    
    # SAFETY: Limit number of boundaries
    for match in re.finditer(sentence_pattern, text):
        boundaries.append(match.end())
        if len(boundaries) > 1000:  # LIMIT: Max 1000 sentences
            break
    
    boundaries.append(len(text))
    return boundaries


def count_sentences_between(text: str, pos1: int, pos2: int) -> int:
    """
    Count number of sentences between two positions - SAFE VERSION
    """
    if pos1 > pos2:
        pos1, pos2 = pos2, pos1
    
    # SAFETY: Limit text length
    if pos2 - pos1 > 10000:
        return 100  # Just return large number
    
    text_between = text[pos1:pos2]
    sentence_pattern = r'[.!?]+[\s]+'
    
    sentences = re.findall(sentence_pattern, text_between)
    return min(len(sentences), 100)  # Cap at 100


def create_sentence_context(text: str, match_start: int, match_end: int, 
                           sentences_before: int = 2, sentences_after: int = 2) -> Tuple[str, int, int]:
    """
    Create context around matched keyword using sentence boundaries - SAFE VERSION
    
    Returns:
        Tuple of (context_text, relative_match_start, relative_match_end)
    """
    # SAFETY: Check bounds
    if not text or match_start < 0 or match_end > len(text):
        return text[max(0, match_start-100):min(len(text), match_end+100)], 100, 120
    
    # SAFETY: For very long text, use simple character-based context
    if len(text) > 50000:
        start = max(0, match_start - 300)
        end = min(len(text), match_end + 300)
        context = text[start:end]
        rel_start = match_start - start
        rel_end = match_end - start
        return context, rel_start, rel_end
    
    try:
        # Find sentence boundaries - SAFE
        sentence_pattern = r'[.!?]+[\s]+'
        sentences = list(re.finditer(sentence_pattern, text))
        
        # SAFETY: Limit sentence processing
        if len(sentences) > 500:
            sentences = sentences[:500]
        
        # Find which sentence contains the match
        current_sentence_idx = 0
        for i, sent in enumerate(sentences):
            if sent.start() > match_start:
                current_sentence_idx = i
                break
        else:
            current_sentence_idx = len(sentences)
        
        # Determine context boundaries
        start_sentence_idx = max(0, current_sentence_idx - sentences_before)
        end_sentence_idx = min(len(sentences), current_sentence_idx + sentences_after + 1)
        
        # Get start position
        if start_sentence_idx == 0:
            start = 0
        else:
            start = sentences[start_sentence_idx - 1].end() if start_sentence_idx > 0 else 0
        
        # Get end position
        if end_sentence_idx >= len(sentences):
            end = len(text)
        else:
            end = sentences[end_sentence_idx - 1].end() if end_sentence_idx > 0 else len(text)
        
        # Extract context - SAFE
        start = max(0, start)
        end = min(len(text), end)
        
        context = text[start:end].strip()
        
        # SAFETY: Limit context length
        if len(context) > 2000:
            # Trim to reasonable length
            half = 1000
            mid = (match_start + match_end) // 2 - start
            ctx_start = max(0, mid - half)
            ctx_end = min(len(context), mid + half)
            context = context[ctx_start:ctx_end]
            start += ctx_start
        
        # Calculate relative positions
        relative_start = match_start - start
        relative_end = match_end - start
        
        # Ensure positions are within context bounds
        relative_start = max(0, min(relative_start, len(context)))
        relative_end = max(relative_start, min(relative_end, len(context)))
        
        return context, relative_start, relative_end
    
    except Exception as e:
        # FALLBACK: If anything fails, use simple character-based context
        print(f"Error in create_sentence_context: {e}")
        start = max(0, match_start - 200)
        end = min(len(text), match_end + 200)
        context = text[start:end]
        rel_start = match_start - start
        rel_end = match_end - start
        return context, max(0, rel_start), max(0, rel_end)


def get_file_size(file_path: str) -> str:
    """Get human-readable file size"""
    try:
        size = Path(file_path).stat().st_size
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    except:
        return "Unknown"


def validate_directory(directory: str) -> Tuple[bool, str]:
    """Validate if directory exists and is accessible"""
    path = Path(directory)
    
    if not path.exists():
        return False, f"Directory does not exist: {directory}"
    
    if not path.is_dir():
        return False, f"Path is not a directory: {directory}"
    
    if not os.access(directory, os.R_OK):
        return False, f"Directory is not readable: {directory}"
    
    return True, "Valid directory"


def get_all_files(directory: str, extensions: List[str]) -> List[Path]:
    """Get all files with specified extensions from directory"""
    try:
        directory_path = Path(directory)
        files = []
        
        for ext in extensions:
            files.extend(directory_path.rglob(f"*{ext}"))
        
        # SAFETY: Limit number of files
        if len(files) > 10000:
            print(f"Warning: Found {len(files)} files, limiting to first 10000")
            files = files[:10000]
        
        return sorted(files)
    except Exception as e:
        print(f"Error getting files: {e}")
        return []
    
    