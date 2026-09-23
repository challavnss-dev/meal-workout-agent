import json
import base64
from typing import Any, Dict, Optional

from groq import Groq

class MealWorkoutAgents:
"""
Multi-agent system for coordinating:
- Workout planning
- Meal planning
- Pantry/vision analysis
- Constraint checking
- Coordination
- Monitoring
- Replanning
"""

def __init__(self, api_key: str):
    if not api_key:
        raise ValueError("Groq API key is missing.")

    self.client = Groq(api_key=api_key)

    # Current Groq model with text + vision + JSON support.
    self.model = "qwen/qwen3.8-27b"

# ---------------------------------------------------------
# BASIC AI CALL
# ---------------------------------------------------------

def call_ai(
    self,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 4000,
) -> str:
    """
    Sends a text request to Groq and returns the response text.
    """

    response = self.client.chat.completions.create(
        model=self.model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=temperature,
        max_completion_tokens=max_tokens,
    )

    return response.choices[0].message.content or ""

# ---------------------------------------------------------
# JSON PARSER
# ---------------------------------------------------------

def extract_json(self, text: str) -> Dict[str, Any]:
    """
    Safely converts AI output into a Python dictionary.
    """

    if not text:
        return {}

    text = text.strip()

    # Remove accidental Markdown code fences.
    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # Try normal JSON.
    try:
        result = json.loads(text)

        if isinstance(result, dict):
            return result

        return {"result": result}

    except json.JSONDecodeError:
        pass

    # Try to find the first JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        possible_json = text[start : end + 1]

        try:
            result = json.loads(possible_json)

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError:
            pass

    return {
        "raw_response": text
    }

# ---------------------------------------------------------
# PANTRY VISION AGENT
# ---------------------------------------------------------

def pantry_vision_agent(self, image_bytes: bytes) -> Dict[str, Any]:
    """
    Looks at a pantry image and identifies visible ingredients.
    """

    if not image_bytes:
        return {
            "ingredients": [],
            "notes": "No pantry image was provided."
        }

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    image_data_url = (
        "data:image/jpeg;base64,"
        + image_base64
    )

    system_prompt = """

You are the Pantry Vision Agent in a meal and workout coordination system.

Your task is to inspect the uploaded pantry image and identify food
ingredients that are clearly visible.

Do not invent ingredients.

Return valid JSON only.

Required format:
{
"ingredients": [
"ingredient 1",
"ingredient 2"
],
"confidence_notes": "short explanation"
}
"""

    try:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Identify the visible food ingredients "
                                "in this pantry image."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url
                            },
                        },
                    ],
                },
            ],
            temperature=0.1,
            max_completion_tokens=1500,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"

        return self.extract_json(content)

    except Exception as e:
        return {
            "ingredients": [],
            "error": str(e)
        }

# ---------------------------------------------------------
# WORKOUT AGENT
# ---------------------------------------------------------

def workout_agent(
    self,
    state: Dict[str, Any]
) -> Dict[str, Any]:

    system_prompt = """

You are the Workout Planning Agent.

Create a simple weekly workout plan based on the user's supplied
schedule.

Respect the workout types selected by the user.

Do not provide medical diagnosis or medical treatment.

Return valid JSON only.
"""

    user_prompt = f"""

USER STATE:

{json.dumps(state, indent=2)}

Create a workout plan for every day of the week.

For each day provide:

workout
duration_minutes
intensity
notes

Return:

{{
"workouts": {{
"Monday": {{}},
"Tuesday": {{}},
"Wednesday": {{}},
"Thursday": {{}},
"Friday": {{}},
"Saturday": {{}},
"Sunday": {{}}
}}
}}
"""

    try:
        result = self.call_ai(
            system_prompt,
            user_prompt,
            temperature=0.2,
            max_tokens=2500,
        )

        return self.extract_json(result)

    except Exception as e:
        return {
            "workouts": {},
            "error": str(e)
        }

# ---------------------------------------------------------
# MEAL AGENT
# ---------------------------------------------------------

def meal_agent(
    self,
    state: Dict[str, Any],
    workout_result: Dict[str, Any]
) -> Dict[str, Any]:

    system_prompt = """

You are the Meal Planning Agent.

Create meals that coordinate with the user's workouts, food
preferences, available ingredients, budget and cooking time.

Prefer ingredients already available in the pantry.

Do not make medical or disease-treatment claims.

Return valid JSON only.
"""

    user_prompt = f"""

USER STATE:

{json.dumps(state, indent=2)}

WORKOUT PLAN:

{json.dumps(workout_result, indent=2)}

Create a meal plan for Monday through Sunday.

Each day should contain:

breakfast
lunch
snack
dinner
approximate_cost
reason

Keep the meals practical and simple.

Return:

{{
"meals": {{
"Monday": {{}},
"Tuesday": {{}},
"Wednesday": {{}},
"Thursday": {{}},
"Friday": {{}},
"Saturday": {{}},
"Sunday": {{}}
}}
}}
"""

    try:
        result = self.call_ai(
            system_prompt,
            user_prompt,
            temperature=0.3,
            max_tokens=4500,
        )

        return self.extract_json(result)

    except Exception as e:
        return {
            "meals": {},
            "error": str(e)
        }

# ---------------------------------------------------------
# CONSTRAINT AGENT
# ---------------------------------------------------------

