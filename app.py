import streamlit as st
import json
import base64
from copy import deepcopy
from typing import Any, Dict, Optional
from groq import Groq

st.set_page_config(
page_title="Meal & Workout Coordination Agent",
page_icon="🍽️",
layout="wide"
)

    class MealWorkoutAgents:

def __init__(self, api_key: str):
    self.client = Groq(api_key=api_key)
    self.model = "qwen/qwen3.8-27b"

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

def extract_json(self, text: str) -> Dict[str, Any]:

    if not text:
        return {}

    text = text.strip()

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

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:

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

You are the Pantry Vision Agent.

Identify food ingredients that are clearly visible
in the uploaded pantry image.

Do not invent ingredients.

Return JSON only.

{
"ingredients": [],
"confidence_notes": ""
}
"""

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

        content = (
            response.choices[0].message.content
            or "{}"
        )

        return self.extract_json(content)

    except Exception as e:

        return {
            "ingredients": [],
            "error": str(e)
        }

def workout_agent(
    self,
    state: Dict[str, Any]
) -> Dict[str, Any]:

    system_prompt = """

You are the Workout Agent.

Create a practical weekly workout plan based on
the user's selected workout schedule.

Return JSON only.
"""

    user_prompt = f"""

USER STATE:

{json.dumps(state, indent=2)}

Create a workout plan for Monday through Sunday.

For every day include:

workout
duration_minutes
intensity

notes
"""

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

def meal_agent(
self,
state: Dict[str, Any],
workout_result: Dict[str, Any]
) -> Dict[str, Any]:

  system_prompt = """

You are the Meal Agent.

Create meals coordinated with:

workouts
food preference
pantry
budget
cooking time
foods to avoid

Prefer available pantry ingredients.

Return JSON only.
"""

    user_prompt = f"""

USER STATE:

{json.dumps(state, indent=2)}

WORKOUT PLAN:

{json.dumps(workout_result, indent=2)}

Create meals for Monday through Sunday.

For every day include:

breakfast
lunch
snack
dinner
approximate_cost

reason
"""

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

def constraint_agent(
self,
state: Dict[str, Any],
workout_result: Dict[str, Any],
meal_result: Dict[str, Any]
) -> Dict[str, Any]:

  system_prompt = """

You are the Constraint Agent.

Check the plan against:

food preference
foods to avoid
pantry
weekly budget
cooking time
workout schedule

Identify conflicts and corrections.

Return JSON only.
"""

    user_prompt = f"""

USER STATE:

{json.dumps(state, indent=2)}

WORKOUT:

{json.dumps(workout_result, indent=2)}

MEALS:

{json.dumps(meal_result, indent=2)}

Return:

{{
"status": "",
"estimated_budget": 0,
"violations": [],
"suggestions": [],
"pantry_items_used": [],
"missing_items": []
}}
"""

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
            "violations": [str(e)]
        }

def coordinator_agent(
    self,
    state: Dict[str, Any],
    workout_result: Dict[str, Any],
    meal_result: Dict[str, Any],
    constraint_result: Dict[str, Any]
) -> Dict[str, Any]:

    system_prompt = """

You are the Supervisor Coordinator Agent.

Combine the outputs of the Workout Agent,
Meal Agent and Constraint Agent.

Create one coordinated weekly meal and workout plan.

Return JSON only.
"""

    user_prompt = f"""

USER STATE:

{json.dumps(state, indent=2)}

WORKOUT AGENT:

{json.dumps(workout_result, indent=2)}

MEAL AGENT:

{json.dumps(meal_result, indent=2)}

CONSTRAINT AGENT:

{json.dumps(constraint_result, indent=2)}

Create the final weekly plan.

For every day include:

workout
breakfast
lunch
snack
dinner
reason

Also include:

summary
estimated_weekly_budget
grocery_list
constraint_status
active_agents

