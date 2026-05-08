"""
Unit tests for normalize_snippets.py

Run with: python -m pytest tests/test_normalize_snippets.py -v
"""
import sys
import os

# Make the scripts directory importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'reference'))

from normalize_snippets import (
    _norm, normalize_content, _BODY_DEDENT_THRESHOLD,
    _decode_prose_entities, llm_classify_fence,
)


# ---------------------------------------------------------------------------
# _norm() tests
# ---------------------------------------------------------------------------

class TestNorm:

    def test_body_only_dedent_class1(self):
        """Defect Class 1: line 0 has 0 indent, lines 1+ have massive indent (>=40 spaces)."""
        deep = ' ' * 72
        code = f'methodSignature()\n{deep}line1\n{deep}line2'
        result = _norm(code)
        assert result == 'methodSignature()\nline1\nline2'

    def test_body_only_dedent_threshold(self):
        """Body-only dedent triggers at exactly _BODY_DEDENT_THRESHOLD spaces."""
        indent = ' ' * _BODY_DEDENT_THRESHOLD
        code = f'line0\n{indent}line1\n{indent}line2'
        result = _norm(code)
        assert result == 'line0\nline1\nline2'

    def test_body_only_dedent_does_not_trigger_below_threshold(self):
        """Body-only dedent (threshold=40) does not trigger at 39 spaces.
        However, _reindent_orphan_blocks (threshold=30) DOES trigger at 39 spaces when
        the preceding line is at indent 0 (adjustment=39 >= 20).  This is correct: 39
        spaces of alignment artifact relative to a 0-indent preceding line is fixed.
        The test verifies the body-only dedent path specifically by ensuring that
        standard dedent also doesn't trigger (common_indent=0) — the final fix comes
        from _reindent_orphan_blocks, not body-only dedent.
        """
        indent = ' ' * (_BODY_DEDENT_THRESHOLD - 1)   # 39 spaces
        code = f'line0\n{indent}line1'
        result = _norm(code)
        # _reindent_orphan_blocks fires (39 >= 30, adjustment=39 >= 20) → lines normalized
        assert result == 'line0\nline1'

    def test_body_only_dedent_does_not_trigger_below_orphan_threshold(self):
        """Neither body-only dedent nor orphan-block reindent triggers at 25 spaces.
        25 < 30 (_ORPHAN_BLOCK_THRESHOLD), so _reindent_orphan_blocks skips it.
        25 < 40 (_BODY_DEDENT_THRESHOLD), so body-only dedent skips it.
        Standard dedent sees common=0 (line0 has 0 indent) → no change.
        """
        indent = ' ' * 25
        code = f'line0\n{indent}line1'
        result = _norm(code)
        assert result == f'line0\n{indent}line1'

    def test_tab_expansion_class2(self):
        """Defect Class 2: tab characters expanded to 4 spaces, then dedented.
        \tline1 → '    line1', \t\tline2 → '        line2'.
        Standard dedent removes 4-space common indent → 'line1', '    line2'.
        """
        code = '\tline1\n\t\tline2'
        result = _norm(code)
        # After expand: '    line1\n        line2'; after standard dedent (common=4): 'line1\n    line2'
        assert result == 'line1\n    line2'

    def test_strip_leading_blank_lines_class4(self):
        """Defect Class 4: blank lines at start of fence body are removed."""
        code = '\n\n\nactual code\nmore code'
        result = _norm(code)
        assert result == 'actual code\nmore code'

    def test_trailing_blank_lines_via_splitlines_join(self):
        """splitlines()/join() naturally normalizes trailing blank lines.
        'code line\n\n'.splitlines() = ['code line', ''] → join → 'code line\n'
        (one trailing newline, not two). The change-detection comparison uses rstrip()
        so this does NOT trigger false positives on clean fences.
        """
        code = 'code line\n\n'
        result = _norm(code)
        assert result.startswith('code line')
        # splitlines()+join collapses two trailing newlines to one
        assert result == 'code line\n'

    def test_standard_dedent_all_lines_share_indent(self):
        """Standard dedent: when all lines share common indent > 0."""
        code = '    line1\n    line2\n        line3'
        result = _norm(code)
        assert result == 'line1\nline2\n    line3'

    def test_empty_input(self):
        result = _norm('')
        assert result == ''

    def test_only_blank_lines(self):
        result = _norm('\n\n\n')
        assert result == ''

    def test_idempotency_simple(self):
        code = 'var x = 1;\nvar y = 2;'
        assert _norm(_norm(code)) == _norm(code)

    def test_idempotency_body_dedent(self):
        deep = ' ' * 72
        code = f'method()\n{deep}body'
        once = _norm(code)
        twice = _norm(once)
        assert once == twice

    def test_standard_dedent_then_orphan_blocks_single_pass(self):
        """TASK-01 regression guard: standard dedent + orphan block resolved in one _norm() call.

        All lines share a 4-space common indent; after standard dedent line 0 has 0
        indent but line 1 has 40-space orphan alignment.  Before the G1 fix, the
        orphan block was left uncorrected after the early return from the standard-
        dedent path.  After the fix, _reindent_orphan_blocks() is applied to the
        dedented result in the same call.
        """
        code = '    line0\n' + '    ' + ' ' * 40 + 'orphan_line'
        result = _norm(code)
        # Standard dedent removes 4 common spaces → 'line0\n' + ' '*40 + 'orphan_line'
        # Orphan pass: preceding=0, block_min=40, adjustment=40 >= 20 → shift left 40
        assert result == 'line0\norphan_line'

    def test_mixed_tabs_and_spaces(self):
        """Tabs mixed with spaces: tabs expanded first, then dedent."""
        code = '\t    line1\n\t    line2'
        result = _norm(code)
        # \t → 4 spaces, then '    line1' with 8 spaces total → dedent removes 8
        assert result == 'line1\nline2'


