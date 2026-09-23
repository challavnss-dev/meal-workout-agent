import json
import base64
from groq import Groq


class MealWorkoutAgents:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(self, api_key):

        self.client = Groq(api_key=api_key)

        # Main reasoning/planning model
        self.text_model = "openai/gpt-oss-120b"

        # Vision model for pantry images
        self.vision_model = "qwen/qwen3.8-27b"

    # =========================================================
    # GENERAL GROQ CALL
    # =========================================================

    def call_ai(self, system_prompt, user_prompt):

        try:

            response = self.client.chat.completions.create(
                model=self.text_model,
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
                temperature=0.2,
                max_tokens=5000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:

            return f"AI_ERROR: {str(e)}"

    # =========================================================
    # JSON PARSER
    # =========================================================

    def extract_json(self, text):

        if not text:
            return {}

        text = text.strip()

        # Direct JSON
        try:
            return json.loads(text)

        except Exception:
            pass

        # JSON inside markdown
        if "```json" in text:

            try:

                text = text.split("```json", 1)[1]
                text = text.split("```", 1)[0]

                return json.loads(text.strip())

            except Exception:
                pass

        if "```" in text:

            try:

                text = text.split("```", 1)[1]
                text = text.split("```", 1)[0]

                return json.loads(text.strip())

            except Exception:
                pass

        return {
            "raw_response": text
        }

    # =========================================================
    # PANTRY VISION AGENT
    # =========================================================

    def pantry_vision_agent(self, image_bytes):

        if not image_bytes:

            return {
                "ingredients": [],
                "notes": "No image uploaded."
            }

        try:

            encoded_image = base64.b64encode(
                image_bytes
            ).decode("utf-8")

            response = self.client.chat.completions.create(

                model=self.vision_model,

                messages=[
                    {
                        "role": "system",
                        "content": """
You are the Pantry Vision Agent.

Analyze the uploaded pantry or food image.

Identify only food ingredients that are
reasonably visible.

Do not invent ingredients.

Return ONLY valid JSON:

{
  "ingredients": [
    {
      "name": "",
      "quantity_estimate": "",
      "confidence": "high/medium/low"
    }
  ],
  "notes": ""
}
"""
                    },

                    {
                        "role": "user",

                        "content": [

                            {
                                "type": "text",
                                "text":
                                "Identify the visible food ingredients."
                            },

                            {
                                "type": "image_url",

                                "image_url": {
                                    "url":
                                    f"data:image/jpeg;base64,{encoded_image}"
                                }
                            }

                        ]
                    }
                ],

                temperature=0.1,
                max_tokens=2000
            )

            result = response.choices[0].message.content

            return self.extract_json(result)

        except Exception as e:

            return {
                "ingredients": [],
                "notes": f"Vision error: {str(e)}"
            }

    # =========================================================
    # WORKOUT AGENT
    # =========================================================

    def workout_agent(self, state):

        prompt = f"""

USER CONTEXT:

{json.dumps(state, indent=2)}


You are the Workout Agent.

Analyze the user's weekly workout schedule.

For every day:

- identify workout type
- identify intensity
- determine whether it is a training or rest day
- identify useful meal-planning implications

Do not provide medical advice.

Return ONLY JSON:

{{
    "weekly_workout_analysis": [
        {{
            "day": "",
            "workout": "",
            "intensity": "",
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

    # =========================================================
    # MEAL AGENT
    # =========================================================

    def meal_agent(
        self,
        state,
        workout_result
    ):

        prompt = f"""

USER STATE:

{json.dumps(state, indent=2)}


WORKOUT ANALYSIS:

{json.dumps(workout_result, indent=2)}


You are the Meal Planning Agent.

Create a practical weekly meal plan.

Consider:

- food preference
- foods to avoid
- pantry ingredients
- budget
- cooking time
- daily schedule
- workout schedule

Prefer ingredients already available.

Do not make medical claims.

Return ONLY JSON:

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

    # =========================================================
    # CONSTRAINT AGENT
    # =========================================================

    def constraint_agent(
        self,
        state,
        workout_result,
        meal_result
    ):

        prompt = f"""

USER STATE:

{json.dumps(state, indent=2)}


WORKOUT ANALYSIS:

{json.dumps(workout_result, indent=2)}


MEAL PLAN:

{json.dumps(meal_result, indent=2)}


You are the Constraint Agent.

Check:

1. Food preference
2. Foods to avoid
3. Budget
4. Pantry availability
5. Cooking time
6. Daily schedule
7. Workout timing

Return ONLY JSON:

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

    # =========================================================
    # COORDINATOR AGENT
    # =========================================================

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


You are the Supervisor Coordinator Agent.

Your responsibility is to coordinate all
specialist agents.

If a constraint is violated:

- correct the affected component
- preserve valid recommendations
- avoid unnecessary changes

Create the final coordinated weekly plan.

Return ONLY JSON:

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

    # =========================================================
    # COMPLETE INITIAL PLANNING
    # =========================================================

    def create_plan(self, state):

        logs = []

        logs.append(
            "🏋️ Workout Agent: analyzing workout schedule"
        )

        workout_result = self.workout_agent(state)

        logs.append(
            "🍱 Meal Agent: generating meals"
        )

        meal_result = self.meal_agent(
            state,
            workout_result
        )

        logs.append(
            "🔍 Constraint Agent: checking constraints"
        )

        constraint_result = self.constraint_agent(
            state,
            workout_result,
            meal_result
        )

        logs.append(
            "🧠 Coordinator Agent: synchronizing agents"
        )

        final_plan = self.coordinator_agent(
            state,
            workout_result,
            meal_result,
            constraint_result
        )

        return {

            "plan": final_plan,

            "workout_analysis":
            workout_result,

            "meal_analysis":
            meal_result,

            "constraints":
            constraint_result,

            "logs":
            logs
        }

    # =========================================================
    # MONITORING AGENT
    # =========================================================

    def monitoring_agent(
        self,
        old_state,
        new_state,
        current_plan
    ):

        prompt = f"""

OLD STATE:

{json.dumps(old_state, indent=2)}


NEW STATE:

{json.dumps(new_state, indent=2)}


CURRENT PLAN:

{json.dumps(current_plan, indent=2)}


You are the Continuous Monitoring Agent.

Compare the old and new state.

Detect changes involving:

- pantry
- budget
- workout schedule
- cooking time
- food preference
- foods to avoid
- daily schedule

Determine whether the existing plan
needs to change.

Return ONLY JSON:

{{
    "changes_detected": [],
    "affected_days": [],
    "affected_components": [],
    "replan_required": true,
    "reason": ""
}}

"""

        result = self.call_ai(

            "You continuously monitor the user's planning context.",

            prompt
        )

        return self.extract_json(result)

    # =========================================================
    # REPLANNING AGENT
    # =========================================================

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

The user's environment has changed.

Update only the affected parts.

Preserve unaffected recommendations whenever possible.

Return ONLY JSON:

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
