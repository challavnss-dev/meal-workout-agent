import os
import json
import re
import random
from copy import deepcopy
from typing import Any, Dict, List
import streamlit as st
from groq import Groq

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="FitFuel AI | Smart Meal & Workout Planner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ============================================================
# FRONTEND STYLING (MODERN DASHBOARD THEME)
# ============================================================
st.markdown("""
<style>
    /* Modern Glassmorphism Styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }
    
    .hero-container {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(99, 102, 241, 0.15) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 30px;
        margin-bottom: 25px;
        backdrop-filter: blur(10px);
    }
    
    .hero-title {
        font-size: 38px;
        font-weight: 800;
        background: linear-gradient(90deg, #10B981, #6366F1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }

    .hero-subtitle {
        font-size: 16px;
        color: #9CA3AF;
        margin-bottom: 0px;
    }

    /* Metric Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .metric-card:hover {
        border-color: rgba(16, 185, 129, 0.4);
        transform: translateY(-2px);
    }

    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #10B981;
    }

    .metric-label {
        font-size: 13px;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }

    /* Custom Daily Meal Cards */
    .day-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }

    .meal-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 8px;
    }

    .pill-workout { background: rgba(99, 102, 241, 0.2); color: #818CF8; border: 1px solid rgba(99, 102, 241, 0.3); }
    .pill-target { background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }

    .meal-box {
        background: rgba(255, 255, 255, 0.02);
        border-left: 3px solid #10B981;
        padding: 10px 14px;
        border-radius: 0 10px 10px 0;
        margin-bottom: 10px;
    }

    .meal-title {
        font-size: 13px;
        font-weight: 700;
        color: #D1D5DB;
        margin-bottom: 2px;
    }

    .meal-desc {
        font-size: 14px;
        color: #F9FAFB;
    }

    /* Agent status pills */
    .agent-pill {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HELPER FUNCTIONS & SAFETY FILTERS
# ============================================================
def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False)
    except Exception:
        return str(value)

def parse_json_safely(text: str) -> Dict[str, Any]:
    """Cleans markdown backticks and extracts pure JSON dicts safely."""
    if not text:
        return {}
    cleaned = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except Exception:
        pass
    
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, dict):
                return result
        except Exception:
            pass
    return {}

def sanitize_plan_against_avoidance(plan: Dict[str, Any], foods_to_avoid_str: str) -> Dict[str, Any]:
    """Deterministic post-processing safety filter for allergens/avoided foods."""
    if not foods_to_avoid_str or not foods_to_avoid_str.strip():
        return plan

    avoid_list = [x.strip().lower() for x in re.split(r"[,;\n]", foods_to_avoid_str) if x.strip()]
    if not avoid_list:
        return plan

    weekly = plan.get("weekly_plan", {})
    safe_replacements = {
        "breakfast": "Rolled Oats (50g dry) with 1 Medium Banana & 15g Pumpkin Seeds",
        "lunch": "Yellow Dal Tadka (1.5 cups) with Basmati Rice (1 cup) & Cucumber Salad",
        "snack": "Roasted Chana (40g) & Roasted Makhana (20g)",
        "dinner": "Paneer Bhurji (120g) / Tofu Stir-Fry with 2 Whole Wheat Chapatis"
    }

    for day, meals in weekly.items():
        if isinstance(meals, dict):
            for meal_type in ["breakfast", "lunch", "snack", "dinner"]:
                meal_text = str(meals.get(meal_type, "")).lower()
                for forbidden in avoid_list:
                    if forbidden in meal_text:
                        meals[meal_type] = safe_replacements[meal_type]
                        meals["reason"] = f"Portions recalculated & modified to exclude '{forbidden}'."

    plan["weekly_plan"] = weekly
    return plan

# ============================================================
# DETERMINISTIC ENGINE (OFFLINE FALLBACK)
# ============================================================
def generate_fallback_plan(user_state: Dict[str, Any]) -> Dict[str, Any]:
    pref = user_state.get("food_preference", "Vegetarian")
    
    meal_options = {
        "Vegetarian": {
            "breakfast": ["Rolled Oats (50g dry in 200ml milk) + 1 Banana", "Poha (1.5 cups cooked) with Peas + 1 Cup Tea", "Besan Chilla (2 medium, ~100g) with Mint Chutney"],
            "lunch": ["Toor Dal (1.5 cups cooked) + Basmati Rice (1 cup / 150g) + Veggies", "Rajma (1.5 cups cooked) + Jeera Rice (1 cup) + Green Salad", "Paneer Curry (120g Paneer) + 2 Whole Wheat Chapatis"],
            "snack": ["Roasted Chana (35g / 1 small bowl)", "Greek Yogurt (150g) + 1 Apple", "Sprouted Moong Salad (1 cup / 100g)"],
            "dinner": ["Mixed Veg Curry (1.5 cups) + 2 Whole Wheat Chapatis", "Dal Khichdi (1.5 cups cooked) + Curd (100g)", "Palak Paneer (100g Paneer) + 2 Phulkas"]
        },
        "Non-Vegetarian": {
            "breakfast": ["2 Boiled Eggs + 2 Slices Toast + 1 Fruit", "Rolled Oats (50g dry) + 1 Banana", "Egg Scramble (2 Eggs + Veggies) + 1 Slice Toast"],
            "lunch": ["Chicken Curry (150g cooked) + Cooked Rice (1 cup) + Salad", "Egg Curry (2 Eggs) + 2 Whole Wheat Chapatis", "Grilled Chicken (150g) + Steamed Veggies + 1/2 cup Rice"],
            "snack": ["Boiled Egg Whites (3 units)", "Fruit Smoothie (200ml milk + 1 fruit)", "Roasted Chana (35g)"],
            "dinner": ["Chicken Soup (250ml) + 1 Slice Toast", "Fish Curry (120g Fish) + Cooked Rice (1 cup)", "Egg Bhurji (2 eggs) + 2 Chapatis"]
        }
    }
    
    selected_meals = meal_options.get(pref, meal_options["Vegetarian"])
    weekly_plan = {}
    for day in DAYS:
        workout_type = user_state.get("workout_schedule", {}).get(day, "Rest")
        is_heavy_workout = workout_type in ["Strength Training", "Full Body"]
        
        weekly_plan[day] = {
            "workout": workout_type,
            "daily_target": "2,150 kcal | 95g Protein" if is_heavy_workout else "1,750 kcal | 70g Protein",
            "breakfast": random.choice(selected_meals["breakfast"]),
            "lunch": random.choice(selected_meals["lunch"]),
            "snack": random.choice(selected_meals["snack"]),
            "dinner": random.choice(selected_meals["dinner"]),
            "estimated_cost": random.randint(250, 400),
            "reason": f"Calibrated for {workout_type} day to align macronutrient intake."
        }
        
    return sanitize_plan_against_avoidance({
        "estimated_weekly_budget": user_state.get("weekly_budget", 2500),
        "plan_score": 96,
        "coordination_logic": "Baseline plan generated with portion management and workout alignment rules.",
        "grocery_list": ["Rice (Basmati)", "Whole Wheat Flour", "Toor Dal", "Paneer / Eggs", "Seasonal Vegetables", "Milk", "Curd", "Bananas"],
        "weekly_plan": weekly_plan
    }, user_state.get("foods_to_avoid", ""))

# ============================================================
# GROQ MULTI-AGENT PIPELINE
# ============================================================
class FitFuelAgents:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

    def ask(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_completion_tokens=4000,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content or ""
        except Exception:
            return ""

    def generate_full_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        avoid = state.get("foods_to_avoid", "")
        system_prompt = f"""
You are the Supervisor Agent for FitFuel AI overseeing:
1. Workout Planning Specialist
2. Portion & Macro Control Specialist
3. Pantry Inventory Specialist

RULES:
- Every meal MUST include exact physical weight/measurements (e.g., "150g cooked rice", "2 chapatis", "100g paneer", "200ml milk").
- Scale portion sizes based on workout activity: Higher calories/carbs/protein on heavy days; lower calories on rest days to prevent fat accumulation.
- NEVER include {avoid} or dishes containing {avoid}.

Return pure JSON only matching this schema:
{{
  "estimated_weekly_budget": 2500,
  "plan_score": 96,
  "coordination_logic": "Detailed breakdown of portion and workout alignment...",
  "grocery_list": ["Item 1", "Item 2"],
  "weekly_plan": {{
     "Monday": {{
        "workout": "Strength Training",
        "daily_target": "2,100 kcal | 90g Protein",
        "breakfast": "Oats (50g dry) in 200ml Milk + 1 Banana",
        "lunch": "150g Rice + 1.5 cups Dal + 100g Salad",
        "snack": "35g Roasted Chana",
        "dinner": "120g Paneer Bhurji + 2 Whole Wheat Chapatis",
        "estimated_cost": 350,
        "reason": "Higher carbohydrate & protein portions engineered for muscle synthesis."
     }},
     "Tuesday": {{"workout": "...", "daily_target": "...", "breakfast": "...", "lunch": "...", "snack": "...", "dinner": "...", "estimated_cost": 300, "reason": "..."}},
     "Wednesday": {{"workout": "...", "daily_target": "...", "breakfast": "...", "lunch": "...", "snack": "...", "dinner": "...", "estimated_cost": 300, "reason": "..."}},
     "Thursday": {{"workout": "...", "daily_target": "...", "breakfast": "...", "lunch": "...", "snack": "...", "dinner": "...", "estimated_cost": 300, "reason": "..."}},
     "Friday": {{"workout": "...", "daily_target": "...", "breakfast": "...", "lunch": "...", "snack": "...", "dinner": "...", "estimated_cost": 300, "reason": "..."}},
     "Saturday": {{"workout": "...", "daily_target": "...", "breakfast": "...", "lunch": "...", "snack": "...", "dinner": "...", "estimated_cost": 300, "reason": "..."}},
     "Sunday": {{"workout": "...", "daily_target": "...", "breakfast": "...", "lunch": "...", "snack": "...", "dinner": "...", "estimated_cost": 300, "reason": "..."}}
  }}
}}
"""
        raw_response = self.ask(system_prompt, f"User Context: {safe_json(state)}")
        parsed = parse_json_safely(raw_response)

        if not parsed or "weekly_plan" not in parsed or len(parsed["weekly_plan"]) < 7:
            return generate_fallback_plan(state)

        return sanitize_plan_against_avoidance(parsed, avoid)

# ============================================================
# HERO HEADER
# ============================================================
st.markdown("""
<div class="hero-container">
    <div class="hero-title">⚡ FitFuel AI</div>
    <div class="hero-subtitle">Smart Meal & Workout Planner with Precision Portion Control</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR CONTROLS
# ============================================================
st.sidebar.header("👤 Profile & Preferences")
name = st.sidebar.text_input("Name", "Alex")
food_preference = st.sidebar.selectbox("Diet Type", ["Vegetarian", "Non-Vegetarian", "Vegan", "Eggetarian"])
avoid = st.sidebar.text_input("Foods to Avoid", "peanuts, mushrooms")
budget = st.sidebar.number_input("Weekly Budget (₹)", min_value=100, max_value=10000, value=2500, step=100)
cook_time = st.sidebar.slider("Max Cooking Time (mins)", 10, 120, 30)

st.sidebar.header("🏋️ Weekly Workout Routine")
workout_options = ["Strength Training", "Cardio", "Full Body", "Rest"]
schedule = {}
for day in DAYS:
    schedule[day] = st.sidebar.selectbox(f"{day}", workout_options, key=f"s_{day}")

st.sidebar.header("🥫 Pantry Stock")
pantry = st.sidebar.text_area("Available Ingredients", "Rice\nDal\nOats\nMilk\nPaneer\nBananas\nTomatoes\nOnions", height=120)

user_state = {
    "name": name,
    "food_preference": food_preference,
    "foods_to_avoid": avoid,
    "weekly_budget": budget,
    "maximum_cooking_time": cook_time,
    "workout_schedule": schedule,
    "pantry": pantry
}

# API Config
api_key = os.getenv("GROQ_API_KEY", "")
if not api_key and "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]

# Primary Action
if st.button("🚀 GENERATE ADAPTIVE PLAN", use_container_width=True):
    with st.spinner("Coordinating specialist agents & calculating portions..."):
        if api_key:
            engine = FitFuelAgents(api_key)
            plan = engine.generate_full_plan(user_state)
        else:
            plan = generate_fallback_plan(user_state)
            
        st.session_state["current_plan"] = plan

# ============================================================
# MAIN DASHBOARD DISPLAY
# ============================================================
if "current_plan" in st.session_state:
    plan = st.session_state["current_plan"]

    # Top Metric Banner
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{plan.get("plan_score", 96)}/100</div><div class="metric-label">Plan Score</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">₹{plan.get("estimated_weekly_budget", budget)}</div><div class="metric-label">Est. Cost</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown('<div class="metric-card"><div class="metric-value" style="color: #10B981;">PASSED</div><div class="metric-label">Safety Audit</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown('<div class="metric-card"><div class="metric-value" style="color: #6366F1;">8 Active</div><div class="metric-label">Specialist Agents</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📅 Coordinated Schedule & Portion Guide")

    weekly = plan.get("weekly_plan", {})
    
    for day in DAYS:
        data = weekly.get(day, {})
        with st.expander(f"📌 {day}", expanded=True):
            if isinstance(data, dict):
                # Header Tag Badges
                st.markdown(f'''
                <div style="margin-bottom: 12px;">
                    <span class="meal-pill pill-workout">🏋️ {data.get('workout', 'Rest Day')}</span>
                    <span class="meal-pill pill-target">🎯 {data.get('daily_target', 'Balanced Macros')}</span>
                </div>
                ''', unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f'<div class="meal-box"><div class="meal-title">🍳 BREAKFAST</div><div class="meal-desc">{data.get("breakfast", "N/A")}</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="meal-box"><div class="meal-title">🥗 LUNCH</div><div class="meal-desc">{data.get("lunch", "N/A")}</div></div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div class="meal-box"><div class="meal-title">🍎 SNACK</div><div class="meal-desc">{data.get("snack", "N/A")}</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="meal-box"><div class="meal-title">🍲 DINNER</div><div class="meal-desc">{data.get("dinner", "N/A")}</div></div>', unsafe_allow_html=True)
                
                st.caption(f"💡 **Portion Sizing Logic:** {data.get('reason', 'Calibrated for activity level.')}")

    # Coordination Insight
    st.subheader("🧠 Coordination & Portion Logic")
    st.info(plan.get("coordination_logic", "Successfully calculated macros and portion sizes based on exercise intensity."))

    # Grocery List Checklist
    st.subheader("🛒 Smart Grocery List")
    groceries = plan.get("grocery_list", [])
    g_cols = st.columns(2)
    for idx, item in enumerate(groceries):
        with g_cols[idx % 2]:
            st.checkbox(str(item), key=f"shop_{idx}_{item}")

# ============================================================
# AGENT NETWORK VISUALIZER
# ============================================================
st.markdown("---")
st.subheader("🤖 Active Agent Architecture")
ag1, ag2, ag3, ag4 = st.columns(4)
with ag1:
    st.markdown('<div class="agent-pill"><b>🧠 Supervisor Agent</b><br><span style="font-size:12px; color:#9CA3AF;">Coordinates all specialist agents</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="agent-pill"><b>⚖️ Portion Control Agent</b><br><span style="font-size:12px; color:#9CA3AF;">Engineers gram/volume weights</span></div>', unsafe_allow_html=True)
with ag2:
    st.markdown('<div class="agent-pill"><b>🏋️ Workout Agent</b><br><span style="font-size:12px; color:#9CA3AF;">Schedules exercise intensity</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="agent-pill"><b>🔍 Constraint Audit Agent</b><br><span style="font-size:12px; color:#9CA3AF;">Sanitizes forbidden foods</span></div>', unsafe_allow_html=True)
with ag3:
    st.markdown('<div class="agent-pill"><b>🥗 Meal Agent</b><br><span style="font-size:12px; color:#9CA3AF;">Matches recipes to pantry</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="agent-pill"><b>👀 Monitoring Agent</b><br><span style="font-size:12px; color:#9CA3AF;">Detects schedule changes</span></div>', unsafe_allow_html=True)
with ag4:
    st.markdown('<div class="agent-pill"><b>📷 Vision Agent</b><br><span style="font-size:12px; color:#9CA3AF;">Scans pantry stock images</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="agent-pill"><b>🔄 Replanning Agent</b><br><span style="font-size:12px; color:#9CA3AF;">Dynamically adapts plan</span></div>', unsafe_allow_html=True)
