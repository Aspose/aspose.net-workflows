"""
Unit tests for normalize_snippets.py

Run with: python -m pytest tests/test_normalize_snippets.py -v
"""
import sys
import os

# Make the scripts directory importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'reference'))

from normalize_snippets import _norm, normalize_content, _BODY_DEDENT_THRESHOLD


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
        """Body-only dedent should NOT trigger when indent is below threshold."""
        indent = ' ' * (_BODY_DEDENT_THRESHOLD - 1)
        code = f'line0\n{indent}line1'
        result = _norm(code)
        # Standard dedent sees common=0 (line0 has 0), body indent < threshold → no change
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
