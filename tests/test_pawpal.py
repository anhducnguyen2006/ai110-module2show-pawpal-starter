from datetime import date, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pawpal_system import CareTask, Pet, Owner, Constraint, DailyPlan, Planner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def task(task_type="walk", duration=20, priority="high",
         frequency="daily", window="morning", required=True) -> CareTask:
    """Convenience factory so tests stay concise."""
    return CareTask(task_type, duration, priority, frequency, window, required)


TODAY    = date.today()
TOMORROW = TODAY + timedelta(days=1)


# ---------------------------------------------------------------------------
# 1 – Task completion & auto-rescheduling
# ---------------------------------------------------------------------------

def test_mark_completed_updates_last_completed_on():
    """mark_completed() records the completion date."""
    t = task()
    assert t.last_completed_on is None
    t.mark_completed(TODAY)
    assert t.last_completed_on == TODAY


def test_mark_completed_makes_task_not_due_same_day():
    """A daily task completed today is not due again today."""
    t = task(frequency="daily")
    t.mark_completed(TODAY)
    assert t.is_due(TODAY) is False


def test_daily_task_is_due_next_day_after_completion():
    """A daily task completed today becomes due again tomorrow."""
    t = task(frequency="daily")
    t.mark_completed(TODAY)
    assert t.next_due_on == TOMORROW
    assert t.is_due(TOMORROW) is True


def test_weekly_task_schedules_seven_days_ahead():
    """A weekly task is not due within 6 days but is due on day 7 exactly."""
    t = task(frequency="weekly")
    t.mark_completed(TODAY)
    assert t.is_due(TODAY + timedelta(days=6)) is False
    assert t.is_due(TODAY + timedelta(days=7)) is True


def test_twice_daily_still_due_after_first_completion():
    """twice_daily task is still due on the same day after the first completion."""
    t = task(frequency="twice_daily")
    t.mark_completed(TODAY)
    assert t.is_due(TODAY) is True
    assert t.next_due_on == TODAY


def test_twice_daily_not_due_after_second_completion():
    """twice_daily task is done for the day after both completions."""
    t = task(frequency="twice_daily")
    t.mark_completed(TODAY)
    t.mark_completed(TODAY)
    assert t.is_due(TODAY) is False
    assert t.next_due_on == TOMORROW


# ---------------------------------------------------------------------------
# 2 – Pet task management
# ---------------------------------------------------------------------------

def test_add_task_increases_pet_task_count():
    """Pet.add_task appends to the task list."""
    pet = Pet("Mochi", "dog", 3)
    assert len(pet.tasks) == 0
    pet.add_task(task())
    assert len(pet.tasks) == 1


def test_add_multiple_tasks_all_appear_on_pet():
    """All added tasks are retrievable in insertion order."""
    pet = Pet("Luna", "cat", 5)
    types = ["feed", "med", "groom"]
    for tt in types:
        pet.add_task(task(task_type=tt))
    assert [t.task_type for t in pet.tasks] == types


def test_pet_with_no_tasks_returns_empty_due_list():
    """Edge: a pet with no tasks should return an empty list from get_due_tasks."""
    pet = Pet("Empty", "rabbit", 1)
    assert pet.get_due_tasks(TODAY) == []


def test_owner_with_no_pets_returns_empty_due_list():
    """Edge: an owner with no pets should aggregate zero due tasks."""
    owner = Owner("Nobody", constraint=Constraint(available_minutes=60))
    assert owner.get_all_due_tasks(TODAY) == []


# ---------------------------------------------------------------------------
# 3 – rank_tasks
# ---------------------------------------------------------------------------

def test_rank_tasks_required_before_optional():
    """Required tasks must rank above optional tasks regardless of priority."""
    planner = Planner()
    constraint = Constraint(available_minutes=999)
    optional  = task(task_type="groom",  priority="high", required=False)
    required  = task(task_type="walk",   priority="low",  required=True)
    ranked = planner.rank_tasks([optional, required], constraint)
    assert ranked[0].task_type == "walk"


