# Plan: Per-Task Schedule Mode (Fixed vs. Rolling) — v1.8.0

> **Status:** Draft — first pass
> **Target release:** v1.8.0
> **Scope:** Add a per-task "rolling" option alongside the current behavior, and change the default to **fixed** (anchored) for new tasks.

---

## 1. Problem Statement & Goals

### 1.1 Current behavior (as of v1.7.4)

The binary sensor's `next_due` is computed as:

```python
next_due = last_performed + interval
```

`last_performed` is **overwritten to today** every time a task is completed (via the Complete button, NFC tag scan, or the `home_maintenance.reset_last_performed` service with no `performed_date`). The result: **the schedule shifts forward when you complete late.** A task with `last_performed = 2026-07-13` and a 1-month interval becomes due `2026-08-13`. If you then complete it on `2026-08-20`, the next due date becomes `2026-09-20` — not `2026-09-13`.

This is operationally **rolling-from-last-completion**.

### 1.2 Desired behavior

The user wants the option to make the schedule **fixed/anchored** (i.e., a "recurring appointment" model: due on the 13th of every month, regardless of when the user actually completes it). This becomes the new default. The current rolling behavior remains available as an opt-in "rolling" mode.

**Two modes, two semantics:**

| | **Fixed (new default)** | **Rolling (opt-in)** |
|---|---|---|
| User completes on time | `last_performed` updates to today; `next_due_anchor` advances by interval. `next_due` = new anchor. | `last_performed` updates to today. `next_due` = today + interval. |
| User completes late | `last_performed` updates to today (record of actual work); `next_due_anchor` advances by interval from the old anchor. `next_due` stays on schedule. | `last_performed` updates to today. `next_due` = today + interval — schedule shifts. |
| Late completion impact on schedule | None — schedule is anchored. | Schedule shifts forward by the lateness. |

### 1.3 Goals

- G1. Add a per-task `schedule_mode` field: `"fixed"` (new default for new tasks) or `"rolling"`.
- G2. Existing tasks migrate transparently: they keep their current rolling behavior (their `last_performed` reflects prior completions, switching them to fixed could surprise the user).
- G3. The `next_due` attribute is correct for both modes, including month-end clamping and leap years.
- G4. The `home_maintenance.reset_last_performed` service with an explicit `performed_date` works correctly in both modes.
- G5. The frontend Add Task and Edit Task dialogs expose the choice; both `en.json` and `de.json` translations are updated.
- G6. All logic that needs testing lands in `schedule.py` (the existing testable seam) and is covered by `tests/test_schedule.py`.
- G7. No regressions in the count-based or runtime-based trigger types (they are unaffected by this feature).
- G8. The frontend independently computes `next_due` for sort/display, matching the backend's calculation for both modes.

### 1.4 Non-goals (deferred)

