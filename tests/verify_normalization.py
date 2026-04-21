#!/usr/bin/env python3
"""
verify_normalization.py — local evidence harness for code snippet normalization.

Addresses Gap G3: proves, without access to the Aspose/aspose.net content repo,
that normalize_snippets.py:
  - detects and fixes all 5 defect classes (Classes 1, 1b, 2, 3, 4, 5)
  - leaves clean files untouched (non-regression)
  - produces zero changes on a second pass (idempotency)

Usage:
    python tests/verify_normalization.py

Exit codes:
    0  All scenarios PASS
    1  One or more scenarios FAIL
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess

# -----------------------------------------------------------------------
# Synthetic markdown fixtures — one per defect class + one clean file
# -----------------------------------------------------------------------

FIXTURES = {
    'class1_massive_indent.md': (
        '---\ntitle: Class1\n---\n\n'
        'Example method:\n\n'
        '```csharp\n'
        'MethodSignature()\n'
        + ' ' * 72 + 'body_line1\n'
        + ' ' * 72 + 'body_line2\n'
        '```\n'
    ),
    'class1b_orphan_block.md': (
        '---\ntitle: Class1b\n---\n\n'
        'Object initializer example:\n\n'
        '```csharp\n'
        'options = new CadRasterizationOptions\n'
        + ' ' * 45 + '{\n'
        + ' ' * 49 + 'LineScale = 0.25f\n'
        + ' ' * 45 + '};\n'
        '```\n'
    ),
    'class2_tabs.md': (
        '---\ntitle: Class2\n---\n\n'
        'Tab-indented code:\n\n'
        '```csharp\n'
        '\tvar x = 1;\n'
        '\t\tvar y = 2;\n'
        '```\n'
    ),
    'class3_mixed_vb.md': (
        '---\ntitle: Class3\n---\n\n'
        'Mixed language example:\n\n'
        '```csharp\n'
        'var doc = new Document();\n'
        'doc.Save("out.docx");\n'
        '\n'
        'Using doc As New Document()\n'
        '    doc.Save("out.docx")\n'
        'End Using\n'
        '```\n'
    ),
    'class4_blank_start.md': (
        '---\ntitle: Class4\n---\n\n'
        'Blank-start fence:\n\n'
        '```csharp\n'
        '\n'
        'var x = 1;\n'
        '```\n'
    ),
    'class5_prose_entity.md': (
        '---\ntitle: Class5\n---\n\n'
        'The IEnumerable&lt;T&gt; interface is generic.\n'
        'Use &amp; for address-of operator.\n\n'
        '```csharp\n'
        'IEnumerable<int> items = GetItems();\n'
        '```\n'
    ),
    'clean_file.md': (
        '---\ntitle: Clean\n---\n\n'
        'No defects here.\n\n'
        '```csharp\n'
        'var x = 1;\n'
        'var y = x + 2;\n'
        'Console.WriteLine(y);\n'
        '```\n'
    ),
}

# Which files are expected to change on first pass
EXPECTED_TO_CHANGE = {
    'class1_massive_indent.md',
    'class1b_orphan_block.md',
    'class2_tabs.md',
    'class3_mixed_vb.md',
    'class4_blank_start.md',
    'class5_prose_entity.md',
}
EXPECTED_CLEAN = {'clean_file.md'}


def run_normalizer(target_dir, dry_run=False, report_path=None):
    """Invoke normalize_snippets.py as a subprocess; return (returncode, report_dict_or_None)."""
    script = os.path.join(
        os.path.dirname(__file__), '..', 'scripts', 'reference', 'normalize_snippets.py'
    )
    cmd = [sys.executable, script, target_dir]
    if dry_run:
        cmd.append('--dry-run')
    if report_path:
        cmd += ['--report', report_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    report = None
    if report_path and os.path.exists(report_path):
        with open(report_path, encoding='utf-8') as f:
            report = json.load(f)
    return result.returncode, report, result.stdout


def check(label, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    print(f'  [{status}] {label}' + (f': {detail}' if detail else ''))
    return condition


def main():
    all_passed = True
    tmpdir = tempfile.mkdtemp(prefix='verify_norm_')

    try:
        print(f'\nVerification harness — temp dir: {tmpdir}')
        print('=' * 72)

        # ---------------------------------------------------------------
        # Step 1: Write fixtures
        # ---------------------------------------------------------------
        print('\nStep 1: Writing synthetic fixture files')
        for fname, content in FIXTURES.items():
            path = os.path.join(tmpdir, fname)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        print(f'  Wrote {len(FIXTURES)} files.')

        # ---------------------------------------------------------------
        # Step 2: Dry-run — confirm defective files detected, clean safe
        # ---------------------------------------------------------------
        print('\nStep 2: Dry-run pass — detecting defects without writing')
        rpt1 = os.path.join(tmpdir, 'dry_report.json')
        rc, report, stdout = run_normalizer(tmpdir, dry_run=True, report_path=rpt1)

        ok = check('Normalizer exited 0', rc == 0, f'exit code={rc}')
        all_passed = all_passed and ok

        if report:
            changed = report.get('files_changed', -1)
            scanned = report.get('files_scanned', -1)
            ok = check(
                f'Dry-run: {len(EXPECTED_TO_CHANGE)} defective files detected',
                changed == len(EXPECTED_TO_CHANGE),
                f'files_changed={changed}, expected={len(EXPECTED_TO_CHANGE)}'
            )
            all_passed = all_passed and ok

            ok = check(
                f'Dry-run: all {len(FIXTURES)} files scanned',
                scanned == len(FIXTURES),
                f'files_scanned={scanned}'
            )
            all_passed = all_passed and ok

            dc = report.get('defect_counts', {})
            ok = check('Dry-run: defect_counts present', bool(dc), str(dc))
            all_passed = all_passed and ok
        else:
            print('  [FAIL] Could not read dry-run report JSON')
            all_passed = False

        # ---------------------------------------------------------------
        # Step 3: Write pass — apply fixes
        # ---------------------------------------------------------------
        print('\nStep 3: Write pass — applying fixes')
        rpt2 = os.path.join(tmpdir, 'write_report.json')
        rc, report2, stdout2 = run_normalizer(tmpdir, dry_run=False, report_path=rpt2)

        ok = check('Write pass exited 0', rc == 0, f'exit code={rc}')
        all_passed = all_passed and ok
        if report2:
            changed2 = report2.get('files_changed', -1)
            ok = check(
                f'Write pass: {len(EXPECTED_TO_CHANGE)} files changed',
                changed2 == len(EXPECTED_TO_CHANGE),
                f'files_changed={changed2}'
            )
            all_passed = all_passed and ok

        # ---------------------------------------------------------------
        # Step 4: Idempotency — second dry-run must show 0 changes
        # ---------------------------------------------------------------
        print('\nStep 4: Idempotency — second dry-run must show 0 files changed')
        rpt3 = os.path.join(tmpdir, 'idem_report.json')
        rc, report3, stdout3 = run_normalizer(tmpdir, dry_run=True, report_path=rpt3)

        ok = check('Second dry-run exited 0', rc == 0, f'exit code={rc}')
        all_passed = all_passed and ok
        if report3:
            changed3 = report3.get('files_changed', 0)
            ok = check(
                'Idempotency: 0 files changed on second pass',
                changed3 == 0,
                f'files_changed={changed3}'
            )
            all_passed = all_passed and ok
        else:
            print('  [FAIL] Could not read idempotency report JSON')
            all_passed = False

        # ---------------------------------------------------------------
        # Step 5: Non-regression — clean file must be byte-for-byte stable
        # ---------------------------------------------------------------
        print('\nStep 5: Non-regression — clean file untouched by write pass')
        for fname in EXPECTED_CLEAN:
            path = os.path.join(tmpdir, fname)
            with open(path, encoding='utf-8') as f:
                current = f.read()
            original = FIXTURES[fname]
            ok = check(
                f'Clean file unchanged: {fname}',
                current == original,
                'content changed unexpectedly' if current != original else ''
            )
            all_passed = all_passed and ok

        # ---------------------------------------------------------------
        # Summary
        # ---------------------------------------------------------------
        print('\n' + '=' * 72)
        if all_passed:
            print('RESULT: ALL SCENARIOS PASSED')
        else:
            print('RESULT: ONE OR MORE SCENARIOS FAILED — see details above')
        print('=' * 72)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
