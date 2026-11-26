"""Run a deterministic command-line demonstration of PawPal+."""

from datetime import datetime

from pawpal_system import Owner, Pet, Scheduler, Task


def main() -> None:
    """Build and print a sample schedule for two pets."""
    demo_day = datetime(2026, 1, 15)
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "cat")
    biscuit = Pet("Biscuit", "dog")
    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    mochi.add_task(Task("Brush coat", demo_day.replace(hour=18), 10, priority="Low"))
    breakfast = Task(
        "Serve breakfast", demo_day.replace(hour=7, minute=30), 10,
        frequency="daily", priority="High",
    )
    mochi.add_task(breakfast)
    mochi.add_task(Task("Give medication", demo_day.replace(hour=12), 5, priority="High"))
    biscuit.add_task(Task("Vet appointment", demo_day.replace(hour=15), 45, priority="High"))
    biscuit.add_task(Task("Morning walk", demo_day.replace(hour=8), 30, frequency="daily"))
    biscuit.add_task(Task("Serve dinner", demo_day.replace(hour=17, minute=30), 10))

    breakfast.mark_complete()
    print(f"Marked complete: {mochi.name} — {breakfast.description}")
    print()
    print(f"Today's Schedule — {demo_day:%Y-%m-%d}")
    scheduler = Scheduler(owner)
    for pet, task in scheduler.sort_chronologically():
        status = "Completed" if task.completed else "Pending"
        print(
            f"{task.due_at:%Y-%m-%d %H:%M} | {pet.name} | {task.description}"
            f" | {task.priority} | {status}"
        )


if __name__ == "__main__":
    main()
