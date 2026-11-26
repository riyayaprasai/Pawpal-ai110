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

### Submission documentation pass

The user asked Codex to review the final repository for academic submission and public GitHub presentation. The request included a final Mermaid diagram, a README tied to the real implementation, evidence-based reflection notes, an audit of this log, repository hygiene, and a fresh CLI and pytest run.

**Files changed in this pass**

- Added `diagrams/uml_final.mmd` from the implemented Python API. The starter and draft diagrams were preserved.
- Updated `README.md`, `reflection.md`, and `ai_interactions.md`. The README contains the captured CLI and pytest output and describes the available scheduling features.
- Updated `.gitignore` and removed the tracked, generated `__pycache__/pawpal_system.cpython-314.pyc` file. The Python implementation and dependency list were left intact.

**Actual verification**

- `python main.py` completed. The sample found an 08:00 slot and restored two pets and eight tasks using a temporary JSON file.
- `python -m pytest` reported **62 passed, 0 failed, 0 skipped**, including Streamlit AppTest cases.
- A local Streamlit server returned `ok` from its health endpoint. This check verifies startup. It was not a manual browser walkthrough.
- An isolated first save created a missing `data/` directory. The final diagram's classes, attributes, and implemented method signatures were checked against Python.

### Independent grading audit follow-up

Codex reviewed the source, Git history, and documentation against the supplied 30-point rubric. The audit replaced the placeholder at the course's `diagrams/uml.mmd` path with the validated final diagram and kept the draft. It also reproduced a stale-save case in which a change to a timestamp's ISO offset and local date was lost even though the instant was unchanged. The fix compares serialized snapshots, and a new regression test verifies that the saved file is preserved.

Files changed in this follow-up were `diagrams/uml.mmd`, `pawpal_system.py`, `tests/test_stretch_features.py`, `README.md`, `reflection.md`, and this log. After the fixes, `python main.py` reproduced the README CLI block. Both `python -m pytest -v` and `python -m pytest` reported **63 passed**. The attribution for the attached response remains a student confirmation item.

A repeat audit reproduced another JSON edge case. Python's default decoder accepted invalid non-finite literals, allowing a later save to overwrite the file. Codex made the loader reject those literals and added three regression cases that verify the saved bytes remain intact. This pass updated `pawpal_system.py`, `tests/test_stretch_features.py`, `README.md`, `reflection.md`, and this log. The CLI still matched the README. Both pytest commands reported **66 passed**.

**Student section — manual review and corrections**

<!-- Record the code you reviewed, any changes you made yourself, and how you verified them. -->

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

### Shared prompt

The user identified the following scheduling prompt as common to both responses. The attachment contains an answer and does not independently show its prompt or model metadata.

```text
Act as a senior Python algorithms engineer.

I am developing an object-oriented pet care scheduling application called PawPal+.

Design a Python algorithm that finds the earliest available scheduling interval across multiple pets belonging to the same owner.

Each existing task has:

- A due datetime representing its start.
- A duration in minutes.
- A completion status.
- An associated pet.

The requested new task has:

- An earliest acceptable start datetime.
- A required duration.
- A latest acceptable end datetime.

The algorithm must:

- Search tasks across multiple pets.
- Ignore completed tasks.
- Handle existing tasks that overlap each other.
- Treat adjacent intervals as nonoverlapping.
- Return the earliest valid start datetime.
- Return None if no valid interval exists.
- Avoid mutating existing tasks.
- Validate invalid inputs.

Provide:

1. Your recommended algorithm.
2. A readable Python implementation.
3. Time and space complexity.
4. Five important edge cases.
5. Potential limitations.
6. An alternative approach and why you would or would not use it.

Use only the Python standard library. Prioritize correctness, readability, and maintainability over clever syntax.
```

### Solution comparison

