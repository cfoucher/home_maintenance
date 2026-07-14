"""Regression tests for TypeScript panel import hygiene.

These tests statically analyse the TypeScript source files in
panel/src/ to catch a class of bugs that esbuild's bundler does
not catch at build time: missing imports from node_modules (e.g.
@mdi/js icons) that cause ReferenceError crashes in the browser.

The motivating bug (v1.7.0, reported 2026-07-13):
  panel/src/main.ts referenced mdiPencil and mdiDelete in template
  literals but only imported mdiCheckCircleOutline from @mdi/js.
  esbuild bundled successfully (it does not track template-literal
  references), but the panel crashed on load with:
    ReferenceError: mdiPencil is not defined
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PANEL_SRC = REPO_ROOT / "custom_components" / "home_maintenance" / "panel" / "src"


def _read_file(rel_path: str) -> str:
    """Read a panel source file returning its text."""
    path = PANEL_SRC / rel_path
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# mdi icon checks (main.ts)
# ---------------------------------------------------------------------------

def _parse_mdi_imports(source: str) -> set[str]:
    """Extract mdi<Name> imported from '@mdi/js'.

    Handles the multi-line import block:
        import {
            mdiFoo,
            mdiBar,
        } from "@mdi/js";
    """
    # Match everything between 'import {' and '} from "@mdi/js"'
    m = re.search(
        r"import\s*\{([^}]+)\}\s*from\s*[\"']@mdi/js[\"']",
        source,
        re.DOTALL,
    )
    if not m:
        return set()
    body = m.group(1)
    return {name.strip() for name in re.findall(r"mdi[A-Z]\w+", body)}


def _parse_mdi_references(source: str) -> set[str]:
    """Extract all mdi<Name> references outside the import block."""
    # Remove the import block so we don't count declarations as references
    without_imports = re.sub(
        r"import\s*\{[^}]+\}\s*from\s*[\"']@mdi/js[\"']",
        "",
        source,
        flags=re.DOTALL,
    )
    return set(re.findall(r"mdi[A-Z]\w+", without_imports))


def test_all_mdi_references_are_imported():
    """Regression test for v1.7.0 ReferenceError: mdiPencil is not defined.

    Every mdi<Name> used outside the @mdi/js import block must have a
    corresponding import.  If this test fails, add the missing icon to
    the import block in panel/src/main.ts.
    """
    source = _read_file("main.ts")
    imports = _parse_mdi_imports(source)
    references = _parse_mdi_references(source)

    missing = references - imports
    assert not missing, (
        f"\nMissing @mdi/js imports for: {sorted(missing)}"
        f"\nCurrently imported: {sorted(imports)}"
        f"\nFix: add the missing names to the import block in panel/src/main.ts"
    )


def test_no_unused_mdi_imports():
    """Fail if any @mdi/js import has zero references in the file.

    Dead imports accumulate over time and make it harder to spot
    missing ones.  Remove unused entries from the import block.
    """
    source = _read_file("main.ts")
    imports = _parse_mdi_imports(source)
    references = _parse_mdi_references(source)

    unused = imports - references
    assert not unused, (
        f"\nUnused @mdi/js imports: {sorted(unused)}"
        f"\nRemove them from the import block in panel/src/main.ts"
    )


# ---------------------------------------------------------------------------
# Broader import check across all panel .ts files
# ---------------------------------------------------------------------------

def test_other_components_import_their_dependencies():
    """Check all .ts files under panel/src/ for missing mdi references.

    This extends the mdi-import check beyond main.ts to any other
    file that might reference mdi icons.

    Coverage note: this test only checks mdi[A-Z]\\w+ patterns (the
    immediate bug class).  It intentionally does NOT verify:
      - imports from 'lit', '@material/mwc-*', custom-card-helpers
      - relative imports between project files
      - locally-registered custom elements
    Those would require a full TypeScript AST analysis.
    """
    ts_files = sorted(PANEL_SRC.rglob("*.ts"))

    for ts_file in ts_files:
        rel = ts_file.relative_to(PANEL_SRC)
        source = ts_file.read_text(encoding="utf-8")

        imports = _parse_mdi_imports(source)
        references = _parse_mdi_references(source)

        missing = references - imports
        assert not missing, (
            f"\n{rel}: missing @mdi/js imports for: {sorted(missing)}"
            f"\nCurrently imported: {sorted(imports)}"
        )

        unused = imports - references
        assert not unused, (
            f"\n{rel}: unused @mdi/js imports: {sorted(unused)}"
        )
