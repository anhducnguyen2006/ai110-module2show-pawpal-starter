import streamlit as st
from datetime import date
from pawpal_system import CareTask, Pet, Owner, Constraint, Planner

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Session-state vault — initialised ONCE per browser session
# ---------------------------------------------------------------------------
if "owner"   not in st.session_state: st.session_state.owner  = None
if "pets"    not in st.session_state: st.session_state.pets   = []
if "tasks"   not in st.session_state: st.session_state.tasks  = []
if "plan"    not in st.session_state: st.session_state.plan   = None

_planner = Planner()   # shared, stateless — safe to create at module level

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🐾 PawPal+")
st.caption("A daily pet-care planner that fits tasks to your schedule.")
st.divider()

# ---------------------------------------------------------------------------
# Section 1 – Owner
# ---------------------------------------------------------------------------
st.subheader("1. Owner")

with st.form("owner_form"):
    owner_name    = st.text_input("Your name",
                        value=st.session_state.owner.name if st.session_state.owner else "")
    avail_minutes = st.number_input("Available minutes today",
                        min_value=10, max_value=480, value=90, step=10)
    max_tasks     = st.number_input("Max tasks per day",
                        min_value=1, max_value=20, value=8)
    pref_input    = st.text_input("Preference rules (comma-separated)",
                        value="no walks after 21:00",
                        help='e.g. "no walks after 21:00, no grooms after 20:00"')
    save_owner    = st.form_submit_button("Save owner")

if save_owner:
    prefs = [p.strip() for p in pref_input.split(",") if p.strip()]
    st.session_state.owner = Owner(
        name=owner_name,
        preferences=prefs,
        constraint=Constraint(
            available_minutes=int(avail_minutes),
            max_tasks_per_day=int(max_tasks),
            preference_rules=prefs,
        ),
    )
    for pet in st.session_state.pets:
        st.session_state.owner.add_pet(pet)
    st.success(f"Owner **{owner_name}** saved — {avail_minutes} min, max {max_tasks} tasks.")

if st.session_state.owner:
    c = st.session_state.owner.constraint
    st.info(
        f"**{st.session_state.owner.name}** · "
        f"{c.available_minutes} min available · "
        f"max {c.max_tasks_per_day} tasks/day"
    )

st.divider()

# ---------------------------------------------------------------------------
# Section 2 – Pets
# ---------------------------------------------------------------------------
st.subheader("2. Pets")

with st.form("pet_form"):
    pet_name    = st.text_input("Pet name", value="Mochi")
    species     = st.selectbox("Species", ["dog", "cat", "other"])
    age         = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
    health      = st.text_input("Health notes (optional)")
    add_pet_btn = st.form_submit_button("Add pet")

if add_pet_btn:
    new_pet = Pet(name=pet_name, species=species, age=int(age), health_notes=health)
    st.session_state.pets.append(new_pet)
    if st.session_state.owner:
        st.session_state.owner.add_pet(new_pet)
    st.success(f"Added **{pet_name}** the {species}.")

if st.session_state.pets:
    for pet in st.session_state.pets:
        st.write(f"- **{pet.name}** ({pet.species}, age {pet.age}) — {len(pet.tasks)} task(s)")
else:
    st.info("No pets added yet.")

st.divider()

# ---------------------------------------------------------------------------
# Section 3 – Tasks
# ---------------------------------------------------------------------------
st.subheader("3. Tasks")

pet_names = [p.name for p in st.session_state.pets]

if not pet_names:
    st.info("Add at least one pet before adding tasks.")
