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
    completions_today: int = 0            # tracks twice_daily completions within one day

    def is_due(self, on_date: date) -> bool:
        """Return True if this task still needs to be done on on_date."""
        if self.last_completed_on is None:
            return True
        days_since = (on_date - self.last_completed_on).days
        if self.frequency == "daily":
            return days_since >= 1
        if self.frequency == "twice_daily":
            # Not yet done today → due; done once today → still due for second round
            if self.last_completed_on != on_date:
                return True
            return self.completions_today < 2
        if self.frequency == "weekly":
            return days_since >= 7
        return True                       # unknown frequency → always treat as due

    def mark_completed(self, on_date: date) -> None:
        """Record a completion; increments counter when done multiple times on the same day."""
        if self.last_completed_on == on_date:
            self.completions_today += 1
        else:
            self.last_completed_on = on_date
            self.completions_today = 1


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

    def get_completed_tasks(self, on_date: date) -> list[CareTask]:
        """Return tasks that have been completed on on_date."""
        return [t for t in self.tasks if t.last_completed_on == on_date]

    def get_pending_tasks(self, on_date: date) -> list[CareTask]:
        """Return tasks that are due on on_date but not yet fully completed."""
        return [t for t in self.tasks if t.is_due(on_date) and t.last_completed_on != on_date]


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

    def get_tasks_for_pet(self, pet_name: str) -> list[CareTask]:
        """Return all tasks (regardless of due status) for the named pet."""
        for pet in self.pets:
            if pet.name == pet_name:
                return list(pet.tasks)
        return []


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
    conflicts: list[str] = field(default_factory=list)
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

        if self.conflicts:
            lines.append("Conflicts:")
            for c in self.conflicts:
                lines.append(f"  ! {c}")

        lines.append(f"\nTime used : {self.total_minutes_used} min")
        if self.rationale:
            lines.append(f"Summary   : {self.rationale}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

_PRIORITY_RANK: dict[str, int] = {"high": 3, "medium": 2, "low": 1}

# Canonical time-window order used for sorting and block display
_WINDOW_ORDER: list[str] = ["morning", "midday", "afternoon", "evening", "any"]

# Max minutes per window before flagging as overloaded
_WINDOW_CAPACITY_MINUTES: int = 60


def _window_index(window: str) -> int:
    """Return sort key for a time window; unknown windows sort last."""
    try:
        return _WINDOW_ORDER.index(window)
    except ValueError:
        return len(_WINDOW_ORDER)


class Planner:
    """Scheduling engine: reads owner + pet data and produces a DailyPlan."""

    def generate_plan(self, owner: Owner, on_date: date) -> DailyPlan:
        """Build and return a DailyPlan for on_date using owner.pets and owner.constraint."""
        constraint = owner.constraint or Constraint(available_minutes=120)

        all_due = owner.get_all_due_tasks(on_date)
        ranked = self.rank_tasks(all_due, constraint)
        scheduled = self.fit_to_time_budget(ranked, constraint)

        # Sort selected tasks by time window so the output reads chronologically
        scheduled.sort(key=lambda t: _window_index(t.time_window))

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

        # Build schedule blocks grouped by time window (already in order)
        grouped: dict[str, list[CareTask]] = {}
        for task in scheduled:
            grouped.setdefault(task.time_window, []).append(task)

        blocks: list[str] = []
        for window in _WINDOW_ORDER:
            if window in grouped:
                task_str = ", ".join(
                    f"{t.task_type} ({t.duration_minutes}min)" for t in grouped[window]
                )
                blocks.append(f"{window.capitalize()}: {task_str}")
        for window, tasks in grouped.items():
            if window not in _WINDOW_ORDER:
                task_str = ", ".join(f"{t.task_type} ({t.duration_minutes}min)" for t in tasks)
                blocks.append(f"{window.capitalize()}: {task_str}")

        plan.schedule_blocks = blocks
        plan.conflicts = self.detect_conflicts(plan, constraint)
        plan.rationale = (
            f"Scheduled {len(scheduled)} of {len(ranked)} due tasks, "
            f"using {plan.total_minutes_used} of {constraint.available_minutes} available minutes. "
            f"{len(plan.deferred_tasks)} task(s) deferred."
            + (f" {len(plan.conflicts)} conflict(s) detected." if plan.conflicts else "")
        )

        return plan

    def sort_by_time(self, tasks: list[CareTask]) -> list[CareTask]:
        """Return tasks sorted chronologically by time window (morning → midday → afternoon → evening → any).

        Uses a lambda key that maps each task's time_window string to its index
        in _WINDOW_ORDER, so unknown windows fall to the end rather than raising.
        """
        return sorted(tasks, key=lambda t: _window_index(t.time_window))

    def filter_tasks(
        self,
        tasks: list[CareTask],
        *,
        pet: Optional[Pet] = None,
        completed_on: Optional[date] = None,
        pending_on: Optional[date] = None,
        task_type: Optional[str] = None,
    ) -> list[CareTask]:
        """Return a filtered subset of tasks.

        Filters are AND-combined; omit a parameter to skip that filter.
        - pet:          only tasks belonging to this Pet object
        - completed_on: only tasks whose last_completed_on equals this date
        - pending_on:   only tasks that are still due (not fully done) on this date
        - task_type:    only tasks whose task_type matches (case-insensitive)
        """
        result = list(tasks)
        if pet is not None:
            result = [t for t in result if t in pet.tasks]
        if completed_on is not None:
            result = [t for t in result if t.last_completed_on == completed_on]
        if pending_on is not None:
            result = [t for t in result if t.is_due(pending_on)]
        if task_type is not None:
            result = [t for t in result if t.task_type.lower() == task_type.lower()]
        return result

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

    def detect_conflicts(self, plan: DailyPlan, constraint: Constraint) -> list[str]:
        """Flag window overloads and preference-rule violations in a scheduled plan."""
        issues: list[str] = []

        # 1. Window overload: a single window exceeds _WINDOW_CAPACITY_MINUTES
        window_minutes: dict[str, int] = {}
        for task in plan.scheduled_tasks:
            window_minutes[task.time_window] = (
                window_minutes.get(task.time_window, 0) + task.duration_minutes
            )
        for window, total in window_minutes.items():
            if total > _WINDOW_CAPACITY_MINUTES:
                issues.append(
                    f"{window.capitalize()} window overloaded: "
                    f"{total} min scheduled (>{_WINDOW_CAPACITY_MINUTES} min threshold)"
                )

        # 2. Preference-rule violations
        # Parses rules of the form "no <task_type> after HH:MM" and flags
        # tasks of that type placed in the evening window.
        for rule in constraint.preference_rules:
            rule_lower = rule.lower()
            if rule_lower.startswith("no "):
                words = rule_lower.split()
                if len(words) >= 2:
                    restricted_type = words[1].rstrip("s")  # normalise plural
                    for task in plan.scheduled_tasks:
                        if (task.task_type.rstrip("s") == restricted_type
                                and task.time_window == "evening"):
                            issues.append(
                                f"Preference rule '{rule}' may be violated: "
                                f"'{task.task_type}' is placed in the evening window"
                            )

        return issues
