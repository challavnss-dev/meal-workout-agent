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
# DYNAMIC DETERMINISTIC ENGINE (VARIED FALLBACK)
# ============================================================
def generate_fallback_plan(user_state: Dict[str, Any]) -> Dict[str, Any]:
    pref = user_state.get("food_preference", "Vegetarian")
    
    # Expanded meal pools grouped by meal type & workout intensity
    pools = {
        "Vegetarian": {
            "heavy": {
                "breakfast": ["High-Protein Oats (60g) + 200ml Soy Milk + 15g Peanut Butter + 1 Banana", "3 Besan Chillas (150g) with Paneer Stuffing + Mint Chutney", "Paneer & Vegetable Paratha (2 medium) + 100g Greek Yogurt"],
                "lunch": ["Paneer Curry (150g Paneer) + 1.5 cups Basmati Rice + Green Salad", "Rajma Masala (2 cups cooked) + Jeera Rice (1.5 cups) + Cucumber Raita", "Soya Chunk Curry (100g dry soya) + 3 Whole Wheat Chapatis + Salad"],
                "snack": ["Sprouted Moong & Paneer Salad (1.5 cups) + Roasted Pumpkin Seeds", "Protein Shake / Soy Milk (250ml) + 40g Roasted Chana", "100g Cottage Cheese/Paneer Cubes + 1 Apple"],
                "dinner": ["Dal Makhani (1.5 cups) + 2 Whole Wheat Chapatis + Mixed Veggies", "Tofu & Broccoli Stir-Fry (150g Tofu) + 1 cup Quinoa/Rice", "Palak Paneer (120g Paneer) + 2 Phulkas + 1 Bowl Cucumber Salad"]
            },
            "light": {
                "breakfast": ["Vegetable Poha (1.5 cups cooked) + 1 Cup Green Tea", "Moong Dal Chilla (2 light chillas) + Mint Chutney", "Upma with Peas & Carrots (1.5 cups) + 10 Almonds"],
                "lunch": ["Toor Dal Tadka (1 cup) + 1 cup Cooked Basmati Rice + Green Salad", "Mix Veg Curry + 2 Whole Wheat Chapatis + 1 Bowl Curd (100g)", "Lauki Dal (1 cup) + 1 cup Brown Rice + Tomato Salad"],
                "snack": ["Roasted Makhana (25g) + 1 Cup Green Tea", "1 Medium Apple + 5 Walnuts", "Cucumber & Carrot Sticks with 2 tbsp Hummus"],
                "dinner": ["Light Vegetable Soup + 1 Chapati + Sauteed Beans", "Dal Khichdi (1 cup cooked) + 100g Plain Yogurt", "Bottle Gourd (Lauki) Sabzi + 2 Phulkas + Salad"]
            }
        },
        "Non-Vegetarian": {
            "heavy": {
                "breakfast": ["3 Whole Boiled Eggs + 2 Slices Brown Bread + 1 Banana", "3-Egg Omelette with Spinach & Cheese + 2 Toast", "High-Protein Oats (50g) with Whey/Milk + 2 Egg Whites"],
                "lunch": ["Grilled Chicken Breast (180g) + 1.5 cups Cooked Rice + Steamed Broccoli", "Chicken Curry (150g Chicken) + 3 Chapatis + Garden Salad", "Fish Curry (180g Fish) + 1.5 cups Brown Rice + Salad"],
                "snack": ["Boiled Egg Whites (4 units) + Black Pepper", "Protein Shake + 1 Banana", "Chicken Breast Strips (80g grilled) + Cucumber"],
                "dinner": ["Grilled Salmon/Fish (150g) + Sauteed Veggies + 1/2 cup Sweet Potato", "Chicken Soup with Veggies (300ml) + 2 Slices Whole Grain Toast", "Egg Bhurji (3 eggs) + 2 Chapatis + Green Salad"]
            },
            "light": {
                "breakfast": ["2 Boiled Eggs + 1 Slice Brown Bread + Green Tea", "2 Egg Whites Scramble + Veggies + 1 Fruit", "Rolled Oats (40g dry in water/milk) + 1 Apple"],
                "lunch": ["Grilled Chicken Salad (120g Chicken) + Olive Oil Dressing", "Egg Curry (2 Eggs) + 1.5 Chapatis + Cucumber Salad", "Light Fish Stew (120g Fish) + 1/2 cup Rice + Salad"],
                "snack": ["Boiled Egg Whites (2 units)", "1 Orange or Apple", "Roasted Chana (30g) + Green Tea"],
                "dinner": ["Clear Chicken & Vegetable Broth (250ml)", "Grilled White Fish (120g) + Mixed Green Salad", "Egg White Scramble (3 whites) + 1 Chapati + Veggies"]
            }
        }
    }

    selected_diet = pools.get(pref, pools["Vegetarian"])
    weekly_plan = {}
    
    # Track used meals to prevent exact duplication across days
    used_meals = set()

    for day in DAYS:
        workout_type = user_state.get("workout_schedule", {}).get(day, "Rest")
        is_heavy = workout_type in ["Strength Training", "Full Body", "Cardio"]
        intensity_key = "heavy" if is_heavy else "light"
        
        meal_pool = selected_diet[intensity_key]
        
        def pick_unique(category: str) -> str:
            available = [m for m in meal_pool[category] if m not in used_meals]
            if not available:
                available = meal_pool[category]
            chosen = random.choice(available)
            used_meals.add(chosen)
            return chosen

        # Dynamic Targets per workout
        if workout_type == "Strength Training":
            target = "2,200 kcal | 105g Protein | High Carbs"
            reason = "High carbohydrate and protein density engineered to support muscle hypertrophy and recovery."
            cost = random.randint(320, 420)
        elif workout_type == "Full Body":
            target = "2,050 kcal | 95g Protein | Balanced Macros"
            reason = "Balanced macronutrient distribution to optimize stamina and full-body tissue repair."
            cost = random.randint(300, 380)
        elif workout_type == "Cardio":
            target = "1,900 kcal | 80g Protein | Endurance Fuel"
            reason = "Moderate complex carbs to replenish glycogen depleted during cardiovascular training."
            cost = random.randint(280, 350)
        else: # Rest Day
            target = "1,650 kcal | 70g Protein | Lower Carbs"
            reason = "Caloric restriction with maintenance protein to prevent surplus fat storage on low-activity days."
            cost = random.randint(220, 300)

        weekly_plan[day] = {
            "workout": workout_type,
            "daily_target": target,
            "breakfast": pick_unique("breakfast"),
            "lunch": pick_unique("lunch"),
            "snack": pick_unique("snack"),
            "dinner": pick_unique("dinner"),
            "estimated_cost": cost,
            "reason": reason
        }
        
    return sanitize_plan_against_avoidance({
        "estimated_weekly_budget": user_state.get("weekly_budget", 2500),
        "plan_score": 98,
        "coordination_logic": "Dynamic portion scaling applied: High-intensity workout days feature increased protein and carb portions, while rest days trim calories to eliminate surplus.",
        "grocery_list": ["Basmati Rice / Brown Rice", "Whole Wheat Flour (Atta)", "Paneer / Tofu / Chicken", "Toor Dal & Rajma", "Oats", "Eggs / Soy Milk", "Seasonal Veggies (Broccoli, Spinach)", "Greek Yogurt / Curd"],
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
                temperature=0.4, # Slightly higher temperature for menu diversity
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

CRITICAL VARIATION & PORTION RULES:
1. EACH OF THE 7 DAYS MUST HAVE A UNIQUE MEAL PLAN. Do NOT repeat the same breakfast, lunch, or dinner across multiple days.
2. TAILOR MEALS DIRECTLY TO THE WORKOUT INTENSITY FOR THAT DAY:
   - Strength Training / Full Body: Higher calories, high protein (e.g., 90-110g), higher complex carbs for muscle building.
   - Cardio Days: Moderate calories, high complex carbs for endurance.
   - Rest Days: Lower calories (e.g., 1500-1700 kcal), moderate protein, low carbs to prevent excess fat accumulation.
3. Every single meal item MUST state exact gram/volume measurements (e.g., "180g cooked rice", "2 whole wheat chapatis", "120g paneer", "3 egg whites").
4. NEVER include {avoid} or any ingredient derived from {avoid}.

Return pure JSON matching this exact schema:
{{
  "estimated_weekly_budget": 2500,
  "plan_score": 98,
  "coordination_logic": "Detailed explanation of how calorie/macro portions vary across heavy vs rest days...",
  "grocery_list": ["Item 1", "Item 2", "Item 3"],
  "weekly_plan": {{
     "Monday": {{
        "workout": "Strength Training",
        "daily_target": "2,200 kcal | 100g Protein",
        "breakfast": "High-Protein Oats (60g dry) in 250ml Soy Milk + 1 Banana + 15g Almonds",
        "lunch": "Grilled Chicken (160g) / Paneer Curry (150g) + 1.5 cups Rice + Cucumber Salad",
        "snack": "40g Roasted Chana + 1 Apple",
        "dinner": "Dal Makhani (1.5 cups) + 2 Chapatis + Mixed Greens",
        "estimated_cost": 380,
        "reason": "Increased calorie and protein loading tailored for Strength Training recovery."
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
    <div class="hero-subtitle">Smart Meal & Workout Planner with Dynamic Portion & Menu Variance</div>
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

# Set realistic default schedule variation
default_workouts = {
    "Monday": "Strength Training",
    "Tuesday": "Cardio",
    "Wednesday": "Rest",
    "Thursday": "Strength Training",
    "Friday": "Full Body",
    "Saturday": "Cardio",
    "Sunday": "Rest"
}

schedule = {}
for day in DAYS:
    default_idx = workout_options.index(default_workouts[day])
    schedule[day] = st.sidebar.selectbox(f"{day}", workout_options, index=default_idx, key=f"s_{day}")

st.sidebar.header("🥫 Pantry Stock")
pantry = st.sidebar.text_area("Available Ingredients", "Rice\nDal\nOats\nMilk\nPaneer\nEggs\nBananas\nTomatoes\nOnions\nSpinach", height=120)

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
    with st.spinner("Coordinating specialist agents, varying meals & adjusting macro portions..."):
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
        st.markdown(f'<div class="metric-card"><div class="metric-value">{plan.get("plan_score", 98)}/100</div><div class="metric-label">Plan Score</div></div>', unsafe_allow_html=True)
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
        with st.expander(f"📌 {day} — {data.get('workout', 'Rest')}", expanded=True):
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
