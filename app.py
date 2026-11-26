"""Streamlit interface for the PawPal+ pet care tracker."""

from collections import Counter
from copy import deepcopy
from datetime import date, datetime, time
from html import escape
from pathlib import Path
from typing import get_args
from uuid import UUID

import streamlit as st

from pawpal_system import (
    DEFAULT_DATA_PATH, Frequency, Owner, Pet, PetTask, Priority, Scheduler, Task,
    load_from_json, save_to_json,
)

APP_CSS = Path(__file__).resolve().parent / "assets" / "pawpal.css"
PRIORITY_LABELS = {"High": "▲ High", "Medium": "● Medium", "Low": "▼ Low"}


def persist_owner(candidate: Owner, message: str) -> bool:
    """Publish a changed snapshot only after its save succeeds."""
    try:
        save_to_json(candidate, DEFAULT_DATA_PATH, expected_owner=st.session_state["owner"])
    except (OSError, ValueError) as error:
        st.session_state["notice"] = (False, f"Change could not be saved. {error}")
        return False

    st.session_state["owner"] = candidate
    st.session_state["notice"] = (True, message)
    return True


def save_owner_name(owner: Owner) -> None:
    """Save the sidebar name on the existing owner."""
    candidate = deepcopy(owner)
    try:
        candidate.rename(st.session_state["owner_name"].strip())
    except ValueError as error:
        st.session_state["notice"] = (False, str(error))
    else:
        persist_owner(candidate, "Owner name saved.")


def add_pet(owner: Owner) -> None:
    """Create and register a pet using the submitted details."""
    candidate = deepcopy(owner)
    try:
        pet = Pet(
            name=st.session_state["pet_name"].strip(),
            species=st.session_state["pet_species"],
        )
        candidate.add_pet(pet)
    except ValueError as error:
        st.session_state["notice"] = (False, str(error))
    else:
        if persist_owner(candidate, f"Added {pet.name}."):
            st.session_state["pet_name"] = ""


def remove_pet(owner: Owner, pet_id: UUID, confirmation_key: str) -> None:
    """Remove the selected pet after explicit confirmation."""
    if not st.session_state[confirmation_key]:
        st.session_state["notice"] = (False, "Check the confirmation box before removing a pet.")
        return

    candidate = deepcopy(owner)
    pet = candidate.remove_pet(pet_id)
    if pet is None:
        st.session_state["notice"] = (False, "This pet is no longer registered.")
        return

    if not persist_owner(candidate, f"Removed {pet.name} and their tasks."):
        return

    st.session_state["remove_pet_id"] = None
    for selection_key in ("task_pet_id", "schedule_pet_id"):
        if st.session_state.get(selection_key) == pet_id:
            st.session_state[selection_key] = None


def add_task(owner: Owner, pet_id: UUID) -> None:
    """Validate and add a task to the selected registered pet."""
    candidate = deepcopy(owner)
    pet = candidate.find_pet(pet_id)
    if pet is None:
        st.session_state["notice"] = (False, "Select a registered pet before adding a task.")
        return

    try:
        task = Task(
            description=st.session_state["task_description"].strip(),
            due_at=datetime.combine(st.session_state["task_date"], st.session_state["task_time"]),
            duration_minutes=st.session_state["task_duration"],
            frequency=st.session_state["task_frequency"],
            priority=st.session_state["task_priority"],
        )
        pet.add_task(task)
    except (TypeError, ValueError) as error:
        st.session_state["notice"] = (False, str(error))
    else:
        if persist_owner(candidate, f"Added a task for {pet.name}."):
            st.session_state["task_description"] = ""


def complete_task(owner: Owner, pet_id: UUID, selection_key: str) -> None:
    """Complete the selected occurrence through the scheduler."""
    task_id = st.session_state[selection_key]
    if task_id is None:
        st.session_state["notice"] = (False, "Choose a pending task to mark complete.")
        return

    candidate = deepcopy(owner)
    try:
        next_task = Scheduler(candidate).mark_task_complete(pet_id, task_id)
    except ValueError as error:
        st.session_state["notice"] = (False, str(error))
        return
    except OverflowError:
        st.session_state["notice"] = (False, "The next occurrence is outside the supported date range.")
        return

    message = "Task marked complete."
    if next_task is not None:
        message += f" Next occurrence: {next_task.due_at:%b %d, %Y at %H:%M}."
    if persist_owner(candidate, message):
        st.session_state[selection_key] = None


def pet_labels(pets: list[Pet]) -> dict[UUID, str]:
    """Disambiguate pets with the same name for display."""
    name_counts = Counter(pet.name for pet in pets)
    return {
        pet.pet_id: (
            pet.name if name_counts[pet.name] == 1
            else f"{pet.name} ({pet.species}, {pet.pet_id.hex[:8]})"
        )
        for pet in pets
    }


