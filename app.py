import os
import json
import time
import base64
import io
import pandas as pd
from PIL import Image
import streamlit as st

# Safe Plotly Import with Standard Streamlit Fallback
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from groq import Groq

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS INJECTION
# ==========================================
st.set_page_config(
    page_title="NutriFit AI - Multi-Agent System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Glassmorphism Dark Theme Styling
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
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(99, 102, 241, 0.4);
        transform: translateY(-2px);
    }

    /* Metric Badge Stat Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.15) 100%);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    
    .metric-value {
        font-size: 28px;
        font-weight: 800;
        background: linear-gradient(90deg, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-label {
        font-size: 13px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Styled Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 14px 28px !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton>button:hover {
        box-shadow: 0 6px 28px rgba(168, 85, 247, 0.6) !important;
        transform: scale(1.01);
    }

    /* Agent Badge Indicators */
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

    /* Hide default Streamlit overhead padding */
    .block-container { padding-top: 2rem; }
    </style>
""", unsafe_allow_html=True)

# API Key Validation
api_key = os.getenv("GROQ_API_KEY")
if not api_key and "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]

if not api_key:
    st.error("🔑 Groq API Key Missing! Please add `GROQ_API_KEY` to Streamlit Cloud Secrets.")
    st.stop()

client = Groq(api_key=api_key)

# ==========================================
# 2. AGENT CLASSES
# ==========================================

class VisionAgent:
    def __init__(self, groq_client):
        self.client = groq_client
        self.model = "llama-3.2-11b-vision-preview"

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
        self.model = "llama-3.3-70b-versatile"

    def generate_plan(self, goal: str, workout: str, restrictions: str, prefs: str, pantry: list[str], constraints: str) -> dict:
        system_prompt = """
        You are an elite AI Sports Nutritionist and Fitness Coach.
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
    def __init__(self, groq_client):
        self.client = groq_client
        self.model = "llama-3.3-70b-versatile"

    def audit_plan(self, raw_plan: dict) -> dict:
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
# 3. APP UI & NAVIGATION
# ==========================================

