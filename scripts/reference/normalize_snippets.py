#!/usr/bin/env python3
"""
normalize_snippets.py — post-processing normalization for reference markdown code fences.

Operates on already-generated markdown files (not HTML). Applies the same normalization
logic used inside postprocessor.py's format_examples() so that:
  - Defect Class 1: massive leading whitespace in code lines is removed (textwrap.dedent)
  - Defect Class 2: tab characters are expanded to 4 spaces
  - Defect Class 3: VB.NET code concatenated inside ```csharp fences is split into
                    separate ```csharp and ```vb fences
  - Defect Class 4: blank lines at the start/end of code fences are stripped

Usage:
    python normalize_snippets.py <directory> [--dry-run]

    <directory>  Root directory to scan recursively for .md files.
    --dry-run    Report what would change without writing any files.
                 Prints a per-fence before/after diff for every affected fence.

Exit codes:
    0  Success (including dry-run with zero changes)
    1  Usage error
"""

import sys
import os
import re
import textwrap
import difflib

# NOTE: The _norm() function in this file deliberately differs from the one in postprocessor.py:
# - This file: strips LEADING blank lines only (conservative — avoids churn on existing files
#   where the trailing '\n' before the closing ``` is intentional).
# - postprocessor.py: strips BOTH leading and trailing blank lines (aggressive — fresh content
#   extracted from HTML has no intentional trailing blanks).
# Both share the same body-only dedent logic (threshold: _BODY_DEDENT_THRESHOLD spaces).

# Minimum leading spaces in body lines (lines[1:]) that triggers body-only dedent.
# Source C# test methods are typically nested 3-5 class/namespace levels deep (4 spaces ×
# ~18 levels = 72+ spaces), so 40 is well below the minimum artifact level while staying
# above realistic intentional indentation depths.
_BODY_DEDENT_THRESHOLD = 40

# ---------------------------------------------------------------------------
# Core normalization (mirrors _norm / _split_mixed_vbnet in postprocessor.py)
# ---------------------------------------------------------------------------

def _norm(code: str) -> str:
    """
    Conservative normalization for existing markdown files:
      1. Expand tabs to 4 spaces
      2. Strip LEADING blank lines only (trailing blank lines are preserved to
         avoid unnecessary churn on content that was generated correctly)
      3. Remove common leading whitespace (textwrap.dedent)

    Special case for Defect Class 1 in existing words/* files:
      The original postprocessor called .strip() on the whole code block, which
      stripped the leading indent from line 0 (e.g. the method signature) but left
      lines 1+ with their original deep indentation (72-92 spaces). textwrap.dedent
      sees common_indent=0 (because line 0 has none) and does nothing.
      We detect this: if body lines 1+ all share a large common indent (>= 40 spaces)
      while line 0 has less, we strip that body-only common indent from lines 1+.
    """
    code = code.expandtabs(4)
    lines = code.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return ''

    # Standard dedent: handles the case where ALL lines (including line 0) share
    # a common indent — this covers fresh pipeline output normalized by _norm().
    non_empty = [l for l in lines if l.strip()]
    if non_empty:
        common = min(len(l) - len(l.lstrip(' ')) for l in non_empty)
        if common > 0:
            return textwrap.dedent('\n'.join(lines))

    # Body-only dedent: existing files where line 0 has indent 0 (stripped by old
    # postprocessor) but lines 1+ carry the original deep indentation.
    if len(lines) > 1:
        body_non_empty = [l for l in lines[1:] if l.strip()]
        if body_non_empty:
            body_common = min(len(l) - len(l.lstrip(' ')) for l in body_non_empty)
            if body_common >= _BODY_DEDENT_THRESHOLD:
                # Strip body_common spaces from all body lines
                fixed = [lines[0]]
                for l in lines[1:]:
                    fixed.append(l[body_common:] if len(l) >= body_common else l.lstrip(' '))
                return '\n'.join(fixed)

    return '\n'.join(lines)


