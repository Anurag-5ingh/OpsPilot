"""
Find filename-similar and exact duplicate files in the repository.

Outputs a JSON report to stdout with two keys:
- exact_duplicates: list of groups of files with identical SHA256 hash
- name_similar: list of pairs of files with normalized names equal (underscores/dashes/case) or short Levenshtein distance

This is a safe read-only analysis script — it will not modify files.
"""
import os
import sys
import hashlib
import json
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# simple levenshtein implementation (iterative, small files ok)
def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)
    v0 = list(range(len(b) + 1))
    v1 = [0] * (len(b) + 1)
    for i in range(len(a)):
        v1[0] = i + 1
        for j in range(len(b)):
            cost = 0 if a[i] == b[j] else 1
            v1[j+1] = min(v1[j] + 1, v0[j+1] + 1, v0[j] + cost)
        v0, v1 = v1, v0
    return v0[len(b)]


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def normalize_name(p):
    name = os.path.basename(p)
    name = name.lower()
    name = name.replace('.', '_')
    name = name.replace('-', '_')
    name = name.replace('__', '_')
    return name


def main():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # skip virtual env-like and .git
        if any(part in ('.git', 'node_modules', '.venv', 'venv', '__pycache__') for part in dirpath.split(os.sep)):
            continue
        for fn in filenames:
            # skip binary heavy files
            if fn.endswith(('.png', '.jpg', '.jpeg', '.gif', '.zip', '.tar', '.tar.gz')):
                continue
            full = os.path.join(dirpath, fn)
            files.append(full)

    # exact duplicates
    hash_map = defaultdict(list)
    for f in files:
        try:
            h = sha256_of_file(f)
            hash_map[h].append(os.path.relpath(f, ROOT))
        except Exception as e:
            print(f"Warning: failed to hash {f}: {e}", file=sys.stderr)

    exact_duplicates = [group for group in hash_map.values() if len(group) > 1]

    # name-similar by normalization and small levenshtein
    normalized = defaultdict(list)
    for f in files:
        n = normalize_name(f)
        normalized[n].append(os.path.relpath(f, ROOT))

    name_similar = []
    # exact normalized matches
    for n, group in normalized.items():
        if len(group) > 1:
            name_similar.append({'kind': 'normalized_match', 'files': group})

    # near matches using levenshtein on basenames
    basenames = [(os.path.relpath(f, ROOT), os.path.basename(f).lower()) for f in files]
    N = len(basenames)
    for i in range(N):
        for j in range(i+1, N):
            a_path, a = basenames[i]
            b_path, b = basenames[j]
            # skip extremely different sizes
            if abs(len(a) - len(b)) > 6:
                continue
            dist = levenshtein(a, b)
            if 0 < dist <= 3:
                name_similar.append({'kind': 'levenshtein', 'distance': dist, 'files': [a_path, b_path]})

    report = {
        'root': ROOT,
        'exact_duplicates': exact_duplicates,
        'name_similar': name_similar
    }

    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