def show_task_table(
    entries: list[PetTask], labels: dict[UUID, str], *, details: bool = False
) -> None:
    """Display task pairs using readable, consistent column names."""
    rows = []
    for pet, task in entries:
        row = {
            "Pet": labels[pet.pet_id],
            "Task": task.description,
            "Due": task.due_at.strftime("%b %d, %Y · %H:%M"),
            "Priority": PRIORITY_LABELS[task.priority],
            "Status": "Completed" if task.completed else "Pending",
        }
        if details:
            row["Frequency"] = task.frequency
            row["Minutes"] = str(task.duration_minutes)
        rows.append(row)
    st.table(rows)


def show_dashboard(
    scheduler: Scheduler, entries: list[PetTask], labels: dict[UUID, str], today: date
) -> None:
    """Show owner-wide counts and the current day's tasks."""
    completed = sum(task.completed for _, task in entries)
    pets_metric, pending_metric, completed_metric = st.columns(3)
    pets_metric.container(border=True).metric("Pets", len(labels))
    pending_metric.container(border=True).metric("Pending tasks", len(entries) - completed)
    completed_metric.container(border=True).metric("Completed tasks", completed)

    with st.container(border=True):
        st.header("Today's schedule")
        st.caption(today.strftime("%A, %B %d, %Y"))
        today_entries = scheduler.filter_tasks(due_on=today)
        if today_entries:
            show_task_table(today_entries, labels)
        elif not labels:
            st.info("Add a pet in the Pets tab to start planning their care.")
        else:
            st.info("No tasks are due today.")