_VB_LINE_START = re.compile(
    r'^(End\s+(Using|Sub|Function|Class|If|Module|Namespace)|'
    r'For\s+Each\s|'
    r'Next\b|'
    r'Using\s+\w|'
    r'Dim\s+\w|'
    r'Module\s+\w)',
    re.MULTILINE
)

# Matches a full code fence: opening marker, body, closing marker.
# Group 1 = language tag (may be empty), Group 2 = body (may be empty)
_FENCE_RE = re.compile(r'(```([^\n`]*)\n)(.*?)(```)', re.DOTALL)


def _normalize_fence_body(lang: str, body: str):
    """
    Return (normalized_body, vb_body_or_None).
    If the fence is a mixed csharp/VB.NET fence, vb_body_or_None is the VB block.
    """
    normalized = _norm(body)

    # Defect Class 3: split mixed VB.NET only for csharp fences
    if lang.strip().lower() == 'csharp' and _VB_LINE_START.search(normalized):
        lines = normalized.splitlines()
        split_idx = None
        for i, line in enumerate(lines):
            if _VB_LINE_START.match(line.lstrip()):
                split_idx = i
                while split_idx > 0 and not lines[split_idx - 1].strip():
                    split_idx -= 1
                break
        if split_idx is not None and split_idx > 0:
            cs_block = _norm('\n'.join(lines[:split_idx]))
            vb_block = _norm('\n'.join(lines[split_idx:]))
            if cs_block and vb_block:
                return cs_block, vb_block

    return normalized, None


def normalize_content(content: str):
    """
    Normalize all code fences in a markdown string.
    Returns (new_content, list_of_fence_changes).

    Each fence change is a dict:
        {
            'lang': str,
            'original': str,   # original fence body
            'normalized': str, # normalized fence body
            'split_vb': str or None,  # VB block if fence was split
            'defect_classes': list[int],
        }
    """
    changes = []
    output_parts = []
    last_end = 0

    for m in _FENCE_RE.finditer(content):
        open_marker = m.group(1)   # e.g. "```csharp\n"
        lang = m.group(2)          # e.g. "csharp"
        body = m.group(3)          # content between fences
        close_marker = m.group(4)  # "```"

        normalized, vb_block = _normalize_fence_body(lang, body)

        # Compare ignoring trailing whitespace: the regex body always ends with \n
        # (the newline before the closing ```), so body.rstrip() == normalized.rstrip()
        # for a clean fence. Only flag genuine content changes.
        defects = []
        if body.rstrip() != normalized.rstrip() or vb_block is not None:
            original_lines = body.splitlines()

            # Class 1: any non-empty line has >= 40 leading spaces (massive indent artifact)
            if any(len(l) - len(l.lstrip(' ')) >= 40 for l in original_lines if l.strip()):
                defects.append(1)
            # Class 2: tab characters present
            if '\t' in body:
                defects.append(2)
            # Class 3: VB.NET split
            if vb_block is not None:
                defects.append(3)
            # Class 4: blank line at the START of the fence body
            if original_lines and not original_lines[0].strip():
                defects.append(4)

            if not defects:
                defects.append(0)  # changed but no specific class (other whitespace)

        # Build replacement
        if body.rstrip() == normalized.rstrip() and vb_block is None:
            # No meaningful change — copy verbatim
            output_parts.append(content[last_end:m.end()])
            last_end = m.end()
            continue

        # Record the change
        changes.append({
            'lang': lang,
            'original': body,
            'normalized': normalized,
            'split_vb': vb_block,
            'defect_classes': defects,
            'span': (m.start(), m.end()),
        })

        # Emit the text before this fence
        output_parts.append(content[last_end:m.start()])

        # Emit the normalized fence, preserving the trailing newline from the original body
        trailing = '\n' if body.endswith('\n') else ''
        output_parts.append(f'```{lang}\n{normalized}{trailing}```')
        if vb_block is not None:
            output_parts.append(f'\n```vb\n{vb_block}{trailing}```')

        last_end = m.end()

    output_parts.append(content[last_end:])
    return ''.join(output_parts), changes


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

