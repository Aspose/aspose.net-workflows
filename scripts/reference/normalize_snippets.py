#!/usr/bin/env python3
"""
normalize_snippets.py — post-processing normalization for reference markdown code fences.

Operates on already-generated markdown files (not HTML). Applies the same normalization
logic used inside postprocessor.py's format_examples() so that:
  - Defect Class 1:  massive leading whitespace in code lines is removed (textwrap.dedent)
  - Defect Class 1b: orphan deep-indent blocks — e.g. C# object/array initializers where
                     a brace is aligned with a class-name or 'new' keyword instead of
                     using standard 4-space indentation.  Detected when a contiguous block
                     of lines all have indent >= _ORPHAN_BLOCK_THRESHOLD (30) while the
                     preceding code line is indented significantly less.
  - Defect Class 2:  tab characters are expanded to 4 spaces
  - Defect Class 3:  VB.NET code concatenated inside ```csharp fences is split into
                     separate ```csharp and ```vb fences
  - Defect Class 4:  blank lines at the start/end of code fences are stripped
  - Defect Class 5:  HTML entities (&lt; &gt; &amp; &#xa0; etc.) in markdown prose
                     (outside code fences) are decoded to their literal characters.
                     Code fences are left untouched — entities inside string literals
                     in C# or VB code are intentional.

Usage:
    python normalize_snippets.py <directory> [--dry-run] [--lang <code>]
                                             [--report <path>] [--llm]

    <directory>   Root directory to scan recursively for .md files.
    --dry-run     Report what would change without writing any files.
                  Prints a per-fence before/after diff for every affected fence.
    --lang <code> Only apply fence normalization (Classes 1-4) to files under a
                  /<code>/ directory segment.  Prose entity decoding (Class 5)
                  is always applied to every file regardless of this filter.
    --report <p>  Write a machine-readable JSON report to path <p>.
    --llm         Enable the optional LLM quality-scanner pass (reads LLM_ENDPOINT
                  and LLM_KEY from environment variables).  Disabled by default.

Exit codes:
    0  Success (including dry-run with zero changes)
    1  Usage error
"""

import sys
import os
import re
import textwrap
import difflib
import html as html_module
import json
import datetime

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

# Lines with indent >= this value are candidates for orphan-block reindent (Class 1b).
# Normal C# indentation rarely exceeds 24 spaces (6 nesting levels × 4 spaces), so
# 30 safely separates intentional deep alignment from ordinary nested code.
_ORPHAN_BLOCK_THRESHOLD = 30

# Minimum adjustment (spaces to remove) required before applying orphan-block reindent.
# Prevents triggering on mildly indented code that is fine as-is.
_MIN_ORPHAN_ADJUSTMENT = 20

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

    return '\n'.join(_reindent_orphan_blocks(lines))


def _reindent_orphan_blocks(lines: list) -> list:
    """
    Defect Class 1b — orphan deep-indent blocks.

    Finds contiguous runs of lines where every non-empty line has
    indent >= _ORPHAN_BLOCK_THRESHOLD (30).  When such a block exists and its
    minimum indent exceeds the preceding code line's indent by at least
    _MIN_ORPHAN_ADJUSTMENT (20), the entire block is shifted left so that its
    shallowest line aligns with the preceding line's indent level.

    Example (C# object initializer aligned to 'new' keyword):

        Before:
            options.VectorRasterizationOptions = new CadRasterizationOptions
                                                     {          ← 45 spaces
                                                         LineScale = 0.25f  ← 49 spaces
                                                     };

        After:
            options.VectorRasterizationOptions = new CadRasterizationOptions
            {          ← 4 spaces (same indent as the statement)
                LineScale = 0.25f  ← 8 spaces
            };

    Safe-guards:
    - Only activates when adjustment >= _MIN_ORPHAN_ADJUSTMENT (prevents false positives
      on mildly over-indented but acceptable code).
    - Blank lines inside an orphan block are passed through unchanged.
    - Lines whose indent would go negative are clamped to 0.
    - Does not modify lines outside detected orphan blocks.
    - Iterates until stable to handle deeply nested alignment artifacts where a single
      pass may leave inner blocks still above the threshold.
    """
    result = list(lines)
    while True:
        changed = False
        n = len(result)
        i = 0
        while i < n:
            ln = result[i]
            if not ln.strip():
                i += 1
                continue
            ind = len(ln) - len(ln.lstrip(' '))
            if ind < _ORPHAN_BLOCK_THRESHOLD:
                i += 1
                continue

            # Found the start of a potential orphan block at index i.
            block_start = i
            block_end = i

            # Extend the block forward as long as every non-empty line stays deep.
            j = i + 1
            while j < n:
                candidate = result[j]
                if candidate.strip():
                    cind = len(candidate) - len(candidate.lstrip(' '))
                    if cind < _ORPHAN_BLOCK_THRESHOLD:
                        break
                block_end = j
                j += 1

            # Find the indent of the nearest preceding non-empty line.
            preceding_indent = 0
            for k in range(block_start - 1, -1, -1):
                prev = result[k]
                if prev.strip():
                    preceding_indent = len(prev) - len(prev.lstrip(' '))
                    break

            # Compute the minimum indent within the orphan block (non-empty lines only).
            block_non_empty = [result[k] for k in range(block_start, block_end + 1)
                               if result[k].strip()]
            if block_non_empty:
                block_min = min(len(l) - len(l.lstrip(' ')) for l in block_non_empty)
                adjustment = block_min - preceding_indent
                if adjustment >= _MIN_ORPHAN_ADJUSTMENT:
                    for k in range(block_start, block_end + 1):
                        bl = result[k]
                        if bl.strip():
                            old_ind = len(bl) - len(bl.lstrip(' '))
                            new_ind = max(0, old_ind - adjustment)
                            result[k] = ' ' * new_ind + bl.lstrip(' ')
                        # blank lines: leave as-is
                    changed = True

            i = block_end + 1

        if not changed:
            break

    return result


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