def constraint_agent(
    self,
    state: Dict[str, Any],
    workout_result: Dict[str, Any],
    meal_result: Dict[str, Any]
) -> Dict[str, Any]:

    system_prompt = """

You are the Constraint Checking Agent.

Check whether the proposed meal and workout plan respects:

Food preference
Foods to avoid
Pantry availability
Weekly food budget
Cooking time
Workout schedule
Practicality

Identify conflicts and suggest corrections.

Return valid JSON only.
"""

    user_prompt = f"""

USER STATE:

{json.dumps(state, indent=2)}

WORKOUT PLAN:

{json.dumps(workout_result, indent=2)}

MEAL PLAN:

{json.dumps(meal_result, indent=2)}

Return:

{{
"status": "PASS or NEEDS_ADJUSTMENT",
"estimated_budget": 0,
"budget_limit": 0,
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
            max_tokens=2500,
        )

        return self.extract_json(result)

    except Exception as e:
        return {
            "status": "ERROR",
            "violations": [str(e)],
            "suggestions": []
        }

# ---------------------------------------------------------
# COORDINATOR AGENT
# ---------------------------------------------------------

def coordinator_agent(
    self,
    state: Dict[str, Any],
    workout_result: Dict[str, Any],
    meal_result: Dict[str, Any],
    constraint_result: Dict[str, Any]
) -> Dict[str, Any]:

    system_prompt = """

You are the Supervisor / Coordinator Agent.

You coordinate multiple specialist agents.

Your job is to combine:

workout recommendations
meal recommendations
pantry information
user preferences
constraints
budget
cooking time

Create one coordinated weekly plan.

If the constraint agent identifies a conflict, correct it.

The final result should be practical and easy for the user to understand.

Return valid JSON only.
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

Create the final coordinated weekly plan.

For every day provide:

workout
breakfast
lunch
snack
dinner
reason

Also provide:

summary
estimated_weekly_budget
grocery_list
constraint_status
active_agents
coordinator_explanation

Return:

{{
"summary": "",
"estimated_weekly_budget": 0,
"constraint_status": "",
"active_agents": [],
"coordinator_explanation": "",
"weekly_plan": {{
"Monday": {{}},
"Tuesday": {{}},
"Wednesday": {{}},
"Thursday": {{}},
"Friday": {{}},
"Saturday": {{}},
"Sunday": {{}}
}},
"grocery_list": []
}}
"""

    try:
        result = self.call_ai(
            system_prompt,
            user_prompt,
            temperature=0.2,
            max_tokens=6000,
        )

        return self.extract_json(result)

    except Exception as e:
        return {
            "summary": "Coordinator failed.",
            "weekly_plan": {},
            "grocery_list": [],
            "error": str(e)
        }

# ---------------------------------------------------------
# CREATE COMPLETE PLAN
# ---------------------------------------------------------

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
                "Supervisor / Coordinator Agent",
            ],
        }

    except Exception as e:
        return {
            "plan": {},
            "error": str(e),
            "agents_used": []
        }

# ---------------------------------------------------------
# MONITORING AGENT
# ---------------------------------------------------------

def monitoring_agent(
    self,
    old_state: Dict[str, Any],
    new_state: Dict[str, Any]
) -> Dict[str, Any]:

    system_prompt = """

You are the Monitoring Agent.

Compare the previous user state with the new user state.

Detect meaningful changes such as:

pantry changes
workout schedule changes
budget changes
cooking time changes
food preference changes
foods to avoid changes
newly detected pantry ingredients

Determine whether the existing plan needs to be changed.

Return valid JSON only.
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
            max_tokens=2500,
        )

        return self.extract_json(result)

    except Exception as e:
        return {
            "change_detected": True,
            "replan_required": True,
            "changes": [str(e)],
            "affected_days": [],
            "affected_components": [],
            "reason": "Monitoring agent encountered an error."
        }

# ---------------------------------------------------------
# REPLANNING AGENT
# ---------------------------------------------------------

def replanning_agent(
    self,
    old_state: Dict[str, Any],
    new_state: Dict[str, Any],
    old_plan: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    system_prompt = """

You are the Replanning Agent.

The user's real-world situation has changed.

Compare the previous state with the new state and update the
meal/workout plan accordingly.

Preserve parts of the old plan that are still valid.

Only change affected parts where practical.

Examples:

If bananas are unavailable, replace banana-based meals.
If workout time changes, adjust meal timing.
If the budget decreases, choose cheaper meals.
If cooking time decreases, choose simpler meals.
If a workout becomes Rest, coordinate meals accordingly.

Return valid JSON only.
"""

    user_prompt = f"""

OLD STATE:

{json.dumps(old_state, indent=2)}

NEW STATE:

{json.dumps(new_state, indent=2)}

OLD PLAN:

{json.dumps(old_plan or {}, indent=2)}

Create an updated plan.

Return:

{{
"updated_plan": {{
"Monday": {{}},
"Tuesday": {{}},
"Wednesday": {{}},
"Thursday": {{}},
"Friday": {{}},
"Saturday": {{}},
"Sunday": {{}}
}},
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
            max_tokens=6000,
        )

        return self.extract_json(result)

    except Exception as e:
        return {
            "updated_plan": {},
            "changes_made": [],
            "reason": str(e),
            "new_grocery_list": []
        }
