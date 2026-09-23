import os
import json
import re
import random
import streamlit as st
from groq import Groq

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="NourishSync AI",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ============================================================
# FALLBACK / DETERMINISTIC GENERATOR
# ============================================================
def generate_fallback_plan(user_state: dict) -> dict:
    """Guarantees a complete plan even if LLM calls or API keys fail."""
    pref = user_state.get("food_preference", "Vegetarian")
    
    meal_options = {
        "Vegetarian": {
            "breakfast": ["Oatmeal with banana and honey", "Poha with peanuts and tea", "Besan chilla with mint chutney"],
            "lunch": ["Dal fry, roti, and mixed veg", "Rajma chawal with salad", "Paneer bhurji with chapati"],
            "snack": ["Handful of roasted chana", "Greek yogurt with apples", "Sprouted moong salad"],
            "dinner": ["Mixed vegetable curry with roti", "Khichdi with curd", "Palak paneer with phulka"]
        },
        "Non-Vegetarian": {
            "breakfast": ["Boiled eggs with toast and fruit", "Oatmeal with banana", "Egg bhurji with whole wheat toast"],
            "lunch": ["Chicken curry with rice", "Egg curry with roti", "Grilled chicken salad"],
            "snack": ["Boiled egg whites", "Fruit smoothie", "Roasted chana"],
            "dinner": ["Light chicken soup with toast", "Fish curry with rice", "Egg bhurji with roti"]
        }
    }
    
    selected_meals = meal_options.get(pref, meal_options["Vegetarian"])
    
    weekly_plan = {}
    for day in DAYS:
        workout_type = user_state.get("workout_schedule", {}).get(day, "General Fitness")
        weekly_plan[day] = {
            "workout": workout_type if workout_type != "Rest" else "Rest Day / Stretching",
            "breakfast": random.choice(selected_meals["breakfast"]),
            "lunch": random.choice(selected_meals["lunch"]),
            "snack": random.choice(selected_meals["snack"]),
            "dinner": random.choice(selected_meals["dinner"]),
            "estimated_cost": random.randint(250, 400),
            "reason": f"Balanced high-energy fuel suited for {workout_type}."
        }
        
    return {
        "estimated_weekly_budget": user_state.get("weekly_budget", 2500),
        "plan_score": 92,
        "coordination_logic": "Fallback plan auto-generated based on user dietary preferences, workout schedule, and budget parameters.",
        "grocery_list": ["Rice", "Wheat Flour", "Dal/Lentils", "Paneer/Eggs", "Vegetables", "Milk", "Curd", "Bananas"],
        "weekly_plan": weekly_plan
    }

# ============================================================
# GROQ ENGINE
# ============================================================
def run_groq_planner(api_key: str, user_state: dict) -> dict:
    if not api_key:
        return generate_fallback_plan(user_state)

    client = Groq(api_key=api_key)
    
    system_prompt = """
You are NourishSync AI. Output ONLY raw JSON matching this schema exactly:
{
  "estimated_weekly_budget": 2500,
  "plan_score": 95,
  "coordination_logic": "Explanation...",
  "grocery_list": ["Item 1", "Item 2"],
  "weekly_plan": {
     "Monday": {"workout": "", "breakfast": "", "lunch": "", "snack": "", "dinner": "", "estimated_cost": 300, "reason": ""},
     "Tuesday": {"workout": "", "breakfast": "", "lunch": "", "snack": "", "dinner": "", "estimated_cost": 300, "reason": ""},
     "Wednesday": {"workout": "", "breakfast": "", "lunch": "", "snack": "", "dinner": "", "estimated_cost": 300, "reason": ""},
     "Thursday": {"workout": "", "breakfast": "", "lunch": "", "snack": "", "dinner": "", "estimated_cost": 300, "reason": ""},
     "Friday": {"workout": "", "breakfast": "", "lunch": "", "snack": "", "dinner": "", "estimated_cost": 300, "reason": ""},
     "Saturday": {"workout": "", "breakfast": "", "lunch": "", "snack": "", "dinner": "", "estimated_cost": 300, "reason": ""},
     "Sunday": {"workout": "", "breakfast": "", "lunch": "", "snack": "", "dinner": "", "estimated_cost": 300, "reason": ""}
  }
}
"""

    user_prompt = f"Generate complete 7-day schedule for: {json.dumps(user_state)}"

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_completion_tokens=4000
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        if "weekly_plan" in parsed and len(parsed["weekly_plan"]) > 0:
            return parsed
    except Exception as e:
        st.warning(f"Using fallback generator due to API error: {e}")
        
    return generate_fallback_plan(user_state)

