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

    task_type: str                        # "walk", "feed", "med", "groom", "enrichment"
    duration_minutes: int
    priority: str                         # "low", "medium", or "high"
    frequency: str                        # "daily", "twice_daily", "weekly"
    time_window: str                      # "morning", "midday", "afternoon", "evening", "any"
    required: bool = True
    notes: str = ""
    last_completed_on: Optional[date] = None

    def is_due(self, on_date: date) -> bool:
        """Return True if this task should be done on on_date."""
        if self.last_completed_on is None:
            return True
        days_since = (on_date - self.last_completed_on).days
        if self.frequency == "daily":
            return days_since >= 1
        if self.frequency == "twice_daily":
            return days_since >= 1      # simplified: once per calendar day minimum
        if self.frequency == "weekly":
            return days_since >= 7
        return True                     # unknown frequency → always treat as due

    def mark_completed(self, on_date: date) -> None:
        """Record that the task was completed on on_date."""
        self.last_completed_on = on_date


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
        self.tasks.append(task)

    def get_due_tasks(self, on_date: date) -> list[CareTask]:
        """Return all tasks that are due on on_date."""
        return [t for t in self.tasks if t.is_due(on_date)]


# ---------------------------------------------------------------------------
# Constraint
# ---------------------------------------------------------------------------

@dataclass
class Constraint:
    """Scheduling constraints that govern how a daily plan is built."""

    available_minutes: int
    blocked_times: list[str] = field(default_factory=list)    # e.g. ["22:00-06:00"]
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
        self.pets.append(pet)

    def get_all_due_tasks(self, on_date: date) -> list[CareTask]:
        """Return every due task across all pets for on_date."""
        tasks: list[CareTask] = []
        for pet in self.pets:
            tasks.extend(pet.get_due_tasks(on_date))
        return tasks


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
        self.scheduled_tasks.append(task)

    def add_deferred_task(self, task: CareTask, reason: str) -> None:
        """Record a task that was skipped and why."""
        self.deferred_tasks.append((task, reason))

    @property
    def total_minutes_used(self) -> int:
        """Sum of duration_minutes for all scheduled tasks."""
        return sum(t.duration_minutes for t in self.scheduled_tasks)

    def explain_choices(self) -> str:
        """Return a human-readable summary of why each task was scheduled or skipped."""
        lines: list[str] = [f"Plan for {self.plan_date}", "-" * 36]

        if self.scheduled_tasks:
            lines.append("Scheduled:")
            for task in self.scheduled_tasks:
                req_label = " [required]" if task.required else ""
                lines.append(
                    f"  + {task.task_type:<14} {task.duration_minutes:>3} min  "
                    f"priority={task.priority}{req_label}"
                )
        else:
            lines.append("  No tasks scheduled.")

        if self.deferred_tasks:
            lines.append("Deferred:")
            for task, reason in self.deferred_tasks:
                lines.append(f"  - {task.task_type:<14} ({reason})")

        lines.append(f"\nTime used : {self.total_minutes_used} min")
        if self.rationale:
            lines.append(f"Summary   : {self.rationale}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

_PRIORITY_RANK: dict[str, int] = {"high": 3, "medium": 2, "low": 1}

_WINDOW_ORDER: list[str] = ["morning", "midday", "afternoon", "evening", "any"]


class Planner:
    """Scheduling engine: reads owner + pet data and produces a DailyPlan."""

    def generate_plan(self, owner: Owner, on_date: date) -> DailyPlan:
        """Build and return a DailyPlan for on_date using owner.pets and owner.constraint."""
        constraint = owner.constraint or Constraint(available_minutes=120)

        all_due = owner.get_all_due_tasks(on_date)
        ranked = self.rank_tasks(all_due, constraint)
        scheduled = self.fit_to_time_budget(ranked, constraint)

        scheduled_ids = {id(t) for t in scheduled}

        plan = DailyPlan(plan_date=on_date)

        for task in scheduled:
            plan.add_scheduled_task(task)

        minutes_left = constraint.available_minutes - plan.total_minutes_used
        for task in ranked:
            if id(task) in scheduled_ids:
                continue
            if len(plan.scheduled_tasks) >= constraint.max_tasks_per_day:
                reason = "daily task limit reached"
            elif task.duration_minutes > minutes_left:
                reason = f"needs {task.duration_minutes} min, only {minutes_left} min left"
            else:
                reason = "excluded by constraints"
            plan.add_deferred_task(task, reason)

        # Build readable schedule blocks grouped by time window
        grouped: dict[str, list[CareTask]] = {}
        for task in scheduled:
            grouped.setdefault(task.time_window, []).append(task)

        blocks: list[str] = []
        seen_windows: set[str] = set()
        for window in _WINDOW_ORDER:
            if window in grouped:
                seen_windows.add(window)
                task_str = ", ".join(
                    f"{t.task_type} ({t.duration_minutes}min)" for t in grouped[window]
                )
                blocks.append(f"{window.capitalize()}: {task_str}")
        for window, tasks in grouped.items():
            if window not in seen_windows:
                task_str = ", ".join(f"{t.task_type} ({t.duration_minutes}min)" for t in tasks)
                blocks.append(f"{window.capitalize()}: {task_str}")

        plan.schedule_blocks = blocks
        plan.rationale = (
            f"Scheduled {len(scheduled)} of {len(ranked)} due tasks, "
            f"using {plan.total_minutes_used} of {constraint.available_minutes} available minutes. "
            f"{len(plan.deferred_tasks)} task(s) deferred."
        )

        return plan

    def rank_tasks(self, tasks: list[CareTask], constraint: Constraint) -> list[CareTask]:
        """Sort tasks by required flag then priority; most important first."""
        return sorted(
            tasks,
            key=lambda t: (t.required, _PRIORITY_RANK.get(t.priority, 0)),
            reverse=True,
        )

    def fit_to_time_budget(self, tasks: list[CareTask], constraint: Constraint) -> list[CareTask]:
        """Select tasks that fit within available_minutes and max_tasks_per_day."""
        selected: list[CareTask] = []
        minutes_used = 0
        for task in tasks:
            if len(selected) >= constraint.max_tasks_per_day:
                break
            if minutes_used + task.duration_minutes <= constraint.available_minutes:
                selected.append(task)
                minutes_used += task.duration_minutes
        return selected
