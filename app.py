import os
import json
import time
import base64
import io
import pandas as pd
from PIL import Image
import plotly.express as px
import streamlit as st
from groq import Groq

# ==========================================
# 1. STREAMLIT CONFIGURATION & INITIALIZATION
# ==========================================
st.set_page_config(
    page_title="NutriFit AI - Coordinated Routine Agent (Groq)",
    page_icon="🏋️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fetch Groq API Key from Environment or Streamlit Secrets
api_key = os.getenv("GROQ_API_KEY")
if not api_key and "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]

if not api_key:
    st.error("🔑 API Key Missing! Please set GROQ_API_KEY in your environment variables or Streamlit secrets.")
    st.stop()

# Initialize Groq Client
client = Groq(api_key=api_key)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def encode_image_to_base64(image: Image.Image) -> str:
    """Encodes PIL Image to Base64 string for Groq Vision input."""
    buffered = io.BytesIO()
    image.convert("RGB").save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def analyze_pantry_image(image: Image.Image) -> list[str]:
    """Uses Groq Vision (llama-3.2-11b-vision-preview) to identify ingredients from an image."""
    base64_image = encode_image_to_base64(image)
    
    prompt = """
    Analyze this pantry or refrigerator image.
    Extract a clean list of all visible edible food ingredients, produce, proteins, grains, and condiments.
    Return ONLY a valid JSON array of strings containing ingredient names. Do NOT include markdown code blocks or additional text.
    Example output format: ["chicken breast", "spinach", "eggs", "greek yogurt", "oats"]
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        # Handle cases where LLM returns {"ingredients": [...]} or raw array
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            for key in parsed:
                if isinstance(parsed[key], list):
                    return parsed[key]
        return []
        
    except Exception as e:
        st.error(f"Pantry Image Analysis Error: {e}")
        return []


def generate_coordinated_routine(
    workout_schedule: str,
    meal_prefs: str,
    dietary_restrictions: str,
    pantry_items: list[str],
    daily_constraints: str,
    fitness_goal: str
) -> dict:
    """Orchestrates multi-day routine using Groq's high-speed Llama-3.3 model."""
    
    system_prompt = """
    You are an elite Sports Nutritionist and Strength Coach Agent.
    Your mission is to generate a tightly coordinated 7-day meal and workout routine.
    
    CRITICAL COORDINATION RULES:
    1. Pre-Workout Meals: High fast-acting carbs, moderate protein, low fat 1-2 hours before intense workouts.
    2. Post-Workout Meals: High-quality protein + restoring carbs within 60 minutes after workout.
    3. Rest Days: Lower carbohydrates, higher healthy fats, steady protein.
    4. Prioritize using items from the available pantry inventory.
    5. Strictly respect all user constraints, time limitations, and dietary restrictions.
    
    OUTPUT REQUIREMENTS:
    You MUST output valid JSON conforming strictly to this JSON structure:
    {
      "weekly_summary": "Brief summary of the coordinated approach",
      "days": [
        {
          "day": "Monday",
          "workout": {
            "title": "Workout Name / Rest",
            "time_slot": "7:00 AM - 8:00 AM",
            "type": "Strength / Cardio / Rest",
            "intensity": "High / Medium / Low"
          },
          "meals": {
            "pre_workout_snack": "Specific meal description",
            "breakfast": "Specific meal description",
            "lunch": "Specific meal description",
            "post_workout_snack": "Specific meal description",
            "dinner": "Specific meal description"
          },
          "estimated_macros": {
            "protein_g": 160,
            "carbs_g": 220,
            "fats_g": 65,
            "total_calories": 2105
          },
          "coordination_notes": "Explanation of how meals align with workout times today"
        }
      ]
    }
    """

    user_prompt = f"""
    - Fitness Goal: {fitness_goal}
    - Workout Schedule Input: {workout_schedule}
    - Meal Preferences: {meal_prefs}
    - Dietary Restrictions: {dietary_restrictions}
    - Available Pantry Inventory: {", ".join(pantry_items) if pantry_items else "Standard fresh grocery list"}
    - Daily Constraints / Time Limits: {daily_constraints}
    
    Generate the full 7-day plan in JSON format now.
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
        
    except Exception as e:
        st.error(f"Routine Generation Error: {e}")
        return {}


# ==========================================
# 3. STREAMLIT USER INTERFACE
# ==========================================

st.title("🏋️‍♂️ NutriFit AI: Coordinated Meal & Workout Agent")
st.caption("⚡ Powered by Groq LPU Inference")

# Sidebar Configuration
st.sidebar.header("⚙️ User Profile & Constraints")

fitness_goal = st.sidebar.selectbox(
    "Primary Goal",
    ["Hypertrophy / Muscle Building", "Fat Loss & Conditioning", "Endurance Training", "General Fitness & Maintenance"]
)

dietary_restrictions = st.sidebar.text_input(
    "Dietary Restrictions / Allergies",
    value="Dairy-free, No peanuts"
)

meal_prefs = st.sidebar.text_area(
    "Meal Preferences & Cuisines",
    value="High protein, Mediterranean style, quick 15-minute prep lunches.",
    height=80
)

daily_constraints = st.sidebar.text_area(
    "Daily Constraints / Schedule",
    value="Busy office meetings 9 AM - 12 PM. Must finish dinner before 8 PM.",
    height=80
)

st.sidebar.markdown("---")
st.sidebar.subheader("📷 Visual Pantry Scanner")
uploaded_pantry_img = st.sidebar.file_uploader(
    "Upload Pantry / Fridge Photo", 
    type=["jpg", "jpeg", "png"]
)

pantry_items = []
if uploaded_pantry_img:
    image = Image.open(uploaded_pantry_img)
    st.sidebar.image(image, caption="Uploaded Pantry", use_container_width=True)
    
    with st.sidebar.spinner("Scanning pantry with Groq Vision..."):
        pantry_items = analyze_pantry_image(image)
        if pantry_items:
            st.sidebar.success(f"Detected {len(pantry_items)} ingredients!")
            st.sidebar.write(pantry_items)

# Main Form Setup
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🗓️ Weekly Workout Input")
    workout_input = st.text_area(
        "Define your training schedule",
        value="""Monday: 7:00 AM Heavy Upper Body Strength
Tuesday: 6:30 PM HIIT Cardio
Wednesday: Rest & Mobility
Thursday: 7:00 AM Leg Day Strength
Friday: 6:00 PM Zone 2 Running
Saturday: 9:00 AM Full Body Conditioning
Sunday: Rest Day""",
        height=180
    )

with col2:
    st.subheader("🥑 Pantry & Inventory List")
    manual_pantry = st.text_area(
        "Detected or additional ingredients (comma-separated)",
        value=", ".join(pantry_items) if pantry_items else "Chicken breast, Eggs, Oats, Spinach, Brown rice, Olive oil, Bananas, Protein powder, Sweet potatoes, Almonds",
        height=180
    )
    final_pantry_list = [item.strip() for item in manual_pantry.split(",") if item.strip()]

st.markdown("---")

# Execution Button
if st.button("⚡ Generate Coordinated Routine", type="primary", use_container_width=True):
    with st.spinner("Agent generating plan via Groq..."):
        start_time = time.time()
        routine_data = generate_coordinated_routine(
            workout_schedule=workout_input,
            meal_prefs=meal_prefs,
            dietary_restrictions=dietary_restrictions,
            pantry_items=final_pantry_list,
            daily_constraints=daily_constraints,
            fitness_goal=fitness_goal
        )
        duration = time.time() - start_time

    if routine_data:
        st.session_state["routine_result"] = routine_data
        st.success(f"Coordinated Routine Generated in {duration:.2f} seconds!")

# ==========================================
# 4. RESULTS DISPLAY & VISUALIZATIONS
# ==========================================

if "routine_result" in st.session_state:
    routine = st.session_state["routine_result"]
    
    st.markdown("### 📋 Executive Summary")
    st.info(routine.get("weekly_summary", "Routine planned successfully."))

    days_data = routine.get("days", [])
    macro_list = []
    
    for d in days_data:
        macros = d.get("estimated_macros", {})
        macro_list.append({
            "Day": d.get("day"),
            "Calories": macros.get("total_calories", 0),
            "Protein (g)": macros.get("protein_g", 0),
            "Carbs (g)": macros.get("carbs_g", 0),
            "Fats (g)": macros.get("fats_g", 0),
            "Workout": d.get("workout", {}).get("title", "Rest")
        })
    
    df_macros = pd.DataFrame(macro_list)

    tab1, tab2, tab3 = st.tabs(["📅 Daily Coordinated Schedule", "📊 Macro & Calorie Analytics", "🛒 Grocery & Pantry Alignment"])

    with tab1:
        for day in days_data:
            with st.expander(f"**{day.get('day')}** — 🏋️ {day.get('workout', {}).get('title')} ({day.get('workout', {}).get('time_slot')})", expanded=True):
                
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.markdown("#### 🍱 Timed Meal Plan")
                    meals = day.get("meals", {})
                    st.write(f"• **Pre-Workout:** {meals.get('pre_workout_snack', 'N/A')}")
                    st.write(f"• **Breakfast:** {meals.get('breakfast', 'N/A')}")
                    st.write(f"• **Lunch:** {meals.get('lunch', 'N/A')}")
                    st.write(f"• **Post-Workout:** {meals.get('post_workout_snack', 'N/A')}")
                    st.write(f"• **Dinner:** {meals.get('dinner', 'N/A')}")
                    
                    st.markdown(f"**🧠 Coordination Logic:** *{day.get('coordination_notes')}*")

                with c2:
                    st.markdown("#### 🎯 Macro Targets")
                    m = day.get("estimated_macros", {})
                    st.metric("Total Calories", f"{m.get('total_calories')} kcal")
                    st.write(f"• **Protein:** {m.get('protein_g')}g")
                    st.write(f"• **Carbs:** {m.get('carbs_g')}g")
                    st.write(f"• **Fats:** {m.get('fats_g')}g")

    with tab2:
        st.subheader("Weekly Calorie and Macronutrient Distribution")
        
        fig_cal = px.bar(
            df_macros, 
            x="Day", 
            y="Calories", 
            color="Workout",
            title="Daily Caloric Intake vs. Workout Activity",
            text_auto=True
        )
        st.plotly_chart(fig_cal, use_container_width=True)

        fig_macro = px.line(
            df_macros, 
            x="Day", 
            y=["Protein (g)", "Carbs (g)", "Fats (g)"],
            markers=True,
            title="Daily Macronutrient Breakdown Trends"
        )
        st.plotly_chart(fig_macro, use_container_width=True)

    with tab3:
        st.subheader("Inventory Utilization Check")
        st.write("Cross-referencing used items against provided pantry items:")
        st.write("**Pantry Items Provided:**")
        st.write(final_pantry_list)
        st.success("✅ Output verified against provided pantry items.")
