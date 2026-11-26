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
Today's Schedule — 2026-01-15
2026-01-15 07:30 | Mochi | Serve breakfast | High | Pending
2026-01-15 07:30 | Biscuit | Morning walk | Medium | Pending
2026-01-15 12:00 | Mochi | Give medication | High | Pending
2026-01-15 15:00 | Biscuit | Vet appointment | High | Pending
2026-01-15 17:30 | Biscuit | Serve dinner | Medium | Pending
2026-01-15 18:00 | Mochi | Brush coat | Low | Pending

Filtered schedule — Mochi, pending, High priority
2026-01-15 07:30 | Mochi | Serve breakfast | High | Pending
2026-01-15 12:00 | Mochi | Give medication | High | Pending

Scheduling conflicts
Warning: 2026-01-15 07:30 | Mochi — Serve breakfast conflicts with Biscuit — Morning walk

Recurring tasks
Completed: Mochi — Serve breakfast (daily)
Next occurrence: 2026-01-16 07:30
Completed: Mochi — Brush coat (weekly)
Next occurrence: 2026-01-22 18:00

Completed task history
2026-01-15 07:30 | Mochi | Serve breakfast | High | Completed
2026-01-15 18:00 | Mochi | Brush coat | Low | Completed
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
============================== 25 passed in 0.04s ==============================
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

Conflict checks use the full start datetime. Checking overlapping durations and proposing alternate slots are future features. Sorting uses UTC instants for timezone-aware values and requires a consistent choice of timezone-aware or timezone-naive datetimes within the schedule. Date filters use the calendar date recorded on each task.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