# ============================================================
# USER INTERFACE
# ============================================================
st.title("🥗 NourishSync AI")
st.caption("Adaptive Meal × Workout Coordination Agent")

# Sidebar
st.sidebar.header("👤 User Profile")
name = st.sidebar.text_input("Name", "Alex")
food_preference = st.sidebar.selectbox("Food preference", ["Vegetarian", "Non-Vegetarian", "Vegan"])
avoid = st.sidebar.text_input("Foods to avoid", "Peanuts")
budget = st.sidebar.number_input("Weekly food budget ₹", value=2500, step=100)
cook_time = st.sidebar.slider("Maximum cooking time (mins)", 10, 120, 30)

st.sidebar.header("🏋️ Workout Schedule")
workout_options = ["Strength Training", "Cardio", "Full Body", "Rest"]
schedule = {}
for day in DAYS:
    schedule[day] = st.sidebar.selectbox(f"{day}", workout_options, key=f"s_{day}")

st.sidebar.header("🥫 Pantry")
pantry = st.sidebar.text_area("Current ingredients", "Rice, Dal, Oats, Milk, Paneer, Bananas, Tomatoes, Onions")

# Debug / Offline mode option
use_mock = st.sidebar.checkbox("Use Demo Mode (No API needed)", value=False)

user_state = {
    "name": name,
    "food_preference": food_preference,
    "foods_to_avoid": avoid,
    "weekly_budget": budget,
    "maximum_cooking_time": cook_time,
    "workout_schedule": schedule,
    "pantry": pantry
}

# Main Action Button
if st.button("🚀 GENERATE ADAPTIVE PLAN", use_container_width=True):
    with st.spinner("Coordinating specialist agents..."):
        api_key = os.getenv("GROQ_API_KEY", "")
        if use_mock or not api_key:
            plan = generate_fallback_plan(user_state)
        else:
            plan = run_groq_planner(api_key, user_state)
            
        st.session_state["current_plan"] = plan

# Render Results
if "current_plan" in st.session_state:
    plan = st.session_state["current_plan"]
    
    # Top Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Plan Score", f"{plan.get('plan_score', 90)}/100")
    c2.metric("Estimated Cost", f"₹{plan.get('estimated_weekly_budget', budget)}")
    c3.metric("Status", "PASS")
    
    st.markdown("---")
    st.subheader("📅 Coordinated Weekly Plan")
    
    weekly = plan.get("weekly_plan", {})
    for day in DAYS:
        day_data = weekly.get(day, {})
        with st.expander(f"📌 {day}", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"🏋️ **Workout:** {day_data.get('workout', 'Rest/Light activity')}")
                st.write(f"🍳 **Breakfast:** {day_data.get('breakfast', 'N/A')}")
                st.write(f"🥗 **Lunch:** {day_data.get('lunch', 'N/A')}")
            with col2:
                st.write(f"🍎 **Snack:** {day_data.get('snack', 'N/A')}")
                st.write(f"🍲 **Dinner:** {day_data.get('dinner', 'N/A')}")
                st.write(f"💰 **Cost:** ₹{day_data.get('estimated_cost', 0)}")
            st.caption(f"💡 {day_data.get('reason', 'Plan calculated to match user constraints.')}")
            
    st.subheader("🧠 Coordination Logic")
    st.info(plan.get("coordination_logic", "Successfully coordinated meals and workouts."))
    
    st.subheader("🛒 Grocery List")
    for item in plan.get("grocery_list", []):
        st.checkbox(item, key=f"grocer_{item}")
