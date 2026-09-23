import streamlit as st
import json
import base64
from copy import deepcopy
from typing import Any, Dict, Optional

from groq import Groq

# ============================================================

# PAGE CONFIGURATION

# ============================================================

st.set_page_config(
page_title="Meal & Workout Coordination Agent",
page_icon="🍽️",
layout="wide"
)

# ============================================================

# CUSTOM CSS

# ============================================================

st.markdown(
""" <style>
.main-title {
font-size: 42px;
font-weight: 700;
margin-bottom: 5px;
}

```
.subtitle {
    font-size: 18px;
    opacity: 0.75;
    margin-bottom: 25px;
}

.agent-box {
    padding: 15px;
    border-radius: 12px;
    border: 1px solid rgba(128,128,128,0.25);
    margin-bottom: 10px;
}

.status-box {
    padding: 15px;
    border-radius: 12px;
    border: 1px solid rgba(128,128,128,0.25);
    margin-top: 10px;
    margin-bottom: 10px;
}
</style>
""",
unsafe_allow_html=True

)

# ============================================================

# MULTI-AGENT SYSTEM

# ============================================================

class MealWorkoutAgents:

````
def __init__(self, api_key: str):

    if not api_key:
        raise ValueError("Groq API key is missing.")

    self.client = Groq(api_key=api_key)

    # Groq model supporting text and image input
    self.model = "qwen/qwen3.8-27b"


# ========================================================
# GENERAL AI CALL
# ========================================================

def call_ai(
    self,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 4000
) -> str:

    response = self.client.chat.completions.create(
        model=self.model,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=temperature,
        max_completion_tokens=max_tokens
    )

    return response.choices[0].message.content or ""


# ========================================================
# JSON PARSER
# ========================================================

def extract_json(self, text: str) -> Dict[str, Any]:

    if not text:
        return {}

    text = text.strip()

    # Remove accidental Markdown fences
    if text.startswith("```"):
        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    try:

        result = json.loads(text)

        if isinstance(result, dict):
            return result

        return {"result": result}

    except Exception:
        pass

    # Try to extract JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:

        try:

            result = json.loads(
                text[start:end + 1]
            )

            if isinstance(result, dict):
                return result

        except Exception:
            pass

    return {
        "raw_response": text
    }


# ========================================================
# PANTRY VISION AGENT
# ========================================================

def pantry_vision_agent(
    self,
    image_bytes: bytes
) -> Dict[str, Any]:

    if not image_bytes:

        return {
            "ingredients": [],
            "confidence_notes": "No image provided."
        }

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    image_url = (
        "data:image/jpeg;base64,"
        + image_base64
    )

    system_prompt = """
````

You are the Pantry Vision Agent.

Look at the uploaded pantry image and identify food ingredients
that are clearly visible.

Do not invent ingredients.

Return JSON only.

Format:

{
"ingredients": [],
"confidence_notes": ""
}
"""

```
    try:

        response = self.client.chat.completions.create(

            model=self.model,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Identify the visible food "
                                "ingredients in this image."
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ],

            temperature=0.1,

            max_completion_tokens=1500,

            response_format={
                "type": "json_object"
            }
        )

        result = (
            response
            .choices[0]
            .message
            .content
            or "{}"
        )

        return self.extract_json(result)

    except Exception as e:

        return {
            "ingredients": [],
            "error": str(e)
        }


# ========================================================
# WORKOUT AGENT
# ========================================================

def workout_agent(
    self,
    state: Dict[str, Any]
) -> Dict[str, Any]:

    system_prompt = """
```

You are the Workout Planning Agent.

Create a weekly workout plan based on the workout schedule
provided by the user.

Respect the selected workout types.

Keep the recommendations practical.

Do not provide medical diagnosis or treatment.

Return JSON only.
"""

```
    user_prompt = f"""
```

USER STATE:

{json.dumps(state, indent=2)}

Create a workout plan for:

Monday
Tuesday
Wednesday
Thursday
Friday
Saturday
Sunday

For every day provide:

* workout
* duration_minutes
* intensity
* notes

Return JSON.
"""

```
    try:

        result = self.call_ai(
            system_prompt,
            user_prompt,
            temperature=0.2,
            max_tokens=3000
        )

        return self.extract_json(result)

    except Exception as e:

        return {
            "workouts": {},
            "error": str(e)
        }


