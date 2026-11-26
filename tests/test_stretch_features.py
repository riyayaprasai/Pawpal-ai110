"""Tests for slot suggestions, persistence, priority order, and formatting."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from main import format_table, main
from pawpal_system import Owner, Pet, Scheduler, Task, load_from_json, save_to_json

DAY = datetime(2026, 1, 15)


def test_slot_skips_overlapping_and_adjacent_tasks_across_pets() -> None:
    cat = Pet("Mochi", "Cat", tasks=[
        Task("Appointment", DAY.replace(hour=9, minute=40), 20),
        Task("Feed", DAY.replace(hour=8, minute=45), 45),
    ])
    dog = Pet("Biscuit", "Dog", tasks=[
        Task("Walk", DAY.replace(hour=9, minute=20), 20),
        Task("Completed grooming", DAY.replace(hour=10), 60, completed=True),
    ])
    scheduler = Scheduler(Owner("Jordan", pets=[cat, dog]))
    before = [pet.list_tasks() for pet in (cat, dog)]

    assert scheduler.find_next_available_slot(
        DAY.replace(hour=9), DAY.replace(hour=10, minute=30), 30
    ) == DAY.replace(hour=10)
    assert [pet.list_tasks() for pet in (cat, dog)] == before


def test_slot_can_end_at_busy_start_but_rejects_unavailable_duration() -> None:
    busy = Task("Walk", DAY.replace(hour=9, minute=30), 60)
    scheduler = Scheduler(Owner("Jordan", pets=[Pet("Biscuit", "Dog", tasks=[busy])]))
    start = DAY.replace(hour=9)
    end = DAY.replace(hour=11)

    assert scheduler.find_next_available_slot(start, end, 30) == start
    assert scheduler.find_next_available_slot(start, end, 31) is None


def test_slot_handles_empty_schedule_and_exact_window_end() -> None:
    scheduler = Scheduler(Owner("Jordan"))
    start = DAY.replace(hour=9)
    end = start + timedelta(minutes=20)

    assert scheduler.find_next_available_slot(start, end, 20) == start
    assert scheduler.find_next_available_slot(start, end, 21) is None


def test_slot_compares_aware_intervals_and_returns_window_timezone() -> None:
    offset = timezone(timedelta(hours=-5))
    start = DAY.replace(hour=9, tzinfo=offset)
    occupied = Task("Walk", start.astimezone(timezone.utc), 30)
    scheduler = Scheduler(Owner("Jordan", pets=[Pet("Biscuit", "Dog", tasks=[occupied])]))

    slot = scheduler.find_next_available_slot(start, start + timedelta(hours=1), 30)

    assert slot == start + timedelta(minutes=30)
    assert slot.tzinfo is offset
    with pytest.raises(ValueError, match="pending tasks"):
        scheduler.find_next_available_slot(DAY, DAY + timedelta(days=1), 30)


@pytest.mark.parametrize(("duration", "error"), [(0, ValueError), (-1, ValueError), (True, TypeError), (2.5, TypeError)])
def test_slot_rejects_invalid_duration(duration: int, error: type[Exception]) -> None:
    with pytest.raises(error, match="Duration"):
        Scheduler(Owner("Jordan")).find_next_available_slot(DAY, DAY + timedelta(hours=1), duration)


def test_slot_rejects_invalid_windows() -> None:
    scheduler = Scheduler(Owner("Jordan"))
    with pytest.raises(ValueError, match="must be after"):
        scheduler.find_next_available_slot(DAY, DAY, 10)
    with pytest.raises(ValueError, match="must be after"):
        scheduler.find_next_available_slot(DAY, DAY - timedelta(hours=1), 10)
    with pytest.raises(ValueError, match="time zones"):
        scheduler.find_next_available_slot(DAY, DAY.replace(tzinfo=timezone.utc), 10)


def test_priority_order_spans_pets_and_breaks_ties_by_due_datetime() -> None:
    low = Task("Brush", DAY, 15, priority="Low")
    high_late = Task("Medicine", DAY.replace(hour=17), 5, priority="High")
    high_early = Task("Vet", DAY.replace(hour=8), 20, priority="High")
    medium = Task("Walk", DAY.replace(hour=7), 15, priority="Medium")
    cat = Pet("Mochi", "Cat", tasks=[low, high_late])
    dog = Pet("Biscuit", "Dog", tasks=[high_early, medium])
    scheduler = Scheduler(Owner("Jordan", pets=[cat, dog]))

    assert scheduler.sort_by_priority() == [
        (dog, high_early), (cat, high_late), (dog, medium), (cat, low),
    ]
    assert scheduler.sort_by_priority(scheduler.filter_tasks(pet_id=cat.pet_id)) == [
        (cat, high_late), (cat, low),
    ]
    assert scheduler.sort_by_priority([]) == []
    assert cat.list_tasks() == [low, high_late]
    assert dog.list_tasks() == [high_early, medium]


def test_json_round_trip_restores_entities_relationships_and_history(tmp_path: Path) -> None:
    original = Task("Médecine", DAY.replace(tzinfo=timezone.utc), 5, frequency="daily", priority="High")
    cat = Pet("Mochi", "Cat", tasks=[original])
    dog = Pet("Mochi", "Dog", tasks=[Task("Walk", DAY, 30, priority="Low")])
    owner = Owner("Jordan", pets=[cat, dog])
    Scheduler(owner).mark_task_complete(cat.pet_id, original.task_id)
    path = tmp_path / "nested" / "data.json"

    save_to_json(owner, path)
    restored = load_from_json(str(path))

    assert isinstance(restored, Owner)
    assert restored == owner
    assert restored is not owner
    restored_cat, restored_dog = restored.list_pets()
    assert isinstance(restored_cat, Pet)
    assert isinstance(restored_cat.list_tasks()[0], Task)
    assert restored_cat.pet_id != restored_dog.pet_id
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["pets"][0]["tasks"][0]["due_at"] == original.due_at.isoformat()

    restored.rename("New name")
    save_to_json(restored, path, expected_owner=owner)
    assert load_from_json(path) == restored
    assert list(path.parent.iterdir()) == [path]


def test_missing_json_is_not_created_by_loading(tmp_path: Path) -> None:
    path = tmp_path / "missing" / "data.json"
    assert load_from_json(path) is None
    assert not path.parent.exists()


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("{broken", "Malformed JSON"),
        ("{}", "Invalid PawPal\\+ data"),
        ('{"pets": "wrong"}', "Pets must be an array"),
        ('{"pets": [{"tasks": [null]}]}', "Task must be an object"),
    ],
)
def test_invalid_json_is_reported_and_left_intact(tmp_path: Path, contents: str, message: str) -> None:
    path = tmp_path / "data.json"
    path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_from_json(path)
    with pytest.raises(ValueError, match=message):
        save_to_json(Owner("Jordan"), path)

    assert path.read_text(encoding="utf-8") == contents


def test_failed_replacement_keeps_the_previous_saved_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "data.json"
    before = Owner("Jordan")
    save_to_json(before, path)

    def fail_replacement(self: Path, target: Path) -> None:
        raise OSError("Disk write failed")

    monkeypatch.setattr(Path, "replace", fail_replacement)
    with pytest.raises(OSError, match="Disk write failed"):
        save_to_json(Owner("New name"), path)

    assert load_from_json(path) == before
    assert list(tmp_path.iterdir()) == [path]


def test_save_rejects_a_stale_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    original = Owner("Jordan")
    save_to_json(original, path)
    latest = Owner("Sam", owner_id=original.owner_id)
    save_to_json(latest, path, expected_owner=original)

    with pytest.raises(ValueError, match="another session"):
        save_to_json(Owner("Stale", owner_id=original.owner_id), path, expected_owner=original)

    assert load_from_json(path) == latest


def test_format_table_aligns_columns_without_trailing_spaces() -> None:
    table = format_table(("Pet", "Task"), [("Mochi", "Walk"), ("Biscuit", "Feed")])

    assert table.splitlines() == [
        "Pet     | Task",
        "--------+-----",
        "Mochi   | Walk",
        "Biscuit | Feed",
    ]


def test_demo_is_reproducible_and_keeps_live_data_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    live_path = tmp_path / "data" / "data.json"
    live_path.parent.mkdir()
    live_path.write_text("sentinel", encoding="utf-8")

    main()
    first = capsys.readouterr().out
    main()
    second = capsys.readouterr().out

    assert first == second
    assert "=== Core scheduling ===" in first
    assert "=== Stretch features ===" in first
    assert "WARNING" in first and "Earliest start: Thu, Jan 15, 2026 08:00" in first
    assert "Restored Jordan, 2 pets, and 8 tasks with their original IDs." in first
    assert live_path.read_text(encoding="utf-8") == "sentinel"


def test_save_detects_a_changed_offset_even_when_the_instant_is_equal(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    original = Task("Feed", datetime(2026, 1, 16, 0, 30, tzinfo=timezone.utc), 20)
    pet = Pet("Mochi", "Cat", tasks=[original])
    owner = Owner("Jordan", pets=[pet])
    save_to_json(owner, path)
    previous = load_from_json(path)
    assert previous is not None

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["pets"][0]["tasks"][0]["due_at"] = "2026-01-15T19:30:00-05:00"
    updated = json.dumps(payload)
    path.write_text(updated, encoding="utf-8")

    with pytest.raises(ValueError, match="saved data changed"):
        save_to_json(Owner("Stale edit", owner_id=owner.owner_id), path, expected_owner=previous)

    assert path.read_text(encoding="utf-8") == updated


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_invalid_json_numeric_literals_are_rejected_and_preserved(
    tmp_path: Path, literal: str
) -> None:
    path = tmp_path / "data.json"
    owner = Owner("Jordan")
    save_to_json(owner, path)
    malformed = path.read_text(encoding="utf-8").replace(
        '"pets": []', f'"pets": [], "extra": {literal}'
    )
    path.write_text(malformed, encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON numeric literal"):
        load_from_json(path)
    with pytest.raises(ValueError, match="Invalid JSON numeric literal"):
        save_to_json(owner, path)

    assert path.read_text(encoding="utf-8") == malformed