def scan_directory(root: str, dry_run: bool, lang: str = None):
    """Walk root, normalize every .md file, report and optionally write.

    If lang is given (e.g. 'en'), only process files whose path contains
    a /<lang>/ directory segment (i.e. content/reference.aspose.net/<family>/<lang>/).
    """
    total_files = 0
    total_fences = 0
    changed_files = 0
    changed_fences = 0

    for dirpath, _, filenames in os.walk(root):
        # Language filter: skip directories that don't contain /<lang>/ in their path.
        # Works whether root is reference.aspose.net/ (parts: family/lang) or a
        # specific family dir (parts: lang).
        if lang is not None:
            parts = os.path.relpath(dirpath, root).replace('\\', '/').split('/')
            if lang not in parts:
                continue

        for fname in filenames:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(dirpath, fname)
            total_files += 1

            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    original = f.read()
            except Exception as e:
                print(f'[ERROR] Could not read {fpath}: {e}')
                continue

            new_content, changes = normalize_content(original)
            # Count fences in original (rough count for stats)
            total_fences += len(list(_FENCE_RE.finditer(original)))

            if not changes:
                continue

            changed_files += 1
            changed_fences += len(changes)
            rel_path = os.path.relpath(fpath, root)

            print(f'\n{"="*72}')
            print(f'FILE: {rel_path}')
            print(f'  {len(changes)} fence(s) would be {"changed" if dry_run else "changed"}')

            for i, ch in enumerate(changes, 1):
                dc_labels = ', '.join(f'Class {d}' for d in ch['defect_classes']) or 'unknown'
                print(f'\n  Fence #{i}  lang={ch["lang"] or "(none)"}  defects=[{dc_labels}]')

                # Show a unified diff of the fence body
                before_lines = ch['original'].splitlines(keepends=True)
                after_lines = ch['normalized'].splitlines(keepends=True)
                diff = list(difflib.unified_diff(
                    before_lines, after_lines,
                    fromfile='before', tofile='after', lineterm=''
                ))
                if diff:
                    # Limit output to first 30 diff lines to avoid flooding
                    for line in diff[:30]:
                        safe = ('    ' + line).encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace')
                        print(safe)
                    if len(diff) > 30:
                        print(f'    ... ({len(diff) - 30} more diff lines)')

                if ch['split_vb']:
                    print(f'  [VB split] VB.NET block separated into ```vb fence ({len(ch["split_vb"].splitlines())} lines)')

            if not dry_run:
                try:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                except Exception as e:
                    print(f'[ERROR] Could not write {fpath}: {e}')

    print(f'\n{"="*72}')
    print(f'SUMMARY')
    print(f'  Files scanned  : {total_files}')
    print(f'  Fences found   : {total_fences}')
    print(f'  Files {"that would change" if dry_run else "changed"}  : {changed_files}')
    print(f'  Fences {"that would change" if dry_run else "changed"} : {changed_fences}')
    if dry_run:
        print(f'\n  DRY RUN — no files were written.')
    return changed_files


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    flags = {'--dry-run', '--lang'}
    dry_run = '--dry-run' in sys.argv[1:]

    # Parse --lang <value>
    lang = None
    raw_args = sys.argv[1:]
    filtered = []
    i = 0
    while i < len(raw_args):
        if raw_args[i] == '--lang' and i + 1 < len(raw_args):
            lang = raw_args[i + 1]
            i += 2
        elif raw_args[i] == '--dry-run':
            i += 1
        else:
            filtered.append(raw_args[i])
            i += 1

    if len(filtered) != 1:
        print('Usage: python normalize_snippets.py <directory> [--dry-run] [--lang <code>]')
        sys.exit(1)

    root = filtered[0]
    if not os.path.isdir(root):
        print(f'Error: {root!r} is not a directory.')
        sys.exit(1)

    if lang:
        print(f'Language filter: {lang}')
    scan_directory(root, dry_run=dry_run, lang=lang)