coordinator_explanation
"""

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
          "weekly_plan": {},
          "grocery_list": [],
          "error": str(e)
      }

def create_plan(
self,
state: Dict[str, Any]
) -> Dict[str, Any]:

  workout_result = self.workout_agent(state)

  meal_result = self.meal_agent(
      state,
      workout_result
  )

  constraint_result = self.constraint_agent(
      state,
      workout_result,
      meal_result
  )

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

def monitoring_agent(
self,
old_state: Dict[str, Any],
new_state: Dict[str, Any]
) -> Dict[str, Any]:

  system_prompt = """

You are the Monitoring Agent.

Compare the old state and new state.

Detect changes in:

pantry
workout
budget
cooking time
food preference
foods to avoid

Determine whether replanning is required.

Return JSON only.
"""

    user_prompt = f"""

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
            "reason": str(e)
        }

def replanning_agent(
    self,
    old_state: Dict[str, Any],
    new_state: Dict[str, Any],
    old_plan: Optional[Dict[str, Any]]
) -> Dict[str, Any]:

    system_prompt = """

You are the Replanning Agent.

The user's situation has changed.

Compare the old state and new state.

Preserve valid parts of the old plan.

Change only affected components.

Return JSON only.
"""

    user_prompt = f"""

OLD STATE:

{json.dumps(old_state, indent=2)}

NEW STATE:

{json.dumps(new_state, indent=2)}

OLD PLAN:

{json.dumps(old_plan or {}, indent=2)}

Create an updated weekly plan.

Return:

{{
"updated_plan": {{}},
"changes_made": [],
"reason": "",
"new_grocery_list": [],
"estimated_weekly_budget": 0
}}
"""

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
============================================================
GROQ API
============================================================

try:
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
st.error(
"GROQ_API_KEY is missing. "
"Add it in Streamlit Cloud → Manage app → Settings → Secrets."
)
st.stop()

try:
agents = MealWorkoutAgents(GROQ_API_KEY)
except Exception as e:
st.error(f"Could not initialize AI agents: {e}")
st.stop()

============================================================
SESSION STATE
============================================================

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

============================================================
HEADER
============================================================

st.title("🍽️ Meal & Workout Coordination Agent")

st.write(
"An adaptive multi-agent system that coordinates "
"meals, workouts, pantry, budget and daily constraints."
)

============================================================
SIDEBAR
============================================================

st.sidebar.header("👤 User Context")

name = st.sidebar.text_input(
"Name",
"User"
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
""
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
10,
120,
30
)

============================================================
WORKOUT SCHEDULE
============================================================

st.sidebar.header("🏋️ Workout Schedule")

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

workout_schedule[day] = st.sidebar.selectbox(
    day,
    workout_options,
    key="workout_" + day
)
============================================================
PANTRY
============================================================

st.sidebar.header("🥫 Pantry")

pantry_text = st.sidebar.text_area(
"Available Ingredients",
"Rice\nDal\nOats\nMilk\nBanana\nTomato\nOnion\nVegetables",
height=150
)

pantry_image = st.sidebar.file_uploader(
"📷 Upload Pantry Image",
type=[
"jpg",
"jpeg",
"png",
"webp"
]
)

============================================================
BUILD STATE
============================================================

def build_state():

return {
    "name": name,
    "food_preference": food_preference,
    "foods_to_avoid": foods_to_avoid,
    "weekly_budget": budget,
    "maximum_cooking_time_minutes": cooking_time,
    "workout_schedule": workout_schedule,
    "pantry": pantry_text
}
============================================================
GENERATE PLAN
============================================================

st.header("🚀 Generate Plan")

if st.button(
"🚀 GENERATE COORDINATED PLAN",
use_container_width=True
):

