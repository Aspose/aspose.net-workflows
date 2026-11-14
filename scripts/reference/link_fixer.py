"""Internal-link rewriting for generated reference pages (import-safe, no side effects).

Used by ``postprocessor.py`` (generation time) and ``repair_links.py`` (repair of pages that
were generated before this fix). Kept separate from ``postprocessor.py`` because that script
parses ``sys.argv`` and walks ``workspace/`` at import time and therefore cannot be unit-tested.

Two defects fixed here (TC-SYS-159 reference link investigation):

1. **Anchored links were never rewritten.** DocFX writes inherited-member links as
   ``[Foo.Bar](Aspose.Pdf.Foo.md\\#Aspose\\_Pdf\\_Foo\\_Bar)``. The old STEP 2 regex required the
   link target to end in ``.md)``, so a link carrying an anchor stayed a raw relative link with
   backslashes and Hugo emitted ``.md%5c#...``. Locale copies carry the same link without the
   backslashes (``File.md#Anchor``) because the AST round trip strips them; both forms are handled.

2. **Links to types the DocFX filter did not generate** (for example core ``Aspose.Pdf.Document``
   members referenced from a LowCode page) pointed at pages that do not exist. They are rewritten to
   the corresponding page on reference.aspose.com. This step is opt-in per family
   (``rewrite_dangling``) so other families keep their output until it is enabled for them.

Non-anchored link handling is byte-for-byte what it was before (see ``_rewrite_md_link``).
"""

import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

EXTERNAL_BASE = "https://reference.aspose.com"

# [text](path.md) or [text](path.md\#anchor) or [text](path.md#anchor)
#   group 1: link text, group 2: path ending in .md, group 3: anchor (optional)
# The text may contain backslash-escaped characters (generic types: ``CadParameter<byte\[\]\>``).
# The path group is lazy and cannot contain ')' or '#', so a trailing ``\#`` / ``#`` starts the anchor.
_MD_LINK_RE = re.compile(r"\[((?:\\.|[^\]\\])+)\]\((?!https?://)([^)#]+?\.md)(?:\\?#([^)]*))?\)")


def _unescape(text: str) -> str:
    """Remove the markdown backslash escapes DocFX adds (``\\_`` ``\\#`` ``\\(`` ...)."""
    return re.sub(r"\\(.)", r"\1", text)


def _slug(path: str) -> str:
    """Same slug rule the generator always used: lowercase, drop '.md', strip leading '/'.

    Backslash escapes are removed first: DocFX escapes ``-`` in generic type pages
    (``CadParameter\\-1.md``) and a backslash is never valid in a URL path.
    """
    return _unescape(path).lower().replace(".md", "").lstrip("/")


def _rewrite_md_link(match, family: str) -> str:
    text, path, anchor = match.group(1), match.group(2), match.group(3)
    slug = _slug(path)
    # Preserve the historical behaviour exactly: a target that already starts with the family name
    # is not prefixed again (the old code emitted "/<slug>" in that case).
    base = f"/{slug}" if path.lower().startswith(family) else f"/{family}/{slug}"
    if anchor is None:
        return f"[{text}]({base})"
    # Anchors keep their case: they match the ``<a id="...">`` DocFX emits in the target page.
    return f"[{text}]({base}/#{_unescape(anchor)})"


