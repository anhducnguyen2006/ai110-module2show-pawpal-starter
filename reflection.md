# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

The design has six classes with clear, separated responsibilities:

- **Owner** — holds the owner's name and free-text preferences (e.g. "no walks after 9pm"). Acts as the root of the object graph: it owns a list of Pets and a Constraint.
- **Constraint** — a dedicated config object that captures all scheduling limits: available minutes per day, blocked time windows, max tasks per day, and structured preference rules. Keeping this separate from Owner means the scheduler can read one object instead of picking fields off the owner.
- **Pet** — stores a pet's identity and health notes, and owns a list of CareTasks. Responsible for knowing which tasks are due on a given date.
- **CareTask** — a single care activity (walk, feed, med, groom, enrichment). Holds scheduling metadata (duration, priority, frequency, time window, required flag) and tracks when it was last completed. Knows how to report whether it is due.
- **DailyPlan** — the output of the scheduler. Holds the tasks that were scheduled, the tasks that were deferred (with reasons), time-block labels, and a rationale string. Exposes a computed `total_minutes_used` so the scheduler can check budget at any time.
- **Planner** — the scheduling engine. Takes an Owner (with its Pets and Constraint) and a date, ranks tasks by priority and preferences, fits them into the time budget, and returns a DailyPlan.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Three changes were made after reviewing the skeleton against the UI and scheduling logic:

1. **`priority` changed from `int` to `str`** — The original UML used an integer (1–3). The Streamlit UI in `app.py` collects priority as `"low"`, `"medium"`, or `"high"`. Keeping an int would have required a conversion layer at every boundary; using the same string values the UI produces removes that friction.

2. **`Planner.generate_plan` dropped the `pets` parameter** — The original signature was `generate_plan(owner, pets, on_date)`. Since `Owner` already holds a `pets` list, passing pets separately was redundant and created a potential bug: a caller could pass pets that don't belong to the owner. The method now reads `owner.pets` directly, making the relationship explicit and safe.

3. **`DailyPlan.total_minutes_used` added as a computed property** — The scheduler needs to check remaining time budget after each task is added. Without this, `fit_to_time_budget` would have to recompute the sum on every iteration. A single `@property` that sums `duration_minutes` across `scheduled_tasks` solves this cleanly and keeps the budget logic out of `Planner`.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

**Tradeoff 1 — Time windows are labels, not clock intervals.**

The scheduler assigns tasks to named slots (`"morning"`, `"afternoon"`, `"evening"`) rather than specific start and end times like `08:00–08:30`. Conflict detection treats any two tasks sharing a window label as if they are simultaneous, which produces false positives: a pet owner can absolutely walk the dog at 8 am and feed the cat at 8:30 am — both are "morning" tasks but they do not actually overlap.

This is reasonable for a pet care planning app because the goal is to give the owner a rough daily structure, not a minute-by-minute calendar. Requiring precise clock times would make data entry far more burdensome and would give a false sense of precision (the owner does not know in advance whether the dog walk will take 20 or 35 minutes). The window-label approach is honest about that uncertainty, at the cost of occasional spurious warnings that the owner can safely ignore.

**Tradeoff 2 — Greedy selection is not optimal packing.**

`fit_to_time_budget` picks tasks in priority order and takes each one if it still fits in the time budget. This is O(n) but does not guarantee the maximum number of tasks or maximum value. Example: budget = 50 min, tasks = [A = 40 min high, B = 30 min medium, C = 20 min medium]. Greedy picks A (40 min used), then skips B and C because neither fits in the remaining 10 min. The optimal solution would be B + C = 50 min (two tasks instead of one). For a home pet-care scenario with fewer than ~15 tasks per day, greedy is fast and predictable enough; a full knapsack solver would be harder to debug and explain to the user without meaningful benefit.

**AI review note (section 3 cross-reference):** When asked to simplify `fit_to_time_budget`, the AI suggested replacing the explicit loop with `itertools.accumulate`. That version was more concise but semantically incorrect — accumulate computes a running prefix sum and would silently exclude tasks C and D even if they individually fit after a large task B was skipped. The explicit loop was kept because correctness outweighs brevity here. The `defaultdict` suggestion for `detect_conflicts` was accepted because it genuinely improved readability (`window_minutes[w] += n` vs `window_minutes.get(w, 0) + n`) without any behavioral change.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

The test suite in `tests/test_pawpal.py` covers 35 tests across eight areas:

1. **Task completion and recurrence** — `mark_completed` records the date and sets `next_due_on` correctly for `daily`, `weekly`, and `twice_daily` frequencies. The `twice_daily` case was the trickiest: the task must remain due on the same day after the first completion, and advance to the next day only after the second. These tests mattered because an off-by-one bug in `next_due_on` would silently skip a pet's medication or double-schedule it.

