"""PawPal+ domain entities and owner-wide scheduling."""

import json
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import Literal, get_args
from uuid import UUID, uuid4

Frequency = Literal["once", "daily", "weekly"]
Priority = Literal["Low", "Medium", "High"]
TaskData = dict[str, str | int | bool]

DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "data.json"

_completion_lock = Lock()
_persistence_lock = Lock()


def _require_nonblank(value: str, field_name: str) -> None:
    """Require text with at least one non-whitespace character."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be blank")


@dataclass
class Task:
    """A single pet-care task with a due time and recurrence frequency."""

    description: str
    due_at: datetime
    duration_minutes: int
    task_id: UUID = field(default_factory=uuid4)
    completed: bool = False
    frequency: Frequency = "once"
    priority: Priority = "Medium"

    def __post_init__(self) -> None:
        """Validate task fields after construction."""
        _require_nonblank(self.description, "description")
        if not isinstance(self.due_at, datetime):
            raise TypeError("due_at must be a datetime")
        if type(self.duration_minutes) is not int:
            raise TypeError("duration_minutes must be an integer")
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if not isinstance(self.task_id, UUID):
            raise TypeError("task_id must be a UUID")
        if not isinstance(self.completed, bool):
            raise TypeError("completed must be a boolean")
        if self.frequency not in get_args(Frequency):
            raise ValueError("frequency must be once, daily, or weekly")
        if self.priority not in get_args(Priority):
            raise ValueError("priority must be Low, Medium, or High")

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def to_dict(self) -> TaskData:
        """Return JSON-ready data with the ID and due time encoded as strings."""
        return {
            "task_id": str(self.task_id),
            "description": self.description,
            "due_at": self.due_at.isoformat(),
            "duration_minutes": self.duration_minutes,
            "completed": self.completed,
            "frequency": self.frequency,
            "priority": self.priority,
        }


@dataclass
class Pet:
    """A pet and the care tasks assigned to it."""

    name: str
    species: str
    pet_id: UUID = field(default_factory=uuid4)
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the pet and attach any initial tasks."""
        _require_nonblank(self.name, "name")
        _require_nonblank(self.species, "species")
        if not isinstance(self.pet_id, UUID):
            raise TypeError("pet_id must be a UUID")

        initial_tasks = self.tasks
        self.tasks = []
        for task in initial_tasks:
            self.add_task(task)

    def add_task(self, task: Task) -> None:
        """Attach a task, rejecting a duplicate ID in this pet's tasks."""
        if not isinstance(task, Task):
            raise TypeError("task must be a Task")
        if self.find_task(task.task_id) is not None:
            raise ValueError(f"Duplicate task ID: {task.task_id}")
        self.tasks.append(task)

    def list_tasks(self) -> list[Task]:
        """Return a shallow copy of this pet's task list."""
        return self.tasks.copy()

    def find_task(self, task_id: UUID) -> Task | None:
        """Return the task with this ID, or None if it is absent."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def remove_task(self, task_id: UUID) -> Task | None:
        """Remove and return the matching task, or None if it is absent."""
        for index, task in enumerate(self.tasks):
            if task.task_id == task_id:
                return self.tasks.pop(index)
        return None


@dataclass
class Owner:
    """A pet owner and the pets in their care."""

    name: str
    owner_id: UUID = field(default_factory=uuid4)
    pets: list[Pet] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the owner and attach any initial pets."""
        _require_nonblank(self.name, "name")
        if not isinstance(self.owner_id, UUID):
            raise TypeError("owner_id must be a UUID")

        initial_pets = self.pets
        self.pets = []
        for pet in initial_pets:
            self.add_pet(pet)

    def rename(self, name: str) -> None:
        """Update the owner's name after validating it."""
        _require_nonblank(name, "name")
        self.name = name

    def add_pet(self, pet: Pet) -> None:
        """Attach a pet, rejecting a duplicate ID in this owner's pets."""
        if not isinstance(pet, Pet):
            raise TypeError("pet must be a Pet")
        if self.find_pet(pet.pet_id) is not None:
            raise ValueError(f"Duplicate pet ID: {pet.pet_id}")
        self.pets.append(pet)

    def find_pet(self, pet_id: UUID) -> Pet | None:
        """Return the pet with this ID, or None if it is absent."""
        for pet in self.pets:
            if pet.pet_id == pet_id:
                return pet
        return None

    def list_pets(self) -> list[Pet]:
        """Return a shallow copy of this owner's pet list."""
        return self.pets.copy()

    def remove_pet(self, pet_id: UUID) -> Pet | None:
        """Remove and return the matching pet, or None if it is absent."""
        for index, pet in enumerate(self.pets):
            if pet.pet_id == pet_id:
                return self.pets.pop(index)
        return None

    def get_all_tasks(self) -> list["PetTask"]:
        """Return (pet, task) pairs across all pets belonging to this owner."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]


PetTask = tuple[Pet, Task]
TaskConflict = tuple[PetTask, PetTask]
PlannedTask = tuple[PetTask, datetime, str]  # Pair, proposed start, explanation.


def _datetime_key(value: datetime) -> datetime:
    """Use an absolute clock for aware datetimes and preserve local naive times."""
    if value.utcoffset() is not None:
        return value.astimezone(timezone.utc)
    return value


def _due_time_key(entry: PetTask) -> datetime:
    return _datetime_key(entry[1].due_at)


class Scheduler:
    """Read and update the owner's current schedule without storing a copy."""

    owner: Owner

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def sort_by_time(self) -> list[PetTask]:
        """Return pet-task pairs by due time, preserving insertion order for ties."""
        return sorted(self.owner.get_all_tasks(), key=_due_time_key)

    def sort_by_priority(self, entries: Iterable[PetTask] | None = None) -> list[PetTask]:
        """Order High, Medium, then Low, with earlier tasks first within each group."""
        ranks = {"High": 0, "Medium": 1, "Low": 2}
        if entries is None:
            entries = self.owner.get_all_tasks()
        return sorted(entries, key=lambda entry: (ranks[entry[1].priority], _due_time_key(entry)))

    def sort_chronologically(self) -> list[PetTask]:
        """Return the chronological schedule through the original method name."""
        return self.sort_by_time()

    def filter_tasks(
        self,
        *,
        pet_id: UUID | None = None,
        pet_name: str | None = None,
        due_on: date | None = None,
        completed: bool | None = None,
        priority: Priority | None = None,
    ) -> list[PetTask]:
        """Return sorted pairs matching every supplied filter."""
        name = pet_name.strip().casefold() if pet_name is not None else None
        matches = [
            (pet, task)
            for pet, task in self.owner.get_all_tasks()
            if (pet_id is None or pet.pet_id == pet_id)
            and (name is None or pet.name.strip().casefold() == name)
            and (due_on is None or task.due_at.date() == due_on)
            and (completed is None or task.completed == completed)
            and (priority is None or task.priority == priority)
        ]
        return sorted(matches, key=_due_time_key)

    def next_occurrence_at(self, task: Task) -> datetime | None:
        """Advance the original due time by one interval, even if overdue."""
        if task.frequency == "once":
            return None
        days = 1 if task.frequency == "daily" else 7
        return task.due_at + timedelta(days=days)

    def mark_task_complete(self, pet_id: UUID, task_id: UUID) -> Task | None:
        """Complete an occurrence and return its new successor, if one was added."""
        # A new Scheduler can refer to the same owner on any rerun.
        with _completion_lock:
            pet = self.owner.find_pet(pet_id)
            if pet is None:
                raise ValueError("This pet is no longer registered.")
            task = pet.find_task(task_id)
            if task is None:
                raise ValueError("This task is no longer available.")
            if task.completed:
                return None

            next_due = self.next_occurrence_at(task)
            next_task = None
            if next_due is not None:
                next_task = replace(task, due_at=next_due, task_id=uuid4(), completed=False)
                pet.add_task(next_task)
            task.mark_complete()
            return next_task

    def detect_conflicts(self) -> list[TaskConflict]:
        """Pair pending tasks with exactly the same due datetime."""
        tasks_by_time: dict[datetime, list[PetTask]] = {}
        for entry in self.owner.get_all_tasks():
            if not entry[1].completed:
                tasks_by_time.setdefault(_due_time_key(entry), []).append(entry)
        return [
            pair
            for entries in tasks_by_time.values()
            for pair in combinations(entries, 2)
        ]

    def plan_by_priority(
        self, window_start: datetime, window_end: datetime
    ) -> list[PlannedTask]:
        """Propose a conflict-free plan for pending tasks due in the window.

        Consider higher priorities first and use due time to break ties.
        Return entries by proposed start time, with a reason for each choice.
        """
        raise NotImplementedError

    def find_next_available_slot(
        self, window_start: datetime, window_end: datetime, duration_minutes: int
    ) -> datetime | None:
        """Return the earliest fitting start within the window, or None."""
        if type(duration_minutes) is not int:
            raise TypeError("Duration must be a whole number of minutes.")
        if duration_minutes <= 0:
            raise ValueError("Duration must be positive.")
        if not isinstance(window_start, datetime) or not isinstance(window_end, datetime):
            raise TypeError("The window start and end must be datetimes.")

        start, end = _datetime_key(window_start), _datetime_key(window_end)
        if start.tzinfo != end.tzinfo:
            raise ValueError("The window start and end must use compatible time zones.")
        if start >= end:
            raise ValueError("The latest end must be after the earliest start.")

        minute = timedelta(minutes=1)
        if duration_minutes > (end - start) // minute:
            return None
        duration = timedelta(minutes=duration_minutes)

        occupied = []
        for _, task in self.owner.get_all_tasks():
            if task.completed:
                continue
            task_start = _datetime_key(task.due_at)
            if task_start.tzinfo != start.tzinfo:
                raise ValueError("The search window and pending tasks must use compatible time zones.")
            if task_start >= end:
                continue

            # Cap the occupied end before adding a duration that may exceed datetime's range.
            if task.duration_minutes > (end - task_start) // minute:
                task_end = end
            else:
                task_end = task_start + timedelta(minutes=task.duration_minutes)
            if task_end > start:
                occupied.append((task_start, task_end))

        candidate = start
        for task_start, task_end in sorted(occupied):
            if task_start - candidate >= duration:
                break
            candidate = max(candidate, task_end)

        if end - candidate < duration:
            return None
        if start.tzinfo is not None:
            return candidate.astimezone(window_start.tzinfo)
        return candidate


