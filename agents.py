````python
import json
import base64
from copy import deepcopy
from openai import OpenAI


class MealWorkoutAgents:
    """
    Multi-agent coordination system for the
    Meal & Workout Coordination Agent.

    Agents:
    1. Pantry/Vision Agent
    2. Workout Agent
    3. Meal Agent
    4. Constraint Agent
    5. Coordinator Agent
    6. Monitoring Agent
    7. Replanning Agent
    """

    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-5.6-luna"

    # ---------------------------------------------------------
    # GENERAL AI CALL
    # ---------------------------------------------------------

    def call_ai(self, system_prompt, user_prompt):
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=user_prompt
            )

            return response.output_text.strip()

        except Exception as e:
            return f"AI_ERROR: {str(e)}"

    # ---------------------------------------------------------
    # JSON EXTRACTION
    # ---------------------------------------------------------

    def extract_json(self, text):
        """
        Converts an AI response into a Python dictionary.
        Handles responses that contain markdown code fences.
        """

        if not text:
            return {}

        text = text.strip()

        try:
            return json.loads(text)
        except Exception:
            pass

        if "```json" in text:
            text = text.split("```json", 1)[1]
            text = text.split("```", 1)[0]

        elif "```" in text:
            text = text.split("```", 1)[1]
            text = text.split("```", 1)[0]

        try:
            return json.loads(text.strip())
        except Exception:
            return {
                "raw_response": text
            }

    # ---------------------------------------------------------
    # PANTRY / VISION AGENT
    # ---------------------------------------------------------

    def pantry_vision_agent(self, image_bytes):
        """
        Analyzes a pantry/fridge image and identifies
        visible ingredients.
        """

        if not image_bytes:
            return {
                "ingredients": [],
                "confidence": "none",
                "notes": "No image supplied."
            }

        try:
            encoded = base64.b64encode(image_bytes).decode("utf-8")

            response = self.client.responses.create(
                model=self.model,
                instructions="""
You are the Pantry Vision Agent.

Analyze the uploaded pantry/fridge image.

Identify only ingredients or food items that are reasonably
visible.

Do not invent items that cannot be seen.

Return ONLY valid JSON:

{
  "ingredients": [
    {
      "name": "ingredient",
      "quantity_estimate": "approximate quantity or unknown",
      "confidence": "high/medium/low"
    }
  ],
  "notes": "short explanation"
}
""",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "Identify the visible food ingredients."
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{encoded}"
                            }
                        ]
                    }
                ]
            )

            return self.extract_json(response.output_text)

        except Exception as e:
            return {
                "ingredients": [],
                "confidence": "error",
                "notes": f"Vision error: {str(e)}"
            }

    # ---------------------------------------------------------
    # WORKOUT AGENT
    # ---------------------------------------------------------

    def workout_agent(self, state):

        prompt = f"""
User context:

{json.dumps(state, indent=2)}

You are the Workout Agent.

Analyze the weekly workout schedule.

For each workout day:
- identify workout type
- estimate workout intensity
- identify whether the day is training or rest
- identify useful meal-planning implications
- identify approximate timing if available

Do not provide medical advice.

Return ONLY valid JSON:

{{
  "weekly_workout_analysis": [
    {{
      "day": "",
      "workout": "",
      "intensity": "low/medium/high/rest",
      "meal_implication": ""
    }}
  ],
  "overall_summary": ""
}}
"""

        result = self.call_ai(
            "You are a workout planning specialist.",
            prompt
        )

        return self.extract_json(result)

    # ---------------------------------------------------------
    # MEAL AGENT
    # ---------------------------------------------------------

    def meal_agent(self, state, workout_result):

        prompt = f"""
USER STATE:
{json.dumps(state, indent=2)}

WORKOUT ANALYSIS:
{json.dumps(workout_result, indent=2)}

You are the Meal Planning Agent.

Create meals that coordinate with the user's workout schedule.

Consider:
- food preference
- foods to avoid
- available pantry ingredients
- budget
- cooking time
- daily schedule
- workout timing
- rest days

Prefer pantry ingredients before suggesting purchases.

Do not make medical claims.

Return ONLY valid JSON:

{{
  "weekly_meals": [
    {{
      "day": "",
      "breakfast": "",
      "lunch": "",
      "snack": "",
      "dinner": "",
      "reason": ""
    }}
  ],
  "estimated_budget": 0,
  "grocery_items": []
}}
"""

        result = self.call_ai(
            "You are a practical meal planning specialist.",
            prompt
        )

        return self.extract_json(result)

    # ---------------------------------------------------------
    # CONSTRAINT AGENT
    # ---------------------------------------------------------

    def constraint_agent(self, state, workout_result, meal_result):

        prompt = f"""
USER STATE:
{json.dumps(state, indent=2)}

WORKOUT ANALYSIS:
{json.dumps(workout_result, indent=2)}

MEAL PLAN:
{json.dumps(meal_result, indent=2)}

You are the Constraint Checking Agent.

Check whether the proposed plan respects:

1. Food preference
2. Foods to avoid
3. Budget
4. Pantry availability
5. Cooking time
6. Daily schedule
7. Workout timing

Return ONLY valid JSON:

{{
  "status": "PASS/PARTIAL/FAIL",
  "issues": [],
  "warnings": [],
  "corrections": []
}}
"""

        result = self.call_ai(
            "You are a strict constraint validation agent.",
            prompt
        )

        return self.extract_json(result)

    # ---------------------------------------------------------
    # COORDINATOR AGENT
    # ---------------------------------------------------------

    def coordinator_agent(
        self,
        state,
        workout_result,
        meal_result,
        constraint_result
    ):

        prompt = f"""
USER STATE:
{json.dumps(state, indent=2)}

WORKOUT AGENT:
{json.dumps(workout_result, indent=2)}

MEAL AGENT:
{json.dumps(meal_result, indent=2)}

CONSTRAINT AGENT:
{json.dumps(constraint_result, indent=2)}

You are the Supervisor / Coordinator Agent.

Your job is to coordinate all specialist agents.

If constraints are violated:
- fix the affected parts
- preserve valid parts
- avoid rebuilding everything unnecessarily

Create a clear final weekly routine.

Return ONLY valid JSON:

{{
  "weekly_plan": [
    {{
      "day": "",
      "workout": "",
      "breakfast": "",
      "lunch": "",
      "snack": "",
      "dinner": "",
      "reason": ""
    }}
  ],
  "grocery_list": [],
  "estimated_budget": 0,
  "constraint_status": "",
  "coordination_summary": "",
  "agent_decisions": []
}}
"""

        result = self.call_ai(
            "You are the Supervisor Coordinator Agent.",
            prompt
        )

        return self.extract_json(result)

    # ---------------------------------------------------------
    # COMPLETE INITIAL PLAN
    # ---------------------------------------------------------

    def create_plan(self, state):

        logs = []

        logs.append("Workout Agent: analyzing workout schedule")
        workout_result = self.workout_agent(state)

        logs.append("Meal Agent: generating coordinated meals")
        meal_result = self.meal_agent(
            state,
            workout_result
        )

        logs.append("Constraint Agent: validating plan")
        constraint_result = self.constraint_agent(
            state,
            workout_result,
            meal_result
        )

        logs.append("Coordinator Agent: synchronizing all agents")
        final_plan = self.coordinator_agent(
            state,
            workout_result,
            meal_result,
            constraint_result
        )

        return {
            "plan": final_plan,
            "workout_analysis": workout_result,
            "meal_analysis": meal_result,
            "constraints": constraint_result,
            "logs": logs
        }

    # ---------------------------------------------------------
    # MONITORING AGENT
    # ---------------------------------------------------------

    def monitoring_agent(self, old_state, new_state, current_plan):

        prompt = f"""
OLD STATE:
{json.dumps(old_state, indent=2)}

NEW STATE:
{json.dumps(new_state, indent=2)}

CURRENT PLAN:
{json.dumps(current_plan, indent=2)}

You are the Continuous Monitoring Agent.

Compare the old and new states.

Detect changes involving:
- pantry
- budget
- workout schedule
- cooking time
- food preference
- foods to avoid
- daily schedule

Determine whether the existing plan is still valid.

Return ONLY valid JSON:

{{
  "changes_detected": [],
  "affected_days": [],
  "affected_components": [],
  "replan_required": true,
  "reason": ""
}}
"""

        result = self.call_ai(
            "You continuously monitor planning context and detect changes.",
            prompt
        )

        return self.extract_json(result)

    # ---------------------------------------------------------
    # REPLANNING AGENT
    # ---------------------------------------------------------

    def replanning_agent(
        self,
        state,
        current_plan,
        monitoring_result
    ):

        prompt = f"""
CURRENT STATE:
{json.dumps(state, indent=2)}

CURRENT PLAN:
{json.dumps(current_plan, indent=2)}

MONITORING RESULT:
{json.dumps(monitoring_result, indent=2)}

You are the Replanning Agent.

The environment has changed.

Update only the parts of the weekly plan that are affected.

Keep unaffected recommendations whenever possible.

Return ONLY valid JSON:

{{
  "updated_plan": [],
  "changes_made": [],
  "reason": "",
  "new_grocery_list": [],
  "estimated_budget": 0
}}
"""

        result = self.call_ai(
            "You are an adaptive replanning specialist.",
            prompt
        )

        return self.extract_json(result)
````
