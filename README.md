# PawPal+ (Module 2 Project)

**PawPal+** is a Streamlit app that helps a busy pet owner build a realistic daily care schedule. Enter your pets, add tasks with durations and priorities, set your available time, and get a conflict-aware plan in one click — with plain-English explanations for every decision.

---

## Features

### 📸 Demo

<a href="/pawpal_demo.png" target="_blank"><img src='/pawpal_demo.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

### Owner & constraint management

Define your daily time budget (minutes available), a per-day task cap, and free-text preference rules such as `"no walks after 21:00"`. All settings persist in Streamlit session state for the life of the browser tab.

### Multi-pet support

Add any number of pets (dog, cat, or other) with name, species, age, and optional health notes. Each pet maintains its own independent task list; the scheduler aggregates across all pets automatically.

### Task library

Create tasks of five types — `walk`, `feed`, `med`, `groom`, `enrichment` — each with a duration, priority (`high / medium / low`), preferred time window, required flag, and recurrence frequency.

### Priority-ranked scheduling

`Planner.rank_tasks` sorts all due tasks by `required` flag first, then by priority (`high → medium → low`), so critical tasks like medications are always considered before optional ones.

### Time-budget fitting

`Planner.fit_to_time_budget` uses a greedy O(n) pass to select as many tasks as possible within the owner's available minutes and daily task cap. Tasks that don't fit are recorded as *deferred* with a plain-English reason (e.g. "needs 40 min, only 10 min left") rather than silently dropped. Gap-filling is supported: a smaller lower-priority task can still be picked up after a large one is skipped.

### Chronological ordering

`Planner.sort_by_time` sorts any task list by named time window (`morning → midday → afternoon → evening → any`) so the final schedule reads in the order the owner will actually do things. Unknown window labels sort last rather than raising an error.

### Daily recurrence

`CareTask.mark_completed` uses `timedelta` to automatically advance `next_due_on` after each completion:

- **daily** → next day
- **twice_daily** → same day after the first dose; next day after the second
- **weekly** → seven days later

A completed task disappears from today's plan and reappears automatically on the correct future date.

### Flexible task filtering

`Planner.filter_tasks` accepts keyword-only arguments (`pet`, `completed_on`, `pending_on`, `task_type`) that can be combined freely. The live filter panel in the UI uses this to answer questions like "what walk tasks does Mochi still have today?"

### Conflict detection

`Planner.detect_conflicts` returns warning strings for four problem types — never crashes the app:

| Warning | Meaning |
| --- | --- |
| 🕐 Window overload | A single time slot has more than 60 minutes of tasks |
| 🔁 Same-pet overlap | One pet has two or more tasks in the same window simultaneously |
| ⚡ Cross-pet collision | Two different pets both have required tasks in the same window |
| 🚫 Preference violation | A task type is placed in a window the owner has ruled out |

### Schedule blocks display

The generated plan is grouped into time-window cards (`Morning`, `Midday`, `Afternoon`, `Evening`) so the owner sees a scannable daily structure, not just a flat list.

---

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

## Testing PawPal+

### Run the tests

```bash
python -m pytest
```

Add `-v` for a line-by-line breakdown of every test:

```bash
python -m pytest tests/test_pawpal.py -v
```

### What the tests cover

The suite in `tests/test_pawpal.py` contains **35 tests** across eight areas:

| Area | Tests | What is verified |
| --- | --- | --- |
| Task completion | 6 | `mark_completed` records the date; `next_due_on` is set via `timedelta` for `daily`, `twice_daily`, and `weekly` frequencies |
| Pet management | 4 | Tasks are added and retrieved correctly; a pet or owner with no tasks returns an empty list without crashing |
| `rank_tasks` | 3 | Required tasks always outrank optional ones; within the same required tier, `high → medium → low`; empty input returns empty output |
| `fit_to_time_budget` | 5 | Basic selection; gap-filling (small task fits after a large one is skipped); exact boundary (`≤` not `<`); nothing fits; `max_tasks_per_day` cap |
| `sort_by_time` | 2 | Scrambled windows sort to `morning → afternoon → evening → any`; unknown window names sort last |
| `detect_conflicts` | 4 | No conflicts → empty list; window overload; same-pet overlap; cross-pet collision |
| `generate_plan` integration | 4 | Completed tasks are excluded from today's plan; a daily task reappears in tomorrow's plan (end-to-end recurrence); all tasks deferred when budget is too tight; no pets → no crash |
| `filter_tasks` | 4 | Filter by type, by pet, no-match returns empty, combined filters are AND-ed |

### Confidence level

#### ★★★★☆ (4 / 5)

The happy paths and the most critical edge cases are well covered: recurrence logic, priority ordering, time-budget fitting (including the gap-filling behaviour), and all four conflict-detection checks each have dedicated tests. The end-to-end integration test verifies that a completed task disappears from today's plan and reappears in tomorrow's.

One star is withheld because:

- **Time windows are labels, not clock times.** The system cannot detect a true clock-level overlap (e.g., two 30-minute tasks both labelled "morning" but one starting at 8:00 and the other at 8:15). Conflict warnings are based on window names only.
- **No UI tests.** `app.py` session-state wiring and Streamlit form behaviour are not covered by the pytest suite.
- **Preference-rule parsing is pattern-based.** Rules like `"no walks after 21:00"` are matched by keyword; free-text rules that don't follow the `"no <type> after <time>"` pattern are silently ignored.

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
