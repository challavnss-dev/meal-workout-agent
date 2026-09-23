import os
import json
import base64
import re
from copy import deepcopy
from typing import Any, Dict, List
import streamlit as st
from groq import Groq

# ============================================================
# APP CONFIG
# ============================================================
st.set_page_config(
    page_title="NourishSync AI",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# STYLING
# ============================================================
st.markdown(
    """
    <style>
    .hero {
        padding: 25px;
        border-radius: 18px;
        border: 1px solid rgba(128,128,128,0.25);
        margin-bottom: 20px;
        background: rgba(255, 255, 255, 0.03);
    }

    .hero-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .hero-subtitle {
        font-size: 18px;
        opacity: 0.75;
    }

    .agent-card {
        padding: 15px;
        border-radius: 14px;
        border: 1px solid rgba(128,128,128,0.25);
        min-height: 120px;
        background: rgba(255, 255, 255, 0.02);
        margin-bottom: 10px;
    }

    .agent-title {
        font-weight: 700;
        font-size: 17px;
    }

    .small {
        opacity: 0.7;
        font-size: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================
DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False)
    except Exception:
        return str(value)

def normalize_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [
            x.strip()
            for x in re.split(r"[,;\n]", value)
            if x.strip()
        ]
    return [str(value)]

def contains_any(text: str, words: List[str]) -> bool:
    text = str(text).lower()
    for word in words:
        if word.lower() in text:
            return True
    return False

# ============================================================
# AI AGENT ENGINE
# ============================================================
class NourishSyncAgents:

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Groq API key is missing.")

        self.client = Groq(api_key=api_key)
        # Active production models on Groq
        self.text_models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]
        self.vision_model = "llama-3.2-11b-vision-instruct"

    # --------------------------------------------------------
    # GENERIC AI CALL WITH FALLBACK
    # --------------------------------------------------------
    def ask(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4000
    ) -> str:
        for model in self.text_models:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_completion_tokens=max_tokens
                )
                return response.choices[0].message.content or ""
            except Exception:
                continue
        return ""

    # --------------------------------------------------------
    # JSON EXTRACTION
    # --------------------------------------------------------
    def parse_json(self, text: str) -> Dict[str, Any]:
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
        except Exception:
            pass

        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:
            try:
                result = json.loads(text[start:end + 1])
                if isinstance(result, dict):
                    return result
            except Exception:
                pass

        return {"raw_response": text}

    # --------------------------------------------------------
    # PANTRY VISION AGENT
    # --------------------------------------------------------
    def pantry_agent(self, image_bytes: bytes) -> Dict[str, Any]:
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{image_base64}"

        system_prompt = """
You are Pantry Vision Agent.
Analyze a pantry or kitchen image.
Identify only food ingredients that are reasonably visible.
Do not invent ingredients.
Return JSON only:
{
  "ingredients": [],
  "uncertain_items": [],
  "observations": ""
}
"""
        try:
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Identify ingredients visible in this image."},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                temperature=0.1,
                max_completion_tokens=1800,
                response_format={"type": "json_object"}
            )
            return self.parse_json(response.choices[0].message.content or "{}")
        except Exception as e:
            return {"ingredients": [], "error": str(e)}

    # --------------------------------------------------------
    # WORKOUT AGENT
    # --------------------------------------------------------
    def workout_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
USER CONTEXT:
{safe_json(state)}

Create a practical weekly workout schedule.
Respect the user's selected workout type for each day.
For every day (Monday to Sunday) return:
workout
duration_minutes
intensity
preferred_time
notes

Return JSON only with keys corresponding to days of the week.
"""
        system = """
You are the Workout Agent.
Your role is to coordinate exercise scheduling with the user's weekly constraints.
Do not diagnose medical conditions.
Do not provide medical treatment.
"""
        try:
            return self.parse_json(self.ask(system, prompt, temperature=0.2, max_tokens=3000))
        except Exception as e:
            return {"error": str(e)}

    # --------------------------------------------------------
    # MEAL AGENT
    # --------------------------------------------------------
    def meal_agent(self, state: Dict[str, Any], workout: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
USER CONTEXT:
{safe_json(state)}
WORKOUT PLAN:
{safe_json(workout)}

Create a seven-day meal plan.
Prioritize ingredients already in the pantry.
Respect:
- food preference
- foods to avoid
- weekly budget
- cooking time
- workout schedule

For each day provide:
breakfast, lunch, snack, dinner, estimated_cost, reason.
Also provide: grocery_list (array of strings).
Return JSON only.
"""
        system = """
You are the Meal Planning Agent.
You coordinate food with workout timing, inventory, budget and cooking constraints.
Keep meals practical and affordable.
Do not make medical claims.
"""
        try:
            return self.parse_json(self.ask(system, prompt, temperature=0.3, max_tokens=4000))
        except Exception as e:
            return {"error": str(e)}

    # --------------------------------------------------------
    # CONSTRAINT AGENT
    # --------------------------------------------------------
    def constraint_agent(
        self,
        state: Dict[str, Any],
        workout: Dict[str, Any],
        meals: Dict[str, Any]
    ) -> Dict[str, Any]:
        prompt = f"""
USER:
{safe_json(state)}
WORKOUT:
{safe_json(workout)}
MEALS:
{safe_json(meals)}

Audit the complete plan.
Check: Food preference, Foods to avoid, Pantry usage, Budget, Cooking time, Workout alignment, Practicality.
Return JSON only:
{{
  "status": "PASS or NEEDS_ADJUSTMENT",
  "estimated_budget": 0,
  "violations": [],
  "warnings": [],
  "suggestions": []
}}
"""
        system = """
You are the Constraint and Validation Agent.
Your job is to challenge the proposed plan, not blindly accept it.
"""
        try:
            return self.parse_json(self.ask(system, prompt, temperature=0.1, max_tokens=2000))
        except Exception as e:
            return {"status": "ERROR", "violations": [str(e)]}

    # --------------------------------------------------------
    # COORDINATOR AGENT
    # --------------------------------------------------------
    def coordinator_agent(
        self,
        state: Dict[str, Any],
        workout: Dict[str, Any],
        meals: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        prompt = f"""
USER CONTEXT:
{safe_json(state)}
WORKOUT AGENT:
{safe_json(workout)}
MEAL AGENT:
{safe_json(meals)}
CONSTRAINT AGENT:
{safe_json(constraints)}

You are the Supervisor Coordinator.
Combine all agent outputs.
If constraints identify problems, fix them.
Create one final coordinated seven-day plan.

Return JSON matching this format EXACTLY:
{{
  "summary": "High level overview",
  "estimated_weekly_budget": 200,
  "plan_score": 95,
  "coordination_logic": "Why this plan is unified",
  "grocery_list": ["item1", "item2"],
  "weekly_plan": {{
     "Monday": {{
        "workout": "Strength Training",
        "breakfast": "...",
        "lunch": "...",
        "snack": "...",
        "dinner": "...",
        "estimated_cost": 35,
        "reason": "..."
     }},
     ... (Monday through Sunday)
  }}
}}
"""
        system = """
You are the Supervisor Agent.
You have authority to coordinate specialist agents.
Resolve conflicts and explain why the final plan is coordinated.
"""
        try:
            return self.parse_json(self.ask(system, prompt, temperature=0.2, max_tokens=4500))
        except Exception as e:
            return {"error": str(e)}

    # --------------------------------------------------------
    # MONITORING AGENT
    # --------------------------------------------------------
    def monitoring_agent(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
OLD STATE:
{safe_json(old_state)}
NEW STATE:
{safe_json(new_state)}

Compare the two states.
Identify exactly what changed.
Return JSON:
{{
  "change_detected": true,
  "replan_required": true,
  "changes": [],
  "affected_days": [],
  "affected_components": [],
  "reason": ""
}}
"""
        system = """
You are the Monitoring Agent.
Your job is to detect environmental changes that could invalidate parts of an existing plan.
"""
        try:
            return self.parse_json(self.ask(system, prompt, temperature=0.1, max_tokens=2000))
        except Exception as e:
            return {
                "change_detected": True,
                "replan_required": True,
                "changes": [str(e)],
                "reason": str(e)
            }

    # --------------------------------------------------------
    # REPLANNING AGENT
    # --------------------------------------------------------
    def replanning_agent(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any],
        old_plan: Dict[str, Any],
        monitor_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        prompt = f"""
OLD STATE:
{safe_json(old_state)}
NEW STATE:
{safe_json(new_state)}
OLD PLAN:
{safe_json(old_plan)}
MONITORING RESULT:
{safe_json(monitor_result)}

Update the plan.
Preserve unaffected parts.
Only modify components that need changing.
Return JSON:
{{
  "updated_plan": {{
     "Monday": {{
        "workout": "...",
        "breakfast": "...",
        "lunch": "...",
        "snack": "...",
        "dinner": "..."
     }}
  }},
  "changes_made": [],
  "reason": "",
  "new_grocery_list": [],
  "estimated_weekly_budget": 0,
  "new_plan_score": 0
}}
"""
        system = """
You are the Replanning Agent.
Perform targeted adaptation without unnecessarily regenerating unaffected components.
"""
        try:
            return self.parse_json(self.ask(system, prompt, temperature=0.2, max_tokens=4500))
        except Exception as e:
            return {"error": str(e)}

    # --------------------------------------------------------
    # COMPLETE PLAN PIPELINE
    # --------------------------------------------------------
    def generate_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        workout = self.workout_agent(state)
        meals = self.meal_agent(state, workout)
        constraints = self.constraint_agent(state, workout, meals)
        final_plan = self.coordinator_agent(state, workout, meals, constraints)

        return {
            "workout": workout,
            "meals": meals,
            "constraints": constraints,
            "plan": final_plan
        }

# ============================================================
# DETERMINISTIC VALIDATION
# ============================================================
def deterministic_audit(state: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    issues = []
    budget = float(state.get("weekly_budget", 0))
    estimated = float(plan.get("estimated_weekly_budget", 0) or 0)

    if estimated > budget and budget > 0:
        issues.append(f"Estimated budget ₹{estimated} exceeds the limit of ₹{budget}.")

    avoid = normalize_list(state.get("foods_to_avoid", ""))
    plan_text = safe_json(plan).lower()

    for item in avoid:
        if item and item.lower() in plan_text:
            issues.append(f"Food to avoid may appear in the plan: {item}")

    preference = str(state.get("food_preference", "")).lower()

    if preference == "vegan":
        animal_foods = ["milk", "cheese", "curd", "yogurt", "egg", "chicken", "fish", "meat"]
        for food in animal_foods:
            if food in plan_text:
                issues.append(f"Possible vegan constraint conflict: {food}")

    score = 100
    score -= min(len(issues) * 10, 50)

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "audit_score": max(score, 50)
    }

# ============================================================
# INITIALIZE GROQ ENGINE & SESSION STATE
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY and "GROQ_API_KEY" in st.secrets:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY is missing!")
    st.info("Set `GROQ_API_KEY` in environment variables or Streamlit Cloud Secrets.")
    st.stop()

try:
    engine = NourishSyncAgents(GROQ_API_KEY)
except Exception as e:
    st.error(f"AI initialization failed: {e}")
    st.stop()

defaults = {
    "state": None,
    "result": None,
    "vision": None,
    "monitor": None,
    "replan": None,
    "activity": []
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ============================================================
# HERO HEADER
# ============================================================
st.markdown(
    """
    <div class="hero">
        <div class="hero-title">🥗 NourishSync AI</div>
        <div class="hero-subtitle">Adaptive Meal × Workout Coordination Agent</div>
        <p style="margin-top: 10px;">
        An agentic system that observes user context, coordinates multiple specialist agents,
        validates constraints, and dynamically adapts when real-world conditions change.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# SIDEBAR INPUTS
# ============================================================
st.sidebar.header("👤 User Profile")
name = st.sidebar.text_input("Name", "User")
food_preference = st.sidebar.selectbox(
    "Food preference",
    ["Vegetarian", "Non-Vegetarian", "Vegan", "Eggetarian"]
)
avoid = st.sidebar.text_input("Foods to avoid", placeholder="Example: peanuts, mushrooms")
budget = st.sidebar.number_input("Weekly food budget ₹", min_value=100, max_value=10000, value=2500, step=100)
cook_time = st.sidebar.slider("Maximum cooking time (mins)", 10, 120, 30)

st.sidebar.header("🏋️ Workout Schedule")
workout_options = ["Strength Training", "Cardio", "Full Body", "Mobility", "Rest"]
schedule = {}
for day in DAYS:
    schedule[day] = st.sidebar.selectbox(day, workout_options, key=f"schedule_{day}")

st.sidebar.header("🥫 Pantry")
pantry = st.sidebar.text_area(
    "Current ingredients",
    value="Rice\nDal\nOats\nMilk\nBanana\nTomato\nOnion\nVegetables",
    height=140
)

pantry_image = st.sidebar.file_uploader("📷 Scan pantry image", type=["jpg", "jpeg", "png", "webp"])

def build_state():
    return {
        "name": name,
        "food_preference": food_preference,
        "foods_to_avoid": avoid,
        "weekly_budget": budget,
        "maximum_cooking_time": cook_time,
        "workout_schedule": schedule,
        "pantry": pantry
    }

# ============================================================
# GENERATE BUTTON
# ============================================================
st.header("🚀 Generate Adaptive Plan")
if st.button("🚀 RUN MULTI-AGENT PLANNER", use_container_width=True):
    with st.status("Running agent pipeline...", expanded=True) as status:
        state = build_state()

        if pantry_image:
            st.write("📷 Pantry Vision Agent analyzing image...")
            vision = engine.pantry_agent(pantry_image.getvalue())
            st.session_state.vision = vision
            detected = vision.get("ingredients", [])
            state["vision_detected_ingredients"] = detected

        st.write("🏋️ Workout Agent planning workouts...")
        st.write("🥗 Meal Agent coordinating meals...")
        st.write("🔍 Constraint Agent validating the plan...")
        st.write("🧠 Supervisor Agent coordinating results...")

        result = engine.generate_plan(state)
        st.session_state.state = state
        st.session_state.result = result

        status.update(label="Multi-agent plan completed", state="complete")

# ============================================================
# PANTRY RESULT DISPLAY
# ============================================================
if st.session_state.vision:
    st.subheader("📷 Pantry Vision")
    vision = st.session_state.vision
    ingredients = vision.get("ingredients", [])
    if ingredients:
        st.success("Detected: " + ", ".join(str(x) for x in ingredients))
    uncertain = vision.get("uncertain_items", [])
    if uncertain:
        st.warning("Uncertain items: " + ", ".join(str(x) for x in uncertain))

# ============================================================
# MAIN RESULT DISPLAY
# ============================================================
if st.session_state.result:
    result = st.session_state.result
    plan = result.get("plan", {})
    audit = deterministic_audit(st.session_state.state, plan)

    st.header("🏆 Plan Quality")
    ai_score = plan.get("plan_score", 0)
    try:
        ai_score = float(ai_score)
    except Exception:
        ai_score = 0

    final_score = min(ai_score, audit["audit_score"]) if ai_score > 0 else audit["audit_score"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Plan Score", f"{final_score:.0f}/100")
    with c2:
        st.metric("Budget", f"₹{plan.get('estimated_weekly_budget', 0)}")
    with c3:
        st.metric("Validation", "PASS" if audit["passed"] else "REVIEW")
    with c4:
        st.metric("Agents", "7 Active")

    if audit["passed"]:
        st.success("Deterministic constraint audit passed.")
    else:
        st.warning("Constraint audit found potential issues:")
        for issue in audit["issues"]:
            st.write("⚠️ " + issue)

    st.header("📅 Coordinated Weekly Plan")
    weekly = plan.get("weekly_plan", {})

    for day in DAYS:
        data = weekly.get(day, {})
        with st.expander(f"📌 {day}", expanded=True):
            if isinstance(data, dict):
                a, b = st.columns(2)
                with a:
                    st.markdown(f"**🏋️ Workout:** {data.get('workout', 'Not specified')}")
                    st.markdown(f"**🍳 Breakfast:** {data.get('breakfast', 'Not specified')}")
                    st.markdown(f"**🥗 Lunch:** {data.get('lunch', 'Not specified')}")
                with b:
                    st.markdown(f"**🍎 Snack:** {data.get('snack', 'Not specified')}")
                    st.markdown(f"**🍲 Dinner:** {data.get('dinner', 'Not specified')}")
                    st.markdown(f"**💰 Cost:** ₹{data.get('estimated_cost', 'N/A')}")
                st.info("💡 " + str(data.get("reason", "Coordinated by the supervisor.")))

    st.header("🧠 Why This Plan?")
    st.info(plan.get("coordination_logic", "The supervisor coordinated meals, workouts and constraints."))

    st.header("🛒 Smart Grocery List")
    groceries = plan.get("grocery_list", [])
    for index, item in enumerate(groceries):
        st.checkbox(str(item), key=f"shop_{index}")

# ============================================================
# AGENT ACTIVITY CARDS
# ============================================================
st.header("🤖 Live Agent System")
agent_cards = [
    ("🧠", "Supervisor Agent", "Coordinates all specialist agents."),
    ("🏋️", "Workout Agent", "Builds the workout schedule."),
    ("🥗", "Meal Agent", "Creates meals around workouts and pantry."),
    ("📷", "Vision Agent", "Understands pantry images."),
    ("🔍", "Constraint Agent", "Audits budget, preferences and constraints."),
    ("👀", "Monitoring Agent", "Detects changes in the environment."),
    ("🔄", "Replanning Agent", "Adapts affected parts of the plan.")
]
columns = st.columns(4)
for i, (icon, title, description) in enumerate(agent_cards):
    with columns[i % 4]:
        st.markdown(
            f"""
            <div class="agent-card">
                <div class="agent-title">{icon} {title}</div>
                <div class="small">{description}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ============================================================
# CONTINUOUS MONITORING & REPLANNING
# ============================================================
st.header("👀 Environment Change → Automatic Replanning")
st.write(
    "This is the adaptive layer. Describe a real-world change to test "
    "if the monitoring agent triggers targeted replanning."
)
change = st.text_area(
    "Describe what changed",
    placeholder="Example: I ran out of bananas, my workout moved to 8 PM, and my budget dropped to ₹1500."
)

if st.button("🔄 MONITOR & ADAPT PLAN", use_container_width=True):
    if st.session_state.state is None:
        st.warning("Generate the initial plan first.")
    elif not change.strip():
        st.warning("Describe a change first.")
    else:
        with st.status("Monitoring environment...", expanded=True) as status:
            old_state = deepcopy(st.session_state.state)
            new_state = deepcopy(st.session_state.state)
            new_state["latest_change"] = change

            st.write("👀 Monitoring Agent detecting changes...")
            monitor = engine.monitoring_agent(old_state, new_state)
            st.session_state.monitor = monitor

            if monitor.get("replan_required", False):
                st.write("🔄 Replanning Agent adapting affected components...")
                old_plan = st.session_state.result.get("plan", {})
                replan = engine.replanning_agent(old_state, new_state, old_plan, monitor)
                st.session_state.replan = replan
                st.session_state.state = new_state

            status.update(label="Environment analysis completed", state="complete")

# ============================================================
# MONITORING & UPDATED PLAN DISPLAY
# ============================================================
if st.session_state.monitor:
    monitor = st.session_state.monitor
    st.subheader("👀 Monitoring Agent Audit")
    if monitor.get("change_detected", False):
        st.warning("Environmental change detected.")
    else:
        st.success("No significant change detected.")

    if monitor.get("changes"):
        st.write("**Detected changes:**")
        for item in monitor["changes"]:
            st.write("• " + str(item))

    if monitor.get("affected_days"):
        st.write("**Affected days:** " + ", ".join(str(x) for x in monitor["affected_days"]))

    if monitor.get("affected_components"):
        st.write("**Affected components:** " + ", ".join(str(x) for x in monitor["affected_components"]))

    if monitor.get("reason"):
        st.info(monitor["reason"])

if st.session_state.replan:
    replan = st.session_state.replan
    st.header("🔄 Adapted Plan")

    if replan.get("changes_made"):
        st.write("**What the Replanning Agent changed:**")
        for item in replan["changes_made"]:
            st.write("• " + str(item))

    if replan.get("reason"):
        st.info(replan["reason"])

    updated = replan.get("updated_plan", {})
    for day in DAYS:
        data = updated.get(day, {})
        with st.expander(f"🔄 Updated {day}"):
            if isinstance(data, dict):
                st.write("🏋️ Workout:", data.get("workout", "Unchanged"))
                st.write("🍳 Breakfast:", data.get("breakfast", "Unchanged"))
                st.write("🥗 Lunch:", data.get("lunch", "Unchanged"))
                st.write("🍎 Snack:", data.get("snack", "Unchanged"))
                st.write("🍲 Dinner:", data.get("dinner", "Unchanged"))

    if replan.get("new_grocery_list"):
        st.subheader("🛒 Updated Grocery List")
        for item in replan["new_grocery_list"]:
            st.write("• " + str(item))

st.header("🔁 Agentic Decision Loop")
st.markdown("`OBSERVE` → `ANALYZE` → `VALIDATE` → `DECIDE` → `ACT` → `MONITOR` → `REPLAN`")
st.caption("NourishSync AI is a planning assistant, not a medical diagnosis or treatment system.")
