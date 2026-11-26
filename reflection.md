# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

**Proposed architecture**

- `Task`, `Pet`, and `Owner` are dataclasses. Each pet holds its own tasks and each owner holds their pets. `Owner.get_all_tasks()` keeps each task paired with its pet.
- `Scheduler` reads one owner's tasks across all pets. It sorts, filters, and checks for start-time conflicts. Priority-based plan proposals remain a future feature. Streamlit can display those results and collect input separately.
- The scheduler uses the due time as the scheduled start for exact-time conflict checks. Review whether fixed appointments need a separate start or deadline and which time zone defines the owner's calendar day.

**Three core workflows**

1. **Set up pets and care tasks.** Create an owner, add pets, and assign feeding, walking, medication, grooming, or appointment tasks to the relevant pet. Each task records its due time, duration, frequency, and priority.
2. **Review and plan a day.** Filter the combined schedule by pet, date, or completion status. Check for tasks scheduled at the same time across pets. A priority-based plan or a search for an available slot could extend this workflow.
3. **Complete a task and handle recurrence.** Mark the current task complete. For a daily or weekly task, the scheduler adds one new occurrence to the same pet based on the original due time. It keeps the completed occurrence in the task history.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

**AI recommendations to consider**

- Sort the current pet-task pairs by datetime and keep their input order for ties. Apply filters in one pass before sorting the matches, which keeps filtering readable and avoids maintaining a search index.
- Generate one successor on completion using the original scheduled time as the anchor. This keeps the intended cadence and retains the original as history. A late completion can therefore create a successor that is already overdue.
- Group pending tasks by their exact start time and surface conflicts as warnings. This identifies simultaneous starts without preventing entry of valid care tasks.

**Questions for personal review**

- Should overdue routines advance one interval at a time, skip missed dates, or offer a separate way to record missed care?
- Should the app warn about overlapping durations, or only simultaneous starts? Which pet-care activities can safely run in parallel?
- Which time zone should define the owner's calendar day, especially when pets or caregivers travel?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
