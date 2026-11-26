"""Run a deterministic command-line demonstration of PawPal+."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from pawpal_system import Owner, Pet, PetTask, Scheduler, Task, load_from_json, save_to_json

DATE_TIME_FORMAT = "%a, %b %d, %Y %H:%M"


def format_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    """Build a plain-text table with consistent column widths."""
    widths = [max(len(row[index]) for row in [headers, *rows]) for index in range(len(headers))]

    def format_row(row: tuple[str, ...]) -> str:
        return " | ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()

    separator = "-+-".join("-" * width for width in widths)
    return "\n".join([format_row(headers), separator, *(format_row(row) for row in rows)])


def print_schedule(entries: list[PetTask]) -> None:
    """Print the scheduler's pet-task pairs as a readable table."""
    if not entries:
        print("No tasks to display.")
        return

    rows = [
        (
            task.due_at.strftime(DATE_TIME_FORMAT),
            pet.name,
            task.description,
            task.priority,
            "Completed" if task.completed else "Pending",
        )
        for pet, task in entries
    ]
    print(format_table(("Due", "Pet", "Task", "Priority", "Status"), rows))


def main() -> None:
    """Demonstrate core and stretch scheduling features without live data."""
    demo_day = datetime(2026, 1, 15)
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "cat")
    biscuit = Pet("Biscuit", "dog")
    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    grooming = Task("Brush coat", demo_day.replace(hour=18), 10, frequency="weekly", priority="Low")
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
    print("=== Core scheduling ===")
    print(f"\nToday's Schedule — {demo_day:%A, %B %d, %Y}")
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
            f"WARNING [{first_task.due_at:{DATE_TIME_FORMAT}}] "
            f"{first_pet.name}: {first_task.description} / "
            f"{second_pet.name}: {second_task.description} share a start time."
        )

    print("\nRecurring tasks")
    for task in (breakfast, grooming):
        next_task = scheduler.mark_task_complete(mochi.pet_id, task.task_id)
        print(f"Completed {mochi.name}'s {task.description.lower()} ({task.frequency}).")
        if next_task is not None:
            print(f"Next occurrence: {next_task.due_at:{DATE_TIME_FORMAT}}")

    print("\nCompleted task history")
    print_schedule(scheduler.filter_tasks(completed=True))

    print("\n=== Stretch features ===")
    print("\nNext available slot — 20 minutes between 07:30 and 09:00")
    slot = scheduler.find_next_available_slot(
        demo_day.replace(hour=7, minute=30), demo_day.replace(hour=9), 20
    )
    if slot is None:
        print("No available slot.")
    else:
        print(f"Earliest start: {slot:{DATE_TIME_FORMAT}}")

    print("\nPriority order — pending tasks")
    print_schedule(scheduler.sort_by_priority(scheduler.filter_tasks(completed=False)))

    print("\nJSON persistence — temporary round trip")
    with TemporaryDirectory() as directory:
        path = Path(directory) / "demo.json"
        save_to_json(owner, path)
        restored = load_from_json(path)
        if restored != owner:
            raise RuntimeError("The demo could not restore the saved schedule.")
        print(
            f"Restored {restored.name}, {len(restored.list_pets())} pets, and "
            f"{len(restored.get_all_tasks())} tasks with their original IDs."
        )


if __name__ == "__main__":
    main()
