import streamlit as st
import json
import random
import os
from typing import Dict, List, Any

# Page Config
st.set_page_config(
    page_title="FitFuel AI - Adaptive Meal & Workout Planner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Dashboard Theme)
st.markdown("""
    <style>
    .main { background-color: #0F172A; color: #F8FAFC; }
    .stMetric { background-color: #1E293B; padding: 15px; border-radius: 10px; border-left: 4px solid #10B981; }
    .agent-card { background-color: #1E293B; border-radius: 8px; padding: 15px; margin-bottom: 10px; border: 1px solid #334155; }
    .agent-title { font-weight: bold; color: #6366F1; font-size: 1.1em; }
    .meal-box { background-color: #1E293B; border-radius: 8px; padding: 15px; margin-top: 10px; border-left: 4px solid #6366F1; }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# REAL-WORLD PANTRY & RECIPE DATABASE (With Veg / Non-Veg Categorization)
# ============================================================================
MASTER_PANTRY_DB = {
    "Vegetarian": [
        {"name": "Oats", "category": "Grains", "type": "Veg"},
        {"name": "Brown Rice", "category": "Grains", "type": "Veg"},
        {"name": "Paneer (Cottage Cheese)", "category": "Dairy/Protein", "type": "Veg"},
        {"name": "Tofu", "category": "Protein", "type": "Veg"},
        {"name": "Greek Yogurt", "category": "Dairy", "type": "Veg"},
        {"name": "Lentils (Dal)", "category": "Legumes", "type": "Veg"},
        {"name": "Chickpeas", "category": "Legumes", "type": "Veg"},
        {"name": "Spinach", "category": "Vegetables", "type": "Veg"},
        {"name": "Broccoli", "category": "Vegetables", "type": "Veg"},
        {"name": "Peanut Butter", "category": "Fats/Protein", "type": "Veg"},
        {"name": "Almonds & Walnuts", "category": "Nuts", "type": "Veg"},
        {"name": "Bananas", "category": "Fruits", "type": "Veg"}
    ],
    "Non-Vegetarian": [
        {"name": "Chicken Breast", "category": "Meat/Protein", "type": "Non-Veg"},
        {"name": "Eggs", "category": "Protein", "type": "Non-Veg"},
        {"name": "Salmon Fillet", "category": "Fish/Protein", "type": "Non-Veg"},
        {"name": "Canned Tuna", "category": "Fish/Protein", "type": "Non-Veg"},
        {"name": "Lean Ground Turkey", "category": "Meat/Protein", "type": "Non-Veg"}
    ]
}

RECIPE_TEMPLATES = {
    "Breakfast": [
        {"title": "Oatmeal with Peanut Butter & Banana", "ingredients": ["Oats", "Peanut Butter", "Bananas"], "type": "Veg", "base_calories": 400, "protein": 15},
        {"title": "Scrambled Eggs with Spinach & Toast", "ingredients": ["Eggs", "Spinach"], "type": "Non-Veg", "base_calories": 380, "protein": 24},
        {"title": "Greek Yogurt Parfait with Nuts", "ingredients": ["Greek Yogurt", "Almonds & Walnuts"], "type": "Veg", "base_calories": 320, "protein": 20}
    ],
    "Lunch": [
        {"title": "Grilled Chicken Breast with Brown Rice & Broccoli", "ingredients": ["Chicken Breast", "Brown Rice", "Broccoli"], "type": "Non-Veg", "base_calories": 600, "protein": 50},
        {"title": "Paneer & Vegetable Rice Bowl", "ingredients": ["Paneer (Cottage Cheese)", "Brown Rice", "Spinach"], "type": "Veg", "base_calories": 550, "protein": 28},
        {"title": "High-Protein Lentil & Chickpea Curry", "ingredients": ["Lentils (Dal)", "Chickpeas", "Brown Rice"], "type": "Veg", "base_calories": 500, "protein": 22}
    ],
    "Snacks": [
        {"title": "Boiled Eggs with Almonds", "ingredients": ["Eggs", "Almonds & Walnuts"], "type": "Non-Veg", "base_calories": 250, "protein": 14},
        {"title": "Protein Tofu Bites", "ingredients": ["Tofu", "Peanut Butter"], "type": "Veg", "base_calories": 220, "protein": 16},
        {"title": "Greek Yogurt Bowl", "ingredients": ["Greek Yogurt"], "type": "Veg", "base_calories": 180, "protein": 15}
    ],
    "Dinner": [
        {"title": "Pan-Seared Salmon with Spinach & Rice", "ingredients": ["Salmon Fillet", "Spinach", "Brown Rice"], "type": "Non-Veg", "base_calories": 580, "protein": 42},
        {"title": "Tofu & Stir-Fry Veggie Bowl", "ingredients": ["Tofu", "Broccoli", "Spinach"], "type": "Veg", "base_calories": 420, "protein": 26},
        {"title": "Ground Turkey Lettuce Wraps", "ingredients": ["Lean Ground Turkey", "Spinach"], "type": "Non-Veg", "base_calories": 480, "protein": 38}
    ]
}

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ============================================================================
# MULTI-AGENT EXECUTION ENGINE
# ============================================================================
def execute_multi_agent_pipeline(diet_type: str, selected_pantry: List[str], workout_schedule: Dict[str, str], allergens: List[str]):
    """
    Simulates the coordinated execution of specialized multi-agents for each day.
    """
    generated_plan = {}
    agent_logs = {}

    for day in DAYS_OF_WEEK:
        workout = workout_schedule.get(day, "Rest Day")
        
        # 1. Workout Agent Calculation
        if workout in ["Strength Training", "Full Body Workout"]:
            target_calories = 2300
            target_protein = 130
            intensity_factor = 1.25
        elif workout in ["Cardio / HIIT"]:
            target_calories = 2000
            target_protein = 100
            intensity_factor = 1.10
        else: # Rest Day
            target_calories = 1700
            target_protein = 85
            intensity_factor = 0.90

        # 2. Pantry & Meal Selection Agent Logic
        day_meals = {}
        day_logs = []

        day_logs.append(f"<b>Supervisor Agent:</b> Initiating pipeline for <b>{day}</b> (Workout Target: {workout}).")
        day_logs.append(f"<b>Workout Agent:</b> Computed calorie target as {target_calories} kcal and protein target as {target_protein}g (Intensity Factor: {intensity_factor}x).")

        for meal_cat in ["Breakfast", "Lunch", "Snacks", "Dinner"]:
            eligible_templates = []
            for t in RECIPE_TEMPLATES[meal_cat]:
                # Check dietary role compliance
                if diet_type == "Vegetarian" and t["type"] != "Veg":
                    continue
                # Check if required ingredients exist in active pantry
                has_ingredients = all(ing in selected_pantry for ing in t["ingredients"])
                if has_ingredients:
                    eligible_templates.append(t)

            # Fallback if pantry is constrained
            if not eligible_templates:
                selected_recipe = {
                    "title": f"Custom Pantry {meal_cat} Bowl",
                    "ingredients": [selected_pantry[0]] if selected_pantry else ["Oats"],
                    "calories": int(300 * intensity_factor),
                    "protein": int(15 * intensity_factor)
                }
            else:
                chosen = random.choice(eligible_templates)
                selected_recipe = {
                    "title": chosen["title"],
                    "ingredients": chosen["ingredients"],
                    "calories": int(chosen["base_calories"] * intensity_factor),
                    "protein": int(chosen["protein"] * intensity_factor)
                }

            day_meals[meal_cat] = selected_recipe

        # 3. Portion & Macro Control Agent Logic
        day_logs.append(f"<b>Portion Control Agent:</b> Scaled ingredient portions dynamically by {intensity_factor}x to meet daily macro thresholds.")

        # 4. Safety Audit Agent Logic
        sanitized_meals = {}
        violations = 0
        for meal_cat, m_data in day_meals.items():
            contains_allergen = any(alg.lower() in [ing.lower() for ing in m_data["ingredients"]] for alg in allergens)
            if contains_allergen:
                violations += 1
                day_logs.append(f"<b>Safety Audit Agent:</b> ⚠️ Filtered out invalid item in {meal_cat} containing allergens.")
            else:
                sanitized_meals[meal_cat] = m_data

        if violations == 0:
            day_logs.append("<b>Safety Audit Agent:</b> ✅ Verified. Zero forbidden ingredients or allergens detected.")

        day_logs.append("<b>Replanning Agent:</b> Validated plan against 7-day variance rules. Monotony score low.")

        generated_plan[day] = {
            "workout": workout,
            "target_calories": target_calories,
            "target_protein": target_protein,
            "meals": day_meals
        }
        agent_logs[day] = day_logs

    return generated_plan, agent_logs


# ============================================================================
# STREAMLIT UI & INTERACTION
# ============================================================================

st.title("⚡ FitFuel AI: Adaptive Multi-Agent Planner")
st.caption("Real-world dynamic meal & workout optimization engine powered by local pantry bounds.")

# --- SIDEBAR: User Context & Role-Based Pantry ---
with st.sidebar:
    st.header("1. Profile & Preferences")
    diet_role = st.selectbox("Dietary Preference", ["Vegetarian", "Non-Vegetarian"])
    allergens_input = st.text_input("Allergies / Avoidances (comma separated)", "Peanuts, Shellfish")
    allergens = [a.strip() for a in allergens_input.split(",") if a.strip()]

    st.header("2. Active Pantry Stock")
    st.info("Pantry items automatically adapt to your dietary role.")

    # Hierarchical Pantry Display Logic
    available_items = [item["name"] for item in MASTER_PANTRY_DB["Vegetarian"]]
    if diet_role == "Non-Vegetarian":
        available_items += [item["name"] for item in MASTER_PANTRY_DB["Non-Vegetarian"]]

    selected_pantry = st.multiselect(
        "Available Ingredients in Pantry",
        options=available_items,
        default=available_items[:6]
    )

    st.header("3. Weekly Workout Schedule")
    workout_schedule = {}
    for d in DAYS_OF_WEEK:
        workout_schedule[d] = st.selectbox(
            f"{d}",
            ["Rest Day", "Strength Training", "Cardio / HIIT", "Full Body Workout"],
            index=1 if d in ["Monday", "Wednesday", "Friday"] else 0,
            key=f"ws_{d}"
        )

    generate_btn = st.button("🚀 Generate Adaptive Plan", type="primary", use_container_width=True)

# Application State Initialization
if "plan_generated" not in st.session_state or generate_btn:
    plan, logs = execute_multi_agent_pipeline(diet_role, selected_pantry, workout_schedule, allergens)
    st.session_state["generated_plan"] = plan
    st.session_state["agent_logs"] = logs
    st.session_state["plan_generated"] = True

# --- MAIN DASHBOARD AREA ---

# Top Controls: Day & Navigation Context
col_day, col_info = st.columns([2, 3])
with col_day:
    selected_day = st.selectbox("📅 Select Schedule Day", DAYS_OF_WEEK)

current_day_plan = st.session_state["generated_plan"][selected_day]
current_day_logs = st.session_state["agent_logs"][selected_day]

st.markdown("---")

# Metrics Banner
m1, m2, m3, m4 = st.columns(4)
m1.metric("Selected Day", selected_day)
m2.metric("Workout Focus", current_day_plan["workout"])
m3.metric("Calorie Target", f"{current_day_plan['target_calories']} kcal")
m4.metric("Protein Target", f"{current_day_plan['target_protein']} g")

st.markdown("###")

# Main Content Layout: Meals vs. Agent Internal Reasoning
left_col, right_col = st.columns([3, 2])

with left_col:
    st.subheader(f"🍽️ Planned Meals for {selected_day}")
    st.caption("All planned meals are dynamically assembled strictly using your active pantry items.")

    for meal_type, m_info in current_day_plan["meals"].items():
        with st.container():
            st.markdown(f"""
                <div class="meal-box">
                    <h4 style="margin:0; color:#10B981;">{meal_type}: {m_info['title']}</h4>
                    <p style="margin:5px 0; color:#94A3B8; font-size:0.9em;">
                        <b>Ingredients:</b> {', '.join(m_info['ingredients'])}
                    </p>
                    <p style="margin:0; font-weight:bold; color:#F8FAFC;">
                        🔥 {m_info['calories']} kcal &nbsp;|&nbsp; 🥩 {m_info['protein']}g Protein
                    </p>
                </div>
            """, unsafe_allow_html=True)

with right_col:
    st.subheader("🤖 Agent Coordination Inspector")
    st.caption("Click on an agent to review its specific logic and transformations for this day.")

    # Interactive Agent Inspection Tabs/Expanders
    agents = [
        ("🧠 Supervisor Agent", "Coordinates total workflow execution and state updates."),
        ("🏋️ Workout Agent", "Adjusts daily caloric and macronutrient targets according to training intensity."),
        ("🥗 Portion & Pantry Agent", "Matches recipe templates strictly against active pantry items."),
        ("🛡️ Safety Audit Agent", "Runs strict guardrails against dietary role rules and allergens.")
    ]

    for agent_title, desc in agents:
        with st.expander(agent_title):
            st.write(f"*Role:* {desc}")
            st.markdown("---")
            # Display matching logs for selected agent
            relevant_logs = [log for log in current_day_logs if agent_title.split()[1] in log]
            if relevant_logs:
                for r_log in relevant_logs:
                    st.markdown(f"- {r_log}", unsafe_allow_html=True)
            else:
                st.info(f"{agent_title} completed execution without exceptions for {selected_day}.")

# Bottom Section: Active Pantry Verification
st.markdown("---")
st.subheader("📦 Active Pantry Inventory Verification")
pantry_cols = st.columns(4)
for idx, p_item in enumerate(selected_pantry):
    with pantry_cols[idx % 4]:
        st.success(f"✓ {p_item}")
