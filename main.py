"""Run a deterministic command-line demonstration of PawPal+."""

from datetime import datetime

from pawpal_system import Owner, Pet, PetTask, Scheduler, Task


def print_schedule(entries: list[PetTask]) -> None:
    """Print the scheduler's pet-task pairs."""
    for pet, task in entries:
        status = "Completed" if task.completed else "Pending"
        print(
            f"{task.due_at:%Y-%m-%d %H:%M} | {pet.name} | {task.description}"
            f" | {task.priority} | {status}"
        )


def main() -> None:
    """Demonstrate the four scheduling algorithms on a fixed date."""
    demo_day = datetime(2026, 1, 15)
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "cat")
    biscuit = Pet("Biscuit", "dog")
    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    grooming = Task(
        "Brush coat", demo_day.replace(hour=18), 10, frequency="weekly", priority="Low"
    )
    breakfast = Task(
        "Serve breakfast", demo_day.replace(hour=7, minute=30), 10,
        frequency="daily", priority="High",
    )
    mochi.add_task(grooming)
    mochi.add_task(breakfast)
    mochi.add_task(Task("Give medication", demo_day.replace(hour=12), 5, priority="High"))
    biscuit.add_task(Task("Vet appointment", demo_day.replace(hour=15), 45, priority="High"))
    biscuit.add_task(Task("Morning walk", demo_day.replace(hour=7, minute=30), 30))
    biscuit.add_task(Task("Serve dinner", demo_day.replace(hour=17, minute=30), 10))

    scheduler = Scheduler(owner)
    print(f"Today's Schedule — {demo_day:%Y-%m-%d}")
    print_schedule(scheduler.sort_by_time())

    print("\nFiltered schedule — Mochi, pending, High priority")
    print_schedule(
        scheduler.filter_tasks(
            pet_name="mochi", due_on=demo_day.date(), completed=False, priority="High"
        )
    )

    print("\nScheduling conflicts")
    for (first_pet, first_task), (second_pet, second_task) in scheduler.detect_conflicts():
        print(
            f"Warning: {first_task.due_at:%Y-%m-%d %H:%M} | "
            f"{first_pet.name} — {first_task.description} conflicts with "
            f"{second_pet.name} — {second_task.description}"
        )

    print("\nRecurring tasks")
    for task in (breakfast, grooming):
        next_task = scheduler.mark_task_complete(mochi.pet_id, task.task_id)
        print(f"Completed: {mochi.name} — {task.description} ({task.frequency})")
        if next_task is not None:
            print(f"Next occurrence: {next_task.due_at:%Y-%m-%d %H:%M}")

    print("\nCompleted task history")
    print_schedule(scheduler.filter_tasks(completed=True))


if __name__ == "__main__":
    main()
