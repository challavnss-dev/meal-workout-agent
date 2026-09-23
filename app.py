import os
import json
import time
import base64
import io
import pandas as pd
from PIL import Image
import streamlit as st

# Safe Plotly Import with Streamlit Native Fallback
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from groq import Groq

# ==========================================
# 1. PAGE CONFIG & GLASSMORPHISM STYLING
# ==========================================
st.set_page_config(
    page_title="NutriFit AI - Multi-Agent System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Dark Gradient Background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        color: #f8fafc;
    }
    
    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.15) 100%);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    
    .metric-value {
        font-size: 26px;
        font-weight: 800;
        background: linear-gradient(90deg, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-label {
        font-size: 12px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Agent Badges */
    .agent-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 8px;
    }
    .agent-vision { background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid #38bdf8; }
    .agent-planner { background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid #c084fc; }
    .agent-supervisor { background: rgba(52, 211, 153, 0.2); color: #34d399; border: 1px solid #34d399; }

    .block-container { padding-top: 2rem; }
    </style>
""", unsafe_allow_html=True)

# API Key Validation
api_key = os.getenv("GROQ_API_KEY")
if not api_key and "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]

if not api_key:
    st.error("🔑 Groq API Key Missing! Add `GROQ_API_KEY` to Streamlit Cloud Secrets.")
    st.stop()

client = Groq(api_key=api_key)

# ==========================================
# 2. MULTI-AGENT ARCHITECTURE (ACTIVE MODELS)
# ==========================================

class VisionAgent:
    """Agent 1: Processes pantry photos into ingredient list."""
    def __init__(self, groq_client):
        self.client = groq_client
        self.model = "llama-3.2-11b-vision-instruct"

    def analyze(self, image: Image.Image) -> list[str]:
        buffered = io.BytesIO()
        image.convert("RGB").save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        prompt = "Identify all edible food items in this photo. Return ONLY JSON: {\"ingredients\": [\"item1\", \"item2\"]}"
        
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
    """Agent 2: Synthesizes meal schedule aligned with training timing."""
    def __init__(self, groq_client):
        self.client = groq_client
        # Active production model endpoints with instant fallback
        self.models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]

    def generate_plan(self, goal: str, workout: str, restrictions: str, prefs: str, pantry: list[str], constraints: str) -> dict:
        system_prompt = """
        You are an AI Sports Nutritionist and Strength Coach.
        Synthesize a 7-day coordinated workout and meal schedule.
        
        Rules:
        1. Pre-workout meal: Fast carbs 1-2 hours before training.
        2. Post-workout meal: Protein & restoration carbs post-training.
        
        Output MUST be strict JSON matching this exact structure:
        {
          "summary": "High-level overview of the coordinated approach",
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
              "coordination_logic": "Carbs centered around 7 AM training window."
            }
          ]
        }
        """

        user_prompt = f"Goal: {goal}\nSchedule: {workout}\nRestrictions: {restrictions}\nPreferences: {prefs}\nPantry: {', '.join(pantry)}\nConstraints: {constraints}"

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
                st.warning(f"Model {model_id} failed ({e}). Attempting fallback...")
                continue
        
        st.error("All planning models failed to respond.")
        return {}


class SupervisorAgent:
    """Agent 3: Validates and audits JSON structure and macro balance."""
    def __init__(self, groq_client):
        self.client = groq_client
        self.model = "llama-3.3-70b-versatile"

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

# Instantiate Agents
vision_agent = VisionAgent(client)
planner_agent = PlannerAgent(client)
supervisor_agent = SupervisorAgent(client)

# ==========================================
# 3. USER INTERFACE
# ==========================================

st.markdown("""
    <div style="text-align: center; padding: 10px 0 25px 0;">
        <h1 style="font-size: 2.8rem; font-weight: 900; background: linear-gradient(90deg, #818cf8, #c084fc, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            NutriFit AI System
        </h1>
        <p style="color: #94a3b8; font-size: 1.05rem;">Autonomous Multi-Agent Orchestration for Fitness & Nutrition</p>
        <div style="margin-top: 10px;">
            <span class="agent-badge agent-vision">👁️ Vision Agent</span>
            <span class="agent-badge agent-planner">🧠 Planner Agent</span>
            <span class="agent-badge agent-supervisor">🛡️ Supervisor Agent</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Sidebar Inputs
st.sidebar.markdown("### ⚙️ User Parameters")
goal = st.sidebar.selectbox("Primary Goal", ["Muscle Gain / Hypertrophy", "Fat Loss & Conditioning", "Endurance Training", "General Maintenance"])
restrictions = st.sidebar.text_input("Dietary Restrictions", value="Gluten-Free, Dairy-Free")
prefs = st.sidebar.text_area("Preferences", value="High protein, quick 15-minute prep meals", height=70)
constraints = st.sidebar.text_area("Constraints", value="Busy office hours 9 AM - 1 PM", height=70)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📷 Vision Agent (Optional)")
uploaded_file = st.sidebar.file_uploader("Upload Fridge/Pantry Photo", type=["jpg", "png", "jpeg"])

detected_pantry = []
if uploaded_file:
    img = Image.open(uploaded_file)
    st.sidebar.image(img, use_container_width=True)
    with st.sidebar.spinner("Vision Agent scanning image..."):
        detected_pantry = vision_agent.analyze(img)
        if detected_pantry:
            st.sidebar.success(f"Detected {len(detected_pantry)} items!")

# Main Panel Forms
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("##### 🗓️ Training Schedule Input")
    workout_schedule = st.text_area(
        "Workout Timings",
        value="Monday: 7:00 AM Upper Body Strength\nTuesday: 7:00 AM Lower Body Strength\nWednesday: Rest & Mobility\nThursday: 7:00 AM Push Focus\nFriday: 6:00 PM Zone 2 Cardio\nSaturday: 9:00 AM Full Body Conditioning\nSunday: Rest Day",
        height=190,
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("##### 🥑 Pantry & Inventory Input")
    pantry_text = st.text_area(
        "Ingredient Inventory",
        value=", ".join(detected_pantry) if detected_pantry else "Chicken breast, Eggs, Rice, Oats, Protein powder, Spinach, Olive oil, Bananas, Sweet potatoes, Almonds",
        height=190,
        label_visibility="collapsed"
    )
    pantry_list = [i.strip() for i in pantry_text.split(",") if i.strip()]
    st.markdown('</div>', unsafe_allow_html=True)

# Run Workflow Button
if st.button("🚀 Run Multi-Agent System Workflow", type="primary", use_container_width=True):
    progress_bar = st.progress(0)
    status_msg = st.empty()

    status_msg.markdown("<span class='agent-badge agent-planner'>Planner Agent</span> Synthesizing schedule...", unsafe_allow_html=True)
    progress_bar.progress(35)
    start_time = time.time()

    raw_plan = planner_agent.generate_plan(
        goal=goal,
        workout=workout_schedule,
        restrictions=restrictions,
        prefs=prefs,
        pantry=pantry_list,
        constraints=constraints
    )

    status_msg.markdown("<span class='agent-badge agent-supervisor'>Supervisor Agent</span> Auditing macros...", unsafe_allow_html=True)
    progress_bar.progress(75)

    final_plan = supervisor_agent.audit_plan(raw_plan)
    
    progress_bar.progress(100)
    elapsed = time.time() - start_time
    status_msg.markdown(f"✅ **Orchestration complete in {elapsed:.2f} seconds!**")
    
    st.session_state["final_routine"] = final_plan

# ==========================================
# 4. RESULTS VISUALIZATION
# ==========================================

if "final_routine" in st.session_state and st.session_state["final_routine"]:
    data = st.session_state["final_routine"]
    days = data.get("days", [])

    st.markdown("###")
    st.markdown(f"""
        <div class="glass-card">
            <h4 style="margin:0; color: #818cf8;">📋 Orchestration Summary</h4>
            <p style="color: #cbd5e1; margin-top: 8px;">{data.get("summary", "Plan generated successfully.")}</p>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📅 Daily Schedule", "📊 Macro Analytics"])

    with tab1:
        for d in days:
            st.markdown(f"""
                <div class="glass-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; margin-bottom: 14px;">
                        <h3 style="margin: 0; color: #f8fafc;">{d.get('day')}</h3>
                        <span style="background: rgba(99, 102, 241, 0.2); color: #818cf8; padding: 4px 14px; border-radius: 20px; font-weight: 700; border: 1px solid rgba(99, 102, 241, 0.4);">
                            🏋️ {d.get('workout_title')} ({d.get('workout_time')})
                        </span>
                    </div>
                    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">
                        <div>
                            <p><strong>🥣 Pre-Workout:</strong> {d.get('pre_workout_meal')}</p>
                            <p><strong>🍳 Breakfast:</strong> {d.get('breakfast')}</p>
                            <p><strong>🥗 Lunch:</strong> {d.get('lunch')}</p>
                            <p><strong>🥤 Post-Workout:</strong> {d.get('post_workout_meal')}</p>
                            <p><strong> Dinner:</strong> {d.get('dinner')}</p>
                            <p style="color: #c084fc; font-style: italic; font-size: 13px; margin-top: 10px;">
                                💡 {d.get('coordination_logic')}
                            </p>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 8px;">
                            <div class="metric-card">
                                <div class="metric-value">{d.get('calories')}</div>
                                <div class="metric-label">Total Calories</div>
                            </div>
                            <div style="font-size: 13px; color: #94a3b8; text-align: center;">
                                🥩 <b>{d.get('protein_g')}g</b> P | 🍞 <b>{d.get('carbs_g')}g</b> C | 🥑 <b>{d.get('fats_g')}g</b> F
                            </div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    with tab2:
        df = pd.DataFrame(days)
        if not df.empty and HAS_PLOTLY:
            fig = px.bar(
                df, x="day", y="calories", color="workout_title",
                title="Daily Caloric Intake vs. Workout Focus",
                template="plotly_dark"
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

            fig_macro = px.line(
                df, x="day", y=["protein_g", "carbs_g", "fats_g"],
                title="Macronutrient Distribution Trends (Grams)",
                template="plotly_dark",
                markers=True
            )
            fig_macro.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_macro, use_container_width=True)
        elif not df.empty:
            st.bar_chart(df.set_index("day")[["calories"]])
            st.line_chart(df.set_index("day")[["protein_g", "carbs_g", "fats_g"]])
