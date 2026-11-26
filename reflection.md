# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

**Proposed architecture**

- `Task`, `Pet`, and `Owner` are dataclasses. Each pet holds its own tasks and each owner holds their pets. `Owner.get_all_tasks()` keeps each task paired with its pet.
- `Scheduler` reads one owner's tasks across all pets. It can sort, filter, check for overlaps, and propose a plan with reasons for its choices. Streamlit can display those results and collect input separately.
- The draft uses the due time as the current scheduled start for overlap checks. Review whether fixed appointments need a separate start or deadline and which time zone defines the owner's calendar day.

**Three core workflows**

1. **Set up pets and care tasks.** Create an owner, add pets, and assign feeding, walking, medication, grooming, or appointment tasks to the relevant pet. Each task records its due time, duration, frequency, and priority.
2. **Review and plan a day.** Filter the combined schedule by pet, date, or completion status. Check for overlaps across pets, then propose a priority-based plan or look for a slot that fits within the owner's available time.
3. **Complete a task and handle recurrence.** Mark the current task complete. For a daily or weekly task, use its scheduled due time to preview the next occurrence. A future implementation can add that occurrence to the same pet as a separate task and prevent duplicates when completion is retried.

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
