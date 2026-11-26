# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

**Agent used** — Codex.

<details>
<summary>Exact implementation request</summary>

```text
Act as a senior Python software engineer extending a working PawPal+ application.

Inspect the current implementation, tests, and documentation. Preserve all existing working functionality and avoid unnecessary refactoring.

Implement four distinct stretch features that satisfy the CodePath grading rubric.

STRETCH FEATURE 1: NEXT AVAILABLE SLOT ALGORITHM

Implement Scheduler.find_next_available_slot().

Inputs should include:

- Earliest acceptable start datetime.
- Requested task duration in minutes.
- Latest acceptable end datetime.

Requirements:

- Examine pending tasks across all pets.
- Treat existing task durations as occupied time intervals.
- Sort occupied intervals chronologically.
- Find the earliest available interval large enough for the requested task.
- Treat adjacent intervals as nonoverlapping.
- Handle overlapping occupied intervals correctly.
- Ignore completed tasks.
- Return None when no valid slot is available.
- Do not modify existing tasks.
- Validate invalid durations and date ranges.

Use a simple interval-scanning algorithm rather than unnecessary optimization libraries.

STRETCH FEATURE 2: JSON DATA PERSISTENCE

Implement save_to_json() and load_from_json() functionality in pawpal_system.py.

Persist:

- Owner details.
- Pet details.
- Task IDs.
- Descriptions.
- Due datetimes.
- Completion states.
- Frequencies.
- Priorities.
- Durations.

Requirements:

- Use Python's standard json and pathlib libraries.
- Serialize datetime values using ISO format.
- Restore actual Owner, Pet, and Task objects rather than returning raw dictionaries.
- Preserve identifiers and relationships.
- Support a configurable file path for testing.
- Handle missing files gracefully.
- Report malformed JSON or invalid data clearly.
- Never silently overwrite corrupted data.
- Prefer safe temporary-file replacement when saving.

Use data/data.json as the default persistence path.

Integrate persistence into app.py so user data is loaded on initial startup and saved after successful mutations.

Keep main.py deterministic and independent of live user data. Use a temporary directory when demonstrating persistence.

STRETCH FEATURE 3: ADVANCED PRIORITY SCHEDULING

Implement Scheduler.sort_by_priority().

Requirements:

- High-priority tasks appear before Medium-priority tasks.
- Medium appears before Low.
- Tasks with equal priority are sorted chronologically.
- Include tasks from multiple pets.
- Preserve task-pet associations.
- Do not mutate original task collections.

Integrate a schedule sorting selector into Streamlit for chronological or priority-based sorting.

STRETCH FEATURE 4: PROFESSIONAL OUTPUT FORMATTING

Improve main.py with:

- Consistent table columns.
- Clear section headings.
- Human-readable date and time.
- Readable priority and completion indicators.
- Clear conflict warnings.
- Separate demonstrations of the core and stretch algorithms.

Use tabulate if it provides a clear benefit; otherwise use a small standard-library formatting helper. If a new dependency is introduced, add it to requirements.txt.

Update Streamlit with:

- Summary metrics.
- Priority indicators.
- Conflict notifications.
- An available-slot suggestion feature.
- Clear empty states.
- Consistent formatting.

Add pytest tests for each stretch feature, including JSON round trips, missing or malformed files, priority tie-breaking, overlapping occupied intervals, adjacent intervals, and unavailable slots.

Update README.md with dedicated sections for all four extensions, the relevant methods, files modified, and actual CLI examples.

Create or update ai_interactions.md with an "Agent Workflow" section documenting:

- The exact implementation task requested.
- Files actually modified.
- Features actually completed.
- Tests actually executed.
- Problems encountered and AI-applied fixes.
- A clearly marked section for me to record my own manual corrections.

Do not invent student corrections, fake test results, or pretend I reviewed code that I have not reviewed.

Run the complete demo and pytest suite. Fix failures, preserve previous tests, and report the actual results.

Do not commit or push automatically.
```

</details>

**Files modified by the agent**

- `pawpal_system.py`, `app.py`, and `main.py`
- `tests/test_stretch_features.py` and `diagrams/uml_draft.mmd`
- `.gitignore`, `README.md`, and `ai_interactions.md`

**Features completed**

- The scheduler finds the earliest free slot across pets by scanning appointment intervals.
- PawPal+ saves and restores the owner, pets, tasks, IDs, and recurrence history from JSON. It protects malformed files, validates saved records, and replaces the file only after the new snapshot has been written.
- Streamlit supports chronological and priority ordering, keeps its filters, shows priority indicators and conflict warnings, and suggests an available slot.
- The CLI uses aligned tables and separate core and stretch sections. The persistence example uses a temporary file.

**Tests executed by the agent**

- `python main.py` completed. It reported an 08:00 slot for a 20-minute task and restored two pets and eight tasks. The README contains the captured output.
- `python -m pytest` reported **45 passed**, including all 25 existing cases and 20 new cases.
- Streamlit AppTest used a temporary file to check startup reload, priority and pet filters, conflict warnings, slot suggestions, all five mutation flows, and corrupt-file protection.

**Problems and AI-applied fixes**

- The existing Streamlit callbacks changed objects in memory immediately. A save failure would have left the session displaying a change that was absent on disk. The callbacks now apply changes to a copy and publish that copy after saving succeeds.
- Streamlit sessions can have different snapshots of the same local file. The JSON save checks whether the on-disk owner still matches the session's starting snapshot. Stale sessions are asked to reopen the app.
- An occupied interval can start before the requested window or overlap another pet's task. The interval scan carries forward the furthest occupied end to handle those cases, with tests for exact boundaries and unavailable slots.
- All 45 cases passed on the first combined pytest run. The simulated disk write failure was an intentional regression test.

**Student section — manual review and corrections**

<!-- Record the code you reviewed, any changes you made yourself, and how you verified them. -->

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | | |
| **Prompt** | | |
| **Response summary** | | |
| **What was useful** | | |
| **Problems noticed** | | |
| **Decision** | | |

**Which approach did you use in your final implementation and why?**

<!-- Your conclusion -->