def _object(value: object, label: str) -> dict:
    """Require a JSON object at the current location."""
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _array(value: object, label: str) -> list:
    """Require a JSON array at the current location."""
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _unique_json_fields(fields: list[tuple[str, object]]) -> dict[str, object]:
    """Reject ambiguous objects before a later value can erase an earlier one."""
    result: dict[str, object] = {}
    for key, value in fields:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _restore_owner(data: object) -> Owner:
    """Rebuild and validate the owner, pets, and tasks in a saved document."""
    owner_data = _object(data, "Owner")
    pets = []
    for pet_data in _array(owner_data["pets"], "Pets"):
        pet_data = _object(pet_data, "Pet")
        tasks = []
        for task_data in _array(pet_data["tasks"], "Tasks"):
            task_data = _object(task_data, "Task")
            due_at = task_data["due_at"]
            if not isinstance(due_at, str) or ("T" not in due_at and " " not in due_at):
                raise ValueError("due_at must contain an ISO datetime with a time")
            tasks.append(
                Task(
                    task_id=UUID(task_data["task_id"]),
                    description=task_data["description"],
                    due_at=datetime.fromisoformat(due_at),
                    completed=task_data["completed"],
                    frequency=task_data["frequency"],
                    priority=task_data["priority"],
                    duration_minutes=task_data["duration_minutes"],
                )
            )
        pets.append(
            Pet(
                pet_id=UUID(pet_data["pet_id"]),
                name=pet_data["name"],
                species=pet_data["species"],
                tasks=tasks,
            )
        )
    return Owner(owner_id=UUID(owner_data["owner_id"]), name=owner_data["name"], pets=pets)