def test_rank_tasks_priority_order_within_required():
    """Among required tasks: high → medium → low."""
    planner = Planner()
    constraint = Constraint(available_minutes=999)
    low  = task(task_type="groom", priority="low",    required=True)
    med  = task(task_type="feed",  priority="medium",  required=True)
    high = task(task_type="walk",  priority="high",    required=True)
    ranked = planner.rank_tasks([low, med, high], constraint)
    assert [t.task_type for t in ranked] == ["walk", "feed", "groom"]


def test_rank_tasks_empty_list_returns_empty():
    """Edge: ranking an empty list returns an empty list without error."""
    planner = Planner()
    assert planner.rank_tasks([], Constraint(available_minutes=60)) == []


# ---------------------------------------------------------------------------
# 4 – fit_to_time_budget
# ---------------------------------------------------------------------------

def test_fit_to_time_budget_selects_tasks_that_fit():
    """Basic case: tasks within budget are all selected."""
    planner = Planner()
    constraint = Constraint(available_minutes=60)
    tasks = [task(duration=20), task(task_type="feed", duration=20)]
    selected = planner.fit_to_time_budget(tasks, constraint)
    assert len(selected) == 2


def test_fit_to_time_budget_skips_large_then_fits_smaller():
    """Gap-filling: a task too large to fit is skipped; a smaller later task is still selected."""
    planner = Planner()
    constraint = Constraint(available_minutes=70)
    big   = task(task_type="walk",  duration=60)   # fits (60 ≤ 70); uses 60 min
    large = task(task_type="groom", duration=50)   # won't fit (60+50=110 > 70); skipped
    small = task(task_type="feed",  duration=8)    # fits (60+8=68 ≤ 70); selected
    selected = planner.fit_to_time_budget([big, large, small], constraint)
    assert [t.task_type for t in selected] == ["walk", "feed"]


def test_fit_to_time_budget_exact_boundary_included():
    """A task whose duration exactly equals the remaining budget should be included (≤ not <)."""
    planner = Planner()
    constraint = Constraint(available_minutes=30)
    exact = task(duration=30)
    selected = planner.fit_to_time_budget([exact], constraint)
    assert len(selected) == 1


def test_fit_to_time_budget_all_tasks_too_large_returns_empty():
    """Edge: when every task exceeds the budget, nothing is selected."""
    planner = Planner()
    constraint = Constraint(available_minutes=5)
    tasks = [task(duration=20), task(task_type="feed", duration=30)]
    assert planner.fit_to_time_budget(tasks, constraint) == []


def test_fit_to_time_budget_respects_max_tasks_per_day():
    """Tasks beyond max_tasks_per_day are excluded even if time remains."""
    planner = Planner()
    constraint = Constraint(available_minutes=999, max_tasks_per_day=2)
    tasks = [task(task_type=str(i), duration=5) for i in range(5)]
    selected = planner.fit_to_time_budget(tasks, constraint)
    assert len(selected) == 2


# ---------------------------------------------------------------------------
# 5 – sort_by_time
# ---------------------------------------------------------------------------

def test_sort_by_time_chronological_order():
    """Tasks in scrambled window order are sorted morning → afternoon → evening."""
    planner = Planner()
    eve  = task(task_type="feed",  window="evening")
    morn = task(task_type="walk",  window="morning")
    aft  = task(task_type="groom", window="afternoon")
    sorted_tasks = planner.sort_by_time([eve, morn, aft])
    assert [t.time_window for t in sorted_tasks] == ["morning", "afternoon", "evening"]


def test_sort_by_time_unknown_window_sorts_last():
    """Edge: a task with an unrecognised window string falls to the end."""
    planner = Planner()
    morn    = task(task_type="walk",  window="morning")
    unknown = task(task_type="other", window="whenever")
    sorted_tasks = planner.sort_by_time([unknown, morn])
    assert sorted_tasks[0].time_window == "morning"
    assert sorted_tasks[-1].time_window == "whenever"


# ---------------------------------------------------------------------------
# 6 – detect_conflicts
# ---------------------------------------------------------------------------

