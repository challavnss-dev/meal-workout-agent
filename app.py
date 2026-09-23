import os
import json
import time
import base64
import io
import pandas as pd
from PIL import Image
import streamlit as st

# Safe Plotly Import
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from groq import Groq

# ==========================================
# 1. STREAMLIT CONFIG & API SETUP
# ==========================================
st.set_page_config(
    page_title="NutriFit AI System",
    page_icon="⚡",
    layout="wide"
)

api_key = os.getenv("GROQ_API_KEY")
if not api_key and "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]

if not api_key:
    st.error("🔑 Groq API Key Missing! Please add `GROQ_API_KEY` to Streamlit Cloud Secrets.")
    st.stop()

client = Groq(api_key=api_key)

# ==========================================
# 2. UPDATED AGENTS WITH STABLE MODELS
# ==========================================

class VisionAgent:
    def __init__(self, groq_client):
        self.client = groq_client
        # UPDATED: Use active Vision model
        self.model = "llama-3.2-11b-vision-instruct"

    def analyze(self, image: Image.Image) -> list[str]:
        buffered = io.BytesIO()
        image.convert("RGB").save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        prompt = "Identify all edible items in this photo. Return ONLY JSON: {\"ingredients\": [\"item1\", \"item2\"]}"
        
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
            st.sidebar.warning(f"Vision Agent Notice: {e}")
            return []


class PlannerAgent:
    def __init__(self, groq_client):
        self.client = groq_client
        # UPDATED: Primary stable text model with fallbacks
        self.models = ["llama3-70b-8192", "llama-3.3-70b-specdec", "llama3-8b-8192"]

    def generate_plan(self, goal: str, workout: str, restrictions: str, prefs: str, pantry: list[str], constraints: str) -> dict:
        system_prompt = """
        You are an AI Sports Nutritionist and Fitness Coach.
        Generate a 7-day coordinated workout and timed meal schedule.
        Output MUST be strict JSON matching this format:
        {
          "summary": "Executive summary of the coordinated approach",
          "days": [
            {
              "day": "Monday",
              "workout_title": "Upper Body Strength",
              "workout_time": "7:00 AM",
              "pre_workout_meal": "Oatmeal with banana",
              "breakfast": "3 scrambled eggs & spinach",
              "lunch": "Grilled chicken with rice",
              "post_workout_meal": "Whey protein shake",
              "dinner": "Salmon with broccoli",
              "calories": 2200,
              "protein_g": 170,
              "carbs_g": 200,
              "fats_g": 60,
              "coordination_logic": "Carbs centered around 7 AM training window."
            }
          ]
        }
        """

        user_prompt = f"Goal: {goal}\nSchedule: {workout}\nRestrictions: {restrictions}\nPreferences: {prefs}\nPantry: {', '.join(pantry)}\nConstraints: {constraints}"

        # Model Fallback Loop
        for model_id in self.models:
            try:
                res = self.client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                return json.loads(res.choices[0].message.content)
            except Exception as e:
                st.warning(f"Model {model_id} failed ({e}). Trying backup model...")
                continue
        
        st.error("All planning models failed to respond.")
        return {}


class SupervisorAgent:
    def __init__(self, groq_client):
        self.client = groq_client
        self.model = "llama3-70b-8192"

    def audit_plan(self, raw_plan: dict) -> dict:
        if not raw_plan:
            return {}
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a Quality Control Agent. Audit, balance, and return clean JSON without changing schema."},
                    {"role": "user", "content": json.dumps(raw_plan)}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            return json.loads(res.choices[0].message.content)
        except Exception:
            return raw_plan

# Initialize Agents
vision_agent = VisionAgent(client)
planner_agent = PlannerAgent(client)
supervisor_agent = SupervisorAgent(client)

# ==========================================
# 3. USER INTERFACE
# ==========================================

st.title("⚡ NutriFit AI Multi-Agent System")

st.sidebar.header("⚙️ Settings")
goal = st.sidebar.selectbox("Goal", ["Muscle Gain", "Fat Loss", "Endurance", "Maintenance"])
restrictions = st.sidebar.text_input("Dietary Restrictions", value="Gluten-Free, Dairy-Free")
prefs = st.sidebar.text_area("Preferences", value="High protein, fast meals", height=60)
constraints = st.sidebar.text_area("Constraints", value="Busy mornings", height=60)

uploaded_file = st.sidebar.file_uploader("📷 Pantry Vision (Optional)", type=["jpg", "png", "jpeg"])

detected_pantry = []
if uploaded_file:
    img = Image.open(uploaded_file)
    st.sidebar.image(img, use_container_width=True)
    with st.sidebar.spinner("Scanning pantry..."):
        detected_pantry = vision_agent.analyze(img)
        if detected_pantry:
            st.sidebar.success(f"Detected: {', '.join(detected_pantry)}")

col1, col2 = st.columns(2)
with col1:
    workout_schedule = st.text_area(
        "Workout Timings",
        value="Monday: 7:00 AM Upper Body\nTuesday: 7:00 AM Lower Body\nWednesday: Rest Day\nThursday: 7:00 AM Push\nFriday: 6:00 PM Cardio\nSaturday: Conditioning\nSunday: Rest",
        height=180
    )

with col2:
    pantry_text = st.text_area(
        "Pantry Inventory",
        value=", ".join(detected_pantry) if detected_pantry else "Chicken breast, Eggs, Rice, Oats, Protein powder, Spinach, Olive oil, Bananas",
        height=180
    )
    pantry_list = [i.strip() for i in pantry_text.split(",") if i.strip()]

if st.button("🚀 Run Workflow", type="primary", use_container_width=True):
    with st.spinner("Generating plan via Groq..."):
        raw_plan = planner_agent.generate_plan(
            goal=goal,
            workout=workout_schedule,
            restrictions=restrictions,
            prefs=prefs,
            pantry=pantry_list,
            constraints=constraints
        )
        final_plan = supervisor_agent.audit_plan(raw_plan)
        st.session_state["final_routine"] = final_plan
        st.success("Routine successfully created!")

if "final_routine" in st.session_state and st.session_state["final_routine"]:
    data = st.session_state["final_routine"]
    days = data.get("days", [])

    st.markdown("### 📋 Executive Summary")
    st.info(data.get("summary", "Done."))

    for d in days:
        with st.expander(f"**{d.get('day')}** — 🏋️ {d.get('workout_title')} ({d.get('workout_time')})"):
            st.write(f"• **Pre-Workout:** {d.get('pre_workout_meal')}")
            st.write(f"• **Breakfast:** {d.get('breakfast')}")
            st.write(f"• **Lunch:** {d.get('lunch')}")
            st.write(f"• **Post-Workout:** {d.get('post_workout_meal')}")
            st.write(f"• **Dinner:** {d.get('dinner')}")
            st.caption(f"💡 {d.get('coordination_logic')}")
            st.metric("Calories", f"{d.get('calories')} kcal")