with st.spinner(
    "AI agents are coordinating your plan..."
):

    state = build_state()

    if pantry_image is not None:

        vision_result = agents.pantry_vision_agent(
            pantry_image.getvalue()
        )

        st.session_state.vision_result = (
            vision_result
        )

        state["vision_detected_ingredients"] = (
            vision_result.get(
                "ingredients",
                []
            )
        )

    result = agents.create_plan(state)

    st.session_state.current_state = state

    st.session_state.plan_result = result

    st.session_state.monitor_result = None

    st.session_state.replan_result = None
============================================================
PANTRY VISION RESULT
============================================================

if st.session_state.vision_result:

st.subheader("📷 Pantry Vision Agent")

ingredients = (
    st.session_state.vision_result
    .get("ingredients", [])
)

if ingredients:

    st.success(
        "Detected ingredients: "
        + ", ".join(
            str(x)
            for x in ingredients
        )
    )

notes = (
    st.session_state.vision_result
    .get("confidence_notes")
)

if notes:
    st.caption(notes)
============================================================
DISPLAY PLAN
============================================================

if st.session_state.plan_result:

result = st.session_state.plan_result

if result.get("error"):

    st.error(
        result["error"]
    )

plan = result.get(
    "plan",
    {}
)

weekly_plan = plan.get(
    "weekly_plan",
    {}
)

st.header("📅 Weekly Coordinated Plan")

for day in days:

    day_data = weekly_plan.get(
        day,
        {}
    )

    with st.expander(
        "📌 " + day,
        expanded=True
    ):

        if isinstance(day_data, dict):

            st.write(
                "🏋️ **Workout:**",
                day_data.get(
                    "workout",
                    "Not specified"
                )
            )

            st.write(
                "🍳 **Breakfast:**",
                day_data.get(
                    "breakfast",
                    "Not specified"
                )
            )

            st.write(
                "🥗 **Lunch:**",
                day_data.get(
                    "lunch",
                    "Not specified"
                )
            )

            st.write(
                "🍎 **Snack:**",
                day_data.get(
                    "snack",
                    "Not specified"
                )
            )

            st.write(
                "🍲 **Dinner:**",
                day_data.get(
                    "dinner",
                    "Not specified"
                )
            )

            st.write(
                "💡 **Reason:**",
                day_data.get(
                    "reason",
                    "Not specified"
                )
            )


# ========================================================
# SUMMARY
# ========================================================

st.header("📊 Plan Summary")

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Estimated Budget",
        "₹"
        + str(
            plan.get(
                "estimated_weekly_budget",
                0
            )
        )
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
        "Agents",
        len(
            result.get(
                "agents_used",
                []
            )
        )
    )


# ========================================================
# GROCERY LIST
# ========================================================

st.subheader("🛒 Grocery List")

grocery_list = plan.get(
    "grocery_list",
    []
)

for index, item in enumerate(
    grocery_list
):

    st.checkbox(
        str(item),
        key=f"grocery_{index}"
    )


# ========================================================
# COORDINATOR
# ========================================================

st.subheader("🧠 Coordinator Explanation")

st.info(
    plan.get(
        "coordinator_explanation",
        "The coordinator combined the specialist agents."
    )
)
============================================================
AGENT DASHBOARD
============================================================

st.header("🤖 AI Agent Dashboard")

agents_info = [
(
"🥗 Meal Agent",
"Creates coordinated meals."
),
(
"🏋️ Workout Agent",
"Creates workout plans."
),
(
"📷 Pantry Vision Agent",
"Reads ingredients from pantry images."
),
(
"🔍 Constraint Agent",
"Checks budget and constraints."
),
(
"🧠 Coordinator Agent",
"Combines all agent outputs."
),
(
"👀 Monitoring Agent",
"Detects changes."
),
(
"🔄 Replanning Agent",
"Updates the plan after changes."
)
]

for agent_name, description in agents_info:

st.info(
    f"**{agent_name}** — {description}"
)
============================================================
MONITORING
============================================================

st.header("👀 Continuous Monitoring & Replanning")