# ========================================================
# MEAL AGENT
# ========================================================

def meal_agent(
    self,
    state: Dict[str, Any],
    workout_result: Dict[str, Any]
) -> Dict[str, Any]:

    system_prompt = """
```

You are the Meal Planning Agent.

Create meals that coordinate with the user's workouts,
food preferences, available pantry ingredients,
budget and cooking time.

Prefer ingredients already available.

Avoid foods listed in the user's foods-to-avoid list.

Do not provide medical or disease-treatment advice.

Return JSON only.
"""

```
    user_prompt = f"""
```

USER STATE:

{json.dumps(state, indent=2)}

WORKOUT PLAN:

{json.dumps(workout_result, indent=2)}

Create meals for every day of the week.

Each day must contain:

* breakfast
* lunch
* snack
* dinner
* approximate_cost
* reason

Return JSON.
"""

```
    try:

        result = self.call_ai(
            system_prompt,
            user_prompt,
            temperature=0.3,
            max_tokens=4500
        )

        return self.extract_json(result)

    except Exception as e:

        return {
            "meals": {},
            "error": str(e)
        }


# ========================================================
# CONSTRAINT AGENT
# ========================================================

def constraint_agent(
    self,
    state: Dict[str, Any],
    workout_result: Dict[str, Any],
    meal_result: Dict[str, Any]
) -> Dict[str, Any]:

    system_prompt = """
```

You are the Constraint Checking Agent.

Check the proposed plan against:

1. Food preference
2. Foods to avoid
3. Pantry availability
4. Weekly budget
5. Cooking time
6. Workout schedule
7. Practicality

Identify conflicts and corrections.

Return JSON only.
"""

```
    user_prompt = f"""
```

USER STATE:

{json.dumps(state, indent=2)}

WORKOUT PLAN:

{json.dumps(workout_result, indent=2)}

MEAL PLAN:

{json.dumps(meal_result, indent=2)}

Return:

{{
"status": "",
"estimated_budget": 0,
"budget_limit": 0,
"violations": [],
"suggestions": [],
"pantry_items_used": [],
"missing_items": []
}}
"""

```
    try:

        result = self.call_ai(
            system_prompt,
            user_prompt,
            temperature=0.1,
            max_tokens=2500
        )

        return self.extract_json(result)

    except Exception as e:

        return {
            "status": "ERROR",
            "violations": [str(e)],
            "suggestions": []
        }


# ========================================================
# COORDINATOR AGENT
# ========================================================

def coordinator_agent(
    self,
    state: Dict[str, Any],
    workout_result: Dict[str, Any],
    meal_result: Dict[str, Any],
    constraint_result: Dict[str, Any]
) -> Dict[str, Any]:

    system_prompt = """
```

You are the Supervisor / Coordinator Agent.

You coordinate multiple specialist agents.

Combine:

* workout recommendations
* meal recommendations
* pantry information
* user preferences
* budget
* cooking time
* constraints

Create one coordinated weekly plan.

If conflicts exist, correct them.

Return JSON only.
"""

```
    user_prompt = f"""
```

USER STATE:

{json.dumps(state, indent=2)}

WORKOUT AGENT:

{json.dumps(workout_result, indent=2)}

MEAL AGENT:

{json.dumps(meal_result, indent=2)}

CONSTRAINT AGENT:

{json.dumps(constraint_result, indent=2)}

Create the final coordinated plan.

For every day provide:

* workout
* breakfast
* lunch
* snack
* dinner
* reason

Also provide:

* summary
* estimated_weekly_budget
* grocery_list
* constraint_status
* active_agents
* coordinator_explanation

Return JSON.
"""

```
    try:

        result = self.call_ai(
            system_prompt,
            user_prompt,
            temperature=0.2,
            max_tokens=6000
        )

        return self.extract_json(result)

    except Exception as e:

        return {
            "summary": "Coordinator failed.",
            "weekly_plan": {},
            "grocery_list": [],
            "error": str(e)
        }


# ========================================================
# CREATE PLAN
# ========================================================

