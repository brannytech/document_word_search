"""Utility helper functions"""

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
    # Remove hyphens and replace with space
    normalized = re.sub(r'[-_/]', ' ', keyword)
    # Remove extra spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()


def create_sentence_context(text: str, match_start: int, match_end: int, 
                           sentences_before: int = 2, sentences_after: int = 2) -> Tuple[str, int, int]:
    """
    Create context around matched keyword using sentence boundaries
    
    Returns:
        Tuple of (context_text, relative_match_start, relative_match_end)
    """
    # Sentence boundary pattern (. ! ? followed by space or end)
    sentence_pattern = r'[.!?]+[\s]+'
    
    # Find all sentence boundaries
    sentences = list(re.finditer(sentence_pattern, text))
    
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
        start = sentences[start_sentence_idx - 1].end()
    
    # Get end position
    if end_sentence_idx >= len(sentences):
        end = len(text)
    else:
        end = sentences[end_sentence_idx - 1].end()
    
    # Extract context
    context = text[start:end].strip()
    
    # Calculate relative positions
    relative_start = match_start - start
    relative_end = match_end - start
    
    # Ensure positions are within context bounds
    relative_start = max(0, relative_start)
    relative_end = min(len(context), relative_end)
    
    return context, relative_start, relative_end


def get_file_size(file_path: str) -> str:
    """Get human-readable file size"""
    size = Path(file_path).stat().st_size
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


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
    directory_path = Path(directory)
    files = []
    
    for ext in extensions:
        files.extend(directory_path.rglob(f"*{ext}"))
    
    return sorted(files)