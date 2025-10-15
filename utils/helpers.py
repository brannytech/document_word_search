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
    normalized = re.sub(r'[-_/]', ' ', keyword)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()


def find_sentence_boundaries(text: str) -> List[int]:
    """
    Find all sentence boundary positions in text
    Returns list of positions where sentences end
    """
    sentence_pattern = r'[.!?]+[\s]+'
    boundaries = [0]  # Start of text
    
    for match in re.finditer(sentence_pattern, text):
        boundaries.append(match.end())
    
    boundaries.append(len(text))  # End of text
    return boundaries


def count_sentences_between(text: str, pos1: int, pos2: int) -> int:
    """
    Count number of sentences between two positions
    """
    if pos1 > pos2:
        pos1, pos2 = pos2, pos1
    
    text_between = text[pos1:pos2]
    sentence_pattern = r'[.!?]+[\s]+'
    sentences = re.findall(sentence_pattern, text_between)
    return len(sentences)


def create_sentence_context(text: str, match_start: int, match_end: int, 
                           sentences_before: int = 2, sentences_after: int = 2) -> Tuple[str, int, int]:
    """
    Create context around matched keyword using sentence boundaries
    
    Returns:
        Tuple of (context_text, relative_match_start, relative_match_end)
    """
    sentence_pattern = r'[.!?]+[\s]+'
    sentences = list(re.finditer(sentence_pattern, text))
    
    current_sentence_idx = 0
    for i, sent in enumerate(sentences):
        if sent.start() > match_start:
            current_sentence_idx = i
            break
    else:
        current_sentence_idx = len(sentences)
    
    start_sentence_idx = max(0, current_sentence_idx - sentences_before)
    end_sentence_idx = min(len(sentences), current_sentence_idx + sentences_after + 1)
    
    if start_sentence_idx == 0:
        start = 0
    else:
        start = sentences[start_sentence_idx - 1].end()
    
    if end_sentence_idx >= len(sentences):
        end = len(text)
    else:
        end = sentences[end_sentence_idx - 1].end()
    
    context = text[start:end].strip()
    relative_start = match_start - start
    relative_end = match_end - start
    
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