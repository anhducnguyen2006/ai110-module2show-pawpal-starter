import streamlit as st
from datetime import date
from pawpal_system import CareTask, Pet, Owner, Constraint, Planner

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Session-state vault — initialised ONCE per browser session.
# Every Streamlit rerun executes this file top-to-bottom, so we guard each
# key with "if key not in st.session_state" to avoid overwriting live data.
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None          # Owner object, set when form is saved

if "pets" not in st.session_state:
    st.session_state.pets = []             # list[Pet] – survives reruns

if "tasks" not in st.session_state:
    st.session_state.tasks = []            # list[CareTask] – survives reruns

if "plan" not in st.session_state:
    st.session_state.plan = None           # DailyPlan – last generated plan

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🐾 PawPal+")
st.caption("A daily pet-care planner that fits tasks to your schedule.")
st.divider()

# ---------------------------------------------------------------------------
# Section 1 – Owner setup
# ---------------------------------------------------------------------------
st.subheader("1. Owner")

with st.form("owner_form"):
    owner_name      = st.text_input("Your name", value=st.session_state.owner.name if st.session_state.owner else "")
    avail_minutes   = st.number_input("Available minutes today", min_value=10, max_value=480, value=90, step=10)
    max_tasks       = st.number_input("Max tasks per day", min_value=1, max_value=20, value=8)
    save_owner      = st.form_submit_button("Save owner")

if save_owner:
    st.session_state.owner = Owner(
        name=owner_name,
        constraint=Constraint(
            available_minutes=int(avail_minutes),
            max_tasks_per_day=int(max_tasks),
        ),
    )
    # Re-attach any existing pets to the (re-)saved owner
    for pet in st.session_state.pets:
        st.session_state.owner.add_pet(pet)
    st.success(f"Owner **{owner_name}** saved — {avail_minutes} min available, up to {max_tasks} tasks.")

if st.session_state.owner:
    st.info(f"Current owner: **{st.session_state.owner.name}** | "
            f"{st.session_state.owner.constraint.available_minutes} min | "
            f"max {st.session_state.owner.constraint.max_tasks_per_day} tasks")

st.divider()

# ---------------------------------------------------------------------------
# Section 2 – Pets
# ---------------------------------------------------------------------------
st.subheader("2. Pets")

with st.form("pet_form"):
    pet_name    = st.text_input("Pet name", value="Mochi")
    species     = st.selectbox("Species", ["dog", "cat", "other"])
    age         = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
    health      = st.text_input("Health notes (optional)", value="")
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
        selected_pet  = st.selectbox("Assign to pet", pet_names)
        task_type     = st.selectbox("Task type", ["walk", "feed", "med", "groom", "enrichment"])
        duration      = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority      = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        frequency     = st.selectbox("Frequency", ["daily", "twice_daily", "weekly"])
        time_window   = st.selectbox("Preferred time", ["morning", "midday", "afternoon", "evening", "any"])
        required      = st.checkbox("Required (cannot be skipped)", value=True)
        notes         = st.text_input("Notes (optional)", value="")
        add_task_btn  = st.form_submit_button("Add task")

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
        # Attach to the right pet object
        target_pet = next(p for p in st.session_state.pets if p.name == selected_pet)
        target_pet.add_task(new_task)
        st.session_state.tasks.append(new_task)
        st.success(f"Added **{task_type}** to {selected_pet}.")

    if st.session_state.tasks:
        rows = [
            {
                "Pet":      next((p.name for p in st.session_state.pets if t in p.tasks), "?"),
                "Type":     t.task_type,
                "Duration": f"{t.duration_minutes} min",
                "Priority": t.priority,
                "Window":   t.time_window,
                "Required": "yes" if t.required else "no",
            }
            for t in st.session_state.tasks
        ]
        st.table(rows)

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
        plan = Planner().generate_plan(st.session_state.owner, date.today())
        st.session_state.plan = plan

if st.session_state.plan:
    plan = st.session_state.plan

    st.success(plan.rationale)

    if plan.schedule_blocks:
        st.markdown("**Schedule blocks**")
        for block in plan.schedule_blocks:
            st.write(f"- {block}")

    if plan.scheduled_tasks:
        st.markdown("**Scheduled tasks**")
        st.table([
            {
                "Task":     t.task_type,
                "Duration": f"{t.duration_minutes} min",
                "Priority": t.priority,
                "Window":   t.time_window,
                "Required": "yes" if t.required else "no",
            }
            for t in plan.scheduled_tasks
        ])

    if plan.deferred_tasks:
        st.markdown("**Deferred / skipped**")
        for task, reason in plan.deferred_tasks:
            st.write(f"- **{task.task_type}** — {reason}")

    st.caption(f"Total time used: {plan.total_minutes_used} min")