# Single-group version of _FENCE_RE used to split content into prose/fence alternating
# pieces for prose-only entity decoding.  Captured group = entire fence including markers.
_FENCE_SPLIT_RE = re.compile(r'(```[^\n`]*\n.*?```)', re.DOTALL)

# HTML entity pattern used to count entities in prose before decoding.
_ENTITY_RE = re.compile(r'&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);')


def _decode_prose_entities(content: str) -> str:
    """
    Defect Class 5 — HTML entities in markdown prose.

    Decodes HTML entities (&lt;, &gt;, &amp;, &#xa0;, &#NN;, etc.) in all portions
    of content that are NOT inside a code fence.  Code fences are left verbatim so
    that entities inside C#/VB string literals (e.g. "&#xa0;" as HTML content) are
    preserved intentionally.

    Uses re.split() with _FENCE_SPLIT_RE: odd-indexed parts are fences (preserved),
    even-indexed parts are prose (decoded).  Iterates until stable to handle
    double-encoded entities (e.g. &amp;lt; → &lt; → <) that require two passes.
    """
    result = content
    while True:
        parts = _FENCE_SPLIT_RE.split(result)
        decoded_parts = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                decoded_parts.append(part)           # fence — preserve as-is
            else:
                decoded_parts.append(html_module.unescape(part))  # prose — decode
        decoded = ''.join(decoded_parts)
        if decoded == result:
            break
        result = decoded
    return result


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
            # Class 1b: orphan deep-indent block (contiguous lines with indent >= 30
            # while surrounding code is much shallower)
            elif any(len(l) - len(l.lstrip(' ')) >= _ORPHAN_BLOCK_THRESHOLD
                     for l in original_lines if l.strip()):
                defects.append('1b')
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
    fence_normalized = ''.join(output_parts)

    # Phase 2 — Defect Class 5: decode HTML entities in prose outside fences.
    # Applied regardless of whether fences changed: entities in prose are a separate
    # defect class that does not interact with fence whitespace normalization.
    prose_decoded = _decode_prose_entities(fence_normalized)
    if prose_decoded != fence_normalized:
        entity_count = len(_ENTITY_RE.findall(
            # Count entities in the prose portions only (before decoding)
            ''.join(
                part for i, part in enumerate(_FENCE_SPLIT_RE.split(fence_normalized))
                if i % 2 == 0
            )
        ))
        changes.append({
            'type': 'prose',
            'lang': None,
            'original': fence_normalized,
            'normalized': prose_decoded,
            'split_vb': None,
            'defect_classes': [5],
            'entities_decoded': entity_count,
        })
        return prose_decoded, changes

    return fence_normalized, changes


# ---------------------------------------------------------------------------
# LLM quality scanner (optional — disabled by default)
# ---------------------------------------------------------------------------