- N1. Preserving the **original day-of-month** for fixed tasks across month boundaries (e.g., "always the 31st, fall back to 30/28 when needed"). Out of scope for v1.8.0. Documented as a possible v1.9.0 enhancement. (See §9.)
- N2. Migrating existing tasks to fixed mode automatically. (Decision in §3.2.)
- N3. UI affordances for adjusting the schedule anchor post-creation beyond editing `last_performed`. (Editing `last_performed` on a fixed task does NOT re-anchor — see §5.2.)
- N4. Snooze / pause / "reschedule" features (issues #69, #85). Out of scope.

---

## 2. Data Model Changes

### 2.1 New fields on `HomeMaintenanceTask` (store.py)

```python
@attr.s(slots=True)
class HomeMaintenanceTask:
    # ... existing fields ...
    schedule_mode: str = attr.ib(default="rolling")   # NEW: "fixed" or "rolling"
    next_due_anchor: str | None = attr.ib(default=None)  # NEW: ISO date string, only meaningful when schedule_mode == "fixed"
```

**Default for new tasks:** `"rolling"`. This is the **migration default** — see §3.2 for the per-task default in the UI.

**Storage:** `next_due_anchor` is stored as an ISO date string (`YYYY-MM-DDTHH:MM:SS`), same shape as `last_performed`. Stored with `hour=0, minute=0, second=0, microsecond=0`.

### 2.2 Storage version bump

- `STORAGE_VERSION_MINOR` bumps from `2` to `3`.
- `async_load` adds `setdefault` for the two new fields:
  ```python
  task_data.setdefault("schedule_mode", "rolling")
  task_data.setdefault("next_due_anchor", None)
  ```
- Existing v1.7.x storage files load transparently. The `setdefault` ensures no `KeyError`.

### 2.3 Frontend `Task` type (panel/src/types.ts)

```typescript
export type ScheduleMode = "fixed" | "rolling";

export interface Task {
    // ... existing fields ...
    schedule_mode?: ScheduleMode;   // defaults to "rolling" for legacy tasks
    next_due_anchor?: string | null;
}
```

---

## 3. New Defaults & Migration

### 3.1 New tasks (UI default)

When the user opens the Add Task dialog, the `schedule_mode` selector defaults to `"fixed"`. This is the new behavior the user wants as default.

### 3.2 Existing tasks (migration)

**Decision:** Existing tasks keep `"rolling"` mode after upgrade. This preserves the user's existing schedule behavior and avoids surprise.

**Rationale:** A user who has been using the integration for 6 months with rolling behavior (their `last_performed` has been updated on every completion) would experience a sudden shift in schedule if we forced fixed mode. Their `last_performed` is the most-recent completion date, not the original "anchor" they originally set. Switching to fixed would compute a new anchor = `last_performed + interval`, which might be a different day-of-month than they originally chose. The safest choice is to preserve their current behavior and let them opt in to fixed per-task.

The user can change an existing task to fixed via the Edit dialog. The first time they edit a fixed task, the `next_due_anchor` is computed from the task's current `last_performed + interval` and saved.

---

## 4. Calculation Logic

### 4.1 New pure functions in `schedule.py`

```python
from datetime import datetime
from dateutil.relativedelta import relativedelta

# EXISTING (rename for clarity — see §4.2)
def calculate_next_due_rolling(
    last_performed: datetime, interval_value: int, interval_type: str
) -> datetime:
    """Rolling: next due = last performed + interval."""
    if interval_type == "days":
        return last_performed + timedelta(days=interval_value)
    if interval_type == "weeks":
        return last_performed + timedelta(weeks=interval_value)
    if interval_type == "months":
        return last_performed + relativedelta(months=interval_value)
    return last_performed


# NEW
def calculate_next_due_fixed(
    last_performed: datetime,
    interval_value: int,
    interval_type: str,
    next_due_anchor: datetime | None = None,
) -> datetime:
    """
    Fixed: next due = anchor + interval.
    If anchor is None, initialize it from last_performed + interval.
    """
    if next_due_anchor is None:
        return calculate_next_due_rolling(last_performed, interval_value, interval_type)
    if interval_type == "days":
        return next_due_anchor + timedelta(days=interval_value)
    if interval_type == "weeks":
        return next_due_anchor + timedelta(weeks=interval_value)
    if interval_type == "months":
        return next_due_anchor + relativedelta(months=interval_value)
    return next_due_anchor


# NEW (dispatcher)
def calculate_next_due(
    last_performed: datetime,
    interval_value: int,
    interval_type: str,
    schedule_mode: str = "rolling",
    next_due_anchor: datetime | None = None,
) -> datetime:
    """
    Unified dispatcher used by the binary sensor.
    """
    if schedule_mode == "fixed":
        return calculate_next_due_fixed(
            last_performed, interval_value, interval_type, next_due_anchor
        )
    return calculate_next_due_rolling(last_performed, interval_value, interval_type)
```

**Backward compatibility:** The new `calculate_next_due` signature adds two optional kwargs with defaults, so all existing call sites in `binary_sensor.py` and tests continue to work without modification.

### 4.2 Renaming `calculate_next_due` → `calculate_next_due_rolling`

**Decision:** Keep the name `calculate_next_due` as the dispatcher (4.1 above), and add `calculate_next_due_rolling` as a renamed version of the existing function. This way:

- Existing call sites that don't pass `schedule_mode` keep working (default to "rolling" → matches current behavior).
- The dispatcher is the canonical entry point for new code.
- The `_rolling` suffix is explicit and prevents confusion.

**Alternative considered:** Rename `calculate_next_due` → `calculate_next_due_rolling` and require all call sites to be updated. Rejected because it requires touching `binary_sensor.py` for no behavioral benefit. The dispatcher pattern is cleaner.

---

## 5. State Transitions

### 5.1 Task creation (websocket_add_task)

**New optional inputs (defaulted in the websocket schema):**
- `schedule_mode: str = "fixed"` (new tasks default to fixed)
- `next_due_anchor: str | None = None` (computed if not provided)

**Logic:**
1. If `schedule_mode == "fixed"` and `next_due_anchor` is None: compute it from `last_performed + interval`.
2. If `schedule_mode == "rolling"`: ignore `next_due_anchor`; leave it as `None`.
3. For `count` and `runtime` tasks: `schedule_mode` is irrelevant; store `"rolling"` as a default (no behavior change). The UI does not show the schedule_mode selector for these task types.

### 5.2 Task update (websocket_update_task)

**Editable fields:** `schedule_mode`, `next_due_anchor`, `last_performed`, `interval_value`, `interval_type`, etc. — all the existing ones.

**Special case: switching from `rolling` → `fixed`**

If the user changes `schedule_mode` from `"rolling"` to `"fixed"` and `next_due_anchor` is `None`:
- Compute `next_due_anchor = last_performed + interval` (this is the "next scheduled due" given the current rolling state)
- Persist the new anchor

This way, switching a task from rolling to fixed takes effect immediately and the schedule is anchored to the most-recent rolling `next_due`. Subsequent completions will not shift the schedule.

**Special case: switching from `fixed` → `rolling`**

If the user changes `schedule_mode` from `"fixed"` to `"rolling"`:
- Leave `next_due_anchor` in storage (it's a no-op for rolling, but preserving it means switching back to fixed is lossless).
- Future `next_due` is computed from `last_performed + interval` (the rolling semantics).

**Special case: editing `last_performed` on a fixed task**

`last_performed` represents the actual completion date. Editing it on a fixed task does NOT change `next_due_anchor` — the schedule stays anchored.

**Special case: editing `interval_value` or `interval_type` on a fixed task**

`next_due_anchor` is preserved. The next `next_due` is computed from the same anchor with the new interval. This is the correct behavior — the user might be correcting the interval without wanting to shift the schedule.

### 5.3 Task completion (store.update_last_performed)

**For fixed tasks:**
1. Update `last_performed` to today (or `performed_date` if provided).
2. Advance `next_due_anchor` by interval: `anchor = anchor + interval` (using `relativedelta`/`timedelta`).
3. Persist both.

**For rolling tasks:**
1. Update `last_performed` to today.
2. No anchor change needed (not used in rolling mode).

**For count/runtime tasks:**
1. Existing behavior (reset counter, advance baseline). No change.

### 5.4 Schedule anchor initialization for existing fixed tasks

If a task has `schedule_mode == "fixed"` but `next_due_anchor is None` (e.g., user just switched from rolling to fixed, or migration edge case):
- On first access (in `calculate_next_due_fixed`): compute it from `last_performed + interval`.
- On next completion: persist the computed anchor.
- This is a "lazy initialization" pattern — the anchor is computed when needed and persisted on the next state change.

---

## 6. Sensor & Attribute Changes

### 6.1 `binary_sensor.py` `_update_state_time`

**Current:**
```python
due_date = calculate_next_due(last, interval_value, interval_type).replace(
    hour=0, minute=0, second=0, microsecond=0
)
```

**New:**
```python
schedule_mode = self.task.get("schedule_mode", "rolling")
next_due_anchor = self.task.get("next_due_anchor")
anchor_dt = None
if next_due_anchor:
    parsed_anchor = dt_util.parse_datetime(next_due_anchor)
    if parsed_anchor:
        anchor_dt = parsed_anchor.replace(hour=0, minute=0, second=0, microsecond=0) if parsed_anchor.tzinfo is None else dt_util.as_local(parsed_anchor).replace(hour=0, minute=0, second=0, microsecond=0)

due_date = calculate_next_due(
    last, interval_value, interval_type, schedule_mode, anchor_dt
).replace(hour=0, minute=0, second=0, microsecond=0)
```

**Extra state attributes additions:**
```python
self._attr_extra_state_attributes = {
    "trigger_type": "time",
    "last_performed": self.task["last_performed"],
    "interval_value": self.task["interval_value"],
    "interval_type": self.task["interval_type"],
    "schedule_mode": schedule_mode,                       # NEW
    "next_due_anchor": self.task.get("next_due_anchor"),  # NEW
    "next_due": due_date.isoformat(),
    "description": self.task.get("description"),
}
```

### 6.2 No changes for count / runtime sensors

`_update_state_count` and `_update_state_runtime` are unchanged. The `schedule_mode` and `next_due_anchor` fields are irrelevant for these trigger types.

---

## 7. Frontend Changes (panel/src/main.ts)

### 7.1 `TaskFormData` interface

Add `schedule_mode: "fixed" | "rolling"` to both `_formData` and `_editFormData`.

### 7.2 Schema additions (`_basicSchema`)

For time-based tasks only, add to `_basicSchema` and `_editSchema`:

```typescript
{
    name: "schedule_mode",
    required: false,
    default: "fixed",
    selector: {
        select: {
            options: [
                { value: "fixed", label: localize('panel.cards.new.fields.schedule_modes.fixed', this.hass!.language) },
                { value: "rolling", label: localize('panel.cards.new.fields.schedule_modes.rolling', this.hass!.language) },
            ],
            mode: "dropdown"
        },
    },
},
```

For `count` and `runtime` tasks: do NOT add the `schedule_mode` selector. (It's not relevant.)

### 7.3 Form initial values

- `resetForm`: `_formData.schedule_mode = "fixed"` (default for new time-based tasks).
- `resetEditForm`: `_formData.schedule_mode = "fixed"` (default — overwritten in `_handleOpenEditDialogClick` with the task's actual value).
- `_handleOpenEditDialogClick`: set `schedule_mode: task.schedule_mode ?? "rolling"`.
- `_handleAddTaskClick`: include `schedule_mode: this._formData.schedule_mode || "fixed"` in the payload.
- `_handleSaveEditClick`: include `schedule_mode: this._editFormData.schedule_mode || "rolling"` in the updates payload.

### 7.4 `_rows` calculation (display/sort)

Replace the time-based `next_due` calculation (lines 290–325 of main.ts) with:

```typescript
if (task.trigger_type === "runtime") {
    // ... unchanged ...
}
if (task.trigger_type === "count") {
    // ... unchanged ...
}

// time-based: dispatch on schedule_mode
const scheduleMode = task.schedule_mode ?? "rolling";
if (scheduleMode === "fixed" && task.next_due_anchor) {
    return new Date(task.next_due_anchor);
}
// rolling (or fixed without anchor — fallback): existing logic
const [datePart] = task.last_performed.split("T");
const [year, month, day] = datePart.split("-").map(Number);
const next = new Date(year, month - 1, day);
switch (task.interval_type) {
    case "days":  next.setDate(next.getDate() + task.interval_value); break;
    case "weeks": next.setDate(next.getDate() + task.interval_value * 7); break;
    case "months": next.setMonth(next.getMonth() + task.interval_value); break;
    default: throw new Error(`Unsupported interval type: ${task.interval_type}`);
}
return next;
```

### 7.5 Optional: display the schedule mode in the table

A new "Schedule" column or a small badge next to the title showing "Fixed" or "Rolling" would be nice. Defer this to a follow-up if it doesn't fit in v1.8.0 scope. **For v1.8.0: do not add a new column**; just make the choice visible in the Edit dialog.

### 7.6 Localization keys

In `panel/localize/languages/en.json` and `de.json`, add:

```json
"panel": {
    "cards": {
        "new": {
            "fields": {
                "schedule_mode": {
                    "heading": "Schedule Type",
                    "helper": "Fixed: stays on schedule regardless of when you complete it. Rolling: shifts forward if you complete late."
                },
                "schedule_modes": {
                    "fixed": "Fixed (anchored to schedule)",
                    "rolling": "Rolling (from last completion)"
                }
            }
        },
        "dialog": {
            "edit_task": {
                "fields": {
                    "schedule_mode": {
                        "heading": "Schedule Type",
                        "helper": "Fixed: stays on schedule regardless of when you complete it. Rolling: shifts forward if you complete late."
                    },
                    "schedule_modes": {
                        "fixed": "Fixed (anchored to schedule)",
                        "rolling": "Rolling (from last completion)"
                    }
                }
            }
        }
    }
}
```

Both `en.json` and `de.json` get the same set of keys (the German translation can be rough — see the v1.7.2 `test_localization_keys_match` test that enforces this).

### 7.7 `translations/en.json` and `translations/de.json`

If any of the existing strings change wording (none do), update both. New strings in the HA-level translation files are not required for this feature (the schedule mode is purely a panel concept).

---

## 8. Testing Plan

### 8.1 `tests/test_schedule.py` — new test classes

```python
class TestCalculateNextDueRolling:
    """Existing tests in TestCalculateNextDue — verify they still pass after the rename."""
    # (no new tests; just the renamed function)

class TestCalculateNextDueFixed:
    """Tests for fixed (anchored) mode."""
    def test_fixed_uses_anchor_not_last_performed(self): ...
    def test_fixed_initializes_anchor_from_last_performed(self): ...
    def test_fixed_advances_anchor_with_interval(self): ...
    def test_fixed_month_end_clamping(self): ...  # Jan 31 + 1 month -> Feb 28
    def test_fixed_leap_year(self): ...  # Jan 31 + 1 month in 2024 -> Feb 29
    def test_fixed_days_preserves_time(self): ...
    def test_fixed_weeks_preserves_time(self): ...
    def test_fixed_with_none_anchor_falls_back_to_rolling(self): ...
    def test_fixed_default_anchor_zero_microseconds(self): ...

class TestCalculateNextDueDispatcher:
    """Tests for the unified calculate_next_due function."""
    def test_dispatcher_default_is_rolling(self): ...
    def test_dispatcher_routes_to_rolling(self): ...
    def test_dispatcher_routes_to_fixed(self): ...
    def test_dispatcher_fixed_with_anchor(self): ...
    def test_dispatcher_fixed_with_none_anchor(self): ...

class TestEdgeCases:
    """Cross-cutting edge cases the user explicitly asked about."""
    def test_complete_on_31st_next_month_has_30_days_rolling(self): ...
    def test_complete_on_31st_next_month_has_28_days_rolling(self): ...
    def test_complete_on_31st_next_month_has_29_days_leap_rolling(self): ...
    def test_complete_on_31st_fixed_anchor_handles_short_month(self): ...
    def test_complete_on_feb_29_leap_year(self): ...
    def test_complete_in_future_rolling(self): ...
    def test_complete_in_future_fixed(self): ...
    def test_edit_last_performed_does_not_change_anchor(self): ...
    def test_edit_interval_does_not_change_anchor(self): ...
    def test_switching_rolling_to_fixed_computes_anchor_from_last(self): ...
    def test_switching_fixed_to_rolling_preserves_anchor(self): ...
```

Approximately 25–30 new tests, bringing the total to ~50.

### 8.2 `tests/test_websocket_config.py` — new tests

Add a new test class `TestAddTaskScheduleMode`:
- `test_add_task_defaults_schedule_mode_to_fixed`
- `test_add_task_accepts_explicit_rolling`
- `test_add_task_computes_anchor_for_fixed_when_omitted`
- `test_add_task_preserves_explicit_anchor_for_fixed`
- `test_add_task_ignores_anchor_for_rolling`

Add a new test class `TestUpdateTaskScheduleMode`:
- `test_update_task_can_change_schedule_mode`
- `test_update_task_switching_to_fixed_initializes_anchor`
- `test_update_task_switching_to_rolling_keeps_anchor`
- `test_update_task_preserves_anchor_on_interval_change`

These tests use the same pattern as `test_get_config_returns_version` (mock-based, no HA).

### 8.3 `tests/test_panel_imports.py` — new static analysis

Add tests for:
- `test_main_ts_has_schedule_mode_in_form_data`: verifies `_formData` and `_editFormData` have a `schedule_mode` field.
- `test_main_ts_has_schedule_mode_in_payload`: verifies `_handleAddTaskClick` and `_handleSaveEditClick` include `schedule_mode` in the payload/updates.
- `test_main_ts_rows_use_anchor_for_fixed`: verifies the `_rows` getter branches on `schedule_mode === "fixed"`.
- `test_localization_keys_match_schedule_mode`: verifies `en.json` and `de.json` have the same `schedule_modes` and `schedule_mode` keys.

### 8.4 Manual smoke tests (HA runtime)

Listed in the PR description (not automated):

1. Create a new time-based task, default schedule_mode = "fixed", interval 1 month, last_performed = today.
   - Verify `binary_sensor.next_due` = today + 1 month.
2. Complete the task tomorrow.
   - Verify `last_performed` = tomorrow, `next_due_anchor` advances by 1 month from old anchor, `next_due` reflects the new anchor.
3. Edit the task, change schedule_mode to "rolling".
   - Verify `next_due` = `last_performed + interval` (not the old anchor).
4. Create a task with `last_performed` = Jan 31, interval 1 month, schedule_mode = "fixed".
   - Verify `next_due_anchor` = Feb 28 (clamped), `next_due` = Feb 28.
   - Complete on Feb 28.
   - Verify `next_due_anchor` advances to Mar 28, `next_due` = Mar 28.
5. Create a count-based task. Verify the schedule_mode selector is NOT shown in the dialog.
6. Use the `home_maintenance.reset_last_performed` service with a specific `performed_date` on a fixed task. Verify anchor advances by interval.
7. Reload HA. Verify all tasks load with the correct `schedule_mode` and `next_due_anchor`.

### 8.5 Pre-commit gate (per AGENTS.md §16)

Before commit:
1. `python -m pytest tests/ -v` — all green
2. `python -m ruff check custom_components/home_maintenance/` — clean
3. `python -m ruff format --check custom_components/home_maintenance/` — clean
4. `cd custom_components/home_maintenance/panel && npm ci && npm run build` — succeeds
5. `python -m pytest tests/test_panel_imports.py -v` — all panel regression tests pass

---

## 9. Future Work (Deferred, Not in v1.8.0)

### 9.1 Preserve original day-of-month for fixed tasks

When a task is created with `last_performed = 2026-01-31` and interval 1 month, the fixed schedule will be Feb 28, Mar 28, Apr 28, ... It will never "go back" to the 31st. Some users may want: "always the 31st when possible, fall back to last day of month otherwise." This is a separate feature and a different mental model. Documented in the README as a possible v1.9.0 enhancement.

### 9.2 Bulk conversion of existing tasks to fixed

A one-click "convert all rolling tasks to fixed (anchor = current next_due)" would be a useful migration tool. Not in v1.8.0 scope.

### 9.3 Schedule mode display in the Current Tasks table

Adding a "Schedule" column or a badge next to the task title would surface the mode at a glance. Defer to a UX pass.

---

## 10. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Existing user surprised by behavior change | Medium | Existing tasks keep "rolling" mode. Only NEW tasks default to "fixed". Document clearly in PR description and release notes. |
| Frontend/backend `next_due` calculation diverges | Medium | Both must use the same logic. The frontend's `next_due` for fixed mode is just `new Date(task.next_due_anchor)` — no date math. The test `test_main_ts_rows_use_anchor_for_fixed` guards this. |
| Storage migration breaks old installs | Low | `setdefault` is forgiving. Bumping `STORAGE_VERSION_MINOR` (not MAJOR) signals to HA that the schema is compatible. |
| User edits `last_performed` expecting schedule to shift on a fixed task | Low | Document in the dialog helper text that for fixed tasks, the schedule is anchored and editing the completion date does not shift it. The helper text in `en.json` covers this. |
| `relativedelta(months=1)` from Jan 31 returns Feb 28 in non-leap year | Low | Already tested in `test_calculate_next_due_month_end` and `test_calculate_next_due_month_end_leap_year`. New tests extend coverage. |
| The Complete button via NFC tag scan bypasses the new anchor logic | Low | All completion paths go through `store.update_last_performed`. The anchor advancement is in that one function. |
| `home_maintenance.reset_last_performed` with explicit `performed_date` doesn't advance anchor | Low | Same function, same code path. Tested. |
| German translation missing new keys | Low | `test_localization_keys_match` enforces parity. Both en and de updated in the same commit. |

---

## 11. Open Questions for User Review

1. **Migration default for existing tasks:** Plan says "rolling" (preserves current behavior). Confirm or override to "all fixed".
2. **Add the schedule_mode selector only for time-based tasks?** Plan says yes (count/runtime don't need it). Confirm.
3. **UI: dropdown or boolean checkbox?** Plan says dropdown (matches the trigger_type selector pattern). Confirm.
4. **Display the schedule mode in the Current Tasks table?** Plan says no (defer). Confirm.
5. **Bump VERSION to 1.8.0?** Plan says yes. Confirm.

---

*End of draft — pass 1 complete. Reviewing now for design errors.*
