"""
Scan all files recursively for dpNameEdit[1]+">"+dpNameEdit[2]+">"+dpNameEdit[3] concatenation patterns.
Produces a deduplicated report grouped by template file name.
Output goes to a UTF-8 file to avoid console encoding issues.
"""
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Modules/
OUT_FILE = os.path.join(ROOT, "reports", "dpNameEdit_concat_scan.txt")

def w(text=""):
    out.write(text + "\n")

# Simpler pattern - just match the three indices on one line
PATTERN_SIMPLE = re.compile(r'dpNameEdit\[1\].*dpNameEdit\[2\].*dpNameEdit\[3\]')

# Extract suffix: the last ">" + "SOMETHING" part  (handles XML-encoded and escaped quotes)
SUFFIX_PATTERN = re.compile(
    r'dpNameEdit\[3\]\s*\+\s*'
    r'(?:&quot;&gt;&quot;|\\?">\\?"|\\?"\\?>\\?")\s*\+\s*'
    r'(?:&quot;|\\?"|")([A-Za-z0-9_]+)(?:&quot;|\\?"|")'
)

SKIP_DIRS = {'__pycache__', '.venv', '.git', 'node_modules'}
SKIP_EXTENSIONS = {'.py', '.pyc', '.bat', '.ps1', '.csv', '.json'}

results = []

for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fname in filenames:
        ext = os.path.splitext(fname)[1].lower()
        if ext in SKIP_EXTENSIONS:
            continue
        full_path = os.path.join(dirpath, fname)
        rel_path = os.path.relpath(full_path, ROOT)
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if PATTERN_SIMPLE.search(line):
                        trimmed = line.strip()
                        m = SUFFIX_PATTERN.search(line)
                        suffix = m.group(1) if m else "(no suffix)"
                        results.append((full_path, rel_path, i, trimmed, suffix))
        except Exception:
            pass

with open(OUT_FILE, "w", encoding="utf-8") as out:
    w(f"=== TOTAL MATCHES: {len(results)} ===")
    w()

    # Separate meta vs source
    source_results = []
    meta_results = []
    for r in results:
        top_dir = r[1].split(os.sep)[0]
        if top_dir in ('reports', 'scripts') or r[1].endswith('.md') or r[1].endswith('.txt'):
            meta_results.append(r)
        else:
            source_results.append(r)

    w(f"--- Meta files (reports/scripts/README): {len(meta_results)} matches ---")
    for _, rel, ln, content, suffix in meta_results:
        w(f"  {rel}:{ln}  suffix={suffix}")
        w(f"    {content[:200]}")
    w()

    # Group by template filename
    by_template = defaultdict(list)
    for full, rel, ln, content, suffix in source_results:
        fname = os.path.basename(rel)
        by_template[fname].append((rel, ln, content, suffix))

    unique_file_paths = set(r[1] for r in source_results)
    
    w(f"--- Source XML files: {len(source_results)} matches ---")
    w(f"--- Unique template names (filenames): {len(by_template)} ---")
    w(f"--- Unique file paths (total copies): {len(unique_file_paths)} ---")
    w()

    for template_name in sorted(by_template.keys()):
        entries = by_template[template_name]
        paths = sorted(set(e[0] for e in entries))
        suffixes = sorted(set(e[3] for e in entries))
        
        w(f"== TEMPLATE: {template_name}")
        w(f"   File copies: {len(paths)}")
        w(f"   Suffixes: {', '.join(suffixes)}")
        w(f"   Total line matches: {len(entries)}")
        w(f"   Locations:")
        for p in paths:
            path_entries = [(ln, suf) for (rp, ln, c, suf) in entries if rp == p]
            lines_str = ", ".join(f"L{ln}({suf})" for ln, suf in path_entries)
            w(f"     {p}  -> {lines_str}")
        w()

    # Summary
    w("=" * 80)
    w("SUFFIX SUMMARY")
    w("=" * 80)
    suffix_count = defaultdict(int)
    suffix_templates = defaultdict(set)
    for full, rel, ln, content, suffix in source_results:
        suffix_count[suffix] += 1
        suffix_templates[suffix].add(os.path.basename(rel))

    for suffix in sorted(suffix_count.keys()):
        templates = sorted(suffix_templates[suffix])
        w(f"  {suffix}: {suffix_count[suffix]} matches in {len(templates)} templates")
        for t in templates:
            w(f"      - {t}")

    w()
    w("=" * 80)
    w("BY TOP-LEVEL DIRECTORY")
    w("=" * 80)
    by_top = defaultdict(int)
    for _, rel, _, _, _ in source_results:
        top = rel.split(os.sep)[0]
        by_top[top] += 1
    for top in sorted(by_top.keys()):
        w(f"  {top}: {by_top[top]} matches")

print("Done. Report: " + OUT_FILE)
print("Total: " + str(len(results)))