def llm_classify_fence(lang: str, body: str) -> dict:
    """
    Send a code fence to the LLM endpoint for defect classification.

    Reads LLM_ENDPOINT and LLM_KEY from environment variables.  Returns a
    structured dict with fields: defect_type, explanation, proposed_fix,
    confidence, semantic_risk, apply_fix.

    Returns a safe 'skip' response if the endpoint is not configured, the
    request fails, or the response cannot be parsed.

    Validation rules applied BEFORE accepting a proposed fix:
      - confidence >= 0.85
      - semantic_risk != 'high'
      - proposed_fix length change < 20% of original (prevents wholesale rewrites)
    """
    import os
    endpoint = os.environ.get('LLM_ENDPOINT', '')
    key = os.environ.get('LLM_KEY', '')
    if not endpoint or not key:
        return {'defect_type': 'skip', 'confidence': 0.0, 'apply_fix': False,
                'explanation': 'LLM_ENDPOINT or LLM_KEY not set', 'proposed_fix': None,
                'semantic_risk': 'unknown'}

    try:
        import requests as _requests
        prompt = (
            f'Analyze this {lang or "unknown"} code fence from API reference docs.\n'
            f'Identify rendering/formatting defects. Return JSON only:\n'
            f'{{"defect_type":"clean|excessive_indent|html_entity|malformed_fence|unknown",'
            f'"explanation":"one sentence","proposed_fix":"corrected code or null",'
            f'"confidence":0.0,"semantic_risk":"low|medium|high","apply_fix":true}}\n'
            f'Code (first 2000 chars):\n{body[:2000]}'
        )
        resp = _requests.post(
            endpoint,
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={'messages': [{'role': 'user', 'content': prompt}]},
            timeout=30,
        )
        resp.raise_for_status()
        result = json.loads(resp.json()['choices'][0]['message']['content'])

        # Validate before flagging apply_fix=True
        fix = result.get('proposed_fix')
        if result.get('confidence', 0) < 0.85:
            result['apply_fix'] = False
        if result.get('semantic_risk') == 'high':
            result['apply_fix'] = False
        if fix and len(fix) > 0:
            change_ratio = abs(len(fix) - len(body)) / max(len(body), 1)
            if change_ratio > 0.20:
                result['apply_fix'] = False
        return result
    except Exception as exc:
        return {'defect_type': 'error', 'confidence': 0.0, 'apply_fix': False,
                'explanation': str(exc), 'proposed_fix': None, 'semantic_risk': 'unknown'}


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

