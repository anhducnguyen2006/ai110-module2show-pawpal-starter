# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Smarter Scheduling

The core scheduling logic lives in `pawpal_system.py`. Beyond a basic task list, the planner includes several algorithms that make the schedule more useful for a real pet owner.

**Priority-ranked selection**
`Planner.rank_tasks` sorts all due tasks by `required` flag first, then priority (`high → medium → low`). This ensures critical tasks (medications, feeding) are always considered before optional ones.

**Time-budget fitting**
`Planner.fit_to_time_budget` uses a greedy O(n) pass to select as many tasks as possible within the owner's available minutes and daily task cap. Tasks that don't fit are deferred with a plain-English reason rather than silently dropped.

**Chronological ordering**
`Planner.sort_by_time` sorts any task list by named time window (`morning → midday → afternoon → evening → any`) using a lambda key, so the final schedule reads in the order the owner will actually do things.

**Flexible filtering**
`Planner.filter_tasks` accepts keyword-only arguments (`pet`, `completed_on`, `pending_on`, `task_type`) that can be combined freely. Useful for answering questions like "what does Mochi still need today?" or "which tasks are already done?"

**Recurring task auto-scheduling**
`CareTask.mark_completed` uses `timedelta` to automatically set `next_due_on` after each completion — one day later for `daily` tasks, seven days later for `weekly`, and same-day / next-day for `twice_daily` depending on whether the first or second dose has been given.

**Conflict detection**
`Planner.detect_conflicts` returns warning strings (never crashes) for four problem types:

- Window overload — more than 60 minutes of tasks in a single time slot
- Same-pet overlap — one pet has two or more tasks in the same window simultaneously
- Cross-pet collision — two different pets both have required tasks in the same window
- Preference-rule violations — a task type is scheduled in a window the owner has ruled out

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
