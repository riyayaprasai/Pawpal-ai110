# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

**Documented architecture**

- The UML models one `Owner` with zero or more `Pet` records. Each pet keeps its own `Task` records. `Owner.get_all_tasks()` preserves the pet associated with each task.
- The three domain classes store and validate the records. `Scheduler` reads the owner's schedule to sort, filter, complete tasks, warn about same-start conflicts, and suggest free time. Both the CLI and Streamlit use this backend.
- The main workflows are registering pets and tasks, reviewing the care schedule, and completing a recurring occurrence while keeping its history.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

**Documented design changes**

- Recurrence moved into `Scheduler.mark_task_complete()` so the original can stay in the history while the next occurrence is added to the same pet.
- Streamlit gained JSON persistence. The app now publishes a changed copy of the owner only after saving succeeds. The QA pass added checks for stale saves, malformed timestamps, and consistent timezone handling.
- The final UML records the implemented API. The draft is preserved for comparison. For example, it contains a proposed full priority planner that was never implemented.

**Student confirmation required** — Identify which design change you would use in your answer and explain your own reasons for it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

**Documented scheduling tradeoffs**

- Priority sorting ranks High, Medium, and Low tasks and orders equal priorities by date and time. It leaves due times unchanged.
- Conflict warnings report pending tasks with the same start. The separate slot search uses durations and permits adjacent tasks. Its sorted scan advances to the furthest occupied end across all pets.
- Recurrence uses the original scheduled time as its anchor. This preserves the planned cadence and history, and can leave a successor overdue after a late completion.
- The search assumes one shared caregiver calendar. Working hours, travel time, and simultaneous care by different people would require additional constraints.

**Student confirmation required** — Explain which constraint you consider most important and whether overdue recurrence or same-start warnings are a reasonable tradeoff for your scenario.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**Documented AI activity**

The agent log records prompts about the stretch implementation and an independent scheduling proposal. The conversation separated architecture, implementation, UI, testing, and documentation into distinct requests. The interval comparison used the same scheduling brief for two supplied responses.

**Possible benefit of separate AI chats — student confirmation required**

A fresh chat could provide an independent second approach, while a repository-focused chat could retain implementation and testing context. An independent proposal still needs comparison against the actual API and test data. Confirm whether you used separate chats and, if so, add your own account of what each contributed.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

**Documented disposition of AI suggestions**

- **Retained in the repository:** Sort the pending occupied intervals and advance one candidate start. This works with `Owner.get_all_tasks()` and the existing `Scheduler` API.
- **Modified between proposals and implementation:** The draft's duration-overlap warnings became exact-start warnings. Duration-aware reasoning is available in the separate slot search.
- **Alternative the agent recommended against adopting:** The attached standalone task model and explicit merged list were not adopted. Direct comparisons found differences in completed-task handling, datetime overflow, and elapsed time across daylight-saving changes. The agent also checked the repository against the existing slot-focused pytest suite.

**Student confirmation required** — Choose an example that reflects a judgment you personally made or verified. The [AI interactions log](ai_interactions.md) records the agent's recommendation and test evidence.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**Documented verification**

The final CLI ran on fixed sample data, found an 08:00 slot, and restored two pets and eight tasks through a temporary JSON file. The latest grading audit ran `python -m pytest -v` and passed all 66 tests. The suite covers cross-pet ordering, recurrence, conflicts, exact-fit gaps, persistence, and corrupt or stale saves. Streamlit AppTest checked interactive workflows with temporary data. A separate minute-based test oracle checks the interval scan on a small schedule.

**Student confirmation required** — Record which checks you ran personally and why you consider them important.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

**Student confirmation required** — State your own confidence and next tests. Possible follow-ups include a manual browser walkthrough, date entry around daylight-saving transitions, and longer mixed-priority schedules with back-to-back tasks.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

**Lead architect role — student confirmation required**

The project owner can set scope, decide whether the scheduler should model one shared caregiver, and verify that the UML and documentation match the code before submission. The agent can implement and test proposals and present evidence for those choices. Add your own reflections on what went well, what you would change, and which architectural or verification decisions you personally led.