change_text = st.text_area(
"What changed?",
placeholder=(
"Example: I ran out of bananas and "
"my workout moved from 6 PM to 8 PM."
)
)

if st.button(
"🔍 DETECT CHANGE & REPLAN",
use_container_width=True
):

if st.session_state.current_state is None:

    st.warning(
        "Generate a plan first."
    )

elif not change_text.strip():

    st.warning(
        "Please describe the change."
    )

else:

    with st.spinner(
        "Monitoring and replanning..."
    ):

        old_state = deepcopy(
            st.session_state.current_state
        )

        new_state = deepcopy(
            st.session_state.current_state
        )

        new_state["latest_change"] = (
            change_text
        )

        monitor_result = (
            agents.monitoring_agent(
                old_state,
                new_state
            )
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

                old_plan = (
                    st.session_state.plan_result
                    .get("plan", {})
                )

            replan_result = (
                agents.replanning_agent(
                    old_state,
                    new_state,
                    old_plan
                )
            )

            st.session_state.replan_result = (
                replan_result
            )

            st.session_state.current_state = (
                new_state
            )
============================================================
MONITOR RESULT
============================================================

if st.session_state.monitor_result:

monitor = (
    st.session_state.monitor_result
)

st.subheader(
    "🔍 Monitoring Result"
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

if monitor.get("changes"):

    st.write("**Changes:**")

    for change in monitor["changes"]:

        st.write(
            "• " + str(change)
        )

if monitor.get("affected_days"):

    st.write(
        "**Affected days:** "
        + ", ".join(
            str(x)
            for x in monitor["affected_days"]
        )
    )

if monitor.get("affected_components"):

    st.write(
        "**Affected components:** "
        + ", ".join(
            str(x)
            for x in monitor["affected_components"]
        )
    )

if monitor.get("reason"):

    st.info(
        monitor["reason"]
    )
============================================================
REPLAN RESULT
============================================================

if st.session_state.replan_result:

replan = (
    st.session_state.replan_result
)

st.subheader(
    "🔄 Updated Plan"
)

if replan.get("changes_made"):

    st.write("**Changes made:**")

    for change in replan["changes_made"]:

        st.write(
            "• " + str(change)
        )

if replan.get("reason"):

    st.info(
        replan["reason"]
    )

updated_plan = replan.get(
    "updated_plan",
    {}
)

for day in days:

    day_data = updated_plan.get(
        day,
        {}
    )

    if isinstance(day_data, dict):

        with st.expander(
            "🔄 " + day
        ):

            st.write(
                "🏋️ Workout:",
                day_data.get(
                    "workout",
                    "Not specified"
                )
            )

            st.write(
                "🍳 Breakfast:",
                day_data.get(
                    "breakfast",
                    "Not specified"
                )
            )

            st.write(
                "🥗 Lunch:",
                day_data.get(
                    "lunch",
                    "Not specified"
                )
            )

            st.write(
                "🍎 Snack:",
                day_data.get(
                    "snack",
                    "Not specified"
                )
            )

            st.write(
                "🍲 Dinner:",
                day_data.get(
                    "dinner",
                    "Not specified"
                )
            )

            st.write(
                "💡 Reason:",
                day_data.get(
                    "reason",
                    "Not specified"
                )
            )


if replan.get("new_grocery_list"):

    st.subheader(
        "🛒 Updated Grocery List"
    )

    for index, item in enumerate(
        replan["new_grocery_list"]
    ):

        st.checkbox(
            str(item),
            key=f"updated_grocery_{index}"
        )
============================================================
AGENTIC WORKFLOW
============================================================

st.header("🔄 Agentic Workflow")

st.write(
"Observe → Analyze → Check → Decide → Act → Monitor → Replan"
)

st.divider()

st.caption(
"Built with Streamlit + Groq + Multi-Agent AI"
)

st.caption(
"This is a planning assistant and not a medical "
"diagnosis or treatment system."
)
