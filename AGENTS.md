# Agent Instructions — `cfoucher/home_maintenance` (fork)

This is a fork of [`TJPoorman/home_maintenance`](https://github.com/TJPoorman/home_maintenance) (82 stars, original maintainer unresponsive as of 2026‑07). The fork lives at **https://github.com/cfoucher/home_maintenance**. Released versions are installed on the user's Home Assistant via HACS as a **custom integration** (not a Supervisor add‑on).

This file is the entry point for any agent (or human) picking up work on the fork. Read it before doing anything.

---

## 1. Project identity

| | |
|---|---|
| **Type** | HACS custom integration (Python backend + TypeScript LitElement panel) |
| **Domain** | `home_maintenance` |
| **Current shipped version** | v1.7.0 |
| **HACS install path on HA host** | `custom_components/home_maintenance/` |
| **Install method on user's HA** | HACS custom repository pointing to this fork |
| **Storage file on HA** | `.storage/home_maintenance.storage` (preserved across upgrades) |
| **Test runtime** | Python 3.14.6 on the user's HA; test suite targets Python 3.13+ |
| **HA compatibility** | ≥ 2026.3.2 (set in `hacs.json`) |

The original project on `TJPoorman/home_maintenance` is abandoned. 19 open PRs and 12 open issues (as of last recon 2026‑07‑12). Cherry‑picks from upstream are the primary source of new code; new features are also added on top.

---

## 2. Stack

**Backend (Python):**
- `attrs` for the `HomeMaintenanceTask` dataclass (NOT `pydantic`, NOT `dataclasses`)
- `homeassistant` core imports at module top → tests need `tests/conftest.py` HA stub
- `voluptuous` for service / config schemas
- `dateutil.relativedelta` for month arithmetic in `schedule.py`
- `colorlog` for logging (already a dep — leave it)

**Frontend (TypeScript):**
- LitElement 3.3.0 (HA's own web component framework)
- esbuild 0.25.x for bundling (NO webpack, NO vite, NO rollup)
- `custom-card-helpers`, `@material/mwc-select`, `@material/mwc-list`, `@mdi/js`, `@mdi/svg` (listed in `panel/package.json` dependencies)
- `intl-messageformat` for i18n
- Build output: `panel/dist/main.js` (ESM, minified, ES2020 target)

**Lint / format:**
- `ruff` (config in `.ruff.toml`, all rules minus 4 formatter-incompatible ones)
- `hassfest` (validates manifest, config_flow, services — runs in CI via `home-assistant/actions`)
- `hacs` validator (runs in CI)

**Tests:**
- `pytest` + `freezegun` (added in v1.6.0 pre‑flight — they were not present upstream)
- `tests/conftest.py` stubs the entire `homeassistant.*` module tree using `types.ModuleType` + `MagicMock` so tests can run without a HA install

---

## 3. Repo structure (key paths only)

```
home_maintenance/
├── .github/workflows/
│   ├── lint.yml          # ruff check + format on push/PR to main
│   ├── release.yml       # release:published | push:tags v* | workflow_dispatch → zip + upload
│   └── validate.yml      # hassfest + HACS validator daily/on push (disabled on fork by default)
├── .gitignore
│   └── ! custom_components/home_maintenance/panel/package-lock.json   # MUST stay tracked
├── custom_components/home_maintenance/
│   ├── __init__.py              # setup, services, state-change listeners for count/runtime triggers
│   ├── binary_sensor.py         # entity + _update_state dispatches to time / count / runtime branches
│   ├── config_flow.py           # single-instance config + options
│   ├── const.py                 # VERSION, DOMAIN, service schemas, PANEL_*
│   ├── manifest.json            # version is "v0.0.0" — patched at release time
│   ├── panel.py                 # async_register_panel / async_unregister_panel
│   ├── schedule.py              # PURE functions (no HA imports) — see §6
│   ├── services.yaml            # service schemas (reset_last_performed, increment_count, reset_count)
│   ├── store.py                 # HomeMaintenanceTask (attrs) + TaskStore
│   ├── translations/{de,en}.json
│   ├── websocket.py             # add / update / complete / remove / increment_count / reset_count / get
│   └── panel/
│       ├── dist/main.js                          # committed, minified bundle — shipped in zip
│       ├── localize/
│       │   ├── languages/{de,en}.json
│       │   └── localize.ts                       # imports de + en; was only en before #99
│       ├── package.json                          # "build": "esbuild src/main.ts --bundle --outfile=dist/main.js --format=esm --target=es2020 --minify"
│       ├── package-lock.json                     # MUST be tracked (commit if you regenerate)
│       ├── src/{main.ts,types.ts,styles.ts,helpers.ts,const.ts,data/websockets.ts,components/hm-task-menu.ts}
│       └── tsconfig.json
├── config/                       # minimal HA config for devcontainer
├── hacs.json                     # zip_release: true, filename: home_maintenance.zip, hide_default_branch: true
├── requirements.txt              # colorlog, homeassistant, pip, ruff (no pytest/freezegun — those are dev)
├── scripts/{develop,lint,setup}
├── tests/                        # ADDED in v1.6.0 — didn't exist upstream
│   ├── __init__.py
│   ├── conftest.py               # HA module-tree stub
│   └── test_schedule.py          # 21 tests: 7 time-based + 6 count + 8 runtime
└── RELEASE_NOTES_v*.md           # human-readable release notes (kept per release)
```

**The two dirs that are easy to miss but matter:**
- `tests/` — created by us. If a future cherry-pick from upstream adds tests, they will land in this dir alongside ours.
- `panel/src/components/hm-task-menu.ts` — created by PR #122. The actions menu (Edit / Delete / Complete) was extracted here from `main.ts` because `ha-md-menu` was removed in HA 2026.3.

---

## 4. Build & test pipeline

### Local test
```bash
python -m pytest tests/ -v
```
- 21 tests must all pass
- `tests/conftest.py` is what makes this possible — it stubs the entire `homeassistant.*` tree
- Tests that NEED a live HA (event listener behavior, `device_registry` integration, `entity_registry` async) are **not** written — skip them

### Local lint
```bash
python -m ruff check custom_components/home_maintenance/
python -m ruff format --check custom_components/home_maintenance/
```
- Both must be clean before commit
- `ruff format custom_components/home_maintenance/` to autofix

### Local panel build
```bash
cd custom_components/home_maintenance/panel
npm ci
npm run build
cd ../../../../..
git add custom_components/home_maintenance/panel/dist/main.js
git commit -m "vX.Y.Z: rebuild panel"
```
- `panel/dist/main.js` is shipped — must be rebuilt after any TypeScript change
- `package-lock.json` MUST be tracked (see gitignore override); commit it if it changes
- `node_modules/` is gitignored — never commit it
- Output: 80–90 kB minified bundle

### Pre-commit checklist (in this order)
1. `pytest tests/ -v` — all green
2. `ruff check` + `ruff format --check` — clean
3. `npm run build` in panel/ — committed
4. `git status` — clean
5. `git log --oneline -10` — sensible commit history

---

## 5. Release pipeline (CI)

`.github/workflows/release.yml` runs on three triggers:
- `release: types: [published]`
- `push: tags: ['v*']` ← **what we use**
- `workflow_dispatch` (with optional `version` input)

Required workflow header (forks default `contents: read` — would break the upload):
```yaml
permissions:
  contents: write
```

Steps in order:
1. `actions/checkout@v6`
2. `Get version` — extracts from `GITHUB_REF` (push:tags) or `inputs.version` (dispatch). Output is the full `vX.Y.Z` string.
3. `actions/setup-node@v4` with `node-version: '20'`
4. `Build panel` — `npm ci && npm run build` in `custom_components/home_maintenance/panel/`
5. `Patch manifest and zip` — `sed -i 's/v0.0.0/${{ steps.version.outputs.version }}/' .../manifest.json` then `zip home_maintenance.zip ./* translations/* panel/dist/* -x '.*'`
6. `Upload ZIP to Release` — `softprops/action-gh-release@v2` with `files: home_maintenance.zip` and `tag_name: ${{ steps.version.outputs.version }}`. **Creates the release if it doesn't exist.**

### Why this matters
- `home_maintenance.zip` is the HACS-installable artifact
- HACS only finds it because `hacs.json` has `zip_release: true` and `filename: "home_maintenance.zip"` — DO NOT remove these (PR #115 tried to and would have broken installs)
- The `sed` step is what makes `manifest.json` match the tag — `const.py` `VERSION` is for runtime display only and is the source of truth for the in‑HA version

### Tagging
```bash
git tag -a v1.7.0 -m "v1.7.0 — <one-line summary>"
git push origin v1.7.0
```
Tag push triggers the workflow. The workflow creates the GitHub release (with the zip) if it doesn't exist.

---

## 6. `schedule.py` — the pure-functions module

`custom_components/home_maintenance/schedule.py` was created in v1.6.0 pre‑flight by extracting the date math from `binary_sensor.py`. It is the **only file in the integration that has zero HA imports** — which is what makes testing possible.

**Contains:**
- `calculate_next_due(last_performed, interval_value, interval_type) -> datetime` — the time-based next-due calculation
- `is_count_due(current_count: int, threshold: int) -> bool` — count trigger (added v1.7.0 from #115)
- `check_runtime_due(current_value, baseline, threshold) -> tuple[float, bool]` — runtime trigger; returns `(new_baseline, is_due)`. If `current_value < baseline`, treats as external reset, returns `(current_value, False)`

**Rules:**
- Any new trigger math that can be expressed as a pure function → add to `schedule.py`
- Any new trigger math that genuinely needs HA state → keep in `binary_sensor.py` (or wherever) and DO NOT add to `schedule.py`
- Test every function in `schedule.py` with a pytest case in `tests/test_schedule.py`

---

## 7. HACS deployment (the agentic loop)

The "fully agentic deploy from code to running on the user's HA" loop is:

```
1. Make code changes on dev
2. git push origin dev
3. git tag -a vX.Y.Z -m "..." && git push origin vX.Y.Z
4. (CI runs release.yml — see §5 — uploads zip to the release)
5. ha_manage_hacs(action="download", repository_id="cfoucher/home_maintenance", version="vX.Y.Z")
6. ha_restart(confirm=true)   # will TIMEOUT, that's expected
7. Wait ~60s, then verify via ha_get_state / ha_search
```

**Zero user clicks.** This loop is proven through v1.6.0 and v1.7.0.

### ha-mcp gotchas (from the actual deploys)
- `ha_restart(confirm=true)` returns a **timeout error** — that's the restart in progress, not a failure. Wait 60–90s, then poll `http://192.168.1.70:8123/api/` (returns 401 Unauthorized when up).
- ha-mcp's `base_url: http://127.0.0.1:8123` is INSIDE the HA container. From the Windows host, the user-facing URL is `http://192.168.1.70:8123` (whatever the user's `enp1s0` LAN address is).
- `ha_get_overview` occasionally returns `"fetch failed"` transiently. Retry once.
- HACS shows BOTH the original `TJPoorman/home_maintenance` AND the fork as "installed" after the fork is installed. This is because both repos claim the same `domain: home_maintenance` and the on-disk files are the fork's. Don't try to "remove" the TJPoorman entry — that would delete the integration's files.

---

## 8. Git conventions

**Remotes:**
- `origin` = `cfoucher/home_maintenance` (the fork — this is where you push)
- `upstream` = `TJPoorman/home_maintenance` (do NOT push, only fetch for re-syncing)

**Branches:**
- `main` — tracks upstream; left as a clean fork point. **Do not commit to `main` directly.**
- `dev` — working branch. All cherry-picks, features, and the v1.X.Y tag go here.

**Commit messages:** `vX.Y.Z: <description>` for fork-specific changes. `<PR title> (#<num>)` for cherry-picks from upstream.

**Tags:** `vX.Y.Z` (semver, lowercase v). Annotated tags are preferred (`git tag -a vX.Y.Z -m "..."`).

**Squash-merge policy:** every cherry-pick from upstream is a single commit on dev. Don't preserve upstream's per-commit history — that would bring in 5+ commits per PR and clutter the fork's history.

---

## 9. Conflict resolution rules (when cherry-picking from upstream)

These are hard-won rules from v1.6.0 and v1.7.0. Any cherry-pick from upstream MUST follow them.

| File / field | Rule |
|---|---|
| `custom_components/home_maintenance/const.py` `VERSION` | Keep **our** value until bumped explicitly in a separate commit. If a PR changes it, restore ours. |
| `custom_components/home_maintenance/manifest.json` `version` | Always `v0.0.0` (patched at release time). Don't touch. |
| `.github/workflows/release.yml` | Keep our version (with build step + tag-push trigger + `contents: write`). If a PR touches it, restore. |
| `.gitignore` | Keep the `!custom_components/home_maintenance/panel/package-lock.json` override. If a PR adds new lines, keep ours. |
| `hacs.json` | **ALWAYS** keep `zip_release: true`, `filename: "home_maintenance.zip"`, `hide_default_branch: true`. PR #115 attempted to remove these — would have broken HACS installs. Revert any changes to these keys. |
| Python files (`__init__.py`, `store.py`, `binary_sensor.py`, etc.) | Take the PR's version unless we have specific pre‑flight additions to preserve. Specifically: `schedule.py` and its `calculate_next_due` must remain (and new trigger logic can optionally use it). |
| TypeScript files | Take the PR's version. |
| `panel/dist/main.js` | Take the PR's version (will be stale by release time; CI rebuilds). |
| Translation files (`translations/*.json`, `panel/localize/languages/*.json`) | Take the PR's version if it adds new strings. |

**If a conflict is unresolvable per these rules:** STOP the cherry-pick. Report the file paths, conflict markers, and best guess. Do not force-resolve.

**NEVER:**
- `--force` push
- Modify `main` directly
- Push to `upstream`
- Cherry-pick outside the agreed list

---

## 10. Known landmines / gotchas (in priority order)

1. **`hacs.json` landmine** — the `zip_release: true` + `filename: "home_maintenance.zip"` + `hide_default_branch: true` triplet is what makes HACS find the zip. If any PR removes them, **revert**. (PR #115 / #116 does this. Both are byte-identical and were opened by the same author 47 minutes apart — likely a copy-paste mistake.)
2. **Fork default `contents: read`** — the release workflow's `softprops/action-gh-release@v2` upload step needs `contents: write`. The `permissions:` block at the top of `release.yml` is mandatory. Without it, the workflow runs the build but fails silently at the upload.
3. **`package-lock.json` was gitignored** — `npm ci` (used in CI) refuses to run without it. The `!` override in `.gitignore` is non-obvious. If you regenerate the lockfile, commit it.
4. **Hardcoded English strings from #115** — `panel/src/main.ts` contains literals like `"Time-based"`, `"Count-based"`, `"Runtime-based"` that bypass `localize()`. Documented as a v1.7.1 follow-up. (For new features, **always** go through `localize()` and add the strings to both `panel/localize/languages/en.json` and `translations/en.json`.)
5. **Two independent implementations of `next_due` math** — the Python one in `schedule.py:calculate_next_due` and the TypeScript one in `panel/src/main.ts` `_rows` getter. Risk of divergence (especially around month-end edge cases). Consider consolidating: have the Python entity expose `next_due` as an attribute and have the frontend use that instead of recomputing. (Not started.)
6. **PR #115/#116 are duplicates** — same head commit `2c37e3ed`, byte-identical diffs (SHA-256 `D32A2324...`). The PR bodies describe only one aspect (count vs runtime) but the commit contains both. We can't close #116 upstream (we don't have write access to TJPoorman/*), but a duplicate-of comment is no longer posted (per the global AGENTS.md "no comment as user" rule).
7. **HACS shows both repos as "installed"** — cosmetic but confusing. Don't try to fix by removing the TJPoorman entry; that would delete the integration's files.
8. **`ha_restart(confirm=true)` timeouts** — expected behavior during restart. Don't treat as failure. Poll `http://<lan-ip>:8123/api/` for 401 to confirm HA is up.
9. **`schedule.py` is the testable seam** — any new date math should land here as a pure function. Any logic that imports `homeassistant.*` cannot be unit-tested without the conftest stub and even then, integration testing is hard.
10. **Build outputs commit `panel/dist/main.js`** — yes, even though it's a generated artifact, it's tracked (like many HA integrations do). The CI rebuilds it at release time, so any divergence is fixed at the next tag.

---

## 11. Open issues from upstream (triage as of 2026‑07‑12)

**Already shipped in v1.6.0:**
- HA 2026.3 compatibility (from #122)
- Edit/Delete buttons stuck in corner (from #122)
- "Add Task" button no styling (from #122)
- German translation import (from #99)
- All dependabot bumps

**Already shipped in v1.7.0:**
- Title edit field (#100)
- Description field (#101)
- Area support (#117)
- Count-based task triggers (#115)
- Runtime/duration-based task triggers (#115 — bundled with count)

**Open issues NOT yet addressed (triage summary):**
- #59 (Dutch translation) — needs new `nl.json` files; queued for v1.8.0
- #63 (Fire event when task becomes due) — enhancement, requires event bus integration; NOT critical
- #66 (Date format) — `formatDateNumeric` should already respect locale; may be partially fixed
- #69 (Snooze button) — related to #85; enhancement, not critical
- #70 (Description field) — **closed by #101** in v1.7.0
- #79 (Custom entity ID schemas) — enhancement; low priority
- #85 (Pause button) — seasonal tasks; enhancement, not critical
- #102 (Assign user to task) — enhancement; low priority
- #109 (Count-based triggers) — **closed by #115** in v1.7.0
- #118 (Edit/Delete buttons) — **closed by #122** in v1.6.0
- #120 (Meta: is this maintained?) — meta; no action

**Open PRs NOT yet addressed (v1.8.0 candidates):**
- #104 (French translations) — needs localize.ts follow-up to actually load
- #106 (Ukrainian translations) — same
- #84, #108, #112, #113 (dependabot) — all merged in v1.6.0
- Localization cleanup for #115's hardcoded English strings

---

## 12. Future work (in priority order)

1. **v1.7.1 (bug-fix only)** — localize the hardcoded English strings in `panel/src/main.ts` from #115. Touches `panel/src/main.ts`, `panel/localize/languages/en.json`, `panel/localize/languages/de.json`, `translations/en.json`. Small, low-risk. Follow-up after the v1.7.0 cooldown.
2. **v1.8.0 (localization)** — Cherry-pick #104 (fr) and #106 (uk). For each, **also** update `panel/localize/localize.ts` to import the new language (PR #99 fixed this for de; the same pattern is needed for fr/uk). New `nl.json` to close #59.
3. **Upstream sync** — when the user says "sync", do:
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main   # fast-forward if possible
   git checkout dev
   git rebase main           # may have conflicts with our pre-flight + cherry-picks; resolve per §9
   ```
4. **Storage consolidation** — currently Python and TypeScript both compute `next_due`. Have the Python entity expose `next_due` as an attribute and have the frontend use that. Defer until there's a real bug.
5. **HACS stale-index cleanup** — the `TJPoorman/home_maintenance` HACS entry is stale. Cosmetic; ignore.

---

## 13. Session continuity

These specialist sessions are reusable by alias for the same context (home_maintenance fork):

| Alias | Session ID | Role | Status |
|---|---|---|---|
| `exp-1` | `ses_0a636b8d7ffeogb98Rc7J1rsty` | explorer (recon, code search) | completed, reconciled |
| `fix-1` | `ses_0a62ddcecffeQZKjVbzUjTss7o` | fixer (pre-flight, v1.6.0) | completed, reconciled |
| `fix-3` | `ses_0a5fa4bb0ffeqqra4gvg3Dvr7X` | fixer (v1.7.0 cherry-picks) | completed, reconciled |

When dispatching a new task in this codebase, prefer reusing an alias for context savings. If context is stale or unrelated, start a fresh session.

**Background-job discipline:** when dispatching, do not poll. Wait for hook-driven completion. Reconcile completed sessions before final response.

---

## 14. Local environment (Windows host)

| | |
|---|---|
| Working dir | `C:\Users\conra\Opencode\home_maintenance` |
| `gh` CLI | Authenticated as `cfoucher` via `GITHUB_TOKEN` env var |
| Token storage | `C:\Users\conra\.github_token` (Hidden, ACL restricted to current user) |
| PowerShell profile | `C:\Users\conra\OneDrive\Laptop Documents\WindowsPowerShell\profile.ps1` (loads `$Env:GITHUB_TOKEN` from the dot file) |
| `gh` quirks in PowerShell | Some `gh` commands (notably `gh pr close`, `gh release create`) fail silently inside the PowerShell shell. Use the GitHub REST API directly via `Invoke-RestMethod` for these. |
| `zip` (Unix) | Not on Windows PATH. Use `python` + `zipfile` to replicate the workflow's `zip` command for local builds. |
| HA network | HA at `http://192.168.1.70:8123` from the Windows host. ha-mcp sees it as `http://127.0.0.1:8123` (internal). |
| Node / npm | v22.17.0 / 10.9.2 (verified on host) |
| Python | 3.14.6 (matches HA Core) |
| pytest | 9.1.1 |
| ruff | 0.15.0 (matches v1.6.0 bump) |

---

## 15. Global rules that also apply

This file is project-specific. The **global** agent rules are in `C:\Users\conra\Opencode\AGENTS.md` and include:
- `homeassistant` MCP usage patterns
- Tool result honesty
- **No commenting as the user without explicit approval** (PR comments, issue comments, reviews, etc.) — this applies even more strictly in this repo since the fork is public
- Verified false claims about ha-mcp (e.g., "post-write poll", "silent success")
- The `BytesLike` stale‑cache pattern (not a fork issue, but worth knowing if ha-mcp gets flaky)

When in doubt, read the global file first.

## 16. Testing policy

**The rule (hard):** no commit is made to `dev` without tests that validate the change. **We do not commit any code without tests to validate it all.**

**The principle:** every change to the codebase — new feature, bug fix, refactor, cherry-pick from upstream — ships with tests that prove it works. Tests are the spec; they describe what the code does. "Fully tested" is the default, not the goal.

### What "fully tested" means in this codebase

| Change | Test requirement |
|---|---|
| **New pure function in `schedule.py`** | **Required** — unit test in `tests/test_schedule.py` covering happy path + edge cases (month‑end clamping, leap years, threshold boundaries, zero/negative inputs) |
| **New field on `HomeMaintenanceTask`** | **Required** — test that the field loads from storage with the correct default |
| **New entity / binary sensor logic** | **Required where possible** — extract a pure helper, test that. If it genuinely can't be extracted, `# pragma: no cover` + commit message explains why |
| **New service handler** (e.g., `increment_count`) | **Required at the pure‑logic level** — the handler's delegate is tested; the handler itself is HA‑runtime‑only |
| **New event listener** (count / runtime triggers) | **Required at the helper level** — the threshold / baseline / increment math MUST live in `schedule.py` and be tested there. The listener itself is HA‑runtime‑only |
| **TypeScript change** | **Required** — `npm run build` succeeds. For non‑trivial logic, extract a pure function and test it |
| **New translation strings** | **Required** — strings present in BOTH `translations/en.json` AND `panel/localize/languages/en.json` (and any other supported language). For a new language, `localize.ts` imports it (PR #99 lesson — only en was imported, so `de.json` was dead code) |
| **Bug fix** | **Required** — add a regression test that fails before the fix and passes after |
| **Refactor (no behavior change)** | **Required** — existing tests still pass. Add tests for any newly exposed public API |
| **Cherry‑pick from upstream** | **Required** — re‑run full test suite after. Fix any failures before committing |

### The testable seam: `schedule.py`

`custom_components/home_maintenance/schedule.py` is the only file in the integration with **zero `homeassistant.*` imports**. This is what makes unit testing possible. **If you are adding logic that needs testing, refactor it into `schedule.py` first, then test from there.**

This is the single most important testability rule in the project. It exists because:
- `binary_sensor.py`, `__init__.py`, `store.py`, `websocket.py` all import `homeassistant.*` at module top
- `tests/conftest.py` provides a `homeassistant.*` module‑tree stub, but the stub is fragile — every new HA import might need a conftest update
- `schedule.py` is a pure‑Python module — tests run in milliseconds with no setup

### Pre‑commit checklist (from §4, restated as a hard rule)

Every commit must pass **all** of:
1. `python -m pytest tests/ -v` — all tests green, including new ones
2. `python -m ruff check custom_components/home_maintenance/` — clean
3. `python -m ruff format --check custom_components/home_maintenance/` — clean
4. `cd custom_components/home_maintenance/panel && npm ci && npm run build` — succeeds
5. `git status` — clean
6. New / modified code has tests per the table above

**If any of these fail, the commit does not happen.** Fix and retry. There is no "I'll add tests in a follow‑up commit" — the tests ship with the change.

### When code genuinely can't be tested

- Document the reason in the commit message (`no-test: <reason>`)
- Mark with `# pragma: no cover` in the test file
- Add a follow‑up todo to write the test later
- Open an issue / TODO so it doesn't get lost

### Anti‑patterns to avoid

- "I'll add tests later" — tests get forgotten. Write them with the change.
- Cherry‑picking upstream code without re‑running the existing tests after.
- Adding new trigger math in `binary_sensor.py` directly instead of `schedule.py`.
- Modifying `__init__.py`'s event listeners without extracting the core logic into a testable helper.
- Skipping tests on a "small change" — small changes break things.
- Tests that only cover the happy path. Edge cases (empty input, threshold = 0, month‑end, leap year, type mismatches) are the most likely failure modes.

---

**Last updated:** 2026‑07‑13 (after v1.7.0 deploy; added §16 testing policy)
**Maintainer of this doc:** the agent (cfoucher) — keep it current when the project changes.
