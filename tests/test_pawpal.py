"""Tests for the PawPal+ entities and chronological schedule."""

import json
from datetime import datetime

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task

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