| Criterion | Option A — Codex response, “Phase 2 — Earliest available slot algorithm” | Option B — attachment, “PawPal+ Earliest Available Interval Algorithm” |
|---|---|---|
| Model or tool | OpenAI Codex, from this chat. | The supplied text has no model metadata. DeepSeek is named in a working-copy note. Confirm that it produced this response.
| Proposed solution | Sort pending intervals across all of the owner's pets. Scan once with a candidate start and keep the furthest occupied end. The response shows the scan and points to the complete `Scheduler.find_next_available_slot()` method. | Validate an iterable of simplified tasks, clip busy intervals to the window, explicitly merge overlaps, then scan the gaps before, between, and after the merged intervals. |
| Useful aspects | The candidate invariant explains why nested overlaps cannot move the next start backward. The implementation uses the existing `Owner.get_all_tasks()` API, skips completed tasks, compares aware times in UTC, and returns an aware result in the search start's timezone. | The clipping, merging, and gap scan are broken into readable stages. Half-open intervals and the leading and trailing gaps are explicit. The immutable task example makes the standalone function straightforward to inspect. |
| Readability and integration | One scan after sorting, with no separate merged list. The response excerpt needs the linked repository code for validation, interval collection, and timezone handling. The CLI and Streamlit already call this method. | More self-contained as a teaching example. An extra pass and list make the algorithm longer. Its frozen `Task` uses `due` and `pet_name`, while PawPal+ uses `due_at` and associates tasks through `Pet`. Its runtime type check rejects the existing task class, so adoption would require an adapter and exception-handling changes. |
| Time and space | `O(p + n + b log b)` time for `p` pets, `n` tasks, and `b` busy intervals intersecting the window. Auxiliary space is `O(n + b)`, including the repository's flattened pet-task snapshot. | The response gives a worst-case `O(n log n)` time and `O(n)` space. More precisely, collection, merging, and scanning cost `O(n + b)`, sorting costs `O(b log b)`, and both interval lists cost `O(b)` auxiliary space when consuming an existing iterable. Adapting the repository's flattened snapshot also costs `O(n)`. |
| Edges handled | Empty and booked windows, exact fits, adjacent and nested intervals, tasks that start before the window, completed tasks, invalid windows and durations, and sub-minute boundaries. | The code handles these ordinary interval cases too. It validates even completed tasks before skipping them and compares aware datetimes directly. A task near `datetime.max` can overflow when its end is calculated before the outside-window check. |
| Shared limits | One owner's pending tasks share one calendar. The search uses recorded occurrences, adds no travel or working-hours rules, and returns a suggestion without reserving the slot. | The same single-calendar assumptions apply. Callers must supply the occurrences they want to search. |

The existing approach is implemented in [`pawpal_system.py`](pawpal_system.py#L293) and used by [the CLI](main.py) and [Streamlit](app.py). Both responses discuss a minute-grid search. The repository uses a minute-grid oracle for small test cases while keeping full datetime precision in the production interval scan.

### Verification

Command executed from the repository root. It reported **12 passed, 50 deselected**.

```bash
python -m pytest -v tests/test_pawpal.py tests/test_stretch_features.py -k slot
```

The [core tests](tests/test_pawpal.py) check the independent minute-grid oracle, exact sub-minute gaps, and Streamlit's aware slot display. The [stretch tests](tests/test_stretch_features.py) cover cross-pet overlap and adjacency, completed tasks, empty and unavailable windows, request validation, and aware interval comparisons. These pytest cases exercise the repository implementation.

The Python code extracted from the supplied attachment was also run directly against the same inputs as the repository method. These checks were separate from the pytest run.

| Direct check | Repository result | Attached code result |
|---|---|---|
| Two pending tasks occupy 09:00–09:30 and 09:30–10:00. Find a 30-minute slot between 09:00 and 11:00. | 10:00 | 10:00. This contradicts the attachment's prose that 09:30 should be available. The second task occupies that time. |
| A timezone-aware completed task is present during a timezone-naive search window starting at 09:00. | 09:00 | `SchedulingError` because the awareness check runs before the completed-task skip. |
| A pending 30-minute task at `datetime.max` lies outside the search window. | 09:00 | `OverflowError` while computing the irrelevant busy interval's end. |
| A 90-minute request between 01:30 and 03:30 on March 8, 2026, in `America/New_York`. The window contains 60 elapsed minutes. | `None` | 01:30 local time because subtraction in the shared timezone uses the wall-clock difference. |

### Recommended decision for student review

Keep `Scheduler.find_next_available_slot()` and its sorted-interval scan. It fits the existing owner/pet/task model, requires no adapter or additional merged list, and passed the slot-focused repository suite. Use the explicit clipping and merging explanation from Option B if it helps you explain half-open intervals. The recommendation does not require a production code change.

**Student confirmation or revision**

<!-- Confirm Option B's actual model or tool from the original source. Record whether you agree with the recommendation and whether one shared caregiver calendar, elapsed-time scheduling for aware datetimes, and exact back-to-back scheduling fit your project requirements. -->

**Which approach did you use in your final implementation and why?**

<!-- Record your own conclusion after reviewing the evidence. -->
