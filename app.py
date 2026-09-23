import streamlit as st
from copy import deepcopy

from agents import MealWorkoutAgents


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Meal & Workout Coordination Agent",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .subtitle {
        font-size: 18px;
        color: #666666;
        margin-bottom: 25px;
    }

    .agent-box {
        padding: 12px;
        border-radius: 10px;
        border: 1px solid #dddddd;
        margin-bottom: 8px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">'
    '🥗 Meal & Workout Coordination Agent'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'An adaptive multi-agent AI system that coordinates '
    'meals, workouts, pantry inventory, budget and daily constraints.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# GET GROQ API KEY
# ============================================================

try:
    groq_api_key = st.secrets["GROQ_API_KEY"]

except Exception:
    groq_api_key = None


if not groq_api_key:

    st.error(
        "❌ GROQ_API_KEY is not configured."
    )

    st.info(
        "Go to Streamlit → App Settings → Secrets "
        "and add GROQ_API_KEY."
    )

    st.stop()


# ============================================================
# INITIALIZE AGENT SYSTEM
# ============================================================

try:

    agents = MealWorkoutAgents(
        groq_api_key
    )

except Exception as e:

    st.error(
        f"Could not initialize the AI agent system: {e}"
    )

    st.stop()


# ============================================================
# SESSION STATE
# ============================================================

if "current_state" not in st.session_state:
    st.session_state.current_state = None

if "plan_result" not in st.session_state:
    st.session_state.plan_result = None

if "monitor_result" not in st.session_state:
    st.session_state.monitor_result = None

if "replan_result" not in st.session_state:
    st.session_state.replan_result = None

if "vision_result" not in st.session_state:
    st.session_state.vision_result = None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("👤 User Context")

    name = st.text_input(
        "Name",
        value="Student"
    )

    food_preference = st.selectbox(
        "Food Preference",
        [
            "Vegetarian",
            "Non-Vegetarian",
            "Vegan",
            "Eggetarian"
        ]
    )

    foods_to_avoid = st.text_input(
        "Foods to Avoid",
        placeholder="Example: peanuts, mushrooms"
    )

    budget = st.number_input(
        "Weekly Food Budget (₹)",
        min_value=100,
        max_value=10000,
        value=250,
        step=50
    )

    cooking_time = st.slider(
        "Maximum Cooking Time Per Meal",
        min_value=10,
        max_value=120,
        value=30,
        step=5
    )

    daily_schedule = st.text_area(
        "Daily Schedule",
        value=(
            "College: 9 AM - 4 PM\n"
            "Study: 6 PM - 8 PM\n"
            "Sleep: 11 PM"
        ),
        height=120
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

columns = st.columns(7)

for index, day in enumerate(days):

    with columns[index]:

        default_index = 4

        if day in ["Monday", "Thursday"]:
            default_index = 0

        elif day == "Tuesday":
            default_index = 1

        elif day == "Saturday":
            default_index = 2

        workout_schedule[day] = st.selectbox(
            day,
            workout_options,
            index=default_index,
            key=f"workout_{day}"
        )


# ============================================================
# PANTRY
# ============================================================

st.header("🥕 Pantry / Inventory")

pantry_text = st.text_area(
    "Enter ingredients currently available",
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

st.subheader("📸 Pantry Vision")

pantry_image = st.file_uploader(
    "Upload a photo of your pantry or ingredients",
    type=[
        "jpg",
        "jpeg",
        "png",
        "webp"
    ]
)

if pantry_image:

    st.image(
        pantry_image,
        caption="Uploaded Pantry Image",
        width=400
    )


# ============================================================
# BUILD APPLICATION STATE
# ============================================================

def build_state():

    pantry_items = [
        item.strip()
        for item in pantry_text.splitlines()
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
# GENERATE INITIAL PLAN
# ============================================================

st.header("🤖 AI Agent System")

generate_button = st.button(
    "🚀 GENERATE COORDINATED PLAN",
    type="primary",
    use_container_width=True
)


if generate_button:

    state = build_state()

    st.session_state.current_state = state

    st.session_state.monitor_result = None
    st.session_state.replan_result = None

    with st.status(
        "🤖 AI agents are working...",
        expanded=True
    ) as status:

        try:

            # ------------------------------------------------
            # PANTRY VISION AGENT
            # ------------------------------------------------

            if pantry_image:

                st.write(
                    "📸 Pantry Vision Agent → "
                    "analyzing uploaded image..."
                )

                vision_result = agents.pantry_vision_agent(
                    pantry_image.getvalue()
                )

                st.session_state.vision_result = vision_result

                detected = vision_result.get(
                    "ingredients",
                    []
                )

                if detected:

                    st.write(
                        f"🥕 Detected {len(detected)} "
                        "possible ingredients."
                    )

                    state["vision_detected_ingredients"] = (
                        vision_result
                    )

                else:

                    st.write(
                        "ℹ️ No ingredients were confidently detected."
                    )

            else:

                st.session_state.vision_result = None

                st.write(
                    "📸 Pantry Vision Agent → "
                    "skipped because no image was uploaded."
                )

            # ------------------------------------------------
            # MULTI-AGENT PIPELINE
            # ------------------------------------------------

            st.write(
                "🏋️ Workout Agent → analyzing workout schedule"
            )

            st.write(
                "🍱 Meal Agent → creating coordinated meals"
            )

            st.write(
                "🔍 Constraint Agent → checking constraints"
            )

            st.write(
                "🧠 Coordinator Agent → synchronizing agents"
            )

            result = agents.create_plan(state)

            st.session_state.plan_result = result

            status.update(
                label="✅ Coordinated plan generated",
                state="complete"
            )

        except Exception as e:

            status.update(
                label="❌ Agent pipeline failed",
                state="error"
            )

            st.error(
                f"Error while generating the plan: {e}"
            )


# ============================================================
# DISPLAY PANTRY VISION RESULT
# ============================================================

if st.session_state.vision_result:

    vision = st.session_state.vision_result

    st.divider()

    st.subheader("📸 Pantry Vision Result")

    ingredients = vision.get(
        "ingredients",
        []
    )

    if ingredients:

        for item in ingredients:

            if isinstance(item, dict):

                name_value = item.get(
                    "name",
                    "Unknown"
                )

                quantity = item.get(
                    "quantity_estimate",
                    "Unknown"
                )

                confidence = item.get(
                    "confidence",
                    "Unknown"
                )

                st.write(
                    f"🥕 **{name_value}** — "
                    f"{quantity} — "
                    f"confidence: {confidence}"
                )

            else:

                st.write(
                    f"🥕 {item}"
                )

    else:

        st.info(
            "The vision agent did not identify any "
            "ingredients confidently."
        )

    notes = vision.get(
        "notes",
        ""
    )

    if notes:
        st.caption(notes)


# ============================================================
# DISPLAY WEEKLY PLAN
# ============================================================

if st.session_state.plan_result:

    result = st.session_state.plan_result

    plan = result.get(
        "plan",
        {}
    )

    st.divider()

    st.header("📅 Coordinated Weekly Plan")

    weekly_plan = plan.get(
        "weekly_plan",
        []
    )

    if weekly_plan:

        for day_plan in weekly_plan:

            if not isinstance(day_plan, dict):
                continue

            day = day_plan.get(
                "day",
                "Day"
            )

            with st.expander(
                f"📌 {day}",
                expanded=True
            ):

                left, right = st.columns(2)

                with left:

                    st.markdown(
                        f"**🏋️ Workout**  \n"
                        f"{day_plan.get('workout', 'N/A')}"
                    )

                    st.markdown(
                        f"**🍳 Breakfast**  \n"
                        f"{day_plan.get('breakfast', 'N/A')}"
                    )

                    st.markdown(
                        f"**🍱 Lunch**  \n"
                        f"{day_plan.get('lunch', 'N/A')}"
                    )

                with right:

                    st.markdown(
                        f"**🍌 Snack**  \n"
                        f"{day_plan.get('snack', 'N/A')}"
                    )

                    st.markdown(
                        f"**🍽️ Dinner**  \n"
                        f"{day_plan.get('dinner', 'N/A')}"
                    )

                reason = day_plan.get(
                    "reason",
                    ""
                )

                if reason:

                    st.info(
                        f"💡 Why this plan: {reason}"
                    )

    else:

        st.warning(
            "The Coordinator Agent did not return "
            "a structured weekly plan."
        )

        st.json(plan)


# ============================================================
# PLAN SUMMARY
# ============================================================

if st.session_state.plan_result:

    plan = st.session_state.plan_result.get(
        "plan",
        {}
    )

    st.divider()

    st.header("📊 Plan Summary")

    col1, col2, col3 = st.columns(3)

    with col1:

        estimated_budget = plan.get(
            "estimated_budget",
            "N/A"
        )

        st.metric(
            "Estimated Budget",
            (
                f"₹{estimated_budget}"
                if estimated_budget != "N/A"
                else "N/A"
            )
        )

    with col2:

        constraint_status = plan.get(
            "constraint_status",
            "N/A"
        )

        st.metric(
            "Constraint Status",
            str(constraint_status)
        )

    with col3:

        st.metric(
            "Active Agents",
            "7"
        )


# ============================================================
# GROCERY LIST
# ============================================================

if st.session_state.plan_result:

    plan = st.session_state.plan_result.get(
        "plan",
        {}
    )

    grocery_list = plan.get(
        "grocery_list",
        []
    )

    st.subheader("🛒 Grocery List")

    if grocery_list:

        for index, item in enumerate(grocery_list):

            st.checkbox(
                str(item),
                key=f"grocery_item_{index}"
            )

    else:

        st.success(
            "No additional grocery items were suggested."
        )


# ============================================================
# AGENT DASHBOARD
# ============================================================

if st.session_state.plan_result:

    st.divider()

    st.header("🤖 Agent Dashboard")

    agent_data = [
        (
            "🥕 Pantry / Vision Agent",
            "Analyzes pantry images"
        ),
        (
            "🏋️ Workout Agent",
            "Analyzes workout schedule"
        ),
        (
            "🍱 Meal Agent",
            "Creates coordinated meals"
        ),
        (
            "🔍 Constraint Agent",
            "Checks budget, pantry and constraints"
        ),
        (
            "🧠 Coordinator Agent",
            "Combines all agent outputs"
        ),
        (
            "👁️ Monitoring Agent",
            "Detects changes"
        ),
        (
            "🔄 Replanning Agent",
            "Updates affected parts"
        )
    ]

    dashboard_columns = st.columns(2)

    for index, (agent_name, description) in enumerate(agent_data):

        with dashboard_columns[index % 2]:

            st.markdown(
                f"""
                <div class="agent-box">
                <b>🟢 {agent_name}</b><br>
                <small>{description}</small>
                </div>
                """,
                unsafe_allow_html=True
            )


# ============================================================
# COORDINATOR EXPLANATION
# ============================================================

if st.session_state.plan_result:

    plan = st.session_state.plan_result.get(
        "plan",
        {}
    )

    st.subheader("🧠 Coordinator Explanation")

    explanation = plan.get(
        "coordination_summary",
        ""
    )

    if explanation:

        st.write(explanation)

    else:

        st.info(
            "The Coordinator Agent did not provide "
            "a summary."
        )


# ============================================================
# CONTINUOUS MONITORING
# ============================================================

st.divider()

st.header("🔄 Continuous Monitoring & Replanning")

st.write(
    "Change a real-world condition. The Monitoring Agent "
    "will determine whether the existing plan needs to change."
)

change = st.text_area(
    "Describe what changed",
    placeholder=(
        "Example: I ran out of bananas and my "
        "Tuesday workout moved from 6 PM to 8 PM."
    ),
    height=100
)


monitor_button = st.button(
    "🔍 DETECT CHANGE & REPLAN",
    use_container_width=True
)


if monitor_button:

    if not st.session_state.plan_result:

        st.warning(
            "Please generate the initial weekly plan first."
        )

    elif not change.strip():

        st.warning(
            "Please describe a change first."
        )

    else:

        old_state = deepcopy(
            st.session_state.current_state
        )

        new_state = deepcopy(
            old_state
        )

        new_state["latest_change"] = change

        current_plan = (
            st.session_state.plan_result
            .get("plan", {})
        )

        with st.status(
            "👁️ Monitoring system running...",
            expanded=True
        ) as status:

            try:

                # --------------------------------------------
                # MONITORING AGENT
                # --------------------------------------------

                st.write(
                    "👁️ Monitoring Agent → "
                    "comparing current and previous state"
                )

                monitor_result = agents.monitoring_agent(
                    old_state,
                    new_state,
                    current_plan
                )

                st.session_state.monitor_result = (
                    monitor_result
                )

                replan_required = monitor_result.get(
                    "replan_required",
                    False
                )

                # --------------------------------------------
                # REPLANNING AGENT
                # --------------------------------------------

                if replan_required:

                    st.write(
                        "🔄 Replanning Agent → "
                        "updating affected components"
                    )

                    replan_result = (
                        agents.replanning_agent(
                            new_state,
                            current_plan,
                            monitor_result
                        )
                    )

                    st.session_state.replan_result = (
                        replan_result
                    )

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

            except Exception as e:

                status.update(
                    label="❌ Monitoring failed",
                    state="error"
                )

                st.error(
                    f"Monitoring error: {e}"
                )


# ============================================================
# MONITORING RESULT
# ============================================================

if st.session_state.monitor_result:

    monitor = st.session_state.monitor_result

    st.divider()

    st.subheader("🔍 Monitoring Result")

    changes_detected = monitor.get(
        "changes_detected",
        []
    )

    if changes_detected:

        st.write("### Changes Detected")

        for item in changes_detected:

            st.write(
                f"• {item}"
            )

    affected_days = monitor.get(
        "affected_days",
        []
    )

    if affected_days:

        st.write(
            "**Affected Days:** "
            + ", ".join(
                str(day)
                for day in affected_days
            )
        )

    affected_components = monitor.get(
        "affected_components",
        []
    )

    if affected_components:

        st.write(
            "**Affected Components:**"
        )

        for component in affected_components:

            st.write(
                f"• {component}"
            )

    reason = monitor.get(
        "reason",
        ""
    )

    if reason:

        st.info(
            f"🧠 Monitoring Agent: {reason}"
        )


# ============================================================
# REPLANNING RESULT
# ============================================================

if st.session_state.replan_result:

    replan = st.session_state.replan_result

    st.divider()

    st.subheader("🔄 Updated Plan")

    changes_made = replan.get(
        "changes_made",
        []
    )

    if changes_made:

        st.write("### What Changed?")

        for item in changes_made:

            st.write(
                f"• {item}"
            )

    reason = replan.get(
        "reason",
        ""
    )

    if reason:

        st.info(
            f"🔄 Replanning Agent: {reason}"
        )

    updated_plan = replan.get(
        "updated_plan",
        []
    )

    if updated_plan:

        st.write("### Updated Components")

        for item in updated_plan:

            if isinstance(item, dict):

                day = item.get(
                    "day",
                    ""
                )

                if day:

                    st.markdown(
                        f"**📌 {day}**"
                    )

                st.json(item)

            else:

                st.write(
                    f"• {item}"
                )

    new_grocery_list = replan.get(
        "new_grocery_list",
        []
    )

    if new_grocery_list:

        st.write("### 🛒 Updated Grocery List")

        for item in new_grocery_list:

            st.write(
                f"• {item}"
            )


# ============================================================
# AGENT WORKFLOW
# ============================================================

st.divider()

st.header("🔄 Agentic Workflow")

workflow = """
**Observe → Analyze → Check → Decide → Act → Monitor → Replan**
"""

st.markdown(workflow)

st.caption(
    "The application is a planning assistant. "
    "It does not provide medical diagnosis or treatment."
)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🥗 Meal & Workout Coordination Agent | "
    "Built with Streamlit + Groq + Multi-Agent AI"
)
```
