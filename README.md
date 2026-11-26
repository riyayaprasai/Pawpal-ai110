# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

Run the demo with `python main.py`.

```text
=== Core scheduling ===

Today's Schedule — Thursday, January 15, 2026
Due                     | Pet     | Task            | Priority | Status
------------------------+---------+-----------------+----------+--------
Thu, Jan 15, 2026 07:30 | Mochi   | Serve breakfast | High     | Pending
Thu, Jan 15, 2026 07:30 | Biscuit | Morning walk    | Medium   | Pending
Thu, Jan 15, 2026 12:00 | Mochi   | Give medication | High     | Pending
Thu, Jan 15, 2026 15:00 | Biscuit | Vet appointment | High     | Pending
Thu, Jan 15, 2026 17:30 | Biscuit | Serve dinner    | Medium   | Pending
Thu, Jan 15, 2026 18:00 | Mochi   | Brush coat      | Low      | Pending

Filtered schedule — Mochi, pending, High priority
Due                     | Pet   | Task            | Priority | Status
------------------------+-------+-----------------+----------+--------
Thu, Jan 15, 2026 07:30 | Mochi | Serve breakfast | High     | Pending
Thu, Jan 15, 2026 12:00 | Mochi | Give medication | High     | Pending

Scheduling conflicts
WARNING [Thu, Jan 15, 2026 07:30] Mochi: Serve breakfast / Biscuit: Morning walk share a start time.

Recurring tasks
Completed Mochi's serve breakfast (daily).
Next occurrence: Fri, Jan 16, 2026 07:30
Completed Mochi's brush coat (weekly).
Next occurrence: Thu, Jan 22, 2026 18:00

Completed task history
Due                     | Pet   | Task            | Priority | Status
------------------------+-------+-----------------+----------+----------
Thu, Jan 15, 2026 07:30 | Mochi | Serve breakfast | High     | Completed
Thu, Jan 15, 2026 18:00 | Mochi | Brush coat      | Low      | Completed

=== Stretch features ===

Next available slot — 20 minutes between 07:30 and 09:00
Earliest start: Thu, Jan 15, 2026 08:00

Priority order — pending tasks
Due                     | Pet     | Task            | Priority | Status
------------------------+---------+-----------------+----------+--------
Thu, Jan 15, 2026 12:00 | Mochi   | Give medication | High     | Pending
Thu, Jan 15, 2026 15:00 | Biscuit | Vet appointment | High     | Pending
Fri, Jan 16, 2026 07:30 | Mochi   | Serve breakfast | High     | Pending
Thu, Jan 15, 2026 07:30 | Biscuit | Morning walk    | Medium   | Pending
Thu, Jan 15, 2026 17:30 | Biscuit | Serve dinner    | Medium   | Pending
Thu, Jan 22, 2026 18:00 | Mochi   | Brush coat      | Low      | Pending

JSON persistence — temporary round trip
Restored Jordan, 2 pets, and 8 tasks with their original IDs.
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
============================== 45 passed in 0.05s ==============================
```

## Smarter Scheduling

| Feature | Method | Behavior |
|---------|--------|----------|
| Chronological sorting | `Scheduler.sort_by_time()` | Sorts current `(pet, task)` pairs by full datetime and preserves pet and task insertion order for ties. `sort_chronologically()` remains available. |
| Filtering | `Scheduler.filter_tasks()` | Combines pet ID, case-insensitive exact pet name, due date, completion, and priority with AND semantics. `completed=False` selects pending tasks. A name shared by multiple pets matches all of them. |
| Recurrence | `Scheduler.mark_task_complete()`, `Scheduler.next_occurrence_at()` | Keeps the completed original and adds one pending successor to the same pet for daily and weekly routines. Retrying completion of the same occurrence creates no extra tasks. |
| Conflict warnings | `Scheduler.detect_conflicts()` | Groups pending tasks by exact due datetime and returns each pair once with both pets and tasks. The CLI and Streamlit warn about equal start times, including across pets. |

Daily and weekly recurrence is anchored to the **original scheduled datetime** and advances by one or seven days. Completing a task late can create a successor that is already overdue. Each completion advances one interval and preserves that occurrence as history. One-time tasks have no successor.

For `n` tasks across `p` pets, sorting takes `O(p + n log n)`. Filtering scans once and sorts the `m` matches in `O(p + n + m log m)`. Datetime grouping takes expected `O(p + n + k)` for `k` reported conflict pairs. A large set of tasks at the same time can produce quadratically many pairs.

Conflict checks use the full start datetime. The separate slot search checks occupied durations and can suggest an alternate start. Sorting uses UTC instants for timezone-aware values and requires a consistent choice of timezone-aware or timezone-naive datetimes within the schedule. Date filters use the calendar date recorded on each task.

## Stretch Extensions

### 1. Next Available Slot

`Scheduler.find_next_available_slot(window_start, window_end, duration_minutes)` collects occupied intervals from pending tasks across all pets. It sorts intervals by start and advances a candidate past each occupied end until a full gap fits. An interval may end exactly when another starts. Overlapping intervals keep the candidate at the furthest occupied end. The window is validated, completed tasks are ignored, and the method returns `None` when nothing fits. For `n` tasks and `b` occupied intervals in the search window, gathering and scanning takes linear time and sorting costs `O(b log b)`.

In Streamlit, open **Schedule → Find an available slot** and supply the start, end, and duration. The suggestion is read-only. In the CLI sample above, the 20-minute search after 07:30 returns **08:00**.

### 2. JSON Data Persistence

`save_to_json(owner, path)` writes an owner, pets, task IDs, and task details using ISO datetimes. `load_from_json(path)` restores the actual objects and returns `None` for a missing file. Both default to `data/data.json` relative to the project. That live file is ignored by Git.

Saves validate the stored data before writing a temporary sibling file and replacing the target. Invalid data produces an error and leaves the existing file intact. Streamlit loads on session startup and saves after changes to the owner, pets, and tasks, including recurring completion. A failed save leaves the session's previous data in place. This is a single local data store. Sessions using the same app process share the file, and a stale session must reopen before making further changes. ISO serialization preserves numeric UTC offsets.

The CLI round trip uses a temporary directory and restores **Jordan, two pets, and eight tasks** with their original IDs.

### 3. Advanced Priority Scheduling

`Scheduler.sort_by_priority()` orders High, Medium, and Low tasks across pets. It uses the due datetime to break priority ties and preserves each task's pet. The source collections stay in their original order. Sorting takes `O(n log n)` for `n` entries. In Streamlit, choose **Schedule → Sort by → Priority**. Pet and completion filters still apply. In the CLI sample, the pending High-priority tasks appear first and remain chronological within their group.

### 4. Professional Output Formatting

`format_table()` in `main.py` uses the standard library to align column headers and values. The CLI separates the core and stretch demonstrations and shows human-readable datetimes, priority, completion status, and clear conflict warnings. Streamlit retains summary metrics and uses priority symbols with text labels, consistent schedule tables, conflict warnings, and dedicated empty states.

### Files Updated

| File | Changes |
|------|---------|
| `pawpal_system.py` | Interval scanning, priority order, and safe JSON save/load |
| `app.py` | Startup load, save after mutations, priority controls, and slot suggestions |
| `main.py` | Aligned tables and reproducible core and stretch demos |
| `tests/test_stretch_features.py` | Tests for the four extensions alongside the existing tests |
| `diagrams/uml_draft.mmd` | Priority-sort method signature |
| `.gitignore` | Excludes live local data and its temporary save files |
| `README.md`, `ai_interactions.md` | Extension documentation, captured output, and agent workflow log |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
