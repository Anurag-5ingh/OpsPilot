# utils.py
import re
import shlex

#Safely replace words with full paths in command strings
def safe_replace_keywords(text, replacements):
    for word, full_path in replacements.items():
        # Escape only the word, not the full regex
        pattern = rf"\b{re.escape(word)}\b"
        text = re.sub(pattern, full_path, text, flags=re.IGNORECASE)
    return text

#Add quotes to paths that might have spaces
def quote_paths(paths):
    return [shlex.quote(p) for p in paths if p]

#Normalize Windows-style path to Linux-style
def normalize_path(path):
    # Convert Windows-style "C:\Project" or "C:/Project" to WSL format "/mnt/c/Project"
    path = path.strip()
    if re.match(r"^[A-Za-z]:[\\/]", path):
        drive, rest = path[0], path[2:]
        rest = rest.strip("\\/").replace("\\", "/")
        return f"/mnt/{drive.lower()}/{rest}"
    return path.replace("\\", "/")