def test_detect_conflicts_no_conflicts_returns_empty():
    """Happy path: well-spaced tasks with no rule violations produce no warnings."""
    planner = Planner()
    plan = DailyPlan(plan_date=TODAY)
    plan.add_scheduled_task(task(task_type="walk", duration=20, window="morning"))
    plan.add_scheduled_task(task(task_type="feed", duration=10, window="evening"))
    constraint = Constraint(available_minutes=60)
    assert planner.detect_conflicts(plan, constraint) == []


def test_detect_conflicts_window_overload():
    """More than 60 minutes in one window triggers an overload warning."""
    planner = Planner()
    plan = DailyPlan(plan_date=TODAY)
    plan.add_scheduled_task(task(task_type="walk",  duration=40, window="morning"))
    plan.add_scheduled_task(task(task_type="groom", duration=30, window="morning"))
    constraint = Constraint(available_minutes=999)
    conflicts = planner.detect_conflicts(plan, constraint)
    assert any("overloaded" in c.lower() for c in conflicts)


def test_detect_conflicts_same_pet_overlap():
    """Two tasks for the same pet in the same window produce a same-pet warning."""
    planner = Planner()
    pet = Pet("Rex", "dog", 2)
    walk  = task(task_type="walk",  duration=20, window="morning")
    groom = task(task_type="groom", duration=20, window="morning")
    pet.add_task(walk)
    pet.add_task(groom)
    owner = Owner("Sam", constraint=Constraint(available_minutes=999))
    owner.add_pet(pet)

    plan = DailyPlan(plan_date=TODAY)
    plan.add_scheduled_task(walk)
    plan.add_scheduled_task(groom)

    conflicts = planner.detect_conflicts(plan, owner.constraint, owner)
    assert any("Rex" in c and "morning" in c for c in conflicts)


def test_detect_conflicts_cross_pet_collision():
    """Two different pets with required tasks in the same window trigger a cross-pet warning."""
    planner = Planner()
    pet1 = Pet("Rex",   "dog", 2)
    pet2 = Pet("Kitty", "cat", 3)
    t1 = task(task_type="walk", window="morning", required=True)
    t2 = task(task_type="feed", window="morning", required=True)
    pet1.add_task(t1)
    pet2.add_task(t2)
    owner = Owner("Sam", constraint=Constraint(available_minutes=999))
    owner.add_pet(pet1)
    owner.add_pet(pet2)

    plan = DailyPlan(plan_date=TODAY)
    plan.add_scheduled_task(t1)
    plan.add_scheduled_task(t2)

    conflicts = planner.detect_conflicts(plan, owner.constraint, owner)
    assert any("Rex" in c and "Kitty" in c for c in conflicts)


# ---------------------------------------------------------------------------
# 7 – generate_plan integration
# ---------------------------------------------------------------------------

def test_generate_plan_completed_task_not_rescheduled():
    """A task already completed today must not appear in the scheduled plan."""
    pet = Pet("Mochi", "dog", 3)
    walk = task(task_type="walk", duration=20)
    pet.add_task(walk)
    walk.mark_completed(TODAY)            # done — is_due(TODAY) is now False

    owner = Owner("Jordan", constraint=Constraint(available_minutes=120))
    owner.add_pet(pet)

    plan = Planner().generate_plan(owner, TODAY)
    scheduled_types = [t.task_type for t in plan.scheduled_tasks]
    assert "walk" not in scheduled_types


def test_generate_plan_all_tasks_deferred_when_budget_too_tight():
    """Edge: when available_minutes is smaller than any task, everything is deferred."""
    pet = Pet("Luna", "cat", 5)
    pet.add_task(task(task_type="feed",  duration=20))
    pet.add_task(task(task_type="groom", duration=30))

    owner = Owner("Jordan", constraint=Constraint(available_minutes=5))
    owner.add_pet(pet)

    plan = Planner().generate_plan(owner, TODAY)
    assert plan.scheduled_tasks == []
    assert len(plan.deferred_tasks) == 2


