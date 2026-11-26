"""Architecture stubs for the PawPal+ domain and scheduling service."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

Frequency = Literal["once", "daily", "weekly"]
Priority = Literal["Low", "Medium", "High"]
TaskData = dict[str, str | int | bool]


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

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        raise NotImplementedError

    def to_dict(self) -> TaskData:
        """Return JSON-ready data with the ID and due time encoded as strings."""
        raise NotImplementedError


@dataclass
class Pet:
    """A pet and the care tasks assigned to it."""

    name: str
    species: str
    pet_id: UUID = field(default_factory=uuid4)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task, rejecting a duplicate ID in this pet's tasks."""
        raise NotImplementedError

    def list_tasks(self) -> list[Task]:
        """Return a shallow copy of this pet's task list."""
        raise NotImplementedError

    def find_task(self, task_id: UUID) -> Task | None:
        """Return the task with this ID, or None if it is absent."""
        raise NotImplementedError

    def remove_task(self, task_id: UUID) -> Task | None:
        """Remove and return the matching task, or None if it is absent."""
        raise NotImplementedError


@dataclass
class Owner:
    """A pet owner and the pets in their care."""

    name: str
    owner_id: UUID = field(default_factory=uuid4)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Attach a pet, rejecting a duplicate ID in this owner's pets."""
        raise NotImplementedError

    def find_pet(self, pet_id: UUID) -> Pet | None:
        """Return the pet with this ID, or None if it is absent."""
        raise NotImplementedError

    def list_pets(self) -> list[Pet]:
        """Return a shallow copy of this owner's pet list."""
        raise NotImplementedError

    def remove_pet(self, pet_id: UUID) -> Pet | None:
        """Remove and return the matching pet, or None if it is absent."""
        raise NotImplementedError

    def get_all_tasks(self) -> list["PetTask"]:
        """Return (pet, task) pairs across all pets belonging to this owner."""
        raise NotImplementedError


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
        """Return all pet-task pairs ordered by due time."""
        raise NotImplementedError

    def filter_tasks(
        self,
        *,
        pet_id: UUID | None = None,
        due_on: date | None = None,
        completed: bool | None = None,
    ) -> list[PetTask]:
        """Return pairs matching all supplied filters in chronological order."""
        raise NotImplementedError

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
