
st.set_page_config(
    page_title="FitFuel AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main .block-container {max-width:1250px;padding-top:1.5rem;padding-bottom:3rem}
.hero-container {
    background:linear-gradient(135deg,rgba(16,185,129,.14),rgba(99,102,241,.14));
    border:1px solid rgba(255,255,255,.10); border-radius:20px;
    padding:25px; margin-bottom:22px
}
.hero-title {
    font-size:38px;font-weight:800;
    background:linear-gradient(90deg,#10B981,#6366F1);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent
}
.hero-subtitle {color:#9CA3AF;font-size:15px}
.card {
    background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.09);
    border-radius:16px;padding:20px;margin-bottom:14px
}
.meal-box {
    background:rgba(255,255,255,.025);border-left:3px solid #10B981;
    padding:12px 14px;border-radius:0 10px 10px 0;margin-bottom:10px
}
.meal-title {font-size:12px;font-weight:750;color:#A7F3D0}
.meal-desc {font-size:14px;color:#F9FAFB;margin-top:3px}
.pantry-chip {
    display:inline-block;padding:7px 11px;margin:3px;border-radius:15px;
    background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.25)
}
</style>
""", unsafe_allow_html=True)

import os
import json
import re
import random
from typing import Any, Dict, List, Set

import streamlit as st
from groq import Groq

# ============================================================
# FITFUEL AI - REAL-WORLD PANTRY-AWARE MULTI-AGENT PLANNER
# ============================================================

st.set_page_config(
    page_title="FitFuel AI | Smart Meal & Workout Planner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ============================================================
# STYLING
# ============================================================

st.markdown(
    """
<style>
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1250px;
}
.hero-container {
    background: linear-gradient(135deg, rgba(16,185,129,.14), rgba(99,102,241,.14));
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 20px;
    padding: 28px;
    margin-bottom: 22px;
}
.hero-title {
    font-size: 38px;
    font-weight: 800;
    background: linear-gradient(90deg,#10B981,#6366F1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero-subtitle { color:#9CA3AF; font-size:15px; }
.metric-card {
    background: rgba(255,255,255,.03);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 16px;
    padding: 18px;
    text-align: center;
}
.metric-value { font-size:27px; font-weight:750; color:#10B981; }
.metric-label {
    font-size:12px; color:#9CA3AF; text-transform:uppercase;
    letter-spacing:.5px;
}
.meal-box {
    background: rgba(255,255,255,.025);
    border-left: 3px solid #10B981;
    padding: 12px 14px;
    border-radius: 0 10px 10px 0;
    margin-bottom: 10px;
}
.meal-title { font-size:12px; font-weight:750; color:#A7F3D0; }
.meal-desc { font-size:14px; color:#F9FAFB; margin-top:3px; }
.agent-info {
    background: rgba(255,255,255,.035);
    border:1px solid rgba(255,255,255,.08);
    border-radius:14px;
    padding:16px;
    margin-top:12px;
}
.pantry-chip {
    display:inline-block;
    padding:6px 10px;
    margin:3px;
    border-radius:15px;
    background:rgba(16,185,129,.12);
    border:1px solid rgba(16,185,129,.25);
}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False)
    except Exception:
        return str(value)


def parse_json_safely(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    cleaned = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group(0))
                return obj if isinstance(obj, dict) else {}
            except Exception:
                return {}
    return {}


def normalize_item(item: str) -> str:
    """Normalize pantry text so 'Tomatoes: 1 kg' matches 'tomato'."""
    item = item.lower().strip()
    item = re.sub(r"\([^)]*\)", "", item)
    item = re.sub(r":.*$", "", item)
    item = re.sub(r"\d+(?:\.\d+)?\s*(kg|g|gram|grams|ml|l|litre|litres|pcs|pieces|pack|packs)\b", "", item)
    item = re.sub(r"\s+", " ", item).strip()

    aliases = {
        "tomatoes": "tomato",
        "onions": "onion",
        "potatoes": "potato",
        "bananas": "banana",
        "apples": "apple",
        "carrots": "carrot",
        "spinach leaves": "spinach",
        "eggs": "egg",
        "chicken breast": "chicken",
        "chicken breasts": "chicken",
        "fish fillet": "fish",
        "fish fillets": "fish",
        "paneer": "paneer",
        "cottage cheese": "paneer",
        "curd": "yogurt",
        "plain yogurt": "yogurt",
        "dahi": "yogurt",
        "rice": "rice",
        "basmati rice": "rice",
        "brown rice": "rice",
        "oats": "oats",
        "rolled oats": "oats",
        "dal": "dal",
        "lentils": "dal",
        "toor dal": "dal",
        "moong dal": "dal",
        "atta": "flour",
        "wheat flour": "flour",
        "whole wheat flour": "flour",
        "chapati": "flour",
        "chapatis": "flour",
        "roti": "flour",
        "rotis": "flour",
        "bread": "bread",
        "brown bread": "bread",
        "milk": "milk",
        "soy milk": "soy milk",
        "tofu": "tofu",
        "chickpeas": "chickpea",
        "chana": "chickpea",
        "rajma": "rajma",
        "beans": "beans",
        "green beans": "beans",
        "broccoli": "broccoli",
        "peas": "peas",
        "peanuts": "peanut",
        "almonds": "almond",
        "walnuts": "walnut",
        "makhana": "makhana",
        "banana": "banana",
        "apple": "apple",
    }
    return aliases.get(item, item)


def parse_pantry(raw: str) -> List[str]:
    items = []
    for line in re.split(r"[\n,;]+", raw or ""):
        line = line.strip()
        if line:
            items.append(line)

    # Preserve user order while removing duplicates.
    seen = set()
    result = []
    for item in items:
        key = normalize_item(item)
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


# ============================================================
# PANTRY FOOD CLASSIFICATION
# ============================================================

NON_VEG = {"chicken", "fish", "mutton", "prawns", "beef", "pork", "meat"}
EGG = {"egg"}
DAIRY = {"milk", "paneer", "yogurt", "cheese", "curd", "butter", "ghee"}

def classify_food(item: str) -> str:
    n = normalize_item(item)
    if n in NON_VEG:
        return "Non-Vegetarian"
    if n in EGG:
        return "Egg"
    if n in DAIRY:
        return "Vegetarian / Dairy"
    return "Vegetarian"


def allowed_for_diet(item: str, diet: str) -> bool:
    category = classify_food(item)
    if diet == "Vegetarian":
        return category not in {"Non-Vegetarian", "Egg"}
    if diet == "Vegan":
        return category == "Vegetarian"
    if diet == "Eggetarian":
        return category != "Non-Vegetarian"
    # Non-Vegetarian can use vegetarian, egg and non-vegetarian foods.
    return True


# ============================================================
# RECIPE CATALOG
# IMPORTANT: A recipe is selectable ONLY when every required
# ingredient exists in the user's pantry and is allowed by diet.
# ============================================================

RECIPES = [
    # breakfast
    {"name": "Oats + Banana Bowl", "meal": "breakfast", "ingredients": ["oats", "banana"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "60g oats + 1 banana"},
    {"name": "Oats + Milk Bowl", "meal": "breakfast", "ingredients": ["oats", "milk"], "diet": ["Vegetarian", "Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "60g oats + 200ml milk"},
    {"name": "Egg Toast", "meal": "breakfast", "ingredients": ["egg", "bread"], "diet": ["Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "3 eggs + 2 bread slices"},
    {"name": "Egg + Banana Breakfast", "meal": "breakfast", "ingredients": ["egg", "banana"], "diet": ["Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "3 eggs + 1 banana"},
    {"name": "Paneer + Tomato Bowl", "meal": "breakfast", "ingredients": ["paneer", "tomato"], "diet": ["Vegetarian", "Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "120g paneer + tomato"},
    {"name": "Banana + Milk", "meal": "breakfast", "ingredients": ["banana", "milk"], "diet": ["Vegetarian", "Eggetarian", "Non-Vegetarian"], "heavy": False, "portion": "1 banana + 250ml milk"},
    {"name": "Poha-style Rice & Onion Bowl", "meal": "breakfast", "ingredients": ["rice", "onion"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": False, "portion": "1.5 cups cooked rice + onion"},

    # lunch
    {"name": "Dal Rice", "meal": "lunch", "ingredients": ["dal", "rice"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "1.5 cups dal + 1.5 cups rice"},
    {"name": "Dal + Chapati", "meal": "lunch", "ingredients": ["dal", "flour"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": False, "portion": "1.5 cups dal + 3 chapatis"},
    {"name": "Paneer Rice Bowl", "meal": "lunch", "ingredients": ["paneer", "rice"], "diet": ["Vegetarian", "Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "150g paneer + 1.5 cups rice"},
    {"name": "Chicken Rice Bowl", "meal": "lunch", "ingredients": ["chicken", "rice"], "diet": ["Non-Vegetarian"], "heavy": True, "portion": "180g chicken + 1.5 cups rice"},
    {"name": "Chicken Chapati Plate", "meal": "lunch", "ingredients": ["chicken", "flour"], "diet": ["Non-Vegetarian"], "heavy": True, "portion": "150g chicken + 3 chapatis"},
    {"name": "Egg Rice Bowl", "meal": "lunch", "ingredients": ["egg", "rice"], "diet": ["Eggetarian", "Non-Vegetarian"], "heavy": False, "portion": "3 eggs + 1.5 cups rice"},
    {"name": "Rajma Rice", "meal": "lunch", "ingredients": ["rajma", "rice"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "1.5 cups rajma + 1.5 cups rice"},
    {"name": "Chickpea Rice", "meal": "lunch", "ingredients": ["chickpea", "rice"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "1.5 cups chickpeas + 1 cup rice"},

    # snacks
    {"name": "Banana Snack", "meal": "snack", "ingredients": ["banana"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": False, "portion": "1 medium banana"},
    {"name": "Apple Snack", "meal": "snack", "ingredients": ["apple"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": False, "portion": "1 medium apple"},
    {"name": "Roasted Chickpea Snack", "meal": "snack", "ingredients": ["chickpea"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "40g roasted chickpea"},
    {"name": "Boiled Egg Snack", "meal": "snack", "ingredients": ["egg"], "diet": ["Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "2 boiled eggs"},
    {"name": "Paneer Snack", "meal": "snack", "ingredients": ["paneer"], "diet": ["Vegetarian", "Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "100g paneer"},
    {"name": "Milk Snack", "meal": "snack", "ingredients": ["milk"], "diet": ["Vegetarian", "Eggetarian", "Non-Vegetarian"], "heavy": False, "portion": "250ml milk"},
    {"name": "Makhana Snack", "meal": "snack", "ingredients": ["makhana"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": False, "portion": "25g makhana"},

    # dinner
    {"name": "Dal Rice Dinner", "meal": "dinner", "ingredients": ["dal", "rice"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "1 cup dal + 1 cup rice"},
    {"name": "Dal Chapati Dinner", "meal": "dinner", "ingredients": ["dal", "flour"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": False, "portion": "1 cup dal + 2 chapatis"},
    {"name": "Paneer Chapati Dinner", "meal": "dinner", "ingredients": ["paneer", "flour"], "diet": ["Vegetarian", "Eggetarian", "Non-Vegetarian"], "heavy": True, "portion": "120g paneer + 2 chapatis"},
    {"name": "Chicken Rice Dinner", "meal": "dinner", "ingredients": ["chicken", "rice"], "diet": ["Non-Vegetarian"], "heavy": True, "portion": "150g chicken + 1 cup rice"},
    {"name": "Fish Rice Dinner", "meal": "dinner", "ingredients": ["fish", "rice"], "diet": ["Non-Vegetarian"], "heavy": True, "portion": "150g fish + 1 cup rice"},
    {"name": "Egg Chapati Dinner", "meal": "dinner", "ingredients": ["egg", "flour"], "diet": ["Eggetarian", "Non-Vegetarian"], "heavy": False, "portion": "3 eggs + 2 chapatis"},
    {"name": "Rice + Vegetable Bowl", "meal": "dinner", "ingredients": ["rice", "tomato", "onion"], "diet": ["Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"], "heavy": False, "portion": "1.5 cups rice + tomato + onion"},
]


def pantry_keys(pantry_items: List[str]) -> Set[str]:
    return {normalize_item(x) for x in pantry_items}


def recipe_available(recipe: Dict[str, Any], pantry_set: Set[str], diet: str, avoid: str) -> bool:
    if diet not in recipe["diet"]:
        return False
    if not all(ingredient in pantry_set for ingredient in recipe["ingredients"]):
        return False

    avoid_words = {normalize_item(x) for x in re.split(r"[,;\n]+", avoid or "") if x.strip()}
    if avoid_words.intersection(set(recipe["ingredients"])):
        return False
    return True


def available_recipes(meal: str, pantry_items: List[str], diet: str, avoid: str) -> List[Dict[str, Any]]:
    pset = pantry_keys(pantry_items)
    return [
        r for r in RECIPES
        if r["meal"] == meal and recipe_available(r, pset, diet, avoid)
    ]


# ============================================================
# WORKOUT / PORTION LOGIC
# ============================================================

def target_for_workout(workout: str) -> Dict[str, str]:
    if workout == "Strength Training":
        return {
            "target": "Higher protein + higher carbohydrates",
            "reason": "Strength day: prioritize protein and carbohydrates for training and recovery.",
        }
    if workout == "Full Body":
        return {
            "target": "Balanced calories + protein",
            "reason": "Full-body day: balanced energy and protein distribution.",
        }
    if workout == "Cardio":
        return {
            "target": "Moderate protein + endurance carbohydrates",
            "reason": "Cardio day: maintain moderate protein and carbohydrate availability.",
        }
    return {
        "target": "Lighter balanced meals",
        "reason": "Rest day: avoid automatically increasing food portions when activity is lower.",
    }


def format_recipe(recipe: Dict[str, Any]) -> str:
    return f"{recipe['name']} — {recipe['portion']}"


def select_recipe(
    meal: str,
    workout: str,
    pantry_items: List[str],
    diet: str,
    avoid: str,
    used_names: Set[str],
) -> str:
    options = available_recipes(meal, pantry_items, diet, avoid)
    if not options:
        return "⚠️ No suitable recipe: required pantry ingredients are not available."

    heavy = workout in {"Strength Training", "Full Body"}
    preferred = [r for r in options if r["heavy"] == heavy]
    pool = preferred or options

    unused = [r for r in pool if r["name"] not in used_names]
    chosen = random.choice(unused or pool)
    used_names.add(chosen["name"])
    return format_recipe(chosen)


# ============================================================
# DETERMINISTIC PANTRY-FIRST ENGINE
# This is the safety net even when Groq is unavailable.
# ============================================================

def generate_pantry_plan(state: Dict[str, Any]) -> Dict[str, Any]:
    pantry_items = parse_pantry(state.get("pantry", ""))
    diet = state.get("food_preference", "Vegetarian")
    avoid = state.get("foods_to_avoid", "")
    schedule = state.get("workout_schedule", {})

    weekly_plan: Dict[str, Any] = {}
    used_names: Set[str] = set()
    total_cost = 0

    for day in DAYS:
        workout = schedule.get(day, "Rest")
        target = target_for_workout(workout)

        breakfast = select_recipe("breakfast", workout, pantry_items, diet, avoid, used_names)
        lunch = select_recipe("lunch", workout, pantry_items, diet, avoid, used_names)
        snack = select_recipe("snack", workout, pantry_items, diet, avoid, used_names)
        dinner = select_recipe("dinner", workout, pantry_items, diet, avoid, used_names)

        # This is an estimate of preparation/usage cost, not a claim about
        # actual market prices.
        cost = {"Strength Training": 320, "Full Body": 300, "Cardio": 270, "Rest": 220}.get(workout, 250)
        total_cost += cost

        weekly_plan[day] = {
            "workout": workout,
            "daily_target": target["target"],
            "breakfast": breakfast,
            "lunch": lunch,
            "snack": snack,
            "dinner": dinner,
            "estimated_cost": cost,
            "reason": target["reason"],
            "pantry_used": pantry_items,
        }

    eligible = [x for x in pantry_items if allowed_for_diet(x, diet)]

    # Grocery list is intentionally NOT used to invent meal ingredients.
    # It only reports missing ingredients that could expand the user's options.
    all_recipe_ingredients = sorted(
        {
            ingredient
            for r in RECIPES
            for ingredient in r["ingredients"]
            if diet in r["diet"]
        }
    )
    missing_options = [
        x for x in all_recipe_ingredients
        if x not in pantry_keys(pantry_items)
    ]

    return {
        "estimated_weekly_budget": total_cost,
        "plan_score": 96 if eligible else 40,
        "coordination_logic": (
            "Every selected meal is checked against the pantry before it is displayed. "
            "Diet restrictions, foods to avoid, and the selected day's workout determine which "
            "available pantry recipes are eligible."
        ),
        "pantry_items": pantry_items,
        "eligible_pantry": eligible,
        "missing_options": missing_options,
        "weekly_plan": weekly_plan,
    }


# ============================================================
# GROQ SUPERVISOR
# Groq can improve wording/variety, but the pantry-first
# deterministic validation remains the source of truth.
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
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.35,
                max_completion_tokens=3500,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or ""
        except Exception:
            return ""

    def generate_full_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # First create a validated pantry-only plan.
        base = generate_pantry_plan(state)

        prompt = f"""
You are the FitFuel Supervisor Agent.

Improve ONLY the wording and coordination notes of this already validated plan.

ABSOLUTE RULES:
1. Never introduce an ingredient that is not in pantry_items.
2. Never change a meal to a recipe requiring an ingredient outside pantry_items.
3. Respect food_preference exactly.
4. Respect foods_to_avoid.
5. Keep all seven days.
6. Keep the same breakfast/lunch/snack/dinner meal names and portions from the validated plan.
7. The selected workout must remain unchanged.

Return JSON with:
{{
  "coordination_logic": "...",
  "weekly_plan": {{
    "Monday": {{"reason": "..."}},
    "Tuesday": {{"reason": "..."}},
    "Wednesday": {{"reason": "..."}},
    "Thursday": {{"reason": "..."}},
    "Friday": {{"reason": "..."}},
    "Saturday": {{"reason": "..."}},
    "Sunday": {{"reason": "..."}}
  }}
}}
"""
        raw = self.ask(prompt, safe_json({
            "food_preference": state.get("food_preference"),
            "foods_to_avoid": state.get("foods_to_avoid"),
            "pantry_items": base["pantry_items"],
            "validated_plan": base["weekly_plan"],
        }))
        improved = parse_json_safely(raw)

        if improved:
            base["coordination_logic"] = improved.get(
                "coordination_logic", base["coordination_logic"]
            )
            for day in DAYS:
                if day in improved.get("weekly_plan", {}):
                    reason = improved["weekly_plan"][day].get("reason")
                    if reason:
                        base["weekly_plan"][day]["reason"] = reason

        return base


# ============================================================
# AGENT ROLE CONTENT
# ============================================================

AGENTS = {
    "🧠 Supervisor Agent": "Coordinates the selected day's meal + workout plan.",
    "⚖️ Portion Control Agent": "Explains portions according to the day's workout.",
    "🏋️ Workout Agent": "Explains today's workout and nutrition target.",
    "🔍 Constraint Audit Agent": "Checks diet, avoided foods and pantry compliance.",
    "🥗 Meal Agent": "Shows why today's meals were selected from the pantry.",
    "👀 Monitoring Agent": "Monitors today's schedule and pantry-dependent plan.",
    "📷 Vision Agent": "Represents pantry-image inventory understanding.",
    "🔄 Replanning Agent": "Explains how the selected day changes when pantry/schedule changes.",
}


def agent_content(agent: str, day: str, plan: Dict[str, Any], state: Dict[str, Any]) -> str:
    data = plan.get("weekly_plan", {}).get(day, {})
    pantry = plan.get("pantry_items", [])
    eligible = plan.get("eligible_pantry", [])

    if agent.startswith("🧠"):
        return (
            f"**{day} Supervisor output**\n\n"
            f"Workout: **{data.get('workout', 'N/A')}**\n\n"
            f"Nutrition target: **{data.get('daily_target', 'N/A')}**\n\n"
            f"Today's four meals are coordinated using only recipes validated against the pantry."
        )

    if agent.startswith("⚖️"):
        return (
            f"**{day} Portion Control output**\n\n"
            f"Breakfast: {data.get('breakfast', 'N/A')}\n\n"
            f"Lunch: {data.get('lunch', 'N/A')}\n\n"
            f"Snack: {data.get('snack', 'N/A')}\n\n"
            f"Dinner: {data.get('dinner', 'N/A')}\n\n"
            f"Reason: {data.get('reason', 'N/A')}"
        )

    if agent.startswith("🏋️"):
        return (
            f"**{day} Workout output**\n\n"
            f"Workout: **{data.get('workout', 'Rest')}**\n\n"
            f"Nutrition target: **{data.get('daily_target', 'N/A')}**\n\n"
            f"Coordination: {data.get('reason', 'N/A')}"
        )

    if agent.startswith("🔍"):
        return (
            f"**{day} Constraint Audit output**\n\n"
            f"Diet: **{state.get('food_preference', 'N/A')}**\n\n"
            f"Foods to avoid: **{state.get('foods_to_avoid') or 'None specified'}**\n\n"
            f"Pantry-only validation: **Enabled**\n\n"
            f"Eligible pantry items for this diet: **{len(eligible)}**"
        )

    if agent.startswith("🥗"):
        return (
            f"**{day} Meal Agent output**\n\n"
            f"Breakfast: {data.get('breakfast', 'N/A')}\n\n"
            f"Lunch: {data.get('lunch', 'N/A')}\n\n"
            f"Snack: {data.get('snack', 'N/A')}\n\n"
            f"Dinner: {data.get('dinner', 'N/A')}\n\n"
            "The Meal Agent cannot display a recipe requiring an ingredient missing from the pantry."
        )

    if agent.startswith("👀"):
        return (
            f"**{day} Monitoring output**\n\n"
            f"Today's workout: **{data.get('workout', 'Rest')}**\n\n"
            f"Pantry items currently tracked: **{len(pantry)}**\n\n"
            "If the pantry or workout schedule changes, regenerate the plan so the day is recalculated."
        )

    if agent.startswith("📷"):
        return (
            f"**{day} Vision Agent output**\n\n"
            "In a production version, this agent can receive a pantry photo and convert visible "
            "items into the same normalized inventory used by the Meal Agent.\n\n"
            f"Current text inventory: {', '.join(pantry) if pantry else 'No pantry items'}"
        )

    return (
        f"**{day} Replanning output**\n\n"
        "If an ingredient is removed, the next generation checks every meal again. "
        "A meal that no longer satisfies the pantry check is replaced by another valid pantry recipe; "
        "if no valid recipe exists, the UI clearly reports that more ingredients are required."
    )




# ============================================================
# MULTI-PAGE SHARED STATE
# ============================================================

def initialize_state():
    defaults = {
        "name": "Alex",
        "food_preference": "Vegetarian",
        "foods_to_avoid": "peanuts, mushrooms",
        "weekly_budget": 2500,
        "maximum_cooking_time": 30,
        "pantry": "Rice\nDal\nOats\nMilk\nPaneer\nEggs\nBananas\nTomatoes\nOnions\nSpinach",
        "workout_schedule": {
            "Monday": "Strength Training",
            "Tuesday": "Cardio",
            "Wednesday": "Rest",
            "Thursday": "Strength Training",
            "Friday": "Full Body",
            "Saturday": "Cardio",
            "Sunday": "Rest",
        },
        "current_plan": None,
        "selected_day": "Monday",
        "selected_agent": "🧠 Supervisor Agent",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def build_user_state():
    return {
        "name": st.session_state["name"],
        "food_preference": st.session_state["food_preference"],
        "foods_to_avoid": st.session_state["foods_to_avoid"],
        "weekly_budget": st.session_state["weekly_budget"],
        "maximum_cooking_time": st.session_state["maximum_cooking_time"],
        "workout_schedule": st.session_state["workout_schedule"],
        "pantry": st.session_state["pantry"],
    }


def generate_current_plan():
    state = build_user_state()
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key and "GROQ_API_KEY" in st.secrets:
        api_key = st.secrets["GROQ_API_KEY"]

    if api_key:
        engine = FitFuelAgents(api_key)
        plan = engine.generate_full_plan(state)
    else:
        plan = generate_pantry_plan(state)

    st.session_state["current_plan"] = plan
    return plan


def go(page: str):
    st.switch_page(page)


def page_header(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="hero-container">
            <div class="hero-title">⚡ FitFuel AI</div>
            <h2>{title}</h2>
            <div class="hero-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


initialize_state()

page_header("Agent Workspace", "Each agent opens a dedicated page and reports only on the selected day")

if st.session_state.get("current_plan") is None:
    st.warning("Generate a plan first.")
    if st.button("Open Daily Plan"):
        go("pages/4_Daily_Plan.py")
else:
    plan = st.session_state["current_plan"]

    selected_day = st.selectbox(
        "📅 Day",
        DAYS,
        index=DAYS.index(st.session_state.get("selected_day", "Monday")),
    )
    st.session_state["selected_day"] = selected_day

    agent_names = list(AGENTS.keys())
    selected_agent = st.selectbox(
        "🤖 Agent",
        agent_names,
        index=agent_names.index(
            st.session_state.get("selected_agent", agent_names[0])
        ),
    )
    st.session_state["selected_agent"] = selected_agent

    st.markdown(f"## {selected_agent}")
    st.caption(AGENTS[selected_agent])

    state = build_user_state()
    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )
    st.write(agent_content(selected_agent, selected_day, plan, state))
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("Open another specialist")

    cols = st.columns(4)
    for i, agent in enumerate(agent_names):
        with cols[i % 4]:
            if st.button(agent, key=f"switch_agent_{i}", use_container_width=True):
                st.session_state["selected_agent"] = agent
                st.rerun()

    if st.button("← Back to Daily Plan", type="primary", use_container_width=True):
        go("pages/4_Daily_Plan.py")
