from datetime import date, timedelta
from pawpal_system import CareTask, Pet, Owner, Constraint, Planner


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_task_list(title: str, tasks: list[CareTask]) -> None:
    width = 52
    print(f"\n  {title}")
    print(f"  {'─' * (width - 2)}")
    if not tasks:
        print("  (none)")
        return
    print(f"  {'TASK':<14} {'WINDOW':<12} {'PRIORITY':<8}  {'MIN':>4}  REQ")
    print(f"  {'─'*14} {'─'*12} {'─'*8}  {'─'*4}  {'─'*3}")
    for t in tasks:
        print(
            f"  {t.task_type:<14} {t.time_window:<12} {t.priority:<8}"
            f"  {t.duration_minutes:>4}  {'yes' if t.required else 'no'}"
        )


def print_schedule(plan) -> None:
    width = 52
    today_str = plan.plan_date.strftime("%A, %B %d %Y")
    print()
    print("=" * width)
    print(f"  PawPal+  |  Today's Schedule  |  {today_str}")
    print("=" * width)

    if plan.schedule_blocks:
        for block in plan.schedule_blocks:
            print(f"  {block}")
    print()

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

    if plan.deferred_tasks:
        print()
        print("  DEFERRED / SKIPPED:")
        for task, reason in plan.deferred_tasks:
            print(f"  - {task.task_type:<14} ({reason})")

    if plan.conflicts:
        print()
        print("  CONFLICTS DETECTED:")
        for c in plan.conflicts:
            print(f"  ! {c}")

    print("=" * width)
    print("  * = required task")
    print("=" * width)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    today = date.today()
    planner = Planner()

    # --- Pets ---
    mochi = Pet(name="Mochi", species="Dog", age=3, health_notes="Allergic to chicken")
    luna  = Pet(name="Luna",  species="Cat", age=5, health_notes="Needs joint supplement")

    # Tasks added INTENTIONALLY OUT OF ORDER to prove sort_by_time works
    # Mochi — evening tasks first, morning last
    mochi.add_task(CareTask("enrichment", 15, "medium", "daily",       "afternoon", required=False,
                             notes="Puzzle feeder or sniff mat"))
    mochi.add_task(CareTask("feed",       10, "high",   "twice_daily", "evening",   required=True))
    mochi.add_task(CareTask("walk",       25, "high",   "daily",       "morning",   required=True,
                             notes="At least 20 min"))
    mochi.add_task(CareTask("med",         5, "high",   "daily",       "morning",   required=True,
                             notes="Allergy pill"))
    mochi.add_task(CareTask("feed",       10, "high",   "twice_daily", "morning",   required=True))

    # Luna — also scrambled: groom (afternoon) → feed (morning) → med (morning) → feed (evening)
    luna.add_task(CareTask("groom",  20, "low",    "weekly",      "afternoon", required=False,
                            notes="Brush coat"))
    luna.add_task(CareTask("feed",    5, "high",   "twice_daily", "morning",   required=True))
    luna.add_task(CareTask("med",     5, "high",   "daily",       "morning",   required=True,
                            notes="Joint supplement in wet food"))
    luna.add_task(CareTask("feed",    5, "high",   "twice_daily", "evening",   required=True))

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

    # Collect every task across both pets for demo purposes
    all_tasks = mochi.tasks + luna.tasks

    # -----------------------------------------------------------------------
    # Demo 0 — auto-rescheduling via timedelta
    # -----------------------------------------------------------------------
    print("\n" + "=" * 52)
    print("  DEMO 0 — auto-rescheduling with timedelta")
    print("=" * 52)

    demo_tasks = [
        CareTask("walk",  25, "high", "daily",       "morning"),
        CareTask("groom", 20, "low",  "weekly",      "afternoon"),
        CareTask("feed",  10, "high", "twice_daily",  "morning"),
    ]

    print(f"\n  {'TASK':<10} {'FREQ':<12} {'mark_completed(today)':<22} {'next_due_on'}")
    print(f"  {'─'*10} {'─'*12} {'─'*22} {'─'*14}")
    for t in demo_tasks:
        t.mark_completed(today)
        print(f"  {t.task_type:<10} {t.frequency:<12} is_due(today)={str(t.is_due(today)):<9}  {t.next_due_on}")

    # twice_daily needs a second call to fully complete it
    feed_task = demo_tasks[2]
    feed_task.mark_completed(today)
    print(f"  {'feed':<10} {'(2nd dose)':<12} is_due(today)={str(feed_task.is_due(today)):<9}  {feed_task.next_due_on}")

    tomorrow = today + timedelta(days=1)
    print(f"\n  Checking is_due(tomorrow={tomorrow}):")
    for t in demo_tasks:
        print(f"    {t.task_type:<10} {t.frequency:<12} → {t.is_due(tomorrow)}")

    # -----------------------------------------------------------------------
    # Demo 1 — sort_by_time
    # Tasks were added in scrambled order; sort_by_time reorders them
    # -----------------------------------------------------------------------
    print("\n" + "=" * 52)
    print("  DEMO 1 — sort_by_time()")
    print("=" * 52)
    print_task_list("As-added order (scrambled):", all_tasks)
    sorted_tasks = planner.sort_by_time(all_tasks)
    print_task_list("After sort_by_time():", sorted_tasks)

    # -----------------------------------------------------------------------
    # Demo 2 — filter_tasks
    # -----------------------------------------------------------------------
    print("\n" + "=" * 52)
    print("  DEMO 2 — filter_tasks()")
    print("=" * 52)

    # Mark Mochi's walk as done today to make the completed filter interesting
    mochi.tasks[2].mark_completed(today)   # walk

    print_task_list(
        "filter: pet=Mochi (all Mochi tasks):",
        planner.filter_tasks(all_tasks, pet=mochi),
    )
    print_task_list(
        "filter: completed_on=today:",
        planner.filter_tasks(all_tasks, completed_on=today),
    )
    print_task_list(
        "filter: pending_on=today (due but not yet done):",
        planner.filter_tasks(all_tasks, pending_on=today),
    )
    print_task_list(
        "filter: task_type='feed':",
        planner.filter_tasks(all_tasks, task_type="feed"),
    )
    print_task_list(
        "filter: pet=Luna + pending_on=today (combined):",
        planner.filter_tasks(all_tasks, pet=luna, pending_on=today),
    )

    # -----------------------------------------------------------------------
    # Demo 3 — full schedule
    # -----------------------------------------------------------------------
    plan = planner.generate_plan(jordan, today)
    print_schedule(plan)

    # -----------------------------------------------------------------------
    # Demo 4 — conflict detection
    # Two tasks intentionally stacked in the same window for the same pet,
    # plus a cross-pet required collision, plus a preference-rule violation.
    # -----------------------------------------------------------------------
    print("\n" + "=" * 52)
    print("  DEMO 4 — conflict detection warnings")
    print("=" * 52)

    rex   = Pet(name="Rex",   species="Dog", age=2)
    kitty = Pet(name="Kitty", species="Cat", age=4)

    # Same-pet overlap: Rex has walk + groom both in "morning"
    rex.add_task(CareTask("walk",  30, "high",   "daily", "morning", required=True))
    rex.add_task(CareTask("groom", 20, "medium", "daily", "morning", required=False,
                           notes="Intentionally same window as walk"))

    # Cross-pet collision: Kitty also has a required task in "morning"
    kitty.add_task(CareTask("feed", 10, "high", "daily", "morning", required=True))
    kitty.add_task(CareTask("med",   5, "high", "daily", "morning", required=True))

    # Preference-rule violation: walk in "evening" when rule says "no walks after 21:00"
    rex.add_task(CareTask("walk", 20, "high", "daily", "evening", required=True,
                           notes="Evening walk — violates preference rule"))

    sam = Owner(
        name="Sam",
        constraint=Constraint(
            available_minutes=120,
            max_tasks_per_day=10,
            preference_rules=["no walks after 21:00"],
        ),
    )
    sam.add_pet(rex)
    sam.add_pet(kitty)

    conflict_plan = planner.generate_plan(sam, today)

    print("\n  Scheduled tasks:")
    for t in conflict_plan.scheduled_tasks:
        pet_label = next(
            (p.name for p in sam.pets if t in p.tasks), "?"
        )
        print(f"    [{pet_label}] {t.task_type:<12} window={t.time_window}")

    print()
    if conflict_plan.conflicts:
        for warning in conflict_plan.conflicts:
            print(f"  {warning}")
    else:
        print("  No conflicts detected.")


if __name__ == "__main__":
    main()
