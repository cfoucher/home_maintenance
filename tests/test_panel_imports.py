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


# ---------------------------------------------------------------------------
# v1.7.2 regression checks — version sync and Add Task dialog
# ---------------------------------------------------------------------------

def test_panel_const_ts_deleted():
    """panel/src/const.ts must not exist (v1.7.2 removed it).

    The version constant was moved to the backend as the single
    source of truth.
    """
    const_ts = PANEL_SRC / "const.ts"
    assert not const_ts.exists(), (
        f"{const_ts} should have been deleted. "
        f"It contained a stale VERSION constant that was never synced. "
        f"The backend's const.py VERSION is now the single source of truth."
    )


def test_main_ts_no_const_import():
    """panel/src/main.ts must NOT import from './const'.

    The file should get its version from this.config.version
    (fetched from the getConfig websocket handler).
    """
    source = _read_file("main.ts")
    # Check for imports from "./const" (no quotes — both ' and " are valid TS)
    matches = re.findall(r"from\s+[\"']\.\/const[\"']", source)
    assert not matches, (
        f"main.ts still imports from './const': {matches}. "
        f"Remove the import and use this.config?.version instead."
    )


def test_main_ts_uses_config_version():
    """panel/src/main.ts must reference config.version for the version display.

    This is the replacement for the deleted VERSION constant.
    """
    source = _read_file("main.ts")
    # Look for the version template: v${...config?.version...} or v${...config["version"]...}
    has_config_version = bool(re.search(r"config\?\.\s*version|config\[\s*[\"']version[\"']\s*\]", source))
    assert has_config_version, (
        "main.ts does not appear to use this.config?.version for version display. "
        "The version should come from the backend's getConfig response."
    )


def test_main_ts_has_show_add_dialog():
    """The _showAddDialog state flag must be present for the modal Add Task dialog."""
    source = _read_file("main.ts")
    count = source.count("_showAddDialog")
    assert count >= 2, (
        f"_showAddDialog appears {count} time(s) — expected at least 2 "
        f"(state declaration + usage in render or click handler)."
    )


def test_main_ts_has_add_dialog_cancel_button():
    """The Add Task dialog must have a Cancel button (or a localize() key referencing cancel)."""
    source = _read_file("main.ts")
    # Look for the cancel button (either hardcoded or via localize key)
    has_cancel = (
        "panel.dialog.edit_task.actions.cancel" in source
        or "Cancel" in source
    )
    assert has_cancel, (
        "Add Task dialog missing a Cancel button or its localize key."
    )


def test_main_ts_has_empty_state():
    """renderTasks() must have an empty-state section with a title."""
    source = _read_file("main.ts")
    has_empty = (
        "panel.current.empty.title" in source
        or "No tasks yet" in source
    )
    assert has_empty, (
        "No empty state found in main.ts. Expected localize key 'panel.current.empty.title' "
        "or the text 'No tasks yet'."
    )


def test_hardcoded_trigger_strings_removed():
    """Hardcoded 'Time-based'/'Count-based'/'Runtime-based' must be gone from main.ts.

    v1.7.1 noted these as a follow-up; v1.7.2 routes them through localize().
    """
    source = _read_file("main.ts")
    for bad_string in ["Time-based", "Count-based", "Runtime-based"]:
        assert bad_string not in source, (
            f"Hardcoded '{bad_string}' found in main.ts. "
            f"It should use localize('panel.triggers.*') instead."
        )


def test_localization_keys_match():
    """en.json and de.json must have the same set of localize keys.

    Per the #99 lesson: if we add strings to en.json, we must also
    add them to de.json (even if the translation is rough or empty).
    """
    import json

    en_path = REPO_ROOT / "custom_components" / "home_maintenance" / "panel" / "localize" / "languages" / "en.json"
    de_path = REPO_ROOT / "custom_components" / "home_maintenance" / "panel" / "localize" / "languages" / "de.json"

    def _collect_keys(obj, prefix="") -> set[str]:
        keys = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                full = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    keys |= _collect_keys(v, full)
                else:
                    keys.add(full)
        return keys

    with open(en_path, encoding="utf-8") as f:
        en_data = json.load(f)
    with open(de_path, encoding="utf-8") as f:
        de_data = json.load(f)

    en_keys = _collect_keys(en_data)
    de_keys = _collect_keys(de_data)

    # Don't flag the trivial "common.loading" / "common.none" diff if both exist
    missing_in_de = en_keys - de_keys
    missing_in_en = de_keys - en_keys

    # Common localize prefix checks
    common_prefix = "panel."
    relevant_en = {k for k in missing_in_de if k.startswith(common_prefix)}
    relevant_de = {k for k in missing_in_en if k.startswith(common_prefix)}

    assert not relevant_en, (
        f"de.json is missing these keys that en.json has: {sorted(relevant_en)}"
    )
    assert not relevant_de, (
        f"en.json is missing these keys that de.json has: {sorted(relevant_de)}"
    )


# ---------------------------------------------------------------------------
# v1.7.3 layout regression checks — dialog centering and header gap
# ---------------------------------------------------------------------------