def create_plan(
    self,
    state: Dict[str, Any]
) -> Dict[str, Any]:

    try:

        # Agent 1
        workout_result = self.workout_agent(state)

        # Agent 2
        meal_result = self.meal_agent(
            state,
            workout_result
        )

        # Agent 3
        constraint_result = self.constraint_agent(
            state,
            workout_result,
            meal_result
        )

        # Agent 4
        final_plan = self.coordinator_agent(
            state,
            workout_result,
            meal_result,
            constraint_result
        )

        return {
            "plan": final_plan,
            "workout_agent": workout_result,
            "meal_agent": meal_result,
            "constraint_agent": constraint_result,
            "agents_used": [
                "Workout Agent",
                "Meal Agent",
                "Constraint Agent",
                "Supervisor / Coordinator Agent"
            ]
        }

    except Exception as e:

        return {
            "plan": {},
            "error": str(e),
            "agents_used": []
        }


# ========================================================
# MONITORING AGENT
# ========================================================

def monitoring_agent(
    self,
    old_state: Dict[str, Any],
    new_state: Dict[str, Any]
) -> Dict[str, Any]:

    system_prompt = """
```

You are the Monitoring Agent.

Compare the previous state with the new state.

Detect changes in:

* pantry
* workout schedule
* budget
* cooking time
* food preference
* foods to avoid
* newly detected ingredients

Determine whether replanning is necessary.

Return JSON only.
"""

```
    user_prompt = f"""
```

OLD STATE:

{json.dumps(old_state, indent=2)}

NEW STATE:

{json.dumps(new_state, indent=2)}

Return:

{{
"change_detected": true,
"replan_required": true,
"changes": [],
"affected_days": [],
"affected_components": [],
"reason": ""
}}
"""

```
    try:

        result = self.call_ai(
            system_prompt,
            user_prompt,
            temperature=0.1,
            max_tokens=2500
        )

        return self.extract_json(result)

    except Exception as e:

        return {
            "change_detected": True,
            "replan_required": True,
            "changes": [str(e)],
            "affected_days": [],
            "affected_components": [],
            "reason": str(e)
        }


# ========================================================
# REPLANNING AGENT
# ========================================================

def replanning_agent(
    self,
    old_state: Dict[str, Any],
    new_state: Dict[str, Any],
    old_plan: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    system_prompt = """
```

You are the Replanning Agent.

The user's real-world situation has changed.

Compare the old state with the new state.

Preserve parts of the old plan that are still valid.

Change only the affected components.

Examples:

If bananas are unavailable:
replace banana-based meals.

If workout time changes:
adjust meal timing.

If budget decreases:
choose cheaper meals.

If cooking time decreases:
choose simpler meals.

If a workout changes:
coordinate the meals with the new workout.

Return JSON only.
"""

```
    user_prompt = f"""
```

OLD STATE:

{json.dumps(old_state, indent=2)}

NEW STATE:

{json.dumps(new_state, indent=2)}

OLD PLAN:

{json.dumps(old_plan or {}, indent=2)}

Create the updated coordinated plan.

Return:

{{
"updated_plan": {{}},
"changes_made": [],
"reason": "",
"new_grocery_list": [],
"estimated_weekly_budget": 0
}}
"""

```
    try:

        result = self.call_ai(
            system_prompt,
            user_prompt,
            temperature=0.2,
            max_tokens=6000
        )

        return self.extract_json(result)

    except Exception as e:

        return {
            "updated_plan": {},
            "changes_made": [],
            "reason": str(e),
            "new_grocery_list": []
        }
```

# ============================================================

# GET GROQ API KEY

# ============================================================

try:

```
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
```

except Exception:

```
st.error(
    "GROQ_API_KEY is missing. "
    "Add it in Streamlit Cloud → Manage app → Settings → Secrets."
)

st.stop()
```

# ============================================================

# INITIALIZE AGENTS

# ============================================================

try:

```
agents = MealWorkoutAgents(
    GROQ_API_KEY
)
```

except Exception as e:

```
st.error(
    f"Unable to initialize AI agents: {e}"
)

st.stop()
```

# ============================================================

# SESSION STATE

# ============================================================

if "current_state" not in st.session_state:
st.session_state.current_state = None

if "plan_result" not in st.session_state:
st.session_state.plan_result = None

if "vision_result" not in st.session_state:
st.session_state.vision_result = None

if "monitor_result" not in st.session_state:
st.session_state.monitor_result = None

if "replan_result" not in st.session_state:
st.session_state.replan_result = None

# ============================================================

# HEADER

# ============================================================

st.markdown(
'<div class="main-title">🍽️ Meal & Workout Coordination Agent</div>',
unsafe_allow_html=True
)