else:
    with st.form("task_form"):
        selected_pet = st.selectbox("Assign to pet", pet_names)
        task_type    = st.selectbox("Task type", ["walk", "feed", "med", "groom", "enrichment"])
        duration     = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority     = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        frequency    = st.selectbox("Frequency", ["daily", "twice_daily", "weekly"])
        time_window  = st.selectbox("Preferred time",
                            ["morning", "midday", "afternoon", "evening", "any"])
        required     = st.checkbox("Required (cannot be skipped)", value=True)
        notes        = st.text_input("Notes (optional)")
        add_task_btn = st.form_submit_button("Add task")

    if add_task_btn:
        new_task = CareTask(
            task_type=task_type,
            duration_minutes=int(duration),
            priority=priority,
            frequency=frequency,
            time_window=time_window,
            required=required,
            notes=notes,
        )
        target_pet = next(p for p in st.session_state.pets if p.name == selected_pet)
        target_pet.add_task(new_task)
        st.session_state.tasks.append(new_task)
        st.success(f"Added **{task_type}** to {selected_pet}.")

    # --- Filter + sort controls ------------------------------------------
    if st.session_state.tasks:
        st.markdown("**View & filter tasks**")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            filter_pet  = st.selectbox("Filter by pet",  ["All"] + pet_names, key="fp")
        with col_b:
            filter_type = st.selectbox("Filter by type",
                            ["All", "walk", "feed", "med", "groom", "enrichment"], key="ft")
        with col_c:
            sort_time   = st.checkbox("Sort by time window", value=True, key="st")

        # Resolve the selected pet object (or None for "All")
        filter_pet_obj = next(
            (p for p in st.session_state.pets if p.name == filter_pet), None
        ) if filter_pet != "All" else None

        # Apply filter_tasks then sort_by_time
        visible = _planner.filter_tasks(
            st.session_state.tasks,
            pet=filter_pet_obj,
            task_type=None if filter_type == "All" else filter_type,
        )
        if sort_time:
            visible = _planner.sort_by_time(visible)

        if visible:
            rows = []
            for t in visible:
                pet_label = next(
                    (p.name for p in st.session_state.pets if t in p.tasks), "?"
                )
                rows.append({
                    "Pet":      pet_label,
                    "Type":     t.task_type,
                    "Window":   t.time_window,
                    "Duration": f"{t.duration_minutes} min",
                    "Priority": t.priority,
                    "Required": "✔" if t.required else "—",
                    "Freq":     t.frequency,
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No tasks match the current filter.")

st.divider()

# ---------------------------------------------------------------------------
# Section 4 – Generate schedule
# ---------------------------------------------------------------------------
st.subheader("4. Generate Today's Schedule")

if st.button("Generate schedule", type="primary"):
    if not st.session_state.owner:
        st.error("Please save an owner first (Section 1).")
    elif not st.session_state.pets or not st.session_state.tasks:
        st.error("Add at least one pet and one task before generating a schedule.")
    else:
        st.session_state.plan = _planner.generate_plan(st.session_state.owner, date.today())

if st.session_state.plan:
    plan = st.session_state.plan

    # --- Conflict warnings (shown first — most urgent) --------------------
    if plan.conflicts:
        st.markdown("##### ⚠️ Scheduling conflicts")
        for warning in plan.conflicts:
            w = warning.lower()
            if "overloaded" in w:
                icon = "🕐"
            elif "same" in w or "overlap" in w:
                icon = "🔁"
            elif "both" in w or "cross" in w:
                icon = "⚡"
            else:
                icon = "🚫"
            # Strip the leading "WARNING: " prefix for cleaner display
            clean = warning.removeprefix("WARNING: ")
            st.warning(f"{icon} {clean}")

    # --- Quick-stats row --------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Scheduled",    len(plan.scheduled_tasks))
    m2.metric("Deferred",     len(plan.deferred_tasks))
    m3.metric("Time used",    f"{plan.total_minutes_used} min")
    avail = st.session_state.owner.constraint.available_minutes
    m4.metric("Time left",    f"{avail - plan.total_minutes_used} min")

    st.caption(plan.rationale)

    # --- Schedule blocks — one st.info card per time window --------------
    if plan.schedule_blocks:
        st.markdown("##### 🗓️ Schedule blocks")
        for block in plan.schedule_blocks:
            window, _, tasks_str = block.partition(":")
            st.info(f"**{window.strip()}** · {tasks_str.strip()}")

    # --- Scheduled tasks table -------------------------------------------
    if plan.scheduled_tasks:
        st.markdown("##### ✅ Scheduled tasks")
        scheduled_rows = [
            {
                "Task":      t.task_type,
                "Window":    t.time_window,
                "Duration":  f"{t.duration_minutes} min",
                "Priority":  t.priority,
                "Required":  "✔" if t.required else "—",
            }
            for t in plan.scheduled_tasks
        ]
        st.dataframe(scheduled_rows, use_container_width=True, hide_index=True)

    # --- Deferred tasks — collapsible so they don't dominate the view ----
    if plan.deferred_tasks:
        with st.expander(f"⏭️ {len(plan.deferred_tasks)} deferred / skipped task(s)"):
            for t, reason in plan.deferred_tasks:
                st.error(f"**{t.task_type}** — {reason}", icon="❌")
