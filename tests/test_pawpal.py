"""Tests for the PawPal+ entities and scheduling algorithms."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from streamlit.testing.v1 import AppTest

import app as streamlit_app
import main as demo
import pawpal_system
from pawpal_system import Frequency, Owner, Pet, Scheduler, Task, load_from_json, save_to_json

DEMO_DAY = datetime(2026, 1, 15)
LIVE_DATA_PATH = pawpal_system.DEFAULT_DATA_PATH


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


def test_task_initialization_and_entity_collections_are_independent() -> None:
    task = Task("Feed", DEMO_DAY, 12)
    cat, dog = Pet("Mochi", "cat"), Pet("Biscuit", "dog", tasks=[task])
    owner, another_owner = Owner("Jordan"), Owner("Sam", pets=[dog])

    assert isinstance(task.task_id, UUID)
    assert (task.description, task.due_at, task.duration_minutes) == ("Feed", DEMO_DAY, 12)
    assert (task.completed, task.frequency, task.priority) == (False, "once", "Medium")
    owner.add_pet(cat)
    cat.add_task(task)
    cat.list_tasks().clear()
    owner.list_pets().clear()
    assert owner.list_pets() == [cat]
    assert cat.list_tasks() == dog.list_tasks() == [task]
    cat.remove_task(task.task_id)
    assert another_owner.get_all_tasks() == [(dog, task)]


def test_duplicate_pet_id_is_rejected_without_replacing_original() -> None:
    cat = Pet("Mochi", "cat")
    duplicate = Pet("Biscuit", "dog", pet_id=cat.pet_id)
    owner = Owner("Jordan", pets=[cat])

    with pytest.raises(ValueError, match="Duplicate pet ID"):
        owner.add_pet(duplicate)
    with pytest.raises(ValueError, match="Duplicate pet ID"):
        Owner("Jordan", pets=[cat, duplicate])

    assert owner.find_pet(cat.pet_id) is cat
    assert owner.list_pets() == [cat]


@pytest.mark.parametrize(
    ("frequency", "due_at", "expected"),
    [
        ("daily", datetime(2024, 2, 29, 8, 15), datetime(2024, 3, 1, 8, 15)),
        ("daily", datetime(2025, 12, 31, 8, 15), datetime(2026, 1, 1, 8, 15)),
        ("weekly", datetime(2025, 12, 29, 8, 15), datetime(2026, 1, 5, 8, 15)),
    ],
)
def test_recurring_task_crosses_calendar_boundaries(
    frequency: Frequency, due_at: datetime, expected: datetime
) -> None:
    original = Task("Medication", due_at, 10, frequency=frequency)
    pet = Pet("Mochi", "cat", tasks=[original])
    scheduler = Scheduler(Owner("Jordan", pets=[pet]))

    successor = scheduler.mark_task_complete(pet.pet_id, original.task_id)

    assert successor is not None
    assert successor.due_at == expected


def test_slot_uses_exact_gap_between_two_pets_without_rounding() -> None:
    start = DEMO_DAY.replace(hour=9, second=17, microsecond=1)
    walk = Task("Walk", start, 30)
    vet = Task("Vet", start + timedelta(minutes=50), 20)
    cat = Pet("Mochi", "cat", tasks=[walk])
    dog = Pet("Biscuit", "dog", tasks=[vet])
    scheduler = Scheduler(Owner("Jordan", pets=[dog, cat]))
    end = start + timedelta(minutes=70)

    assert scheduler.find_next_available_slot(start, end, 20) == start + timedelta(minutes=30)
    assert scheduler.find_next_available_slot(start, end, 21) is None


def test_slot_search_agrees_with_independent_minute_grid_oracle() -> None:
    start = DEMO_DAY.replace(hour=9)
    cat = Pet("Mochi", "cat", tasks=[
        Task("Feeding", start + timedelta(minutes=5), 4),
        Task("Grooming", start + timedelta(minutes=17), 5),
    ])
    dog = Pet("Biscuit", "dog", tasks=[
        Task("Walk", start - timedelta(minutes=3), 5),
        Task("Medication", start + timedelta(minutes=8), 3),
        Task("Training", start + timedelta(minutes=11), 3),
        Task("Completed vet visit", start + timedelta(minutes=14), 3, completed=True),
    ])
    occupied = {-3, -2, -1, 0, 1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17, 18, 19, 20, 21}
    scheduler = Scheduler(Owner("Jordan", pets=[cat, dog]))

    for start_minute in range(8):
        for end_minute in range(15, 26):
            for duration in range(1, 8):
                fitting_minute = next((
                    minute for minute in range(start_minute, end_minute - duration + 1)
                    if occupied.isdisjoint(range(minute, minute + duration))
                ), None)
                expected = None if fitting_minute is None else start + timedelta(minutes=fitting_minute)
                assert scheduler.find_next_available_slot(
                    start + timedelta(minutes=start_minute),
                    start + timedelta(minutes=end_minute),
                    duration,
                ) == expected


def test_retrying_completion_after_reload_does_not_add_an_occurrence(tmp_path: Path) -> None:
    original = Task("Feed", DEMO_DAY, 5, frequency="daily", priority="High")
    pet = Pet("Mochi", "cat", tasks=[original])
    owner = Owner("Jordan", pets=[pet, Pet("Biscuit", "dog")])
    successor = Scheduler(owner).mark_task_complete(pet.pet_id, original.task_id)
    assert successor is not None
    path = tmp_path / "history.json"
    save_to_json(owner, path)

    restored = load_from_json(path)

    assert restored is not None
    assert Scheduler(restored).mark_task_complete(pet.pet_id, original.task_id) is None
    saved_pet = restored.find_pet(pet.pet_id)
    assert saved_pet is not None
    assert saved_pet.list_tasks() == [original, successor]


def test_deleted_file_rejects_save_from_stale_session(tmp_path: Path) -> None:
    path = tmp_path / "deleted.json"
    original = Owner("Jordan")
    save_to_json(original, path)
    path.unlink()

    with pytest.raises(ValueError, match="changed"):
        save_to_json(Owner("Sam"), path, expected_owner=original)

    assert not path.exists()


def test_date_only_task_timestamp_is_rejected_and_preserved(tmp_path: Path) -> None:
    path = tmp_path / "date-only.json"
    owner = Owner("Jordan", pets=[Pet("Mochi", "cat", tasks=[Task("Feed", DEMO_DAY, 5)])])
    save_to_json(owner, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["pets"][0]["tasks"][0]["due_at"] = "2026-01-15"
    invalid = json.dumps(payload)
    path.write_text(invalid, encoding="utf-8")

    with pytest.raises(ValueError, match="due_at"):
        load_from_json(path)
    with pytest.raises(ValueError, match="due_at"):
        save_to_json(owner, path)

    assert path.read_text(encoding="utf-8") == invalid


def test_ambiguous_duplicate_json_fields_cannot_be_silently_replaced(tmp_path: Path) -> None:
    path = tmp_path / "duplicate-keys.json"
    owner = Owner("Jordan")
    save_to_json(owner, path)
    text = path.read_text(encoding="utf-8").replace(
        '"name": "Jordan"', '"name": "Jordan", "name": "Sam"'
    )
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate JSON field"):
        load_from_json(path)
    with pytest.raises(ValueError, match="Duplicate JSON field"):
        save_to_json(owner, path)

    assert path.read_text(encoding="utf-8") == text


def test_cli_persistence_only_uses_temporary_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    live = tmp_path / "data.json"
    live.write_text("untouched", encoding="utf-8")
    monkeypatch.setattr(pawpal_system, "DEFAULT_DATA_PATH", live)
    paths = []

    def save_demo(owner: Owner, path: Path) -> None:
        assert path.resolve() != live.resolve()
        assert path.resolve() != LIVE_DATA_PATH.resolve()
        paths.append(path)
        save_to_json(owner, path)

    monkeypatch.setattr(demo, "save_to_json", save_demo)
    demo.main()
    assert len(paths) == 1 and not paths[0].exists()
    assert "temporary round trip" in capsys.readouterr().out
    assert live.read_text(encoding="utf-8") == "untouched"


def render_test_app() -> None:
    from datetime import date

    from app import main

    main(today=date(2026, 1, 15))


@pytest.fixture
def app_data_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "data.json"
    monkeypatch.setattr(streamlit_app, "DEFAULT_DATA_PATH", path)
    return path


def submit_app_form(app: AppTest, label: str) -> None:
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception, [error.message for error in app.exception]


def test_streamlit_saves_pet_task_and_recurring_completion(app_data_path: Path) -> None:
    app = AppTest.from_function(render_test_app).run()
    assert not app.exception and not app_data_path.exists()
    assert [metric.value for metric in app.metric] == ["0", "0", "0"]

    app.text_input(key="pet_name").set_value("Mochi")
    submit_app_form(app, "Add pet")
    saved = load_from_json(app_data_path)
    assert saved is not None
    pet, = saved.list_pets()
    app.selectbox(key="task_pet_id").select(pet.pet_id).run()
    app.text_input(key="task_description").set_value("Medication")
    app.date_input(key="task_date").set_value(date(2025, 12, 31))
    app.time_input(key="task_time").set_value(time(9))
    app.selectbox(key="task_frequency").select("daily")
    submit_app_form(app, "Add task")

    saved = load_from_json(app_data_path)
    assert saved is not None
    original, = saved.list_pets()[0].list_tasks()
    app.selectbox(key=f"pending_task_{pet.pet_id}").select(original.task_id)
    submit_app_form(app, "Mark complete")

    fresh = AppTest.from_function(render_test_app).run()
    assert not fresh.exception
    assert [metric.value for metric in fresh.metric] == ["1", "1", "1"]
    completed, successor = fresh.session_state["owner"].list_pets()[0].list_tasks()
    assert completed.task_id == original.task_id and completed.completed
    assert successor.due_at == datetime(2026, 1, 1, 9)
    assert successor.task_id != completed.task_id


def test_streamlit_aware_schedule_keeps_new_tasks_comparable_and_shows_exact_slot(
    app_data_path: Path,
) -> None:
    due_at = DEMO_DAY.replace(hour=9, second=15, tzinfo=timezone.utc)
    pet = Pet("Mochi", "cat", tasks=[Task("Vet", due_at, 30)])
    save_to_json(Owner("Jordan", pets=[pet]), app_data_path)
    app = AppTest.from_function(render_test_app).run()
    assert not app.exception

    for widget in app.date_input:
        widget.set_value(due_at.date())
    for widget in app.time_input:
        widget.set_value(time(9) if widget.label == "Earliest start time" else time(11))
    submit_app_form(app, "Find slot")
    assert any("09:30:15" in message.value and "UTC" in message.value for message in app.success)

    app.selectbox(key="task_pet_id").select(pet.pet_id).run()
    app.text_input(key="task_description").set_value("Follow-up")
    app.date_input(key="task_date").set_value(due_at.date())
    app.time_input(key="task_time").set_value(time(11))
    submit_app_form(app, "Add task")
    restored = load_from_json(app_data_path)
    assert restored is not None
    assert [task.due_at for _, task in Scheduler(restored).sort_by_time()] == [
        due_at, due_at.replace(hour=11, second=0),
    ]


def test_streamlit_mixed_saved_datetimes_show_readable_error_without_writing(
    app_data_path: Path,
) -> None:
    tasks = [
        Task("Feed", DEMO_DAY, 5),
        Task("Vet", DEMO_DAY.replace(tzinfo=timezone.utc), 30),
    ]
    save_to_json(Owner("Jordan", pets=[Pet("Mochi", "cat", tasks=tasks)]), app_data_path)
    before = app_data_path.read_bytes()

    app = AppTest.from_function(render_test_app).run()

    assert not app.exception
    assert any("timezone-aware and timezone-naive" in error.value for error in app.error)
    assert app_data_path.read_bytes() == before


def test_streamlit_stale_session_cannot_overwrite_another_sessions_first_save(
    app_data_path: Path,
) -> None:
    first = AppTest.from_function(render_test_app).run()
    stale = AppTest.from_function(render_test_app).run()
    assert not first.exception and not stale.exception
    assert not app_data_path.exists()

    first.text_input(key="pet_name").set_value("Mochi")
    submit_app_form(first, "Add pet")
    saved = app_data_path.read_bytes()

    stale.text_input(key="pet_name").set_value("Biscuit")
    submit_app_form(stale, "Add pet")
    assert any("saved data changed" in warning.value for warning in stale.warning)
    assert not stale.success
    assert [metric.value for metric in stale.metric] == ["0", "0", "0"]
    assert app_data_path.read_bytes() == saved


def test_streamlit_schedule_orders_filtered_tasks_and_keeps_cross_pet_warnings(
    app_data_path: Path,
) -> None:
    early = Task("Walk", DEMO_DAY.replace(hour=8), 30, priority="Low")
    feeding = Task("Feed", DEMO_DAY.replace(hour=9), 5, priority="Low")
    grooming = Task("Groom", DEMO_DAY.replace(hour=10), 10, priority="High")
    visit = Task("Vet", feeding.due_at, 20, priority="Medium")
    cat = Pet("Mochi", "cat", tasks=[feeding, grooming, early])
    dog = Pet("Biscuit", "dog", tasks=[visit])
    save_to_json(Owner("Jordan", pets=[cat, dog]), app_data_path)

    app = AppTest.from_function(render_test_app).run()
    assert not app.exception
    assert list(app.table[-1].value["Task"]) == ["Walk", "Feed", "Vet", "Groom"]

    app.selectbox(key="schedule_pet_id").select(cat.pet_id).run()
    app.selectbox(key="schedule_sort").select("Priority").run()

    assert not app.exception
    assert list(app.table[-1].value["Task"]) == ["Groom", "Walk", "Feed"]
    assert list(app.table[-1].value["Priority"]) == ["▲ High", "▼ Low", "▼ Low"]
    assert any("Mochi — Feed and Biscuit — Vet" in warning.value for warning in app.warning)
