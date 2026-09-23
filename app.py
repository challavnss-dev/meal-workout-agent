import os
import json
import time
import base64
import io
import pandas as pd
from PIL import Image
import streamlit as st
from pydantic import BaseModel, Field

# Plotly Safe Import with Native Streamlit Fallback
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from groq import Groq

# ==========================================
# 1. PAGE CONFIG & API AGENT SETUP
# ==========================================
st.set_page_config(
    page_title="NutriFit AI - Multi-Agent Coordinated System",
    page_icon="🤖",
    layout="wide"
)

api_key = os.getenv("GROQ_API_KEY")
if not api_key and "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]

if not api_key:
    st.error("🔑 Groq API Key is Missing! Add `GROQ_API_KEY` to Streamlit Cloud Secrets.")
    st.stop()

client = Groq(api_key=api_key)


# ==========================================
# 2. MULTI-AGENT ARCHITECTURE DEFINITIONS
# ==========================================

class VisionAgent:
    """Agent 1: Scans fridge/pantry images and extracts available ingredients."""
    def __init__(self, groq_client):
        self.client = groq_client
        self.model = "llama-3.2-11b-vision-preview"

    def analyze(self, image: Image.Image) -> list[str]:
        buffered = io.BytesIO()
        image.convert("RGB").save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        prompt = """
        Identify all food items, ingredients, produce, and condiments visible in this image.
        Return ONLY a JSON object with the key "ingredients" containing an array of items.
        Example: {"ingredients": ["chicken breast", "spinach", "eggs", "greek yogurt"]}
        """
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            data = json.loads(res.choices[0].message.content)
            return data.get("ingredients", [])
        except Exception as e:
            st.sidebar.warning(f"Vision Agent Note: Could not parse image ({e})")
            return []


class PlannerAgent:
    """Agent 2: Generates synced workout and nutrition schedule based on inputs."""
    def __init__(self, groq_client):
        self.client = groq_client
        self.model = "llama-3.3-70b-versatile"

    def generate_plan(self, goal: str, workout: str, restrictions: str, prefs: str, pantry: list[str], constraints: str) -> dict:
        system_prompt = """
        You are an AI Sports Nutritionist and Strength Coach Agent.
        Synthesize workout and meal routines.
        
        RULES:
        1. Pre-workout: Fast carbs, moderate protein 1-2 hours before training.
        2. Post-workout: High protein and recovery carbs immediately post training.
        3. Rest days: Lower carbs, steady protein.
        
        Output MUST be strict JSON with this exact structure:
        {
          "summary": "High-level routine overview",
          "days": [
            {
              "day": "Monday",
              "workout_title": "Upper Body Strength",
              "workout_time": "7:00 AM",
              "pre_workout_meal": "Oatmeal with banana",
              "breakfast": "3 scrambled eggs & spinach",
              "lunch": "Grilled chicken breast with rice",
              "post_workout_meal": "Whey protein shake",
              "dinner": "Salmon with broccoli",
              "calories": 2200,
              "protein_g": 170,
              "carbs_g": 200,
              "fats_g": 60,
              "coordination_logic": "Carbs timed around 7 AM training window."
            }
          ]
        }
        """

        user_prompt = f"""
        Goal: {goal}
        Schedule: {workout}
        Dietary Restrictions: {restrictions}
        Preferences: {prefs}
        Available Pantry Items: {', '.join(pantry) if pantry else 'Standard store grocery list'}
        Time Limits: {constraints}
        """

        res = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        return json.loads(res.choices[0].message.content)


class SupervisorAgent:
    """Agent 3: Validates structural integrity and balances macronutrients."""
    def __init__(self, groq_client):
        self.client = groq_client
        self.model = "llama-3.3-70b-versatile"

    def audit_plan(self, raw_plan: dict) -> dict:
        system_prompt = """
        You are the Quality Control Supervisor Agent.
        Check the generated routine dictionary for missing values or unrealistic macros.
        Ensure it matches all formatting rules and return the final JSON object cleaned.
        """
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Audit and return this raw JSON plan: {json.dumps(raw_plan)}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            return json.loads(res.choices[0].message.content)
        except Exception:
            return raw_plan  # Fallback to raw plan if auditing encounters issues


# ==========================================
# 3. USER INTERFACE & AGENT RUNTIME
# ==========================================

st.title("🤖 Multi-Agent Coordinated Fitness System")
st.caption("Powered by Groq Autonomous Vision, Planner, and Supervisor Agents")

# Instantiate Multi-Agent Team
vision_agent = VisionAgent(client)
planner_agent = PlannerAgent(client)
supervisor_agent = SupervisorAgent(client)

# Sidebar UI
st.sidebar.header("⚙️ Agent Inputs")

