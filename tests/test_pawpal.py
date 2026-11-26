"""Tests for the PawPal+ entities and scheduling algorithms."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from pawpal_system import Frequency, Owner, Pet, Scheduler, Task

DEMO_DAY = datetime(2026, 1, 15)


def test_mark_task_complete() -> None:
    task = Task("Serve breakfast", DEMO_DAY, 10)

    assert task.completed is False
    task.mark_complete()

    assert task.completed is True


def test_add_find_and_remove_task() -> None:
    pet = Pet("Mochi", "cat")
    task = Task("Serve breakfast", DEMO_DAY, 10)

    pet.add_task(task)

    assert pet.list_tasks() == [task]
    assert pet.find_task(task.task_id) is task
    assert pet.remove_task(task.task_id) is task
    assert pet.find_task(task.task_id) is None
    assert pet.remove_task(task.task_id) is None


def test_add_multiple_pets_to_owner() -> None:
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "cat")
    biscuit = Pet("Biscuit", "dog")

    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    assert owner.list_pets() == [mochi, biscuit]
    assert owner.find_pet(biscuit.pet_id) is biscuit
    assert owner.remove_pet(mochi.pet_id) is mochi
    assert owner.find_pet(mochi.pet_id) is None
    assert owner.remove_pet(mochi.pet_id) is None
    assert owner.list_pets() == [biscuit]


def test_retrieve_tasks_across_pets() -> None:
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "cat")
    biscuit = Pet("Biscuit", "dog")
    feeding = Task("Serve breakfast", DEMO_DAY, 10)
    walk = Task("Morning walk", DEMO_DAY, 30)
    owner.add_pet(mochi)
    owner.add_pet(biscuit)
    mochi.add_task(feeding)
    biscuit.add_task(walk)

    assert owner.get_all_tasks() == [(mochi, feeding), (biscuit, walk)]


def test_sort_current_tasks_chronologically() -> None:
    owner = Owner("Jordan")
    scheduler = Scheduler(owner)
    assert scheduler.sort_chronologically() == []

    mochi = Pet("Mochi", "cat")
    biscuit = Pet("Biscuit", "dog")
    owner.add_pet(mochi)
    owner.add_pet(biscuit)
    grooming = Task("Brush coat", DEMO_DAY.replace(hour=18), 10)
    walk = Task("Morning walk", DEMO_DAY.replace(hour=8), 30)
    feeding = Task("Serve breakfast", DEMO_DAY.replace(hour=7), 10)
    mochi.add_task(grooming)
    mochi.add_task(feeding)
    biscuit.add_task(walk)

    assert scheduler.sort_chronologically() == [
        (mochi, feeding),
        (biscuit, walk),
        (mochi, grooming),
    ]
    assert mochi.list_tasks() == [grooming, feeding]

    owner.remove_pet(biscuit.pet_id)
    assert scheduler.sort_chronologically() == [(mochi, feeding), (mochi, grooming)]


def test_task_serialization_and_unique_ids() -> None:
    task = Task("Give medication", DEMO_DAY, 5, frequency="daily", priority="High")
    another = Task("Give medication", DEMO_DAY, 5)
    task.mark_complete()

    assert task.task_id != another.task_id
    assert json.loads(json.dumps(task.to_dict())) == {
        "task_id": str(task.task_id),
        "description": "Give medication",
        "due_at": DEMO_DAY.isoformat(),
        "duration_minutes": 5,
        "completed": True,
        "frequency": "daily",
        "priority": "High",
    }


def test_reject_duplicate_task_ids() -> None:
    task = Task("Serve breakfast", DEMO_DAY, 10)
    duplicate = Task("Serve dinner", DEMO_DAY, 10, task_id=task.task_id)
    pet = Pet("Mochi", "cat", tasks=[task])

    with pytest.raises(ValueError, match="Duplicate task ID"):
        pet.add_task(duplicate)
    with pytest.raises(ValueError, match="Duplicate task ID"):
        Pet("Mochi", "cat", tasks=[task, duplicate])

    assert pet.list_tasks() == [task]


@pytest.mark.parametrize(
    ("field_name", "value", "error"),
    [
        ("description", "   ", ValueError),
        ("due_at", "2026-01-15", TypeError),
        ("duration_minutes", 0, ValueError),
        ("duration_minutes", -5, ValueError),
        ("duration_minutes", 1.5, TypeError),
        ("duration_minutes", True, TypeError),
        ("completed", "yes", TypeError),
        ("frequency", "monthly", ValueError),
        ("priority", "Urgent", ValueError),
    ],
)
def test_reject_invalid_task_fields(
    field_name: str, value: object, error: type[Exception]
) -> None:
    fields: dict[str, object] = {
        "description": "Serve breakfast",
        "due_at": DEMO_DAY,
        "duration_minutes": 10,
    }
    fields[field_name] = value

    with pytest.raises(error, match=field_name):
        Task(**fields)


def test_sort_by_time_uses_full_datetime_and_keeps_ties_stable() -> None:
    earlier = Task("Feed", DEMO_DAY.replace(hour=17, second=1), 5)
    first_tie = Task("Walk", DEMO_DAY.replace(hour=17, second=2), 15)
    second_tie = Task("Brush", first_tie.due_at, 5)
    tomorrow = Task("Groom", (DEMO_DAY + timedelta(days=1)).replace(hour=8), 10)
    cat = Pet("Mochi", "cat", tasks=[tomorrow, first_tie])
    dog = Pet("Biscuit", "dog", tasks=[second_tie, earlier])
    scheduler = Scheduler(Owner("Jordan", pets=[cat, dog]))

    assert scheduler.sort_by_time() == [
        (dog, earlier), (cat, first_tie), (dog, second_tie), (cat, tomorrow)
    ]
    assert cat.list_tasks() == [tomorrow, first_tie]
    assert dog.list_tasks() == [second_tie, earlier]
    assert Scheduler(Owner("Jordan")).sort_by_time() == []


def test_filter_tasks_combines_filters_and_supports_shared_pet_names() -> None:
    due_at = DEMO_DAY.replace(hour=9)
    feeding = Task("Feed", due_at, 5, priority="High")
    grooming = Task("Groom", due_at.replace(hour=8), 10, priority="High")
    done = Task("Walk", due_at, 15, completed=True, priority="High")
    lower_priority = Task("Brush", due_at, 5, priority="Low")
    other_date = Task("Vet", due_at + timedelta(days=1), 30, priority="High")
    cat = Pet("Mochi", "cat", tasks=[feeding, lower_priority])
    dog = Pet("Mochi", "dog", tasks=[grooming, done, other_date])
    another_pet = Pet("Biscuit", "dog", tasks=[Task("Feed", due_at, 5, priority="High")])
    scheduler = Scheduler(Owner("Jordan", pets=[cat, dog, another_pet]))

    assert scheduler.filter_tasks(
        pet_name="  moCHi  ", due_on=due_at.date(), completed=False, priority="High"
    ) == [(dog, grooming), (cat, feeding)]
    assert scheduler.filter_tasks(pet_id=dog.pet_id, completed=True) == [(dog, done)]
    assert scheduler.filter_tasks(pet_id=cat.pet_id, pet_name="Biscuit") == []
    assert scheduler.filter_tasks(pet_id=uuid4()) == []
    assert (dog, done) in scheduler.filter_tasks()
    assert (dog, done) not in scheduler.filter_tasks(completed=False)


@pytest.mark.parametrize(("frequency", "days"), [("daily", 1), ("weekly", 7)])
def test_complete_recurring_task_keeps_original_and_adds_one_successor(
    frequency: Frequency, days: int
) -> None:
    # The overdue scheduled time still determines the next occurrence.
    due_at = datetime(2000, 2, 28, 7, 45, 30)
    original = Task("Medication", due_at, 5, frequency=frequency, priority="High")
    cat = Pet("Mochi", "cat", tasks=[original])
    dog = Pet("Biscuit", "dog")
    owner = Owner("Jordan", pets=[cat, dog])
    scheduler = Scheduler(owner)

    successor = scheduler.mark_task_complete(cat.pet_id, original.task_id)

    assert successor is not None
    assert successor.due_at == due_at + timedelta(days=days)
    assert successor.task_id != original.task_id
    assert successor.completed is False
    assert (successor.description, successor.priority, successor.duration_minutes) == (
        original.description, original.priority, original.duration_minutes
    )
    assert successor.frequency == original.frequency
    assert original.completed and original.due_at == due_at
    assert cat.list_tasks() == [original, successor]
    assert dog.list_tasks() == []

    assert Scheduler(owner).mark_task_complete(cat.pet_id, original.task_id) is None
    assert cat.list_tasks() == [original, successor]
    following = scheduler.mark_task_complete(cat.pet_id, successor.task_id)
    assert following is not None
    assert following.due_at == successor.due_at + timedelta(days=days)
    assert scheduler.filter_tasks(completed=True) == [(cat, original), (cat, successor)]


def test_finish_one_time_task_and_reject_unknown_pet_or_task() -> None:
    task = Task("Vet appointment", DEMO_DAY, 30)
    cat = Pet("Mochi", "cat", tasks=[task])
    dog = Pet("Biscuit", "dog")
    scheduler = Scheduler(Owner("Jordan", pets=[cat, dog]))

    with pytest.raises(ValueError, match="no longer registered"):
        scheduler.mark_task_complete(uuid4(), task.task_id)
    with pytest.raises(ValueError, match="no longer available"):
        scheduler.mark_task_complete(dog.pet_id, task.task_id)
    assert not task.completed
    assert scheduler.mark_task_complete(cat.pet_id, task.task_id) is None
    assert scheduler.mark_task_complete(cat.pet_id, task.task_id) is None
    assert task.completed
    assert cat.list_tasks() == [task]


def test_failed_recurrence_keeps_original_pending() -> None:
    task = Task("Feed", datetime.max, 5, frequency="daily")
    pet = Pet("Mochi", "cat", tasks=[task])
    scheduler = Scheduler(Owner("Jordan", pets=[pet]))

    with pytest.raises(OverflowError):
        scheduler.mark_task_complete(pet.pet_id, task.task_id)

    assert not task.completed
    assert pet.list_tasks() == [task]


def test_concurrent_completion_requests_share_the_same_history() -> None:
    original = Task("Feed", DEMO_DAY, 5, frequency="daily")
    pet = Pet("Mochi", "cat", tasks=[original])
    owner = Owner("Jordan", pets=[pet])
    first = Scheduler(owner)
    second = Scheduler(owner)

    with ThreadPoolExecutor(max_workers=2) as executor:
        requests = [
            executor.submit(scheduler.mark_task_complete, pet.pet_id, original.task_id)
            for scheduler in (first, second)
        ]
        occurrences = [request.result() for request in requests]

    assert sum(occurrence is not None for occurrence in occurrences) == 1
    assert original.completed
    assert len(pet.list_tasks()) == 2


def test_detect_conflicts_pairs_only_pending_tasks_at_the_same_full_datetime() -> None:
    due_at = DEMO_DAY.replace(hour=8)
    feeding = Task("Feed", due_at, 10)
    grooming = Task("Groom", due_at, 15)
    walk = Task("Walk", due_at, 20)
    done = Task("Medication", due_at, 5, completed=True)
    overlapping = Task("Brush", due_at + timedelta(seconds=1), 5)
    tomorrow = Task("Feed", due_at + timedelta(days=1), 10)
    cat = Pet("Mochi", "cat", tasks=[feeding, grooming, done])
    dog = Pet("Biscuit", "dog", tasks=[walk, overlapping, tomorrow])
    scheduler = Scheduler(Owner("Jordan", pets=[cat, dog]))

    assert scheduler.detect_conflicts() == [
        ((cat, feeding), (cat, grooming)),
        ((cat, feeding), (dog, walk)),
        ((cat, grooming), (dog, walk)),
    ]

    for pet, task in ((cat, feeding), (cat, grooming)):
        scheduler.mark_task_complete(pet.pet_id, task.task_id)
    assert scheduler.detect_conflicts() == []
    assert Scheduler(Owner("Jordan")).detect_conflicts() == []


def test_sort_and_conflict_detection_compare_aware_times_by_instant() -> None:
    utc = DEMO_DAY.replace(hour=14, tzinfo=timezone.utc)
    eastern = timezone(timedelta(hours=-5))
    same_instant = Task("Feed", utc.astimezone(eastern), 10)
    later_instant = Task("Groom", utc.replace(tzinfo=eastern), 15)
    original = Task("Walk", utc, 10)
    cat = Pet("Mochi", "cat", tasks=[later_instant, same_instant])
    dog = Pet("Biscuit", "dog", tasks=[original])
    scheduler = Scheduler(Owner("Jordan", pets=[cat, dog]))

    assert scheduler.sort_by_time() == [(cat, same_instant), (dog, original), (cat, later_instant)]
    assert scheduler.detect_conflicts() == [((cat, same_instant), (dog, original))]