# Hero Banner Header
st.markdown("""
    <div style="text-align: center; padding: 20px 0 30px 0;">
        <h1 style="font-size: 2.8rem; font-weight: 900; background: linear-gradient(90deg, #818cf8, #c084fc, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            NutriFit AI System
        </h1>
        <p style="color: #94a3b8; font-size: 1.1rem; max-width: 600px; margin: 0 auto;">
            Autonomous multi-agent orchestration for workout synchronization and meal plan timing.
        </p>
        <div style="margin-top: 15px;">
            <span class="agent-badge agent-vision">👁️ Vision Agent</span>
            <span class="agent-badge agent-planner">🧠 Planner Agent</span>
            <span class="agent-badge agent-supervisor">🛡️ Supervisor Agent</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Sidebar Options
st.sidebar.markdown("### ⚙️ User Parameters")
goal = st.sidebar.selectbox("Primary Goal", ["Muscle Gain / Hypertrophy", "Fat Loss & Conditioning", "Endurance Training", "General Maintenance"])
restrictions = st.sidebar.text_input("Dietary Restrictions", value="Dairy-Free, Gluten-Free")
prefs = st.sidebar.text_area("Meal Preferences", value="High protein, quick prep meals under 20 mins", height=70)
constraints = st.sidebar.text_area("Time Constraints", value="Busy mornings, work meetings 9 AM - 1 PM", height=70)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📷 Vision Agent Scanner")
uploaded_file = st.sidebar.file_uploader("Upload Fridge/Pantry Photo", type=["jpg", "png", "jpeg"])

detected_pantry = []
if uploaded_file:
    img = Image.open(uploaded_file)
    st.sidebar.image(img, use_container_width=True)
    with st.sidebar.spinner("Vision Agent scanning image..."):
        detected_pantry = vision_agent.analyze(img)
        if detected_pantry:
            st.sidebar.success(f"Detected {len(detected_pantry)} items!")

# Main Inputs Form
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("##### 🗓️ Training Schedule Input")
    workout_schedule = st.text_area(
        "Workout Timings",
        value="Monday: 7:00 AM Chest & Triceps\nTuesday: 7:00 AM Back & Biceps\nWednesday: Rest & Stretch\nThursday: 7:00 AM Leg Day\nFriday: 6:00 PM Zone 2 Cardio\nSaturday: 9:00 AM Conditioning\nSunday: Rest Day",
        height=200,
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("##### 🥑 Pantry & Inventory Input")
    pantry_text = st.text_area(
        "Ingredient Inventory",
        value=", ".join(detected_pantry) if detected_pantry else "Chicken breast, Eggs, Rice, Oats, Protein powder, Spinach, Olive oil, Bananas, Sweet potatoes, Almonds",
        height=200,
        label_visibility="collapsed"
    )
    pantry_list = [i.strip() for i in pantry_text.split(",") if i.strip()]
    st.markdown('</div>', unsafe_allow_html=True)

# Run Agent Button
if st.button("🚀 Generate Coordinated Schedule", use_container_width=True):
    progress_bar = st.progress(0)
    status_msg = st.empty()

    # Step 1: Planning
    status_msg.markdown("<span class='agent-badge agent-planner'>Planner Agent</span> Synthesizing meals and workout times...", unsafe_allow_html=True)
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

    # Step 2: Quality Control
    status_msg.markdown("<span class='agent-badge agent-supervisor'>Supervisor Agent</span> Auditing macro distribution...", unsafe_allow_html=True)
    progress_bar.progress(75)

    final_plan = supervisor_agent.audit_plan(raw_plan)
    
    progress_bar.progress(100)
    elapsed = time.time() - start_time
    status_msg.markdown(f"✅ **Orchestration complete in {elapsed:.2f} seconds!**")
    
    st.session_state["final_routine"] = final_plan

# ==========================================
# 4. RESULTS DISPLAY & CHARTS
# ==========================================

if "final_routine" in st.session_state:
    data = st.session_state["final_routine"]
    days = data.get("days", [])

    st.markdown("###")
    st.markdown(f"""
        <div class="glass-card">
            <h4 style="margin-0; color: #818cf8;">📋 Orchestration Summary</h4>
            <p style="color: #cbd5e1; margin-top: 8px;">{data.get("summary", "Plan generated successfully.")}</p>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📅 Coordinated Timeline", "📊 Macro & Calorie Analytics"])

    with tab1:
        for d in days:
            st.markdown(f"""
                <div class="glass-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 12px; margin-bottom: 16px;">
                        <h3 style="margin: 0; color: #f8fafc;">{d.get('day')}</h3>
                        <span style="background: rgba(99, 102, 241, 0.2); color: #818cf8; padding: 6px 16px; border-radius: 20px; font-weight: 700; border: 1px solid rgba(99, 102, 241, 0.4);">
                            🏋️ {d.get('workout_title')} ({d.get('workout_time')})
                        </span>
                    </div>
                    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">
                        <div>
                            <p><strong>🥣 Pre-Workout:</strong> {d.get('pre_workout_meal')}</p>
                            <p><strong>🍳 Breakfast:</strong> {d.get('breakfast')}</p>
                            <p><strong>🥗 Lunch:</strong> {d.get('lunch')}</p>
                            <p><strong>🥤 Post-Workout:</strong> {d.get('post_workout_meal')}</p>
                            <p><strong>Dinner:</strong> {d.get('dinner')}</p>
                            <p style="color: #c084fc; font-style: italic; font-size: 14px; margin-top: 12px;">
                                💡 {d.get('coordination_logic')}
                            </p>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 8px;">
                            <div class="metric-card">
                                <div class="metric-value">{d.get('calories')}</div>
                                <div class="metric-label">Total Calories</div>
                            </div>
                            <div style="font-size: 14px; color: #94a3b8; text-align: center;">
                                🥩 <b>{d.get('protein_g')}g</b> Protein | 🍞 <b>{d.get('carbs_g')}g</b> Carbs | 🥑 <b>{d.get('fats_g')}g</b> Fats
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
                template="plotly_dark",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

            fig_macro = px.line(
                df, x="day", y=["protein_g", "carbs_g", "fats_g"],
                title="Macronutrient Distribution (Grams)",
                template="plotly_dark",
                markers=True
            )
            fig_macro.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_macro, use_container_width=True)
        elif not df.empty:
            st.bar_chart(df.set_index("day")[["calories"]])
            st.line_chart(df.set_index("day")[["protein_g", "carbs_g", "fats_g"]])