st.markdown(
""" <div class="subtitle">
An adaptive multi-agent system that coordinates meals,
workouts, pantry inventory, budget and daily constraints. </div>
""",
unsafe_allow_html=True
)

# ============================================================

# SIDEBAR

# ============================================================

st.sidebar.header("👤 User Context")

name = st.sidebar.text_input(
"Name",
value="User"
)

food_preference = st.sidebar.selectbox(
"Food Preference",
[
"Vegetarian",
"Non-Vegetarian",
"Vegan",
"Eggetarian"
]
)

foods_to_avoid = st.sidebar.text_input(
"Foods to Avoid",
placeholder="Example: peanuts, mushrooms"
)

budget = st.sidebar.number_input(
"Weekly Food Budget (₹)",
min_value=100,
max_value=10000,
value=250,
step=50
)

cooking_time = st.sidebar.slider(
"Maximum Cooking Time (minutes)",
min_value=10,
max_value=120,
value=30
)

# ============================================================

# WORKOUT SCHEDULE

# ============================================================

st.sidebar.header("🏋️ Weekly Workout Schedule")

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

for day in days:

```
workout_schedule[day] = st.sidebar.selectbox(
    day,
    workout_options,
    index=0 if day in [
        "Monday",
        "Thursday"
    ]
    else 4 if day in [
        "Wednesday",
        "Friday",
        "Sunday"
    ]
    else 1 if day == "Tuesday"
    else 2,
    key=f"workout_{day}"
)
```

# ============================================================

# PANTRY

# ============================================================

st.sidebar.header("🥫 Pantry")

pantry_text = st.sidebar.text_area(
"Available Ingredients",
placeholder=(
"Example:\n"
"Rice\n"
"Dal\n"
"Oats\n"
"Milk\n"
"Banana\n"
"Tomato\n"
"Onion\n"
"Vegetables"
),
height=160
)

# ============================================================

# PANTRY IMAGE

# ============================================================

pantry_image = st.sidebar.file_uploader(
"📷 Upload Pantry Image",
type=[
"jpg",
"jpeg",
"png",
"webp"
]
)

# ============================================================

# BUILD USER STATE

# ============================================================

def build_state():

```
return {

    "name": name,

    "food_preference": food_preference,

    "foods_to_avoid": foods_to_avoid,

    "weekly_budget": budget,

    "maximum_cooking_time_minutes": cooking_time,

    "workout_schedule": workout_schedule,

    "pantry": pantry_text
}
```

# ============================================================

# GENERATE PLAN

# ============================================================

st.header("🚀 Generate Coordinated Plan")

if st.button(
"🚀 GENERATE COORDINATED PLAN",
use_container_width=True
):

```
with st.spinner(
    "AI agents are coordinating your weekly plan..."
):

    state = build_state()

    # ---------------------------------------------
    # Pantry Vision Agent
    # ---------------------------------------------

    if pantry_image is not None:

        vision_result = agents.pantry_vision_agent(
            pantry_image.getvalue()
        )

        st.session_state.vision_result = vision_result

        detected = vision_result.get(
            "ingredients",
            []
        )

        state[
            "vision_detected_ingredients"
        ] = detected

    # ---------------------------------------------
    # Main Multi-Agent System
    # ---------------------------------------------

    result = agents.create_plan(
        state
    )

    st.session_state.current_state = state

    st.session_state.plan_result = result

    st.session_state.monitor_result = None

    st.session_state.replan_result = None
```

# ============================================================

# DISPLAY PANTRY VISION

# ============================================================

if st.session_state.vision_result:

```
st.subheader("📷 Pantry Vision Agent")

vision = st.session_state.vision_result

ingredients = vision.get(
    "ingredients",
    []
)

if ingredients:

    st.success(
        "Detected ingredients: "
        + ", ".join(
            str(x)
            for x in ingredients
        )
    )

notes = vision.get(
    "confidence_notes"
)

if notes:
    st.caption(notes)
```

# ============================================================

# DISPLAY PLAN

# ============================================================

if st.session_state.plan_result:

```
result = st.session_state.plan_result

plan = result.get(
    "plan",
    {}
)

if result.get("error"):

    st.error(
        result["error"]
    )

else:

    st.header("📅 Coordinated Weekly Plan")

    weekly_plan = plan.get(
        "weekly_plan",
        {}
    )

    for day in days:

        day_data = weekly_plan.get(
            day,
            {}
        )

        with st.expander(
            f"📌 {day}",
            expanded=True
        ):

            if isinstance(day_data, dict):

                col1, col2 = st.columns(2)

                with col1:

                    st.markdown(
                        f"**🏋️ Workout:** "
                        f"{day_data.get('workout', 'Not specified')}"
                    )

                    st.markdown(
                        f"**🍳 Breakfast:** "
                        f"{day_data.get('breakfast', 'Not specified')}"
                    )

                    st.markdown(
                        f"**🥗 Lunch:** "
                        f"{day_data.get('lunch', 'Not specified')}"
                    )

                with col2:

                    st.markdown(
                        f"**🍎 Snack:** "
                        f"{day_data.get('snack', 'Not specified')}"
                    )

                    st.markdown(
                        f"**🍲 Dinner:** "
                        f"{day_data.get('dinner', 'Not specified')}"
                    )

                    st.markdown(
                        f"**💡 Reason:** "
                        f"{day_data.get('reason', 'Not specified')}"
                    )


    # ====================================================
    # SUMMARY
    # ====================================================

    st.header("📊 Plan Summary")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Estimated Weekly Budget",
            f"₹{plan.get('estimated_weekly_budget', 0)}"
        )

    with col2:

        st.metric(
            "Constraint Status",
            str(
                plan.get(
                    "constraint_status",
                    "Not available"
                )
            )
        )

    with col3:

        st.metric(
            "Active Agents",
            len(
                result.get(
                    "agents_used",
                    []
                )
            )
        )


    # ====================================================
    # GROCERY LIST
    # ====================================================

    st.header("🛒 Grocery List")

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

        st.info(
            "No additional grocery items were generated."
        )


    # ====================================================
    # COORDINATOR EXPLANATION
    # ====================================================

    st.header("🧠 Coordinator Explanation")

    st.info(
        plan.get(
            "coordinator_explanation",
            "The coordinator combined the specialist agents."
        )
    )
```

# ============================================================

# AGENT DASHBOARD

# ============================================================

st.header("🤖 Agent Dashboard")

agent_names = [
(
"🥗 Meal Agent",
"Creates meals based on preferences, pantry, budget and cooking time."
),
(
"🏋️ Workout Agent",
"Creates the weekly workout structure."
),
(
"📷 Pantry Vision Agent",
"Identifies visible ingredients from pantry images."
),
(
"🔍 Constraint Agent",
"Checks budget, pantry, preferences and cooking constraints."
),
(
"🧠 Supervisor / Coordinator",
"Combines all agent outputs into one coordinated plan."
),
(
"👀 Monitoring Agent",
"Detects changes in the user's situation."
),
(
"🔄 Replanning Agent",
"Updates the plan when important conditions change."
)
]

cols = st.columns(3)

for index, (agent_name, description) in enumerate(
agent_names
):

```
with cols[index % 3]:

    st.markdown(
        f"""
        <div class="agent-box">
        <strong>{agent_name}</strong><br>
        <small>{description}</small>
        </div>
        """,
        unsafe_allow_html=True
    )
```

# ============================================================

# CONTINUOUS MONITORING

# ============================================================

st.header("👀 Continuous Monitoring & Replanning")

st.write(
"Tell the monitoring agent what changed in the user's situation."
)

change_text = st.text_area(
"Describe a change",
placeholder=(
"Example: I ran out of bananas and "
"my workout moved from 6 PM to 8 PM."
)
)

if st.button(
"🔍 DETECT CHANGE & REPLAN",
use_container_width=True
):

```
if st.session_state.current_state is None:

    st.warning(
        "Generate a plan first."
    )

elif not change_text.strip():

    st.warning(
        "Please describe what changed."
    )

else:

    with st.spinner(
        "Monitoring agent is analyzing the change..."
    ):

        old_state = deepcopy(
            st.session_state.current_state
        )

        new_state = deepcopy(
            st.session_state.current_state
        )

        new_state[
            "latest_change"
        ] = change_text

        monitor_result = agents.monitoring_agent(
            old_state,
            new_state
        )

        st.session_state.monitor_result = (
            monitor_result
        )

        if monitor_result.get(
            "replan_required",
            False
        ):

            old_plan = {}

            if st.session_state.plan_result:

                old_plan = st.session_state.plan_result.get(
                    "plan",
                    {}
                )

            replan_result = agents.replanning_agent(
                old_state,
                new_state,
                old_plan
            )

            st.session_state.replan_result = (
                replan_result
            )

            # Update persistent state
            st.session_state.current_state = (
                new_state
            )
```