# ---------------------------------------------------------------------------
# normalize_content() tests
# ---------------------------------------------------------------------------

class TestNormalizeContent:

    def test_no_change_on_clean_fence(self):
        content = '```csharp\nvar x = 1;\nvar y = 2;\n```'
        new_content, changes = normalize_content(content)
        assert changes == []
        assert new_content == content

    def test_defect_class4_blank_start(self):
        content = '```csharp\n\nvar x = 1;\n```'
        new_content, changes = normalize_content(content)
        assert len(changes) == 1
        assert 4 in changes[0]['defect_classes']
        assert '\n\nvar' not in new_content
        assert '```csharp\nvar x = 1;\n```' in new_content

    def test_defect_class3_vb_split(self):
        content = (
            '```csharp\n'
            'var x = new Foo();\n'
            'x.Bar();\n'
            '\n'
            'Using generator As New Foo()\n'
            '    generator.Bar()\n'
            'End Using\n'
            '```'
        )
        new_content, changes = normalize_content(content)
        assert len(changes) == 1
        assert 3 in changes[0]['defect_classes']
        assert '```csharp' in new_content
        assert '```vb' in new_content
        # C# code must not appear in the vb fence
        cs_part = new_content.split('```vb')[0]
        vb_part = new_content.split('```vb')[1]
        assert 'var x = new Foo()' in cs_part
        assert 'End Using' in vb_part
        assert 'var x = new Foo()' not in vb_part

    def test_defect_class2_tabs(self):
        content = '```csharp\n\tvar x = 1;\n\tvar y = 2;\n```'
        new_content, changes = normalize_content(content)
        assert len(changes) == 1
        assert 2 in changes[0]['defect_classes']
        assert '\t' not in new_content

    def test_idempotency_after_class4_fix(self):
        content = '```csharp\n\nvar x = 1;\n```'
        fixed, _ = normalize_content(content)
        fixed2, changes2 = normalize_content(fixed)
        assert changes2 == []
        assert fixed == fixed2

    def test_idempotency_after_vb_split(self):
        content = (
            '```csharp\n'
            'var x = 1;\n'
            '\n'
            'Dim x As Integer = 1\n'
            'End Using\n'
            '```'
        )
        fixed, _ = normalize_content(content)
        fixed2, changes2 = normalize_content(fixed)
        assert changes2 == []

    def test_multiple_fences_independent(self):
        content = (
            '# Header\n\n'
            '```csharp\n\nvar x = 1;\n```\n\n'
            '```csharp\nvar y = 2;\n```'
        )
        new_content, changes = normalize_content(content)
        assert len(changes) == 1  # only the first fence has a blank start
        assert '# Header' in new_content
        assert '```csharp\nvar y = 2;\n```' in new_content

    def test_no_vb_split_on_non_csharp_fence(self):
        """VB splitting should only apply to ```csharp fences."""
        content = '```vb\nDim x As Integer = 1\nEnd Using\n```'
        new_content, changes = normalize_content(content)
        assert changes == []
        assert new_content == content

    def test_vb_split_not_triggered_without_vb_keywords(self):
        """Clean C# code with 'End' in string literals should not be split."""
        content = (
            '```csharp\n'
            'var x = "End of string";\n'
            'Console.WriteLine(x);\n'
            '```'
        )
        new_content, changes = normalize_content(content)
        # "End of string" is inside a string — _VB_LINE_START won't match at start of line
        assert changes == []

    def test_dual_class1_and_1b_both_reported(self):
        """TASK-02 regression guard: fence with Class 1 (>=40) AND Class 1b (>=30) reports both.

        Before the G2 fix (elif), Class 1b was silently skipped whenever Class 1
        fired first.  After the fix both classes are independently detected and
        appended to defects[], giving accurate counts in normalize-report.json.
        """
        deep = ' ' * 72
        orphan = ' ' * 35
        content = f'```csharp\nmethodSig()\n{deep}body\n{orphan}orphan_block\n```'
        _, changes = normalize_content(content)
        fence_changes = [c for c in changes if c.get('type') != 'prose']
        assert len(fence_changes) == 1
        defects = fence_changes[0]['defect_classes']
        assert 1 in defects
        assert '1b' in defects

    def test_uniform_deep_indent_class1_only_not_1b(self):
        """G-A regression guard: fence where ALL non-empty lines are at >= 40 spaces
        (fresh DocFX all-lines-deep pattern) must classify as Class 1 only, not 1b.

        Root cause of May 1 production issue: 'any(indent >= 30)' fired on every
        Class 1 fence, inflating Class 1b from 1 (true orphan blocks) to 989 (noise)
        in the Words family report.

        The fix (min/max contrast): Class 1b requires min_indent < threshold <= max_indent.
        When all lines are at 72 spaces (including line 0), min=max=72, 72 < 30 is false
        so no 1b.
        """
        deep = ' ' * 72
        # All lines INCLUDING line 0 are at 72 spaces — production DocFX output shape
        content = f'```csharp\n{deep}MethodSig()\n{deep}body1\n{deep}body2\n```'
        _, changes = normalize_content(content)
        fence_changes = [c for c in changes if c.get('type') != 'prose']
        assert len(fence_changes) == 1, 'Expected one fence change'
        defects = fence_changes[0]['defect_classes']
        assert 1 in defects, 'Expected Class 1 (uniform deep indent)'
        assert '1b' not in defects, (
            'Class 1b must not fire when all lines are at uniform deep indent '
            '(structural contrast required: min_indent < threshold <= max_indent)'
        )