def test_generate_plan_owner_with_no_pets_produces_empty_plan():
    """Edge: generating a plan for an owner with no pets should not crash."""
    owner = Owner("Empty", constraint=Constraint(available_minutes=60))
    plan = Planner().generate_plan(owner, TODAY)
    assert plan.scheduled_tasks == []
    assert plan.deferred_tasks  == []


def test_generate_plan_schedule_is_chronological():
    """Scheduled tasks in the output must be ordered by time window."""
    pet = Pet("Rex", "dog", 2)
    pet.add_task(task(task_type="groom", window="evening",   duration=10))
    pet.add_task(task(task_type="med",   window="morning",   duration=5))
    pet.add_task(task(task_type="feed",  window="afternoon", duration=10))

    owner = Owner("Sam", constraint=Constraint(available_minutes=120))
    owner.add_pet(pet)

    plan = Planner().generate_plan(owner, TODAY)
    windows = [t.time_window for t in plan.scheduled_tasks]
    from pawpal_system import _WINDOW_ORDER
    indices = [_WINDOW_ORDER.index(w) for w in windows if w in _WINDOW_ORDER]
    assert indices == sorted(indices)


# ---------------------------------------------------------------------------
# Required verification suite
# Three explicit anchor tests that directly cover the stated requirements.
# Each docstring explains what is being checked and why the assertion matters.
# ---------------------------------------------------------------------------

def test_sorting_correctness_tasks_in_chronological_order():
    """
    REQUIREMENT: Sorting — verify tasks are returned in chronological window order.

    What this tests
    ---------------
    sort_by_time() accepts a list of CareTask objects in any order and must
    return them sorted morning → midday → afternoon → evening → any.

    Why it matters
    --------------
    The scheduler outputs tasks in the order the owner should do them.
    If sorting is wrong, an evening grooming session could appear before a
    morning walk, making the plan confusing and unusable.

    How to read the assertion
    -------------------------
    We build a list with windows deliberately scrambled (evening, any, morning,
    afternoon), call sort_by_time(), and confirm the resulting window sequence
    matches the canonical order exactly.
    """
    planner = Planner()
    scrambled = [
        task(task_type="groom",       window="evening"),
        task(task_type="enrichment",  window="any"),
        task(task_type="walk",        window="morning"),
        task(task_type="feed",        window="afternoon"),
    ]
    result = planner.sort_by_time(scrambled)
    assert [t.time_window for t in result] == ["morning", "afternoon", "evening", "any"]


def test_recurrence_logic_completed_daily_task_reappears_in_tomorrows_plan():
    """
    REQUIREMENT: Recurrence — marking a daily task complete today makes it due again tomorrow.

    What this tests
    ---------------
    After mark_completed(TODAY) is called, next_due_on is set to TOMORROW via
    timedelta(days=1). When generate_plan is run for TOMORROW's date, the task
    must reappear in scheduled_tasks — confirming the recurrence is picked up
    by the full scheduling pipeline, not just the is_due() method in isolation.

    Why it matters
    --------------
    A pet care planner only works if recurring tasks actually recur. Without
    this end-to-end check, a bug in generate_plan could silently discard
    recurring tasks even when is_due() returns True.

    How to read the assertion
    -------------------------
    1. Create a pet with one daily walk and mark it done today.
    2. Run generate_plan for TODAY → walk must NOT be in the plan (already done).
    3. Run generate_plan for TOMORROW → walk MUST be back in the plan.
    """
    pet = Pet("Mochi", "dog", 3)
    walk = task(task_type="walk", duration=20, frequency="daily")
    pet.add_task(walk)
    walk.mark_completed(TODAY)

    owner = Owner("Jordan", constraint=Constraint(available_minutes=120))
    owner.add_pet(pet)

    plan_today    = Planner().generate_plan(owner, TODAY)
    plan_tomorrow = Planner().generate_plan(owner, TOMORROW)

    today_types    = [t.task_type for t in plan_today.scheduled_tasks]
    tomorrow_types = [t.task_type for t in plan_tomorrow.scheduled_tasks]

    assert "walk" not in today_types,    "completed task must not be re-scheduled today"
    assert "walk" in tomorrow_types,     "daily task must reappear in tomorrow's plan"