goal = st.sidebar.selectbox("Goal", ["Muscle Gain", "Fat Loss", "Endurance", "Maintenance"])
restrictions = st.sidebar.text_input("Dietary Restrictions", value="Gluten-Free, Dairy-Free")
prefs = st.sidebar.text_area("Preferences", value="High protein, meals prepared under 20 mins", height=60)
constraints = st.sidebar.text_area("Constraints", value="Busy mornings, workout at 7:00 AM", height=60)

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("📷 Agent 1: Pantry Vision Scan", type=["jpg", "png", "jpeg"])

detected_pantry = []
if uploaded_file:
    img = Image.open(uploaded_file)
    st.sidebar.image(img, use_container_width=True)
    with st.sidebar.spinner("🤖 Vision Agent scanning..."):
        detected_pantry = vision_agent.analyze(img)
        st.sidebar.success(f"Detected: {', '.join(detected_pantry)}")

# Input Columns
c1, c2 = st.columns(2)
with c1:
    workout_schedule = st.text_area(
        "Workout Schedule",
        value="Monday: 7:00 AM Chest & Triceps\nTuesday: 7:00 AM Back & Biceps\nWednesday: Rest Day\nThursday: 7:00 AM Leg Day\nFriday: 6:00 PM Cardio\nSaturday: Full Body\nSunday: Rest",
        height=180
    )

with c2:
    pantry_text = st.text_area(
        "Pantry Items Inventory",
        value=", ".join(detected_pantry) if detected_pantry else "Chicken breast, Eggs, Rice, Oats, Protein powder, Spinach, Olive oil, Bananas, Almonds",
        height=180
    )
    pantry_list = [i.strip() for i in pantry_text.split(",") if i.strip()]

st.markdown("---")

# Execution Engine
if st.button("🚀 Run Multi-Agent System Workflow", type="primary", use_container_width=True):
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Phase 1: Planning
    status_text.text("🧠 Agent 2 (Planner): Formulating coordinated routines...")
    progress_bar.progress(30)
    start_time = time.time()
    
    raw_plan = planner_agent.generate_plan(
        goal=goal,
        workout=workout_schedule,
        restrictions=restrictions,
        prefs=prefs,
        pantry=pantry_list,
        constraints=constraints
    )

    # Phase 2: Supervision
    status_text.text("🛡️ Agent 3 (Supervisor): Auditing macros, schedules, and consistency...")
    progress_bar.progress(70)
    
    final_plan = supervisor_agent.audit_plan(raw_plan)
    
    progress_bar.progress(100)
    elapsed = time.time() - start_time
    status_text.success(f"✅ Multi-Agent Orchestration complete in {elapsed:.2f} seconds!")
    
    st.session_state["final_routine"] = final_plan

# ==========================================
# 4. DATA VISUALIZATION
# ==========================================

if "final_routine" in st.session_state:
    data = st.session_state["final_routine"]
    days = data.get("days", [])

    st.markdown("### 📋 Executive Summary")
    st.info(data.get("summary", "Schedule generated successfully."))

    t1, t2 = st.tabs(["📅 Daily Schedule", "📊 Macro Analytics"])

    with t1:
        for d in days:
            with st.expander(f"**{d.get('day')}** — 🏋️ {d.get('workout_title')} ({d.get('workout_time')})", expanded=True):
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.write(f"• **Pre-Workout:** {d.get('pre_workout_meal')}")
                    st.write(f"• **Breakfast:** {d.get('breakfast')}")
                    st.write(f"• **Lunch:** {d.get('lunch')}")
                    st.write(f"• **Post-Workout:** {d.get('post_workout_meal')}")
                    st.write(f"• **Dinner:** {d.get('dinner')}")
                    st.caption(f"💡 **Coordination Logic:** {d.get('coordination_logic')}")
                with col_b:
                    st.metric("Calories", f"{d.get('calories')} kcal")
                    st.write(f"🥩 **Protein:** {d.get('protein_g')}g")
                    st.write(f"🍞 **Carbs:** {d.get('carbs_g')}g")
                    st.write(f"🥑 **Fats:** {d.get('fats_g')}g")

    with t2:
        df = pd.DataFrame(days)
        if not df.empty and HAS_PLOTLY:
            fig = px.bar(df, x="day", y="calories", color="workout_title", title="Daily Calorie Intake by Workout Focus")
            st.plotly_chart(fig, use_container_width=True)
            
            fig_macro = px.line(df, x="day", y=["protein_g", "carbs_g", "fats_g"], title="Macronutrient Distribution (Grams)")
            st.plotly_chart(fig_macro, use_container_width=True)
        elif not df.empty:
            st.bar_chart(df.set_index("day")[["calories"]])
            st.line_chart(df.set_index("day")[["protein_g", "carbs_g", "fats_g"]])