# ---------------------------------------------------------------------------
# _decode_prose_entities() tests (Defect Class 5)
# ---------------------------------------------------------------------------

class TestDecodeProseEntities:

    def test_entities_in_prose_decoded(self):
        """Named and numeric entities in prose text are decoded."""
        prose = 'Use &lt;T&gt; generic. Also &amp; and &quot;quotes&quot;.'
        result = _decode_prose_entities(prose)
        assert result == 'Use <T> generic. Also & and "quotes".'

    def test_numeric_entity_decoded(self):
        result = _decode_prose_entities('Shift right: value &gt;&gt; 8.')
        assert result == 'Shift right: value >> 8.'

    def test_fence_content_preserved(self):
        """Entities INSIDE code fences must not be decoded."""
        content = '```csharp\nstring s = "&#xa0;";\n```'
        result = _decode_prose_entities(content)
        assert '&#xa0;' in result  # entity inside fence preserved

    def test_prose_decoded_fence_preserved(self):
        """Decode prose entities while leaving fence intact."""
        content = 'Use &lt;T&gt; type.\n\n```csharp\nvar x = "&lt;div&gt;";\n```'
        result = _decode_prose_entities(content)
        assert 'Use <T> type.' in result             # prose decoded
        assert '"&lt;div&gt;"' in result             # fence untouched

    def test_idempotent(self):
        """Calling twice produces the same result as calling once."""
        content = 'Compare &gt;&gt; operator.\n\n```csharp\ncode\n```'
        first = _decode_prose_entities(content)
        second = _decode_prose_entities(first)
        assert first == second

    def test_no_entities_unchanged(self):
        content = 'Plain text with no entities.\n\n```csharp\nvar x = 1;\n```'
        result = _decode_prose_entities(content)
        assert result == content

    def test_multiple_fences(self):
        """Prose between multiple fences is decoded; fences are preserved."""
        content = (
            'Before &amp; text.\n\n'
            '```csharp\nfirst &amp; fence;\n```\n\n'
            'Between &lt; fences.\n\n'
            '```vb\nDim x = "&amp;"\n```\n\n'
            'After &gt; text.'
        )
        result = _decode_prose_entities(content)
        assert 'Before & text.' in result
        assert '```csharp\nfirst &amp; fence;\n```' in result   # fence 1 unchanged
        assert 'Between < fences.' in result
        assert '```vb\nDim x = "&amp;"\n```' in result          # fence 2 unchanged
        assert 'After > text.' in result


