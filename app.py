```python
import streamlit as st
import json
from agents import MealWorkoutAgents


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Meal & Workout Coordination Agent",
    page_icon="🥗",
    layout="wide"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

.main-title {
    font-size: 42px;
    font-weight: 700;
    margin-bottom: 0px;
}

.subtitle {
    font-size: 18px;
    color: #666;
    margin-bottom: 25px;
}

.agent-card {
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #ddd;
    margin-bottom: 10px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🥗 Meal & Workout Coordination Agent</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'An adaptive multi-agent system that coordinates meals, workouts, '
    'pantry inventory, budget and daily constraints.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# API KEY
# ============================================================

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = ""

if not api_key:

    st.warning(
        "OpenAI API key is not configured. "
        "Add OPENAI_API_KEY in Streamlit Secrets."
    )

    st.stop()


agents = MealWorkoutAgents(api_key)


# ============================================================
# SESSION STATE
# ============================================================

if "plan_result" not in st.session_state:
    st.session_state.plan_result = None

if "current_state" not in st.session_state:
    st.session_state.current_state = None

if "monitor_result" not in st.session_state:
    st.session_state.monitor_result = None

if "replan_result" not in st.session_state:
    st.session_state.replan_result = None

if "agent_logs" not in st.session_state:
    st.session_state.agent_logs = []


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("👤 User Context")

name = st.sidebar.text_input(
    "Name",
    value="Student"
)

food_preference = st.sidebar.selectbox(
    "Food preference",
    [
        "Vegetarian",
        "Non-Vegetarian",
        "Vegan",
        "Eggetarian"
    ]
)

foods_to_avoid = st.sidebar.text_input(
    "Foods to avoid",
    placeholder="Example: peanuts, mushrooms"
)

budget = st.sidebar.number_input(
    "Weekly food budget (₹)",
    min_value=100,
    max_value=10000,
    value=250,
    step=50
)

cooking_time = st.sidebar.slider(
    "Maximum cooking time per meal (minutes)",
    10,
    120,
    30
)

daily_schedule = st.sidebar.text_area(
    "Daily schedule",
    value=(
        "College: 9 AM - 4 PM\n"
        "Study: 6 PM - 8 PM\n"
        "Sleep: 11 PM"
    )
)


# ============================================================
# WORKOUT SCHEDULE
# ============================================================

st.header("🏋️ Weekly Workout Schedule")

days = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

workout_options = [
    "Strength Training",
    "Cardio",
    "Full Body",
    "Mobility",
    "Rest"
]

workout_schedule = {}

cols = st.columns(7)

for i, day in enumerate(days):

    with cols[i]:

        workout_schedule[day] = st.selectbox(
            day,
            workout_options,
            index=(
                0 if day in ["Monday", "Thursday"]
                else 4
            ),
            key=f"workout_{day}"
        )


# ============================================================
# PANTRY
# ============================================================

st.header("🥕 Pantry / Inventory")

pantry_text = st.text_area(
    "Enter available ingredients",
    value=(
        "Rice\n"
        "Dal\n"
        "Oats\n"
        "Milk\n"
        "Banana\n"
        "Vegetables"
    ),
    height=150
)


# ============================================================
# PANTRY IMAGE
# ============================================================

st.subheader("📸 Optional Pantry Image")

pantry_image = st.file_uploader(
    "Upload a photo of your pantry or ingredients",
    type=["jpg", "jpeg", "png"]
)


if pantry_image:

    st.image(
        pantry_image,
        caption="Uploaded pantry image",
        width=350
    )


# ============================================================
# BUILD STATE
# ============================================================

def build_state():

    pantry_items = [
        item.strip()
        for item in pantry_text.split("\n")
        if item.strip()
    ]

    return {
        "name": name,
        "food_preference": food_preference,
        "foods_to_avoid": foods_to_avoid,
        "budget": budget,
        "cooking_time_minutes": cooking_time,
        "daily_schedule": daily_schedule,
        "workout_schedule": workout_schedule,
        "pantry": pantry_items
    }


# ============================================================
# GENERATE PLAN
# ============================================================

st.header("🤖 AI Agent System")

generate = st.button(
    "🚀 START AI MONITORING + GENERATE PLAN",
    type="primary",
    use_container_width=True
)


if generate:

    state = build_state()

    st.session_state.current_state = state

    with st.status(
        "AI agents are working...",
        expanded=True
    ) as status:

        st.write("🔎 Collecting user context")

        # ----------------------------------------------------
        # PANTRY VISION
        # ----------------------------------------------------

        if pantry_image:

            st.write("📸 Pantry Vision Agent: analyzing image")

            vision_result = agents.pantry_vision_agent(
                pantry_image.getvalue()
            )

            state["vision_detected_ingredients"] = vision_result

        else:

            vision_result = {
                "ingredients": [],
                "notes": "No pantry image uploaded."
            }

        # ----------------------------------------------------
        # MAIN AGENT PIPELINE
        # ----------------------------------------------------

        st.write("🏋️ Workout Agent: analyzing workout schedule")

        result = agents.create_plan(state)

        st.session_state.plan_result = result
        st.session_state.agent_logs = result["logs"]

        status.update(
            label="✅ Multi-agent planning completed",
            state="complete"
        )


# ============================================================
# DISPLAY PLAN
# ============================================================

if st.session_state.plan_result:

    result = st.session_state.plan_result

    plan = result.get("plan", {})

    st.divider()

    st.header("📅 Coordinated Weekly Plan")

    weekly_plan = plan.get(
        "weekly_plan",
        []
    )

    if weekly_plan:

        for day_plan in weekly_plan:

            day = day_plan.get(
                "day",
                "Day"
            )

            with st.expander(
                f"📌 {day}",
                expanded=True
            ):

                col1, col2 = st.columns(2)

                with col1:

                    st.markdown(
                        f"**🏋️ Workout:** "
                        f"{day_plan.get('workout', 'N/A')}"
                    )

                    st.markdown(
                        f"**🍳 Breakfast:** "
                        f"{day_plan.get('breakfast', 'N/A')}"
                    )

                    st.markdown(
                        f"**🍱 Lunch:** "
                        f"{day_plan.get('lunch', 'N/A')}"
                    )

                with col2:

                    st.markdown(
                        f"**🍌 Snack:** "
                        f"{day_plan.get('snack', 'N/A')}"
                    )

                    st.markdown(
                        f"**🍽️ Dinner:** "
                        f"{day_plan.get('dinner', 'N/A')}"
                    )

                reason = day_plan.get(
                    "reason",
                    ""
                )

                if reason:

                    st.info(
                        f"💡 Why: {reason}"
                    )

    else:

        st.json(plan)


    # ========================================================
    # SUMMARY
    # ========================================================

    st.divider()

    st.header("📊 Plan Summary")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Estimated Budget",
            f"₹{plan.get('estimated_budget', 'N/A')}"
        )

    with col2:

        st.metric(
            "Constraint Status",
            plan.get(
                "constraint_status",
                "N/A"
            )
        )

    with col3:

        st.metric(
            "Agents",
            "7"
        )


    # ========================================================
    # GROCERY LIST
    # ========================================================

    st.subheader("🛒 Grocery List")

    grocery_list = plan.get(
        "grocery_list",
        []
    )

    if grocery_list:

        for item in grocery_list:

            st.checkbox(
                str(item),
                key=f"grocery_{str(item)}"
            )

    else:

        st.write("No additional groceries required.")


    # ========================================================
    # AGENT ACTIVITY
    # ========================================================

    st.divider()

    st.header("🤖 Agent Activity")

    agents_status = [
        ("🥕 Pantry / Vision Agent", "Completed"),
        ("🏋️ Workout Agent", "Completed"),
        ("🍱 Meal Agent", "Completed"),
        ("🔍 Constraint Agent", "Completed"),
        ("🧠 Coordinator Agent", "Completed"),
        ("👁️ Monitoring Agent", "Ready"),
        ("🔄 Replanning Agent", "Ready")
    ]

    for agent_name, status_text in agents_status:

        st.markdown(
            f"**{agent_name}** — 🟢 {status_text}"
        )


    # ========================================================
    # COORDINATION SUMMARY
    # ========================================================

    st.subheader("🧠 Coordinator Explanation")

    st.write(
        plan.get(
            "coordination_summary",
            "The coordinator synchronized the specialist agents."
        )
    )


# ============================================================
# CONTINUOUS MONITORING
# ============================================================

st.divider()

st.header("🔄 Continuous Monitoring & Replanning")

st.write(
    "Change a real-world condition and the Monitoring Agent "
    "will determine whether the existing plan needs updating."
)


change = st.text_area(
    "Describe a change",
    placeholder=(
        "Example: I ran out of bananas and my Tuesday workout "
        "moved from 6 PM to 8 PM."
    )
)


monitor_button = st.button(
    "🔍 DETECT CHANGE & REPLAN",
    use_container_width=True
)


if monitor_button:

    if not st.session_state.plan_result:

        st.warning(
            "Generate the initial weekly plan first."
        )

    elif not change.strip():

        st.warning(
            "Please describe the change."
        )

    else:

        old_state = deepcopy(
            st.session_state.current_state
        )

        new_state = deepcopy(
            old_state
        )

        new_state["latest_change"] = change

        with st.status(
            "Monitoring system running...",
            expanded=True
        ) as status:

            st.write(
                "👁️ Monitoring Agent: comparing system state"
            )

            current_plan = st.session_state.plan_result.get(
                "plan",
                {}
            )

            monitor_result = agents.monitoring_agent(
                old_state,
                new_state,
                current_plan
            )

            st.session_state.monitor_result = monitor_result

            st.write(
                "🔍 Impact analysis completed"
            )

            if monitor_result.get(
                "replan_required",
                False
            ):

                st.write(
                    "🔄 Replanning Agent: updating affected components"
                )

                replan_result = agents.replanning_agent(
                    new_state,
                    current_plan,
                    monitor_result
                )

                st.session_state.replan_result = replan_result

                status.update(
                    label="✅ Plan automatically updated",
                    state="complete"
                )

            else:

                st.session_state.replan_result = None

                status.update(
                    label="✅ Existing plan remains valid",
                    state="complete"
                )


# ============================================================
# MONITORING RESULT
# ============================================================

if st.session_state.monitor_result:

    st.divider()

    st.subheader("🔍 Monitoring Result")

    monitor = st.session_state.monitor_result

    if monitor.get("changes_detected"):

        st.write("### Changes detected")

        for change_item in monitor.get(
            "changes_detected",
            []
        ):

            st.write(
                f"• {change_item}"
            )

    affected_days = monitor.get(
        "affected_days",
        []
    )

    if affected_days:

        st.write(
            "**Affected days:** "
            + ", ".join(affected_days)
        )

    st.info(
        monitor.get(
            "reason",
            "The monitoring agent analyzed the latest state."
        )
    )


# ============================================================
# REPLANNING RESULT
# ============================================================

if st.session_state.replan_result:

    st.divider()

    st.subheader("🔄 Updated Plan")

    replan = st.session_state.replan_result

    changes = replan.get(
        "changes_made",
        []
    )

    if changes:

        st.write("### What changed?")

        for item in changes:

            st.write(
                f"• {item}"
            )

    st.info(
        replan.get(
            "reason",
            "The Replanning Agent updated the affected parts."
        )
    )

    updated_plan = replan.get(
        "updated_plan",
        []
    )

    if updated_plan:

        for item in updated_plan:

            if isinstance(item, dict):

                st.markdown(
                    f"### 📌 {item.get('day', 'Day')}"
                )

                st.write(item)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Meal & Workout Coordination Agent | "
    "Multi-Agent AI Hackathon Project"
)

st.caption(
    "This application is a planning assistant and does not "
    "provide medical diagnosis or medical treatment."
)
```