2. **Pet and owner management** — Tasks are stored in the right pet's list; an owner or pet with no tasks returns an empty list without raising. Guarding the empty-list case was important because `generate_plan` iterates over these lists unconditionally.

3. **`rank_tasks`** — Required tasks always outrank optional ones regardless of priority level; within the required tier, tasks sort `high → medium → low`. An empty input returns empty output. Getting this right is the foundation of the entire scheduling pipeline — if a required medication ranked below an optional enrichment activity, the owner would get the wrong plan.

4. **`fit_to_time_budget`** — Covers basic selection, gap-filling (a smaller task can still be picked up after a large one is skipped), the exact boundary condition (`≤` not `<`), the nothing-fits edge case, and the `max_tasks_per_day` cap. The gap-filling test was the most important: the greedy algorithm's ability to keep scanning after a rejection is what separates it from a simple prefix-fill.

5. **`sort_by_time`** — Scrambled windows are sorted to the canonical order; an unknown window label sorts last rather than raising a `ValueError`. The unknown-window case prevents a crash if a user types a custom window name.

6. **`detect_conflicts`** — Four distinct warnings are each verified: no-conflict happy path, window overload (> 60 min in one slot), same-pet overlap, and cross-pet collision. Conflict detection is the feature most likely to produce false positives, so each case needed an isolated, deterministic test that builds the plan manually.

7. **`generate_plan` integration** — End-to-end tests confirm that a completed task disappears from today's plan, a daily task reappears in tomorrow's plan (the full recurrence pipeline, not just `is_due`), all tasks are deferred when the budget is 5 minutes, and an owner with no pets produces an empty plan without crashing.

8. **`filter_tasks`** — Filtering by type, by pet, no-match returning empty, and combined AND-filters are each tested. These tests matter because the live UI filter panel calls these methods directly; a silent logic error would show the user the wrong task list.

**b. Confidence**

**★★★★☆ (4 / 5)**

The happy paths and the most important edge cases are well covered. The recurrence end-to-end test (`test_recurrence_logic_completed_daily_task_reappears_in_tomorrows_plan`) gives particular confidence because it runs the full `generate_plan` pipeline twice rather than checking `is_due` in isolation.

One star is withheld because:

- **Time windows are labels, not clock times.** A true overlap between two "morning" tasks (one at 8:00, one at 8:15) cannot be detected with the current model.
- **No UI tests.** `app.py` session-state wiring, form submission, and widget interactions are not covered by pytest.
- **Preference-rule parsing is pattern-matched.** Only rules matching `"no <type> after <time>"` are understood; a rule phrased differently is silently ignored.

If I had more time I would add: a preference-rule violation test (the fourth conflict type has no dedicated unit test), a `twice_daily` task in `generate_plan` to verify it appears twice before advancing to the next day, and a test for `explain_choices` output format.

---

## 5. Reflection

**a. What went well**

The clean separation between `pawpal_system.py` and `app.py` paid off throughout the project. Because all scheduling logic lived in pure Python classes with no Streamlit dependencies, every algorithm could be developed and tested in isolation before touching the UI. The `Planner` methods (`rank_tasks`, `fit_to_time_budget`, `sort_by_time`, `filter_tasks`, `detect_conflicts`) were each small enough to reason about independently, which made both writing tests and debugging straightforward. The session-state vault pattern in `app.py` also worked well — keeping `owner`, `pets`, `tasks`, and `plan` as explicit keys made it easy to trace exactly what data each form section was reading and writing.

**b. What you would improve**

The biggest limitation is that time windows are labels, not actual clock intervals. In a next iteration I would replace the five named windows with a proper `(start_time, end_time)` representation, which would allow genuine overlap detection (two tasks whose time ranges intersect) and more useful conflict messages. I would also replace the pattern-matched preference rule parser with a structured format — for example a `PreferenceRule` dataclass with `task_type`, `operator`, and `cutoff_time` fields — so rules like "no walks after 21:00" are validated at entry time rather than silently ignored if the phrasing doesn't match. Finally, I'd add a simple edit/delete flow for tasks in the UI; currently there is no way to remove a task once it has been added.

**c. Key takeaway**

The most important thing I learned is that AI suggestions need to be evaluated against the specific invariants of the algorithm, not just their surface-level readability. When the AI suggested replacing `fit_to_time_budget`'s explicit loop with `itertools.accumulate`, the suggestion looked cleaner — but `accumulate` computes a prefix sum, which would have permanently excluded any task following a large rejected one, breaking the gap-filling behavior entirely. Catching that required understanding *why* the explicit loop was written the way it was, not just reading the code. AI is most useful for generating options quickly; the developer's job is to know which option is actually correct.
