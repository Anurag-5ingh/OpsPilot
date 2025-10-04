# #scanner.py
# import os
# import json
# from ai_shell_agent.utils import normalize_path

# BASE_DIRS = ["/mnt/c/"]
# SKIP_DIRS = {"Windows", "Program Files", "ProgramData", "$Recycle.Bin", "Users", "Program Files (x86)"}
# CACHE_PATH = os.path.join(os.path.dirname(__file__), "scanned_paths.json")

# #Recursively search for a directory or file by name
# def scan_for_target(target_name: str):
#     print(f"Scanning file system for '{target_name}'...", end=" ", flush=True)

#     #Use cache if available
#     if os.path.exists(CACHE_PATH):
#         try:
#             with open(CACHE_PATH, "r") as f:
#                 cache = json.load(f)
#                 if target_name in cache:
#                     valid_paths = [
#                         p for p in cache[target_name]
#                         if is_valid_path(p)
#                     ]
#                     print(f"{len(valid_paths)} cached paths found.")
#                     return valid_paths
#         except:
#             pass  #Ignore cache load errors

#     visited = set()
#     found = []

#     def walk(path):
#         if path in visited:
#             return
#         visited.add(path)

#         #Skip if path contains any folder from SKIP_DIRS
#         path_parts = set(p.lower() for p in path.split(os.sep))
#         if any(skip.lower() in path_parts for skip in SKIP_DIRS):
#             return

#         try:
#             with os.scandir(path) as it:
#                 for entry in it:
#                     full_path = os.path.join(path, entry.name)

#                     if entry.name == target_name:
#                         norm_path = normalize_path(full_path)
#                         if is_valid_path(norm_path):
#                             found.append(norm_path)

#                     if entry.is_dir(follow_symlinks=False):
#                         walk(full_path)
#         except:
#             pass  #Silently skip unreadable folders

#     for base in BASE_DIRS:
#         walk(base)

#     print(f"{len(found)} paths found.")

#     #Update cache
#     try:
#         if os.path.exists(CACHE_PATH):
#             with open(CACHE_PATH, "r") as f:
#                 cache = json.load(f)
#         else:
#             cache = {}

#         cache[target_name] = found

#         os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

#         with open(CACHE_PATH, "w") as f:
#             json.dump(cache, f, indent=2)
#     except Exception as e:
#         print(f"Could not update cache: {e}")

#     return found


# def is_valid_path(path: str) -> bool:
#     """
#     Exclude malformed Windows paths like /mnt/c/Project/opspilot/C:/Project/...
#     """
#     # Invalid if 'C:/' or other Windows root appears after the beginning
#     parts = path.split("/")
#     return not any(part.endswith(":") or ":/" in part for part in parts[2:])