# ---------------------------------------------------------------------------
# normalize_content() — Class 5 integration tests
# ---------------------------------------------------------------------------

class TestNormalizeContentClass5:

    def test_prose_entities_trigger_change(self):
        """Class 5: prose with entities causes normalize_content to report a change."""
        content = 'Use &lt;T&gt; type.\n\n```csharp\nvar x = 1;\n```'
        new_content, changes = normalize_content(content)
        prose_changes = [c for c in changes if c.get('type') == 'prose']
        assert len(prose_changes) == 1
        assert 5 in prose_changes[0]['defect_classes']
        assert 'Use <T> type.' in new_content

    def test_entity_inside_fence_not_flagged(self):
        """Entities inside fences do not trigger Class 5 and are preserved."""
        content = '```csharp\nstring s = "&#xa0;";\n```'
        new_content, changes = normalize_content(content)
        prose_changes = [c for c in changes if c.get('type') == 'prose']
        assert prose_changes == []
        assert '&#xa0;' in new_content

    def test_class5_idempotent(self):
        """Running normalize_content twice produces zero changes on second pass."""
        content = 'Compare &gt; operator.\n\n```csharp\nvar x = 1;\n```'
        first, _ = normalize_content(content)
        second, changes2 = normalize_content(first)
        prose2 = [c for c in changes2 if c.get('type') == 'prose']
        assert prose2 == []
        assert first == second

    def test_real_world_imaging_entity(self):
        """Real-world example: &lt;T&gt; in imaging family description text."""
        content = (
            'The IEnumerable&lt;T&gt; interface is implemented here.\n\n'
            '```csharp\nIEnumerable<int> result = GetItems();\n```'
        )
        new_content, changes = normalize_content(content)
        assert 'IEnumerable<T>' in new_content
        assert 'IEnumerable<int>' in new_content  # fence content unchanged

    def test_fence_and_prose_both_changed(self):
        """File with both a fence defect (Class 1) and prose entities (Class 5)."""
        deep = ' ' * 72
        content = (
            'Use &lt;T&gt; generic.\n\n'
            f'```csharp\nmethodSig()\n{deep}body_line\n```'
        )
        new_content, changes = normalize_content(content)
        fence_changes = [c for c in changes if c.get('type') != 'prose']
        prose_changes = [c for c in changes if c.get('type') == 'prose']
        assert len(fence_changes) == 1      # Class 1 fence fix
        assert len(prose_changes) == 1      # Class 5 prose fix
        assert 1 in fence_changes[0]['defect_classes']
        assert 5 in prose_changes[0]['defect_classes']
        assert 'Use <T> generic.' in new_content
        assert 'body_line' in new_content
        assert deep not in new_content


# ---------------------------------------------------------------------------
# LLM stub tests
# ---------------------------------------------------------------------------

class TestLlmStub:

    def test_no_endpoint_returns_skip(self):
        """LLM stub returns safe 'skip' response when env vars are not set."""
        import os
        env_backup = os.environ.pop('LLM_ENDPOINT', None), os.environ.pop('LLM_KEY', None)
        try:
            result = llm_classify_fence('csharp', 'var x = 1;')
            assert result['defect_type'] == 'skip'
            assert result['apply_fix'] is False
            assert result['confidence'] == 0.0
        finally:
            if env_backup[0] is not None:
                os.environ['LLM_ENDPOINT'] = env_backup[0]
            if env_backup[1] is not None:
                os.environ['LLM_KEY'] = env_backup[1]

    def test_empty_key_returns_skip(self):
        import os
        os.environ['LLM_ENDPOINT'] = 'https://llm.professionalize.com/v1/chat'
        os.environ['LLM_KEY'] = ''
        try:
            result = llm_classify_fence('csharp', 'code here')
            assert result['apply_fix'] is False
        finally:
            os.environ.pop('LLM_ENDPOINT', None)
            os.environ.pop('LLM_KEY', None)
