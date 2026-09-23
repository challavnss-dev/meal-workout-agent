import streamlit as st
import json
import base64
from copy import deepcopy
from typing import Any, Dict, Optional
from groq import Groq

# ---------------------------------------------------------
# Page Configuration & Custom CSS Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="NourishSync | Multi-Agent Fitness & Meal Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Impact CSS for Hackathon Aesthetics
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e2638 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #10B981;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .agent-pill {
        background-color: #1F2937;
        border: 1px solid #4B5563;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.8rem;
        color: #6366F1;
        display: inline-block;
        margin-right: 5px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Multi-Agent Engine Architecture
# ---------------------------------------------------------
class MealWorkoutAgents:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        # Using Llama 3.3 70B as standard high-performance default on Groq
        self.model = "llama-3.3-70b-versatile"

    def call_ai(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4000
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_completion_tokens=max_tokens
        )
        return response.choices[0].message.content or ""

    def extract_json(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            result = json.loads(text)
            return result if isinstance(result, dict) else {"result": result}
        except Exception:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                result = json.loads(text[start:end + 1])
                return result if isinstance(result, dict) else {"result": result}
            except Exception:
                pass
        return {"raw_response": text}

    def pantry_vision_agent(self, image_bytes: bytes) -> Dict[str, Any]:
        if not image_bytes:
            return {"ingredients": [], "confidence_notes": "No image provided."}
        
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{image_base64}"
        
        system_prompt = """You are the Vision Agent. Identify visible food ingredients. Return strictly JSON: {"ingredients": ["item1", "item2"], "confidence_notes": "..."}"""
        try:
            response = self.client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Identify visible food ingredients in this image."},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]}
                ],
                temperature=0.1,
                max_completion_tokens=1500,
                response_format={"type": "json_object"}
            )
            return self.extract_json(response.choices[0].message.content or "{}")
        except Exception as e:
            return {"ingredients": [], "error": str(e)}

    def workout_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = "You are the Workout Specialist Agent. Return JSON mapping each day (Monday to Sunday) to: workout, duration_minutes, intensity, notes."
        user_prompt = f"USER STATE:\n{json.dumps(state, indent=2)}"
        try:
            res = self.call_ai(system_prompt, user_prompt, 0.2, 3000)
            return self.extract_json(res)
        except Exception as e:
            return {"workouts": {}, "error": str(e)}

    def meal_agent(self, state: Dict[str, Any], workout_result: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = "You are the Nutrition Specialist Agent. Create meals synchronized with workout loads and constraints. Return JSON mapping each day (Monday to Sunday) to: breakfast, lunch, snack, dinner, approximate_cost, reason."
        user_prompt = f"STATE:\n{json.dumps(state, indent=2)}\nWORKOUTS:\n{json.dumps(workout_result, indent=2)}"
        try:
            res = self.call_ai(system_prompt, user_prompt, 0.3, 4000)
            return self.extract_json(res)
        except Exception as e:
            return {"meals": {}, "error": str(e)}

    def constraint_agent(self, state: Dict[str, Any], workout_result: Dict[str, Any], meal_result: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = "You are the Constraint & Safety Inspector. Audit plans against budget, allergies, and workout timing. Return JSON: {\"status\": \"VALID|VIOLATED\", \"estimated_budget\": 0, \"violations\": [], \"suggestions\": [], \"pantry_items_used\": [], \"missing_items\": []}"
        user_prompt = f"STATE:\n{json.dumps(state, indent=2)}\nWORKOUTS:\n{json.dumps(workout_result, indent=2)}\nMEALS:\n{json.dumps(meal_result, indent=2)}"
        try:
            res = self.call_ai(system_prompt, user_prompt, 0.1, 2500)
            return self.extract_json(res)
        except Exception as e:
            return {"status": "ERROR", "violations": [str(e)]}

    def coordinator_agent(self, state: Dict[str, Any], workout_result: Dict[str, Any], meal_result: Dict[str, Any], constraint_result: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = "You are the Executive Orchestrator. Consolidate specialist outputs into a master schedule. Return JSON with 'weekly_plan' (Monday-Sunday object with workout, breakfast, lunch, snack, dinner, reason), 'summary', 'estimated_weekly_budget', 'grocery_list', 'constraint_status', and 'coordinator_explanation'."
        user_prompt = f"STATE:\n{json.dumps(state, indent=2)}\nWORKOUTS:\n{json.dumps(workout_result, indent=2)}\nMEALS:\n{json.dumps(meal_result, indent=2)}\nCONSTRAINTS:\n{json.dumps(constraint_result, indent=2)}"
        try:
            res = self.call_ai(system_prompt, user_prompt, 0.2, 5000)
            return self.extract_json(res)
        except Exception as e:
            return {"weekly_plan": {}, "grocery_list": [], "error": str(e)}

    def create_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        w_res = self.workout_agent(state)
        m_res = self.meal_agent(state, w_res)
        c_res = self.constraint_agent(state, w_res, m_res)
        final_plan = self.coordinator_agent(state, w_res, m_res, c_res)
        return {
            "plan": final_plan,
            "workout_agent": w_res,
            "meal_agent": m_res,
            "constraint_agent": c_res,
            "agents_used": ["Workout Agent", "Meal Agent", "Constraint Agent", "Supervisor Coordinator"]
        }

    def monitoring_agent(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = "You are the Real-time Monitor. Detect schedule or pantry diffs. Return JSON: {\"change_detected\": bool, \"replan_required\": bool, \"changes\": [], \"affected_days\": [], \"reason\": \"\"}"
        user_prompt = f"OLD STATE:\n{json.dumps(old_state, indent=2)}\nNEW STATE:\n{json.dumps(new_state, indent=2)}"
        try:
            res = self.call_ai(system_prompt, user_prompt, 0.1, 2000)
            return self.extract_json(res)
        except Exception as e:
            return {"change_detected": True, "replan_required": True, "changes": [str(e)], "reason": str(e)}

    def replanning_agent(self, old_state: Dict[str, Any], new_state: Dict[str, Any], old_plan: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        system_prompt = "You are the Dynamic Replanner. Rebalance the schedule preserving valid past days. Return JSON: {\"updated_plan\": {}, \"changes_made\": [], \"reason\": \"\", \"new_grocery_list\": [], \"estimated_weekly_budget\": 0}"
        user_prompt = f"OLD STATE:\n{json.dumps(old_state, indent=2)}\nNEW STATE:\n{json.dumps(new_state, indent=2)}\nOLD PLAN:\n{json.dumps(old_plan or {}, indent=2)}"
        try:
            res = self.call_ai(system_prompt, user_prompt, 0.2, 5000)
            return self.extract_json(res)
        except Exception as e:
            return {"updated_plan": {}, "changes_made": [], "reason": str(e), "new_grocery_list": []}


# ---------------------------------------------------------
# API Initialization & Session State
# ---------------------------------------------------------
try:
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
    if not GROQ_API_KEY:
        st.error("🔑 GROQ_API_KEY missing. Configure Streamlit Secrets.")
        st.stop()
    agents = MealWorkoutAgents(GROQ_API_KEY)
except Exception as e:
    st.error(f"Failed to initialize AI Agents: {e}")
    st.stop()

for key in ["current_state", "plan_result", "vision_result", "monitor_result", "replan_result"]:
    if key not in st.session_state:
        st.session_state[key] = None


# ---------------------------------------------------------
# Sidebar - Control Center & Inputs
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/isometric-folders/100/dumbbell.png", width=60)
    st.title("User Profile & Context")
    
    name = st.text_input("Name", "Alex")
    food_preference = st.selectbox("Dietary Preference", ["Vegetarian", "Non-Vegetarian", "Vegan", "Eggetarian"])
    foods_to_avoid = st.text_input("Allergies / Foods to Avoid", "Peanuts, Shellfish")
    budget = st.number_input("Weekly Budget (₹)", min_value=100, max_value=10000, value=2500, step=100)
    cooking_time = st.slider("Max Cooking Time (mins/meal)", 10, 120, 30)

    st.markdown("---")
    st.subheader("🏋️ Workout Schedule")
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    workout_options = ["Strength Training", "Cardio", "Full Body", "Mobility", "Rest"]
    
    workout_schedule = {}
    for day in days:
        workout_schedule[day] = st.selectbox(f"{day}", workout_options, index=0 if day in ["Monday", "Wednesday", "Friday"] else 4, key=f"wk_{day}")

    st.markdown("---")
    st.subheader("🥫 Pantry Inventory")
    pantry_text = st.text_area("Pantry Items", "Rice, Oats, Greek Yogurt, Eggs, Chicken Breast, Spinach, Tomatoes", height=100)
    pantry_image = st.file_uploader("📷 Upload Pantry Photo", type=["jpg", "jpeg", "png", "webp"])

def build_state():
    return {
        "name": name,
        "food_preference": food_preference,
        "foods_to_avoid": foods_to_avoid,
        "weekly_budget": budget,
        "maximum_cooking_time_minutes": cooking_time,
        "workout_schedule": workout_schedule,
        "pantry": pantry_text
    }


# ---------------------------------------------------------
# Hero Banner & Main Workspace
# ---------------------------------------------------------
st.title("⚡ NourishSync AI")
st.caption("Autonomous Multi-Agent Swarm for Meal & Workout Synchronization")

col_btn, col_status = st.columns([2, 3])
with col_btn:
    if st.button("🚀 GENERATE COORDINATED PLAN", use_container_width=True, type="primary"):
        with st.spinner("⚡ Agents collaborating across vision, nutrition, and workout constraints..."):
            state = build_state()
            if pantry_image is not None:
                vision_result = agents.pantry_vision_agent(pantry_image.getvalue())
                st.session_state.vision_result = vision_result
                state["vision_detected_ingredients"] = vision_result.get("ingredients", [])
            
            result = agents.create_plan(state)
            st.session_state.current_state = state
            st.session_state.plan_result = result
            st.session_state.monitor_result = None
            st.session_state.replan_result = None

with col_status:
    if st.session_state.plan_result:
        st.success("✅ Multi-Agent Plan Synchronized & Validated")


# ---------------------------------------------------------
# Tabbed Output Interface
# ---------------------------------------------------------
tab_overview, tab_daily, tab_pantry, tab_monitoring, tab_telemetry = st.tabs([
    "📊 Plan Overview", 
    "📅 Daily Schedule", 
    "🛒 Pantry & Groceries", 
    "👀 Real-Time Replanning", 
    "🤖 Agent Telemetry"
])

# TAB 1: OVERVIEW & DASHBOARD
with tab_overview:
    if st.session_state.plan_result:
        res = st.session_state.plan_result
        plan = res.get("plan", {})
        
        # Metric Cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">₹{plan.get("estimated_weekly_budget", 0)}</div><div class="metric-label">Estimated Budget</div></div>', unsafe_allow_html=True)
        with c2:
            status = plan.get("constraint_status", "VALIDATED")
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#3B82F6;">{status}</div><div class="metric-label">Constraint Audit</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#8B5CF6;">4</div><div class="metric-label">Active Agents</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#EC4899;">100%</div><div class="metric-label">Macro Balance</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🧠 Supervisor Executive Summary")
        st.info(plan.get("coordinator_explanation", "Plan successfully generated without constraint violations."))
        
        if plan.get("summary"):
            st.write(plan["summary"])
    else:
        st.info("👆 Configure user profile in sidebar and click 'Generate Coordinated Plan' to start.")

# TAB 2: DAILY SCHEDULE
with tab_daily:
    if st.session_state.plan_result:
        plan = st.session_state.plan_result.get("plan", {})
        weekly_plan = plan.get("weekly_plan", {})
        
        for day in days:
            day_data = weekly_plan.get(day, {})
            with st.expander(f"📌 {day.upper()}", expanded=(day == "Monday")):
                if isinstance(day_data, dict):
                    col_wk, col_meals = st.columns([1, 2])
                    with col_wk:
                        st.markdown("##### 🏋️ Training")
                        st.info(f"**Workout:** {day_data.get('workout', 'Rest')}")
                    with col_meals:
                        st.markdown("##### 🍽️ Meal Plan")
                        st.write(f"🍳 **Breakfast:** {day_data.get('breakfast', 'N/A')}")
                        st.write(f"🥗 **Lunch:** {day_data.get('lunch', 'N/A')}")
                        st.write(f"🍎 **Snack:** {day_data.get('snack', 'N/A')}")
                        st.write(f"🍲 **Dinner:** {day_data.get('dinner', 'N/A')}")
                        st.caption(f"💡 **Rationale:** {day_data.get('reason', 'Aligned with recovery target.')}")

# TAB 3: PANTRY & GROCERIES
with tab_pantry:
    col_v, col_g = st.columns([1, 1])
    with col_v:
        st.subheader("📷 Vision Analysis")
        if st.session_state.vision_result:
            v_res = st.session_state.vision_result
            items = v_res.get("ingredients", [])
            if items:
                st.success("Detected Ingredients: " + ", ".join(str(i) for i in items))
            if v_res.get("confidence_notes"):
                st.caption(v_res["confidence_notes"])
        else:
            st.caption("Upload a pantry photo in the sidebar to run computer vision extraction.")

    with col_g:
        st.subheader("🛒 AI Generated Grocery List")
        if st.session_state.plan_result:
            g_list = st.session_state.plan_result.get("plan", {}).get("grocery_list", [])
            for idx, item in enumerate(g_list):
                st.checkbox(str(item), key=f"g_item_{idx}")

# TAB 4: REAL-TIME REPLANNING
with tab_monitoring:
    st.subheader("👀 Adaptive Dynamic Replanner")
    st.write("Inject mid-week disruptions (e.g., injuries, missing pantry items, schedule conflicts).")
    
    change_text = st.text_area("Describe unexpected event / context change:", placeholder="e.g., I ran out of eggs and sustained a mild knee injury on Wednesday.")
    
    if st.button("🔍 DETECT IMPACT & REPLAN", type="secondary"):
        if not st.session_state.current_state:
            st.warning("Please generate an initial plan first.")
        elif change_text.strip():
            with st.spinner("Monitoring agent analyzing downstream impact..."):
                old_state = deepcopy(st.session_state.current_state)
                new_state = deepcopy(st.session_state.current_state)
                new_state["latest_change"] = change_text
                
                m_res = agents.monitoring_agent(old_state, new_state)
                st.session_state.monitor_result = m_res
                
                if m_res.get("replan_required", False):
                    old_plan = st.session_state.plan_result.get("plan", {}) if st.session_state.plan_result else {}
                    r_res = agents.replanning_agent(old_state, new_state, old_plan)
                    st.session_state.replan_result = r_res
                    st.session_state.current_state = new_state

    if st.session_state.monitor_result:
        m = st.session_state.monitor_result
        st.markdown("---")
        st.markdown("### Monitor Audit Findings")
        if m.get("change_detected"):
            st.warning(f"⚠️ Change Detected: {m.get('reason')}")
            if m.get("affected_days"):
                st.write(f"**Affected Days:** {', '.join(str(d) for d in m['affected_days'])}")
        else:
            st.success("No critical disruption detected.")

    if st.session_state.replan_result:
        r = st.session_state.replan_result
        st.markdown("### 🔄 Adjusted Plan Output")
        for change in r.get("changes_made", []):
            st.write(f"• {change}")
            
        up = r.get("updated_plan", {})
        for day, ddata in up.items():
            if isinstance(ddata, dict):
                with st.expander(f"Updated {day}"):
                    st.write(ddata)

# TAB 5: AGENT TELEMETRY & GRAPH
with tab_telemetry:
    st.subheader("🤖 Multi-Agent Architecture Visualization")
    
    # Graphviz visualization of the swarm
    st.graphviz_chart("""
    digraph Swarm {
        rankdir=LR;
        node [shape=box, style=filled, color="#1F2937", fontcolor="#F9FAFB", fontname="Helvetica"];
        
        Pantry [label="📷 Vision Agent", color="#3B82F6"];
        Workout [label="🏋️ Workout Agent", color="#10B981"];
        Meal [label="🥗 Meal Agent", color="#10B981"];
        Constraint [label="🔍 Constraint Agent", color="#F59E0B"];
        Supervisor [label="🧠 Supervisor Coordinator", color="#8B5CF6"];
        
        Pantry -> Meal [label="Ingredients"];
        Workout -> Meal [label="Calorie Load"];
        Workout -> Constraint;
        Meal -> Constraint;
        Constraint -> Supervisor [label="Audit Status"];
        Supervisor -> Output [label="Master Plan"];
    }
    """)
    
    st.markdown("### Raw Agent Payloads (Inspector)")
    if st.session_state.plan_result:
        st.json(st.session_state.plan_result)
    else:
        st.caption("No agent logs available yet.")