def show_pets(owner: Owner, pets: list[Pet], labels: dict[UUID, str]) -> None:
    """Render pet registration, roster, and confirmed removal."""
    st.header("Add a pet")
    with st.form("add_pet"):
        name_col, species_col = st.columns([2, 1])
        name_col.text_input("Pet name", placeholder="e.g. Mochi", key="pet_name")
        species_col.selectbox(
            "Species", ("Dog", "Cat", "Bird", "Rabbit", "Other"), key="pet_species"
        )
        st.form_submit_button("Add pet", on_click=add_pet, args=(owner,), type="primary")

    st.header("Registered pets")
    if not pets:
        st.info("No pets registered yet.")
        return

    cards = []
    for pet in pets:
        task_count = len(pet.list_tasks())
        task_label = "task" if task_count == 1 else "tasks"
        cards.append(
            f'<article class="pawpal-pet"><h3>{escape(labels[pet.pet_id])}</h3>'
            f"<p>{escape(pet.species)} · {task_count} {task_label}</p></article>"
        )
    st.markdown(f'<div class="pawpal-pet-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
    with st.expander("Remove a pet"):
        pet_id = st.selectbox(
            "Pet to remove", list(labels), index=None, format_func=labels.__getitem__,
            key="remove_pet_id",
        )
        if pet_id is not None:
            confirmation_key = f"confirm_remove_{pet_id}"
            with st.form(f"remove_pet_{pet_id}"):
                st.warning(f"Removing {labels[pet_id]} also removes all of their tasks.")
                st.checkbox(f"Confirm removal of {labels[pet_id]}", key=confirmation_key)
                st.form_submit_button(
                    "Remove pet", on_click=remove_pet, args=(owner, pet_id, confirmation_key)
                )


def show_tasks(owner: Owner, scheduler: Scheduler, labels: dict[UUID, str], today: date) -> None:
    """Render task entry, the selected pet's tasks, and completion."""
    st.header("Manage tasks")
    if not labels:
        st.info("Add a pet before creating tasks.")
        return

    pet_id = st.selectbox(
        "Pet", list(labels), index=None, format_func=labels.__getitem__, key="task_pet_id",
    )
    if pet_id is None:
        st.info("Choose a pet to add or review their tasks.")
        return

    with st.form("add_task"):
        st.text_input(
            "Task description", placeholder="e.g. Evening walk", key="task_description"
        )
        day_col, time_col = st.columns(2)
        day_col.date_input("Due date", value=today, key="task_date")
        time_col.time_input("Due time", value=time(9), key="task_time")
        frequency_col, priority_col, duration_col = st.columns(3)
        frequency_col.selectbox("Frequency", get_args(Frequency), key="task_frequency")
        priority_col.selectbox("Priority", get_args(Priority), index=1, key="task_priority")
        duration_col.number_input(
            "Duration (minutes)", min_value=1, value=20, step=1, key="task_duration"
        )
        st.caption("Completing a daily or weekly task adds its next scheduled occurrence.")
        st.form_submit_button("Add task", on_click=add_task, args=(owner, pet_id), type="primary")

    st.subheader("Existing tasks")
    entries = scheduler.filter_tasks(pet_id=pet_id)
    if not entries:
        st.info("No tasks have been added for this pet.")
        return
    show_task_table(entries, labels, details=True)

    pending = {
        task.task_id: f"{task.description} · {task.due_at:%b %d, %H:%M} · {task.task_id.hex[:8]}"
        for _, task in entries if not task.completed
    }
    if not pending:
        st.info("All tasks for this pet are complete.")
        return
    with st.form(f"complete_task_{pet_id}"):
        selection_key = f"pending_task_{pet_id}"
        st.selectbox(
            "Pending task", list(pending), index=None, format_func=pending.__getitem__,
            key=selection_key,
        )
        st.form_submit_button(
            "Mark complete", on_click=complete_task, args=(owner, pet_id, selection_key)
        )


def show_schedule(scheduler: Scheduler, labels: dict[UUID, str]) -> None:
    """Render filtered rows and warn about conflicts across the full schedule."""
    with st.container(border=True):
        st.header("Scheduled tasks")
        pet_column, status_column, sort_column = st.columns(3)
        pet_id = pet_column.selectbox(
            "Filter by pet", list(labels), index=None, format_func=labels.__getitem__,
            placeholder="All pets", disabled=not labels, key="schedule_pet_id",
        )
        statuses = {"All statuses": None, "Pending": False, "Completed": True}
        status = status_column.selectbox("Completion status", list(statuses))
        order = sort_column.selectbox("Sort by", ("Chronological", "Priority"), key="schedule_sort")

        entries = scheduler.filter_tasks(pet_id=pet_id, completed=statuses[status])
        if order == "Priority":
            entries = scheduler.sort_by_priority(entries)
        if entries:
            show_task_table(entries, labels)
        elif pet_id is None and status == "All statuses":
            st.info("The schedule is empty. Add a care task to get started.")
        else:
            st.info("No tasks match these filters.")

        conflicts = scheduler.detect_conflicts()
        if conflicts:
            st.subheader("Scheduling conflicts")
            for (first_pet, first_task), (second_pet, second_task) in conflicts:
                st.warning(
                    f"{first_task.due_at:%b %d, %Y at %H:%M}: "
                    f"{labels[first_pet.pet_id]} — {first_task.description} and "
                    f"{labels[second_pet.pet_id]} — {second_task.description} "
                    "are scheduled for the same time."
                )


def show_slot_suggestion(scheduler: Scheduler, today: date) -> None:
    """Suggest a free interval without changing any tasks."""
    with st.expander("Find an available slot"):
        with st.form("find_slot"):
            start_date_col, start_time_col = st.columns(2)
            start_date = start_date_col.date_input("Earliest start date", value=today)
            start_time = start_time_col.time_input("Earliest start time", value=time(8))
            end_date_col, end_time_col = st.columns(2)
            end_date = end_date_col.date_input("Latest end date", value=today)
            end_time = end_time_col.time_input("Latest end time", value=time(18))
            minutes = st.number_input("Requested duration (minutes)", min_value=1, value=30, step=1)
            submitted = st.form_submit_button("Find slot", type="primary")
        if not submitted:
            return

        try:
            start = datetime.combine(start_date, start_time)
            end = datetime.combine(end_date, end_time)
            slot = scheduler.find_next_available_slot(start, end, minutes)
        except (TypeError, ValueError) as error:
            st.warning(str(error))
            return

        if slot is None:
            st.info("No available slot fits that duration and time window.")
        else:
            st.success(f"Earliest available start: {slot:%b %d, %Y at %H:%M} ({minutes} min).")


def main() -> None:
    """Render the dashboard and management views for this session."""
    st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
    st.markdown(f"<style>{APP_CSS.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    if "owner" not in st.session_state:
        try:
            loaded_owner = load_from_json(DEFAULT_DATA_PATH)
        except (OSError, ValueError) as error:
            st.error(f"PawPal+ could not open saved data. {error}")
            st.info("Restore a valid data file and reopen PawPal+.")
            st.stop()
        st.session_state["owner"] = loaded_owner if loaded_owner is not None else Owner("Jordan")
    owner: Owner = st.session_state["owner"]

    with st.sidebar:
        st.header("Pet care profile")
        with st.form("owner_profile"):
            st.text_input("Owner name", value=owner.name, key="owner_name")
            st.form_submit_button("Save name", on_click=save_owner_name, args=(owner,))
        st.caption("Changes are saved to the local PawPal+ data file.")

    st.markdown(
        """
        <header class="pawpal-hero">
          <div class="pawpal-hero__body">
            <h1>PawPal<span>+</span></h1>
            <p>Plan meals, walks, medication, and appointments for your pets.</p>
          </div>
          <img src="./app/static/pets-at-home.jpg"
               alt="A curly-coated dog and an orange tabby resting on a sofa"
               width="960" height="640">
        </header>
        """,
        unsafe_allow_html=True,
    )
    feedback = st.empty()
    notice = st.session_state.pop("notice", None)
    if notice is not None:
        successful, message = notice
        if successful:
            feedback.success(message)
        else:
            feedback.warning(message)

    pets = owner.list_pets()
    labels = pet_labels(pets)
    scheduler = Scheduler(owner)
    entries = scheduler.sort_by_time()
    today = date.today()

    dashboard, pet_tab, task_tab, schedule = st.tabs(["Dashboard", "Pets", "Tasks", "Schedule"])
    with dashboard:
        show_dashboard(scheduler, entries, labels, today)
    with pet_tab:
        show_pets(owner, pets, labels)
    with task_tab:
        show_tasks(owner, scheduler, labels, today)
    with schedule:
        show_schedule(scheduler, labels)
        show_slot_suggestion(scheduler, today)


if __name__ == "__main__":
    main()
