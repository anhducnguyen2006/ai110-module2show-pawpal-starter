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

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
