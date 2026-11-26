"""PawPal+ domain entities and owner-wide scheduling."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, get_args
from uuid import UUID, uuid4

Frequency = Literal["once", "daily", "weekly"]
Priority = Literal["Low", "Medium", "High"]
TaskData = dict[str, str | int | bool]


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


class Scheduler:
    """Plan across an owner's pets using their task lists as the source of truth.

    Collection queries return lists, empty when there are no results. Tasks
    are always paired with their pet. Single-time queries return a datetime
    or None. Scheduling methods leave the owner's task records untouched.
    """

    owner: Owner

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def sort_chronologically(self) -> list[PetTask]:
        """Return current pet-task pairs ordered by comparable due times."""
        return sorted(self.owner.get_all_tasks(), key=lambda pair: pair[1].due_at)

    def filter_tasks(
        self,
        *,
        pet_id: UUID | None = None,
        due_on: date | None = None,
        completed: bool | None = None,
    ) -> list[PetTask]:
        """Return pairs matching all supplied filters in chronological order."""
        return [
            (pet, task)
            for pet, task in self.sort_chronologically()
            if (pet_id is None or pet.pet_id == pet_id)
            and (due_on is None or task.due_at.date() == due_on)
            and (completed is None or task.completed == completed)
        ]

    def detect_conflicts(self) -> list[TaskConflict]:
        """Return each overlapping pair of pending tasks once, across all pets.

        Use due_at as the current start and duration_minutes to find the end.
        Tasks may touch at an endpoint without overlapping.
        """
        raise NotImplementedError

    def next_occurrence_at(self, task: Task) -> datetime | None:
        """Return the next daily or weekly due time from this task's due time.

        Return None for a one-time task.
        """
        raise NotImplementedError

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