def test_dialog_centering_css_present():
    """styles.ts must have CSS that centers the ha-dialog on the host panel.

    At least one of the following must be present:
      - transform: translateX on ha-dialog (v1.7.5 approach — shift to card center)
      - position: absolute on ha-dialog (v1.7.4 approach — constrains to :host)
      - --mdc-dialog-* custom property related to sizing
    """
    styles_path = REPO_ROOT / "custom_components" / "home_maintenance" / "panel" / "src" / "styles.ts"
    source = styles_path.read_text(encoding="utf-8")

    has_transform = bool(re.search(
        r"ha-dialog\s*\{[^}]*transform\s*:\s*translateX",
        source, re.DOTALL,
    ))
    has_mdc_sizing = bool(re.search(r"--mdc-dialog-(min|max|content)-width", source))

    assert has_transform or has_mdc_sizing, (
        "No dialog centering CSS found in styles.ts. "
        "Expected at least one of: transform: translateX on ha-dialog, "
        "or --mdc-dialog-* sizing."
    )


def test_dialog_centering_uses_transform():
    """styles.ts must shift the ha-dialog with a CSS transform to align it
    on the main content area (centered on the Current Tasks card).

    Since MWC's dialog uses position: fixed internally (not reachable
    from outside its shadow DOM), the v1.7.5 approach uses
    transform: translateX(140px) to shift the viewport-centered dialog
    rightward to match the card's center.

    Supporting requirements:
      - :host must have display: block to take full parent width
      - .card-current must have margin: 0 so it spans full host width
    """
    styles_path = REPO_ROOT / "custom_components" / "home_maintenance" / "panel" / "src" / "styles.ts"
    source = styles_path.read_text(encoding="utf-8")

    # Check 1: transform: translateX on ha-dialog
    has_transform = bool(re.search(
        r"ha-dialog\s*\{[^}]*transform\s*:\s*translateX",
        source, re.DOTALL,
    ))

    # Check 2: :host has display: block
    has_host_block = bool(re.search(
        r":host\s*\{[^}]*display\s*:\s*block",
        source, re.DOTALL,
    ))

    # Check 3: .card-current has margin: 0
    has_card_margin_zero = bool(re.search(
        r"\.card-current\s*\{[^}]*margin\s*:\s*0",
        source, re.DOTALL,
    ))

    assert has_transform, (
        "ha-dialog missing transform: translateX. "
        "Expected ha-dialog { transform: translateX(140px); } "
        "to shift the viewport-centered dialog onto the card."
    )
    assert has_host_block, (
        ":host must have display: block to take the full parent width. "
        "Without it, the host shrinks to content width and the card "
        "doesn't span the full main content area."
    )
    assert has_card_margin_zero, (
        ".card-current must have margin: 0 to override the global "
        "ha-card { margin: 5px } and span full host width."
    )


def test_header_card_gap_css_present():
    """styles.ts must have CSS that creates >= 24px gap between the
    toolbar header and the Current Tasks card.

    At least one of these must be present with a value >= 24px:
      - .view with padding-top
      - .card-current with margin-top
      - :host > .view with padding-top (if in shadow DOM scoping)
    """
    styles_path = REPO_ROOT / "custom_components" / "home_maintenance" / "panel" / "src" / "styles.ts"
    source = styles_path.read_text(encoding="utf-8")

    # Search for padding-top on .view
    view_padding_matches = re.findall(
        r"\.view\s*\{[^}]*padding-top\s*:\s*(\d+)px",
        source,
        re.DOTALL,
    )
    # Search for margin-top on .card-current
    card_margin_matches = re.findall(
        r"\.card-current\s*\{[^}]*margin-top\s*:\s*(\d+)px",
        source,
        re.DOTALL,
    )

    for val_str in view_padding_matches + card_margin_matches:
        if int(val_str) >= 24:
            return  # Found a sufficient gap

    assert False, (
        "No header-card gap of >= 24px found in styles.ts. "
        "Expected .view { padding-top: Npx } or .card-current { margin-top: Npx } "
        f"with N >= 24. Found values: padding-top=[{', '.join(view_padding_matches)}], "
        f"margin-top=[{', '.join(card_margin_matches)}]"
    )


# ---------------------------------------------------------------------------
# v1.7.6 regression checks — version display visibility
# ---------------------------------------------------------------------------

def test_version_css_inherits_theme_color():
    """.version CSS must use `color: inherit` so the version text adapts to
    the HA theme (light/dark). A hardcoded color (e.g., white) would be
    invisible on light themes.

    Regression for v1.7.6: the rgba(..., 255, 255, 255, 0.9) fallback made the
    version invisible in light mode because the header background is also light.
    """
    styles_path = REPO_ROOT / "custom_components" / "home_maintenance" / "panel" / "src" / "styles.ts"
    source = styles_path.read_text(encoding="utf-8")

    # Find the .version CSS block
    match = re.search(r"\.version\s*\{([^}]+)\}", source, re.DOTALL)
    assert match, "No .version CSS block found in styles.ts"
    version_block = match.group(1)

    # The .version block must use color: inherit (not a hardcoded color)
    assert "color: inherit" in version_block, (
        f".version CSS must use 'color: inherit' for theme responsiveness. "
        f"Found block:\n{version_block}\n\n"
        f"A hardcoded color (rgba with white fallback, white, etc.) is invisible "
        f"on light themes because HA's light-mode header background is also light."
    )

    # Negative checks: should NOT have hardcoded white
    assert "255, 255, 255" not in version_block, (
        f".version CSS still has a hardcoded white color. Use 'color: inherit' instead."
    )
    assert "--rgb-text-primary-color" not in version_block, (
        f".version CSS still uses --rgb-text-primary-color which doesn't adapt to HA themes. Use 'color: inherit'."
    )

    # Also verify white-space: nowrap is present to prevent wrapping
    assert "white-space: nowrap" in version_block, (
        ".version rule is missing white-space: nowrap"
    )
