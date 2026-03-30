from datetime import date
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
