from datetime import date, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pawpal_system import CareTask, Pet


# ---------------------------------------------------------------------------
# Test 1 – Task Completion
# ---------------------------------------------------------------------------

def test_mark_completed_updates_last_completed_on():
    """mark_completed() should record the date the task was done."""
    task = CareTask(
        task_type="walk",
        duration_minutes=20,
        priority="high",
        frequency="daily",
        time_window="morning",
    )
    assert task.last_completed_on is None

    today = date.today()
    task.mark_completed(today)

    assert task.last_completed_on == today


def test_mark_completed_makes_task_not_due_same_day():
    """A daily task completed today should not be due again today."""
    today = date.today()
    task = CareTask(
        task_type="feed",
        duration_minutes=10,
        priority="high",
        frequency="daily",
        time_window="morning",
    )
    task.mark_completed(today)

    assert task.is_due(today) is False


# ---------------------------------------------------------------------------
# Test 1c – Auto-rescheduling via timedelta
# ---------------------------------------------------------------------------

def test_daily_task_is_due_next_day_after_completion():
    """A daily task completed today should become due again tomorrow."""
    today    = date.today()
    tomorrow = today + timedelta(days=1)
    task = CareTask("walk", 20, "high", "daily", "morning")

    task.mark_completed(today)

    assert task.next_due_on == tomorrow
    assert task.is_due(today)     is False
    assert task.is_due(tomorrow)  is True


def test_weekly_task_schedules_seven_days_ahead():
    """A weekly task completed today should not be due for 7 days."""
    today        = date.today()
    in_six_days  = today + timedelta(days=6)
    in_seven     = today + timedelta(days=7)
    task = CareTask("groom", 20, "low", "weekly", "afternoon")

    task.mark_completed(today)

    assert task.next_due_on == in_seven
    assert task.is_due(in_six_days) is False
    assert task.is_due(in_seven)    is True


def test_twice_daily_still_due_after_first_completion_and_done_after_second():
    """twice_daily: due again same day after 1st completion; not due until tomorrow after 2nd."""
    today    = date.today()
    tomorrow = today + timedelta(days=1)
    task = CareTask("feed", 10, "high", "twice_daily", "morning")

    task.mark_completed(today)          # first dose
    assert task.is_due(today)    is True    # still needs second dose
    assert task.next_due_on      == today

    task.mark_completed(today)          # second dose
    assert task.is_due(today)    is False   # fully done for today
    assert task.next_due_on      == tomorrow
    assert task.is_due(tomorrow) is True    # due again tomorrow


# ---------------------------------------------------------------------------
# Test 2 – Task Addition
# ---------------------------------------------------------------------------

def test_add_task_increases_pet_task_count():
    """Adding a task to a Pet should increase its task list by one."""
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.tasks) == 0

    pet.add_task(CareTask(
        task_type="walk",
        duration_minutes=20,
        priority="high",
        frequency="daily",
        time_window="morning",
    ))

    assert len(pet.tasks) == 1


def test_add_multiple_tasks_all_appear_on_pet():
    """All added tasks should be retrievable from the pet's task list."""
    pet = Pet(name="Luna", species="cat", age=5)
    task_types = ["feed", "med", "groom"]

    for t in task_types:
        pet.add_task(CareTask(
            task_type=t,
            duration_minutes=10,
            priority="medium",
            frequency="daily",
            time_window="any",
        ))

    assert len(pet.tasks) == 3
    assert [t.task_type for t in pet.tasks] == task_types
