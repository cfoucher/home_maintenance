## v1.6.0 — Critical fixes for Home Assistant 2026.3 compatibility

This is the first release of `cfoucher/home_maintenance`, a fork of [TJPoorman/home_maintenance](https://github.com/TJPoorman/home_maintenance) to keep the integration working as upstream maintainership has lapsed.

### What's in this release

**Critical fixes**

- **HA 2026.3 compatibility** ([#122](https://github.com/TJPoorman/home_maintenance/pull/122)) — replaces the removed `ha-md-menu` with `ha-dropdown`, extracts the menu to a new `hm-task-menu` component, and replaces `mwc-button` with `ha-button`. Fixes the broken Edit/Delete actions menu and the unstyled "Add Task" button introduced in HA 2026.3.
- **German translation import fix** ([#99](https://github.com/TJPoorman/home_maintenance/pull/99)) — `localize.ts` was only importing `en.json`, making the existing `de.json` dead code. Now imports both.

**Pre-flight improvements**

- `VERSION` constant bumped to `1.6.0`
- Refactored the `_calculate_next_due` calculation out of `binary_sensor.py` into a pure module-level `calculate_next_due` function in `schedule.py` — no HA-import dependency for the core scheduling logic, eliminating the silent Python ↔ TypeScript duplication of the same formula
- Added a pytest test suite (7 tests, all passing) using a `conftest.py` HA-stub for environment-agnostic testability
- Added a panel build step to the release workflow so `panel/dist/main.js` is always built from source at release time, no longer relying on the stale committed pre-built artifact

**Dependency bumps**

- `softprops/action-gh-release` v1 → v2 ([#17](https://github.com/TJPoorman/home_maintenance/pull/17))
- `actions/checkout` v4 → v6 ([#84](https://github.com/TJPoorman/home_maintenance/pull/84))
- `actions/setup-python` v5.6.0 → v6.2.0 ([#108](https://github.com/TJPoorman/home_maintenance/pull/108))
- `home-assistant/actions` (hassfest) bump ([#112](https://github.com/TJPoorman/home_maintenance/pull/112))
- `colorlog` 6.9.0 → 6.10.1 ([#74](https://github.com/TJPoorman/home_maintenance/pull/74))
- `ruff` 0.11.13 → 0.15.0 ([#113](https://github.com/TJPoorman/home_maintenance/pull/113)) + a follow-up commit to fix `I001` and `FURB110` surfaced by the new ruff version

### Install via HACS

1. In Home Assistant, open **HACS → Settings → Custom repositories**
2. Add `https://github.com/cfoucher/home_maintenance` as category **Integration**
3. The "Home Maintenance" integration appears in HACS — install v1.6.0
4. Restart Home Assistant
5. The integration configuration should migrate; if not, re-add from **Settings → Devices & services**

### What's next

- **v1.7.0** — title edit field ([#100](https://github.com/TJPoorman/home_maintenance/pull/100)), description field ([#101](https://github.com/TJPoorman/home_maintenance/pull/101)), area support ([#117](https://github.com/TJPoorman/home_maintenance/pull/117)), and the count/runtime task triggers (once the [#115](https://github.com/TJPoorman/home_maintenance/pull/115) / [#116](https://github.com/TJPoorman/home_maintenance/pull/116) duplicate situation is resolved upstream)
- **v1.8.0** — French ([#104](https://github.com/TJPoorman/home_maintenance/pull/104)) and Ukrainian ([#106](https://github.com/TJPoorman/home_maintenance/pull/106)) translations, and a new Dutch translation to close [#59](https://github.com/TJPoorman/home_maintenance/issues/59)
