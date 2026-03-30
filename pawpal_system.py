from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


# ---------------------------------------------------------------------------
# CareTask
# ---------------------------------------------------------------------------

@dataclass
class CareTask:
    """A single care task that a pet needs (walk, feed, med, groom, enrichment)."""

    task_type: str                        # e.g. "walk", "feed", "med", "groom", "enrichment"
    duration_minutes: int
    priority: int                         # 1 (low) – 3 (high)
    frequency: str                        # e.g. "daily", "twice_daily", "weekly"
    time_window: str                      # e.g. "morning", "evening", "any"
    required: bool = True
    notes: str = ""
    last_completed_on: Optional[date] = None

    def is_due(self, on_date: date) -> bool:
        """Return True if this task should be done on on_date."""
        pass

    def mark_completed(self, on_date: date) -> None:
        """Record that the task was completed on on_date."""
        pass


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """Represents a pet belonging to an owner."""

    name: str
    species: str
    age: int
    health_notes: str = ""
    tasks: list[CareTask] = field(default_factory=list)

    def add_task(self, task: CareTask) -> None:
        """Add a care task to this pet's task list."""
        pass

    def get_due_tasks(self, on_date: date) -> list[CareTask]:
        """Return all tasks that are due on on_date."""
        pass


# ---------------------------------------------------------------------------
# Constraint
# ---------------------------------------------------------------------------

@dataclass
class Constraint:
    """Scheduling constraints that govern how a daily plan is built."""

    available_minutes: int
    blocked_times: list[str] = field(default_factory=list)   # e.g. ["22:00-06:00"]
    max_tasks_per_day: int = 10
    preference_rules: list[str] = field(default_factory=list) # e.g. ["no walks after 21:00"]


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """The pet owner, their preferences, and their scheduling constraints."""

    name: str
    preferences: list[str] = field(default_factory=list)
    constraint: Optional[Constraint] = None
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's list."""
        pass


# ---------------------------------------------------------------------------
# DailyPlan
# ---------------------------------------------------------------------------

@dataclass
class DailyPlan:
    """The output of the scheduler: a day's worth of planned care tasks."""

    plan_date: date
    scheduled_tasks: list[CareTask] = field(default_factory=list)
    deferred_tasks: list[tuple[CareTask, str]] = field(default_factory=list)  # (task, reason)
    schedule_blocks: list[str] = field(default_factory=list)
    rationale: str = ""

    def add_scheduled_task(self, task: CareTask) -> None:
        """Add a task to the schedule."""
        pass

    def add_deferred_task(self, task: CareTask, reason: str) -> None:
        """Record a task that was skipped and why."""
        pass

    def explain_choices(self) -> str:
        """Return a human-readable summary of why each task was scheduled or skipped."""
        pass


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class Planner:
    """Scheduling engine: reads owner + pet data and produces a DailyPlan."""

    def generate_plan(self, owner: Owner, pets: list[Pet], on_date: date) -> DailyPlan:
        """Build and return a DailyPlan for on_date."""
        pass

    def rank_tasks(self, tasks: list[CareTask], constraint: Constraint) -> list[CareTask]:
        """Sort tasks by priority and preference rules; most important first."""
        pass

    def fit_to_time_budget(self, tasks: list[CareTask], constraint: Constraint) -> list[CareTask]:
        """Select tasks that fit within available_minutes; respect max_tasks_per_day."""
        pass
