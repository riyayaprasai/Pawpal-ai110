"""PawPal+ domain entities and owner-wide scheduling."""

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from itertools import combinations
from threading import Lock
from typing import Literal, get_args
from uuid import UUID, uuid4

Frequency = Literal["once", "daily", "weekly"]
Priority = Literal["Low", "Medium", "High"]
TaskData = dict[str, str | int | bool]

_completion_lock = Lock()


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


def _due_time_key(entry: PetTask) -> datetime:
    """Use an absolute clock for aware datetimes and preserve local naive times."""
    due_at = entry[1].due_at
    if due_at.utcoffset() is not None:
        return due_at.astimezone(timezone.utc)
    return due_at


class Scheduler:
    """Read and update the owner's current schedule without storing a copy."""

    owner: Owner

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def sort_by_time(self) -> list[PetTask]:
        """Return pet-task pairs by due time, preserving insertion order for ties."""
        return sorted(self.owner.get_all_tasks(), key=_due_time_key)

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
        """Return the earliest start that fits inside the window, or None.

        Consider pending tasks across all pets, including overlaps from
        tasks that start before the window.
        """
        raise NotImplementedError