# ============================================================

# MONITORING RESULT

# ============================================================

if st.session_state.monitor_result:

```
monitor = st.session_state.monitor_result

st.subheader(
    "🔍 Monitoring Agent Result"
)

if monitor.get(
    "change_detected",
    False
):

    st.warning(
        "Change detected."
    )

else:

    st.success(
        "No important change detected."
    )

changes = monitor.get(
    "changes",
    []
)

if changes:

    st.markdown(
        "**Detected Changes:**"
    )

    for change in changes:

        st.write(
            "• "
            + str(change)
        )

affected_days = monitor.get(
    "affected_days",
    []
)

if affected_days:

    st.markdown(
        "**Affected Days:** "
        + ", ".join(
            str(x)
            for x in affected_days
        )
    )

affected_components = monitor.get(
    "affected_components",
    []
)

if affected_components:

    st.markdown(
        "**Affected Components:** "
        + ", ".join(
            str(x)
            for x in affected_components
        )
    )

reason = monitor.get(
    "reason"
)

if reason:

    st.info(
        reason
    )
```

# ============================================================

# REPLANNING RESULT

# ============================================================

if st.session_state.replan_result:

```
replan = st.session_state.replan_result

st.subheader(
    "🔄 Replanning Agent Result"
)

updated_plan = replan.get(
    "updated_plan",
    {}
)

changes_made = replan.get(
    "changes_made",
    []
)

if changes_made:

    st.markdown(
        "**Changes Made:**"
    )

    for change in changes_made:

        st.write(
            "• "
            + str(change)
        )

if replan.get("reason"):

    st.info(
        replan["reason"]
    )

st.markdown(
    "### 📅 Updated Plan"
)

for day in days:

    day_data = updated_plan.get(
        day,
        {}
    )

    if isinstance(day_data, dict):

        with st.expander(
            f"🔄 Updated {day}"
        ):

            st.write(
                "**Workout:**",
                day_data.get(
                    "workout",
                    "Not specified"
                )
            )

            st.write(
                "**Breakfast:**",
                day_data.get(
                    "breakfast",
                    "Not specified"
                )
            )

            st.write(
                "**Lunch:**",
                day_data.get(
                    "lunch",
                    "Not specified"
                )
            )

            st.write(
                "**Snack:**",
                day_data.get(
                    "snack",
                    "Not specified"
                )
            )

            st.write(
                "**Dinner:**",
                day_data.get(
                    "dinner",
                    "Not specified"
                )
            )

            st.write(
                "**Reason:**",
                day_data.get(
                    "reason",
                    "Not specified"
                )
            )


new_grocery_list = replan.get(
    "new_grocery_list",
    []
)

if new_grocery_list:

    st.markdown(
        "### 🛒 Updated Grocery List"
    )

    for item in new_grocery_list:

        st.checkbox(
            str(item),
            key=f"new_grocery_{str(item)}"
        )
```

# ============================================================

# AGENTIC WORKFLOW

# ============================================================

st.header("🔄 Agentic Workflow")

st.markdown(
"""
**Observe → Analyze → Check → Decide → Act → Monitor → Replan**
"""
)

workflow_cols = st.columns(7)

workflow = [
("👀", "Observe"),
("🧠", "Analyze"),
("🔍", "Check"),
("🎯", "Decide"),
("⚡", "Act"),
("📡", "Monitor"),
("🔄", "Replan")
]

for col, (icon, label) in zip(
workflow_cols,
workflow
):

```
with col:

    st.markdown(
        f"""
        <div class="agent-box"
             style="text-align:center;">
        <div style="font-size:28px;">
        {icon}
        </div>
        <strong>{label}</strong>
        </div>
        """,
        unsafe_allow_html=True
    )
```

# ============================================================

# FOOTER

# ============================================================

st.divider()

st.caption(
"Built with Streamlit + Groq + Multi-Agent AI"
)

st.caption(
"This application is a planning assistant and "
"is not a medical diagnosis or treatment system."
)