def test_conflict_detection_flags_duplicate_time_windows():
    """
    REQUIREMENT: Conflict detection — the Scheduler flags tasks scheduled at the same time.

    What this tests
    ---------------
    detect_conflicts() must return at least one warning when two tasks belonging
    to the same pet are placed in the same time window.  The warning identifies
    the pet by name and the window where the clash occurs.

    Why it matters
    --------------
    Without conflict detection, a pet owner would see a plan that is physically
    impossible — e.g., "walk Rex at 8 am AND groom Rex at 8 am".  The warning
    doesn't block the plan (the system stays usable) but it surfaces the problem
    so the owner can adjust window assignments.

    How to read the assertion
    -------------------------
    We build a plan manually with two tasks for "Rex" both in "morning", then
    call detect_conflicts().  We assert (a) at least one warning is returned,
    and (b) the warning mentions both the pet name and the window, so the owner
    knows exactly what conflicts.
    """
    planner   = Planner()
    pet       = Pet("Rex", "dog", 2)
    walk      = task(task_type="walk",  duration=20, window="morning")
    groom     = task(task_type="groom", duration=15, window="morning")
    pet.add_task(walk)
    pet.add_task(groom)

    owner = Owner("Sam", constraint=Constraint(available_minutes=999))
    owner.add_pet(pet)

    # Build the plan manually so we control exactly which tasks are "scheduled"
    plan = DailyPlan(plan_date=TODAY)
    plan.add_scheduled_task(walk)
    plan.add_scheduled_task(groom)

    conflicts = planner.detect_conflicts(plan, owner.constraint, owner)

    assert len(conflicts) > 0,                              "expected at least one conflict warning"
    assert any("Rex" in c for c in conflicts),              "warning must name the pet"
    assert any("morning" in c for c in conflicts),          "warning must name the window"


# ---------------------------------------------------------------------------
# 8 – filter_tasks
# ---------------------------------------------------------------------------

def test_filter_tasks_by_type():
    """filter_tasks(task_type=...) returns only tasks of that type."""
    planner = Planner()
    tasks = [task(task_type="walk"), task(task_type="feed"), task(task_type="walk")]
    result = planner.filter_tasks(tasks, task_type="walk")
    assert all(t.task_type == "walk" for t in result)
    assert len(result) == 2


def test_filter_tasks_no_match_returns_empty():
    """Edge: a filter that matches nothing returns an empty list without error."""
    planner = Planner()
    tasks = [task(task_type="walk"), task(task_type="feed")]
    assert planner.filter_tasks(tasks, task_type="groom") == []


def test_filter_tasks_by_pet():
    """filter_tasks(pet=...) returns only tasks belonging to that pet."""
    planner = Planner()
    pet1 = Pet("Rex",   "dog", 2)
    pet2 = Pet("Kitty", "cat", 3)
    t1 = task(task_type="walk")
    t2 = task(task_type="feed")
    pet1.add_task(t1)
    pet2.add_task(t2)

    all_tasks = [t1, t2]
    result = planner.filter_tasks(all_tasks, pet=pet1)
    assert result == [t1]


def test_filter_tasks_combined_filters():
    """Multiple filters are AND-combined: only tasks matching all criteria are returned."""
    planner = Planner()
    pet = Pet("Mochi", "dog", 3)
    walk_morning = task(task_type="walk", window="morning")
    walk_evening = task(task_type="walk", window="evening")
    feed_morning = task(task_type="feed", window="morning")
    for t in [walk_morning, walk_evening, feed_morning]:
        pet.add_task(t)

    result = planner.filter_tasks(
        [walk_morning, walk_evening, feed_morning],
        pet=pet,
        task_type="walk",
    )
    # Both walks belong to the pet; feed is excluded by task_type filter
    assert len(result) == 2
    assert all(t.task_type == "walk" for t in result)