def _reject_json_constant(token: str) -> None:
    """Reject non-finite literals that the default JSON decoder accepts."""
    raise ValueError(f"Invalid JSON numeric literal: {token}")


def load_from_json(path: str | Path = DEFAULT_DATA_PATH) -> Owner | None:
    """Load an owner from disk, or return None when the file is missing."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except UnicodeError as error:
        raise ValueError(f"Invalid UTF-8 in {path}.") from error

    try:
        data = json.loads(
            text,
            object_pairs_hook=_unique_json_fields,
            parse_constant=_reject_json_constant,
        )
    except ValueError as error:
        raise ValueError(f"Malformed JSON in {path}: {error}") from error
    try:
        return _restore_owner(data)
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid PawPal+ data in {path}: {error}") from error


class _UncheckedSnapshot:
    """Sentinel type for writes without a snapshot comparison."""


_UNCHECKED = _UncheckedSnapshot()


def _owner_snapshot(owner: Owner) -> dict[str, object]:
    """Serialize an owner for persistence and snapshot comparisons."""
    return {
        "owner_id": str(owner.owner_id),
        "name": owner.name,
        "pets": [
            {
                "pet_id": str(pet.pet_id),
                "name": pet.name,
                "species": pet.species,
                "tasks": [task.to_dict() for task in pet.list_tasks()],
            }
            for pet in owner.list_pets()
        ],
    }


def save_to_json(
    owner: Owner,
    path: str | Path = DEFAULT_DATA_PATH,
    *,
    expected_owner: Owner | None | _UncheckedSnapshot = _UNCHECKED,
) -> None:
    """Save atomically. Pass an expected owner or None to check for a change."""
    path = Path(path)
    data = _owner_snapshot(owner)
    try:
        _restore_owner(data)
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Cannot save invalid PawPal+ data: {error}") from error

    with _persistence_lock:
        stored_owner = load_from_json(path)
        if expected_owner is not _UNCHECKED:
            # Equal aware datetimes can still have different saved offsets and calendar dates.
            expected = _owner_snapshot(expected_owner) if isinstance(expected_owner, Owner) else None
            stored = _owner_snapshot(stored_owner) if stored_owner is not None else None
            if stored != expected:
                raise ValueError(
                    "The saved data changed in another session or on disk. Reopen PawPal+ and try again."
                )

        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=f".{path.name}.", suffix=".tmp", delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(data, temporary_file, ensure_ascii=False, indent=2)
                temporary_file.write("\n")
            temporary_path.replace(path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
