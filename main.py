from datetime import date
from pawpal_system import CareTask, Pet, Owner, Constraint, Planner


def print_schedule(plan) -> None:
    width = 52
    today_str = plan.plan_date.strftime("%A, %B %d %Y")

    print()
    print("=" * width)
    print(f"  PawPal+  |  Today's Schedule  |  {today_str}")
    print("=" * width)

    # Schedule blocks (grouped by time window)
    if plan.schedule_blocks:
        for block in plan.schedule_blocks:
            print(f"  {block}")
    print()

    # Scheduled tasks table
    print(f"  {'TASK':<14} {'TIME':>6}  {'PRIORITY':<8}  {'WINDOW'}")
    print(f"  {'-'*14} {'-'*6}  {'-'*8}  {'-'*12}")
    for task in plan.scheduled_tasks:
        req = "*" if task.required else " "
        print(
            f"{req} {task.task_type:<14} {task.duration_minutes:>4} min  "
            f"{task.priority:<8}  {task.time_window}"
        )

    print()
    print(f"  Time used : {plan.total_minutes_used} min")
    print(f"  Summary   : {plan.rationale}")

    # Deferred tasks (if any)
    if plan.deferred_tasks:
        print()
        print("  DEFERRED / SKIPPED:")
        for task, reason in plan.deferred_tasks:
            print(f"  - {task.task_type:<14} ({reason})")

    print("=" * width)
    print("  * = required task")
    print("=" * width)
    print()


def main() -> None:
    today = date.today()

    # --- Pets ---
    mochi = Pet(name="Mochi", species="Dog", age=3, health_notes="Allergic to chicken")
    luna  = Pet(name="Luna",  species="Cat", age=5, health_notes="Needs joint supplement")

    # --- Tasks for Mochi ---
    mochi.add_task(CareTask(
        task_type="walk", duration_minutes=25, priority="high",
        frequency="daily", time_window="morning", required=True,
        notes="At least 20 min, avoid the park on rainy days",
    ))
    mochi.add_task(CareTask(
        task_type="feed", duration_minutes=10, priority="high",
        frequency="twice_daily", time_window="morning", required=True,
    ))
    mochi.add_task(CareTask(
        task_type="feed", duration_minutes=10, priority="high",
        frequency="twice_daily", time_window="evening", required=True,
    ))
    mochi.add_task(CareTask(
        task_type="med", duration_minutes=5, priority="high",
        frequency="daily", time_window="morning", required=True,
        notes="Allergy pill — hide in a treat",
    ))
    mochi.add_task(CareTask(
        task_type="enrichment", duration_minutes=15, priority="medium",
        frequency="daily", time_window="afternoon", required=False,
        notes="Puzzle feeder or sniff mat",
    ))

    # --- Tasks for Luna ---
    luna.add_task(CareTask(
        task_type="feed", duration_minutes=5, priority="high",
        frequency="twice_daily", time_window="morning", required=True,
    ))
    luna.add_task(CareTask(
        task_type="feed", duration_minutes=5, priority="high",
        frequency="twice_daily", time_window="evening", required=True,
    ))
    luna.add_task(CareTask(
        task_type="med", duration_minutes=5, priority="high",
        frequency="daily", time_window="morning", required=True,
        notes="Joint supplement mixed into wet food",
    ))
    luna.add_task(CareTask(
        task_type="groom", duration_minutes=20, priority="low",
        frequency="weekly", time_window="afternoon", required=False,
        notes="Brush coat — she tolerates it after a play session",
    ))

    # --- Owner ---
    jordan = Owner(
        name="Jordan",
        preferences=["no walks after 21:00", "prefer morning meds"],
        constraint=Constraint(
            available_minutes=90,
            max_tasks_per_day=8,
            blocked_times=["22:00-07:00"],
            preference_rules=["no walks after 21:00"],
        ),
    )
    jordan.add_pet(mochi)
    jordan.add_pet(luna)

    # --- Generate and display plan ---
    plan = Planner().generate_plan(jordan, today)
    print_schedule(plan)


if __name__ == "__main__":
    main()
