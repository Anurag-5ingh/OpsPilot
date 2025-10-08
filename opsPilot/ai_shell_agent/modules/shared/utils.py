"""
Shared Utilities
Common utility functions used across modules
"""
import re
import shlex


def safe_replace_keywords(text, replacements):
    """
    Safely replace words with full paths in command strings.
    
    Args:
        text: Command string
        replacements: Dict of {word: full_path}
        
    Returns:
        Modified text with replacements
    """
    for word, full_path in replacements.items():
        # Escape only the word, not the full regex
        pattern = rf"\b{re.escape(word)}\b"
        text = re.sub(pattern, full_path, text, flags=re.IGNORECASE)
    return text


def quote_paths(paths):
    """
    Add quotes to paths that might have spaces.
    
    Args:
        paths: List of file paths
        
    Returns:
        List of quoted paths
    """
    return [shlex.quote(p) for p in paths if p]


def normalize_path(path):
    """
    Normalize Windows-style path to Linux-style.
    Convert Windows-style "C:\Project" or "C:/Project" to WSL format "/mnt/c/Project"
    
    Args:
        path: File path string
        
    Returns:
        Normalized path
    """
    path = path.strip()
    if re.match(r"^[A-Za-z]:[\\/]", path):
        drive, rest = path[0], path[2:]
        rest = rest.strip("\\/").replace("\\", "/")
        return f"/mnt/{drive.lower()}/{rest}"
    return path.replace("\\", "/")
