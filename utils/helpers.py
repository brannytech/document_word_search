"""Utility helper functions"""

import re
import os
from typing import Tuple, List
from pathlib import Path


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def create_context(text: str, match_start: int, match_end: int, 
                   context_length: int = 150) -> Tuple[str, int, int]:
    """
    Create context around matched keyword
    
    Returns:
        Tuple of (context_text, relative_match_start, relative_match_end)
    """
    start = max(0, match_start - context_length)
    end = min(len(text), match_end + context_length)
    
    context = text[start:end]
    relative_start = match_start - start
    relative_end = match_end - start
    
    if start > 0:
        context = "..." + context
        relative_start += 3
        relative_end += 3
    if end < len(text):
        context = context + "..."
    
    return clean_text(context), relative_start, relative_end


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