class TypeIndex:
    """Maps lowercase dotted names to their (namespace, [outer type, nested type...]) from XML ``T:`` entries."""

    def __init__(self, full_names: Iterable[str]):
        names = {n.replace("`", "-") for n in full_names if n and not n.endswith("NamespaceDoc")}
        lower_to_orig = {n.lower(): n for n in names}
        self.types: Dict[str, Tuple[str, List[str]]] = {}
        self.namespaces: Dict[str, str] = {}
        for name in names:
            parts = name.split(".")
            # Walk upwards: while the parent is itself a type, we are looking at a nested type.
            chain = [parts[-1]]
            i = len(parts) - 1
            while i > 1 and ".".join(parts[:i]).lower() in lower_to_orig:
                i -= 1
                chain.insert(0, parts[i])
            namespace = ".".join(parts[:i])
            self.types[name.lower()] = (namespace, chain)
            self.namespaces[namespace.lower()] = namespace

    @classmethod
    def from_xml_text(cls, xml_text: str) -> "TypeIndex":
        return cls(re.findall(r'<member name="T:([^"]+)"', xml_text))

    def external_path(self, slug_lower: str) -> Optional[str]:
        """Path below ``https://reference.aspose.com/<family>/net/`` or None if the slug is unknown."""
        if slug_lower in self.types:
            namespace, chain = self.types[slug_lower]
            return f"{namespace.lower()}/{'.'.join(chain).lower()}/"
        if slug_lower in self.namespaces:
            return f"{slug_lower}/"
        return None


def rewrite_internal_links(
    content: str,
    family: str,
    family_name: str,
    *,
    existing_pages: Optional[Set[str]] = None,
    type_index: Optional[TypeIndex] = None,
    overview_slug: Optional[str] = None,
    repair_extra: bool = False,
    stats: Optional[Dict[str, int]] = None,
) -> str:
    """Rewrite internal links of one generated page.

    ``family``       lowercase family key used in URLs (``pdf``).
    ``family_name``  package family name (``Aspose.PDF``), used for the ``Namespace:`` line.
    ``existing_pages`` lowercase slugs of the pages that exist (without ``.md``); needed by ``repair_extra``.
    ``overview_slug`` lowercase slug of the family overview page (it becomes the family root ``_index.md``).
    ``repair_extra`` opt-in per family. Also (a) sends links to pages that were not generated to the matching
                     reference.aspose.com page, (b) sends links to the overview page to the family root and
                     (c) removes the markdown escapes for '-' and '_' from absolute URLs (``list\\-1``).
    ``stats``        optional counter dict: ``anchored``, ``plain``, ``dangling_rewritten``, ``dangling_unresolved``,
                     ``overview_to_root``, ``external_unescaped``.
    """
    stats = stats if stats is not None else {}

    def bump(key: str) -> None:
        stats[key] = stats.get(key, 0) + 1

    # STEP 1: Fix 'Namespace' links first (unchanged)
    content = re.sub(
        rf"Namespace: \[{re.escape(family_name)}\]\(\s*{re.escape(family_name)}\.md\s*\)",
        f"Namespace: [{family_name}](/{family}/)",
        content,
    )

    # STEP 2: internal .md links, with or without an anchor
    def step2(m):
        bump("anchored" if m.group(3) is not None else "plain")
        return _rewrite_md_link(m, family)

    content = _MD_LINK_RE.sub(step2, content)

    if repair_extra:
        # STEP 3: links to generated-page URLs that have no page
        if existing_pages is not None:
            link_re = re.compile(rf"\]\(/{re.escape(family)}/([^)#/\s]+)/?(?:#[^)]*)?\)")

            def step3(m):
                slug = m.group(1).lower()
                if slug in existing_pages:
                    return m.group(0)
                if overview_slug and slug == overview_slug:
                    bump("overview_to_root")
                    return f"](/{family}/)"
                ext = type_index.external_path(slug) if type_index is not None else None
                if ext is None:
                    bump("dangling_unresolved")
                    return m.group(0)
                bump("dangling_rewritten")
                return f"]({EXTERNAL_BASE}/{family}/net/{ext})"

            content = link_re.sub(step3, content)

        # STEP 4: absolute URLs carrying markdown escapes for '-' or '_' (DocFX writes ``list\-1``);
        # Hugo renders the backslash as %5c. Only targets whose every backslash precedes '-' or '_' are touched.
        def step4(m):
            target = m.group(1)
            if "\\" in target and not re.search(r"\\[^-_]", target):
                bump("external_unescaped")
                return "](" + re.sub(r"\\([-_])", r"\1", target) + ")"
            return m.group(0)

        content = re.sub(r"\]\((https?://[^)\s]*)\)", step4, content)

    return content