def scan_directory(root: str, dry_run: bool, lang: str = None,
                   report: str = None, llm: bool = False):
    """Walk root, normalize every .md file, report and optionally write.

    Fence normalization (Classes 1-4) is restricted to files whose path contains
    a /<lang>/ directory segment when lang is given.  Prose entity decoding
    (Class 5) is applied to ALL files regardless of the lang filter, because
    HTML entities in prose are wrong in every language.

    Args:
        root:    Directory to walk.
        dry_run: If True, report changes but do not write files.
        lang:    If set (e.g. 'en'), apply fence normalization only to files under
                 a directory segment matching this language code.  Entity decoding
                 (Class 5) is always applied to all files.
        report:  If set, write a machine-readable JSON summary to this path.
        llm:     If True, run the optional LLM quality-scanner on a sample of fences.
    """
    total_files = 0
    total_fences = 0
    changed_files = 0
    changed_fences = 0
    defect_counts = {}          # {class_label: count}
    llm_sent = 0
    llm_accepted = 0
    llm_rejected = 0
    affected_families = set()

    for dirpath, _, filenames in os.walk(root):
        # Determine whether this directory passes the language filter.
        # Files that do NOT match still get prose entity decoding (Class 5).
        parts = os.path.relpath(dirpath, root).replace('\\', '/').split('/')
        is_lang_match = (lang is None) or (lang in parts)

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

            # Fence count for statistics (always, regardless of lang filter)
            total_fences += len(list(_FENCE_RE.finditer(original)))

            if is_lang_match:
                # Full normalization: fence fixes + prose entity decoding
                new_content, changes = normalize_content(original)
            else:
                # Entity-only pass: skip fence normalization for non-lang files
                decoded = _decode_prose_entities(original)
                if decoded != original:
                    entity_count = len(_ENTITY_RE.findall(
                        ''.join(
                            part for i, part in
                            enumerate(_FENCE_SPLIT_RE.split(original)) if i % 2 == 0
                        )
                    ))
                    changes = [{
                        'type': 'prose',
                        'lang': None,
                        'original': original,
                        'normalized': decoded,
                        'split_vb': None,
                        'defect_classes': [5],
                        'entities_decoded': entity_count,
                    }]
                    new_content = decoded
                else:
                    changes = []
                    new_content = original

            if not changes:
                continue

            # Separate fence changes from prose changes for reporting
            fence_changes = [c for c in changes if c.get('type') != 'prose']
            prose_changes = [c for c in changes if c.get('type') == 'prose']

            changed_files += 1
            changed_fences += len(fence_changes)
            rel_path = os.path.relpath(fpath, root)

            # Track affected family (first path segment under root)
            family = parts[0] if parts and parts[0] != '.' else 'root'
            affected_families.add(family)

            # Accumulate defect counts
            for ch in changes:
                for dc in ch['defect_classes']:
                    key = str(dc)
                    defect_counts[key] = defect_counts.get(key, 0) + 1

            print(f'\n{"="*72}')
            print(f'FILE: {rel_path}')
            n_fence = len(fence_changes)
            n_prose = len(prose_changes)
            summary_parts = []
            if n_fence:
                summary_parts.append(f'{n_fence} fence change(s)')
            if n_prose:
                total_entities = sum(c.get('entities_decoded', 0) for c in prose_changes)
                summary_parts.append(f'prose: {total_entities} entity(ies) decoded')
            print(f'  {", ".join(summary_parts)}')

            for i, ch in enumerate(fence_changes, 1):
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
                        safe = ('    ' + line).encode(
                            sys.stdout.encoding or 'utf-8', errors='replace'
                        ).decode(sys.stdout.encoding or 'utf-8', errors='replace')
                        print(safe)
                    if len(diff) > 30:
                        print(f'    ... ({len(diff) - 30} more diff lines)')

                if ch.get('split_vb'):
                    print(f'  [VB split] VB.NET block separated into ```vb fence '
                          f'({len(ch["split_vb"].splitlines())} lines)')

                # Optional LLM quality scan on unchanged fences (novel defect detection)
                if llm and not ch['defect_classes']:
                    llm_sent += 1
                    result = llm_classify_fence(ch['lang'], ch['original'])
                    if result.get('apply_fix') and result.get('proposed_fix'):
                        llm_accepted += 1
                        print(f'  [LLM] {result["defect_type"]} '
                              f'(confidence={result["confidence"]:.2f}): '
                              f'{result["explanation"]}')
                    else:
                        llm_rejected += 1

            if not dry_run:
                try:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                except Exception as e:
                    print(f'[ERROR] Could not write {fpath}: {e}')

    verb = 'that would change' if dry_run else 'changed'
    print(f'\n{"="*72}')
    print(f'SUMMARY')
    print(f'  Files scanned  : {total_files}')
    print(f'  Fences found   : {total_fences}')
    print(f'  Files {verb}  : {changed_files}')
    print(f'  Fences {verb} : {changed_fences}')
    if defect_counts:
        dc_str = ', '.join(f'Class {k}: {v}' for k, v in sorted(defect_counts.items()))
        print(f'  Defect counts  : {dc_str}')
    if llm:
        print(f'  LLM sent/accepted/rejected: {llm_sent}/{llm_accepted}/{llm_rejected}')
    if dry_run:
        print(f'\n  DRY RUN — no files were written.')

    # Write JSON report if requested
    if report:
        report_data = {
            'run_at': datetime.datetime.utcnow().isoformat() + 'Z',
            'root': root,
            'lang_filter': lang,
            'dry_run': dry_run,
            'files_scanned': total_files,
            'fences_scanned': total_fences,
            'files_changed': changed_files,
            'fences_changed': changed_fences,
            'defect_counts': defect_counts,
            'llm_sent': llm_sent,
            'llm_accepted': llm_accepted,
            'llm_rejected': llm_rejected,
            'affected_families': sorted(affected_families),
        }
        try:
            with open(report, 'w', encoding='utf-8') as rf:
                json.dump(report_data, rf, indent=2)
            print(f'\n  Report written: {report}')
        except Exception as e:
            print(f'[ERROR] Could not write report {report}: {e}')

    return changed_files


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    dry_run = False
    lang = None
    report = None
    llm = False
    raw_args = sys.argv[1:]
    filtered = []
    i = 0
    while i < len(raw_args):
        a = raw_args[i]
        if a == '--dry-run':
            dry_run = True
            i += 1
        elif a == '--lang' and i + 1 < len(raw_args):
            lang = raw_args[i + 1]
            i += 2
        elif a == '--report' and i + 1 < len(raw_args):
            report = raw_args[i + 1]
            i += 2
        elif a == '--llm':
            llm = True
            i += 1
        elif a == '--no-llm':
            llm = False
            i += 1
        else:
            filtered.append(a)
            i += 1

    if len(filtered) != 1:
        print('Usage: python normalize_snippets.py <directory> '
              '[--dry-run] [--lang <code>] [--report <path>] [--llm]')
        sys.exit(1)

    root = filtered[0]
    if not os.path.isdir(root):
        print(f'Error: {root!r} is not a directory.')
        sys.exit(1)

    if lang:
        print(f'Language filter (fence normalization): {lang}')
        print(f'Note: Prose entity decoding (Class 5) applies to ALL files.')
    if llm:
        print(f'LLM scanner: enabled (endpoint from LLM_ENDPOINT env var)')
    scan_directory(root, dry_run=dry_run, lang=lang, report=report, llm=llm)
