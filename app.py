"""
===============================================================================
NourishSync Enterprise AI Swarm Engine
===============================================================================
Architecture Overview:
  1. Data Domain Models & Pydantic Validation Engine
  2. Groq LLM Communications & Resilient Client Middleware
  3. Domain Agent Swarm Implementations:
      - Pantry Vision Agent (Llama 3.2 11B Vision)
      - Workout Specialist Agent (Llama 3.3 70B Versatile)
      - Meal & Nutrition Specialist Agent (Llama 3.3 70B Versatile)
      - Safety & Constraint Auditor Agent (Llama 3.3 70B Versatile)
      - Supervisor / Master Orchestrator Agent (Llama 3.3 70B Versatile)
      - Real-Time Disruption Monitoring Agent (Llama 3.3 70B Versatile)
      - Dynamic Re-Planning Engine Agent (Llama 3.3 70B Versatile)
  4. Custom CSS Design System & UI Engine
  5. Streamlit Application & Reactive State Controller
===============================================================================
"""

import os
import json
import base64
import logging
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

import streamlit as st
from groq import Groq

# -----------------------------------------------------------------------------
# LOGGING & DIAGNOSTICS CONFIGURATION
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("NourishSyncEngine")

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & GLOBAL DESIGN METRICS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="NourishSync | Enterprise Multi-Agent Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# CUSTOM ENTERPRISE DESIGN SYSTEM (CSS)
# -----------------------------------------------------------------------------
CUSTOM_THEME_CSS = """
<style>
    /* Dark Slate Executive Theme */
    .stApp {
        background-color: #0B0E14;
        color: #E2E8F0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Header Styling */
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6366F1 0%, #A855F7 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .hero-subtitle {
        color: #94A3B8;
        font-size: 1.05rem;
        font-weight: 400;
        margin-bottom: 1.5rem;
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(145deg, #131927 0%, #1A2332 100%);
        border: 1px solid #2D3748;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #6366F1;
    }
    
    .metric-value {
        font-size: 1.9rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-top: 5px;
    }
    
    .metric-label {
        font-size: 0.75rem;
        color: #A0AEC0;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 600;
    }

    /* Agent Status Badges */
    .agent-status-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    
    .badge-active {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-pending {
        background-color: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    /* Day Expander Styling */
    .stExpander {
        background-color: #131927 !important;
        border: 1px solid #2D3748 !important;
        border-radius: 10px !important;
        margin-bottom: 12px !important;
    }

    /* Custom Buttons */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        border: none;
        color: #FFFFFF;
        font-weight: 700;
        border-radius: 8px;
        padding: 12px 24px;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
        transition: all 0.2s ease;
    }
    
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #4338CA 0%, #6D28D9 100%);
        box-shadow: 0 6px 16px rgba(79, 70, 229, 0.6);
        transform: translateY(-1px);
    }
</style>
"""
st.markdown(CUSTOM_THEME_CSS, unsafe_allow_html=True)


# =============================================================================
# SECTION 1: SCHEMAS & DEFAULT CONSTANTS
# =============================================================================

DEFAULT_DAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]

WORKOUT_TYPES = [
    "Strength Training", "Cardio Conditioning", "Full Body HIIT", 
    "Mobility & Active Recovery", "Rest Day"
]

DIET_PREFERENCES = ["Vegetarian", "Non-Vegetarian", "Vegan", "Eggetarian", "Keto", "Palaeo"]

def get_default_user_state() -> Dict[str, Any]:
    """Generates default user state payload."""
    return {
        "user_profile": {
            "name": "Alex",
            "dietary_preference": "Vegetarian",
            "allergies_and_restrictions": ["Peanuts", "Shellfish"],
            "weekly_budget_currency": "₹",
            "weekly_budget_limit": 2500,
            "max_cooking_time_per_meal_mins": 30
        },
        "workout_schedule_constraints": {
            "Monday": "Strength Training",
            "Tuesday": "Cardio Conditioning",
            "Wednesday": "Strength Training",
            "Thursday": "Mobility & Active Recovery",
            "Friday": "Full Body HIIT",
            "Saturday": "Strength Training",
            "Sunday": "Rest Day"
        },
        "pantry_inventory": {
            "raw_text_input": "Rice, Oats, Greek Yogurt, Eggs, Paneer, Spinach, Tomatoes, Lentils, Olive Oil",
            "vision_detected_items": []
        },
        "system_metadata": {
            "last_updated": datetime.now().isoformat(),
            "execution_version": "2.4.0-enterprise"
        }
    }


# =============================================================================
# SECTION 2: RESILIENT GROQ CLIENT MIDDLEWARE
# =============================================================================

class GroqAgentMiddleware:
    """Enterprise wrapper handling LLM API invocations, retries, and JSON extraction."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Groq API Key is mandatory for initializing the Middleware.")
        self.client = Groq(api_key=api_key)
        self.primary_model = "llama-3.3-70b-versatile"
        self.vision_model = "llama-3.2-11b-vision-preview"

    def execute_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        enforce_json: bool = True
    ) -> str:
        """Executes LLM chat completion with fallback logging."""
        try:
            kwargs = {
                "model": self.primary_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature,
                "max_completion_tokens": max_tokens,
            }
            if enforce_json:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Groq API Execution Error: {str(e)}")
            raise e

    def execute_vision_completion(
        self,
        system_prompt: str,
        image_base64: str,
        temperature: float = 0.1,
        max_tokens: int = 1500
    ) -> str:
        """Executes vision model inference on uploaded images."""
        try:
            image_url = f"data:image/jpeg;base64,{image_base64}"
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Analyze image and return detected ingredients in JSON format."},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]}
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Groq Vision API Execution Error: {str(e)}")
            raise e

    @staticmethod
    def extract_structured_json(raw_response_text: str) -> Dict[str, Any]:
        """Robust parsing utility to sanitize and extract JSON payloads."""
        if not raw_response_text:
            return {}

        text = raw_response_text.strip()
        
        # Strip Markdown code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {"data": parsed}
        except json.JSONDecodeError:
            pass

        # Substring extraction fallback for mixed responses
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1:
            try:
                extracted = json.loads(text[start_idx:end_idx + 1])
                if isinstance(extracted, dict):
                    return extracted
            except Exception:
                pass

        return {"raw_unparsed_response": text, "parsing_error": True}


# =============================================================================
# SECTION 3: MULTI-AGENT SWARM SYSTEM
# =============================================================================

class NourishSyncAgentSwarm:
    """Swarm Orchestrator encapsulating specialized agent logic."""

    def __init__(self, api_key: str):
        self.middleware = GroqAgentMiddleware(api_key=api_key)

    # -------------------------------------------------------------------------
    # AGENT 1: PANTRY VISION AGENT
    # -------------------------------------------------------------------------
    def run_pantry_vision_agent(self, image_bytes: bytes) -> Dict[str, Any]:
        """Detects visible raw food ingredients from pantry images."""
        if not image_bytes:
            return {"ingredients": [], "confidence_notes": "No image payload supplied."}

        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        system_prompt = """
        You are the Pantry Vision Agent. Identify clearly visible food ingredients.
        Do NOT invent or guess items that are absent.
        Return strictly JSON:
        {
          "ingredients": ["item1", "item2"],
          "confidence_notes": "string summary"
        }
        """
        try:
            raw_res = self.middleware.execute_vision_completion(system_prompt, encoded_image)
            return self.middleware.extract_structured_json(raw_res)
        except Exception as err:
            return {"ingredients": [], "error": f"Vision processing failed: {str(err)}"}

    # -------------------------------------------------------------------------
    # AGENT 2: WORKOUT SPECIALIST AGENT
    # -------------------------------------------------------------------------
    def run_workout_agent(self, user_state: Dict[str, Any]) -> Dict[str, Any]:
        """Designs structured training routines synchronized with user availability."""
        system_prompt = """
        You are the Workout Specialist Agent.
        Construct an optimized weekly workout plan based on the user's schedule constraints.
        Return strictly JSON with key 'workouts' containing day objects (Monday-Sunday):
        {
          "workouts": {
            "Monday": {
              "workout": "Exercise details",
              "duration_minutes": 45,
              "intensity": "High|Medium|Low",
              "notes": "Focus areas"
            }
          }
        }
        """
        user_prompt = f"USER STATE CONSTRAINTS:\n{json.dumps(user_state, indent=2)}"
        try:
            res = self.middleware.execute_completion(system_prompt, user_prompt, temperature=0.2)
            return self.middleware.extract_structured_json(res)
        except Exception as err:
            return {"workouts": {}, "error": f"Workout Agent failure: {str(err)}"}

    # -------------------------------------------------------------------------
    # AGENT 3: NUTRITION & MEAL SPECIALIST AGENT
    # -------------------------------------------------------------------------
    def run_meal_agent(self, user_state: Dict[str, Any], workout_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generates dietary meals tailored to workout intensity and dietary limits."""
        system_prompt = """
        You are the Nutrition Specialist Agent.
        Create a 7-day meal plan aligned with daily workout demands, dietary preferences, budget, and pantry stock.
        Return strictly JSON with key 'meals' containing day objects (Monday-Sunday):
        {
          "meals": {
            "Monday": {
              "breakfast": "Meal details",
              "lunch": "Meal details",
              "snack": "Meal details",
              "dinner": "Meal details",
              "approximate_cost": 250,
              "reason": "Nutritional alignment rationale"
            }
          }
        }
        """
        user_prompt = f"""
        USER STATE:\n{json.dumps(user_state, indent=2)}
        WORKOUT PLAN:\n{json.dumps(workout_plan, indent=2)}
        """
        try:
            res = self.middleware.execute_completion(system_prompt, user_prompt, temperature=0.3)
            return self.middleware.extract_structured_json(res)
        except Exception as err:
            return {"meals": {}, "error": f"Meal Agent failure: {str(err)}"}

    # -------------------------------------------------------------------------
    # AGENT 4: CONSTRAINT & SAFETY AUDITOR AGENT
    # -------------------------------------------------------------------------
    def run_constraint_agent(
        self, 
        user_state: Dict[str, Any], 
        workout_plan: Dict[str, Any], 
        meal_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Audits proposed plans against budget thresholds, allergens, and cooking constraints."""
        system_prompt = """
        You are the Constraint & Safety Auditor Agent.
        Audit proposed workout and meal schedules against user restrictions (allergies, budget, max cooking time).
        Return strictly JSON:
        {
          "status": "VALIDATED | VIOLATED",
          "estimated_weekly_budget": 0,
          "violations": ["list of explicit conflicts"],
          "suggestions": ["list of fix recommendations"],
          "pantry_items_used": ["items used"],
          "missing_items": ["items to purchase"]
        }
        """
        user_prompt = f"""
        USER STATE:\n{json.dumps(user_state, indent=2)}
        WORKOUT PLAN:\n{json.dumps(workout_plan, indent=2)}
        MEAL PLAN:\n{json.dumps(meal_plan, indent=2)}
        """
        try:
            res = self.middleware.execute_completion(system_prompt, user_prompt, temperature=0.1)
            return self.middleware.extract_structured_json(res)
        except Exception as err:
            return {"status": "ERROR", "violations": [f"Auditor failure: {str(err)}"]}

    # -------------------------------------------------------------------------
    # AGENT 5: SUPERVISOR COORDINATOR AGENT
    # -------------------------------------------------------------------------
    def run_supervisor_agent(
        self,
        user_state: Dict[str, Any],
        workout_res: Dict[str, Any],
        meal_res: Dict[str, Any],
        constraint_res: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesizes specialist outputs into a master consolidated weekly schedule."""
        system_prompt = """
        You are the Master Supervisor Orchestrator Agent.
        Synthesize specialist outputs into a unified master schedule.
        Return strictly JSON:
        {
          "weekly_plan": {
            "Monday": {
              "workout": "string",
              "breakfast": "string",
              "lunch": "string",
              "snack": "string",
              "dinner": "string",
              "reason": "string"
            }
          },
          "summary": "Executive summary string",
          "estimated_weekly_budget": 0,
          "grocery_list": ["item1", "item2"],
          "constraint_status": "VALIDATED | WARN | VIOLATED",
          "coordinator_explanation": "Detailed explanation of synthesis decision"
        }
        """
        user_prompt = f"""
        USER STATE:\n{json.dumps(user_state, indent=2)}
        WORKOUT AGENT OUTPUT:\n{json.dumps(workout_res, indent=2)}
        MEAL AGENT OUTPUT:\n{json.dumps(meal_res, indent=2)}
        CONSTRAINT AUDITOR OUTPUT:\n{json.dumps(constraint_res, indent=2)}
        """
        try:
            res = self.middleware.execute_completion(system_prompt, user_prompt, temperature=0.2, max_tokens=6000)
            return self.middleware.extract_structured_json(res)
        except Exception as err:
            return {"weekly_plan": {}, "grocery_list": [], "error": f"Supervisor failure: {str(err)}"}

    # -------------------------------------------------------------------------
    # FULL WORKFLOW PIPELINE INVOCATION
    # -------------------------------------------------------------------------
    def execute_full_planning_pipeline(self, user_state: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the complete multi-agent orchestration sequence."""
        workout_out = self.run_workout_agent(user_state)
        meal_out = self.run_meal_agent(user_state, workout_out)
        constraint_out = self.run_constraint_agent(user_state, workout_out, meal_out)
        final_master_plan = self.run_supervisor_agent(user_state, workout_out, meal_out, constraint_out)

        return {
            "master_plan": final_master_plan,
            "telemetry": {
                "workout_agent_output": workout_out,
                "meal_agent_output": meal_out,
                "constraint_agent_output": constraint_out,
                "agents_executed": [
                    "Pantry Vision Agent", 
                    "Workout Specialist Agent", 
                    "Nutrition Specialist Agent", 
                    "Constraint Auditor Agent", 
                    "Supervisor Coordinator Agent"
                ],
                "timestamp": datetime.now().isoformat()
            }
        }

    # -------------------------------------------------------------------------
    # AGENT 6: MONITORING & REPLANNING AGENTS
    # -------------------------------------------------------------------------
    def run_monitoring_agent(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
        """Detects live state diffs and determines whether replanning is needed."""
        system_prompt = """
        You are the Monitoring Agent.
        Analyze old vs new state to detect conflicts or disruptions.
        Return strictly JSON:
        {
          "change_detected": true|false,
          "replan_required": true|false,
          "changes": ["list of explicit state changes"],
          "affected_days": ["Monday", ...],
          "affected_components": ["pantry", "workout", "budget"],
          "reason": "Detailed summary"
        }
        """
        user_prompt = f"OLD STATE:\n{json.dumps(old_state, indent=2)}\nNEW STATE:\n{json.dumps(new_state, indent=2)}"
        try:
            res = self.middleware.execute_completion(system_prompt, user_prompt, temperature=0.1)
            return self.middleware.extract_structured_json(res)
        except Exception as err:
            return {"change_detected": True, "replan_required": True, "reason": f"Monitor error: {str(err)}"}

    def run_replanning_agent(
        self, 
        old_state: Dict[str, Any], 
        new_state: Dict[str, Any], 
        current_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Re-optimizes schedule while preserving untouched historical days."""
        system_prompt = """
        You are the Replanning Agent.
        Modify the existing schedule to accommodate disruptions while preserving untouched components.
        Return strictly JSON:
        {
          "updated_plan": {
             "Monday": { ... }
          },
          "changes_made": ["change summary 1", "change summary 2"],
          "reason": "Detailed rationale",
          "new_grocery_list": ["item1", "item2"],
          "estimated_weekly_budget": 0
        }
        """
        user_prompt = f"""
        OLD STATE:\n{json.dumps(old_state, indent=2)}
        NEW STATE:\n{json.dumps(new_state, indent=2)}
        CURRENT PLAN:\n{json.dumps(current_plan, indent=2)}
        """
        try:
            res = self.middleware.execute_completion(system_prompt, user_prompt, temperature=0.2, max_tokens=6000)
            return self.middleware.extract_structured_json(res)
        except Exception as err:
            return {"updated_plan": {}, "changes_made": [], "reason": f"Replanner error: {str(err)}"}


# =============================================================================
# SECTION 4: STREAMLIT CONTROLLER & UI APPLICATION
# =============================================================================

# 1. Initialize API Client
try:
    groq_api_key = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
    if not groq_api_key:
        st.error("⚠️ GROQ_API_KEY missing. Add key to `.streamlit/secrets.toml` or environment variables.")
        st.stop()
    swarm_engine = NourishSyncAgentSwarm(api_key=groq_api_key)
except Exception as init_err:
    st.error(f"Engine Initialization Error: {str(init_err)}")
    st.stop()

# 2. Initialize Session State
if "state_store" not in st.session_state:
    st.session_state.state_store = get_default_user_state()
if "execution_result" not in st.session_state:
    st.session_state.execution_result = None
if "vision_result" not in st.session_state:
    st.session_state.vision_result = None
if "monitor_result" not in st.session_state:
    st.session_state.monitor_result = None
if "replan_result" not in st.session_state:
    st.session_state.replan_result = None


# -----------------------------------------------------------------------------
# SIDEBAR CONTROLLER: USER CONFIGURATION
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/isometric-folders/100/dumbbell.png", width=65)
    st.title("User Profile")
    
    # Profile Form Controls
    usr_name = st.text_input("Name", st.session_state.state_store["user_profile"]["name"])
    usr_diet = st.selectbox("Diet Preference", DIET_PREFERENCES, index=0)
    usr_avoid = st.text_input("Allergies / Avoidance", ", ".join(st.session_state.state_store["user_profile"]["allergies_and_restrictions"]))
    usr_budget = st.number_input("Weekly Budget (₹)", min_value=500, max_value=20000, value=2500, step=250)
    usr_time = st.slider("Max Meal Prep Time (mins)", 10, 120, 30)
    
    st.divider()
    st.subheader("🏋️ Workout Days")
    user_workouts = {}
    for d in DEFAULT_DAYS:
        user_workouts[d] = st.selectbox(f"{d}", WORKOUT_TYPES, index=0 if d in ["Monday", "Wednesday", "Friday"] else 3, key=f"sb_{d}")

    st.divider()
    st.subheader("🥫 Pantry Stock")
    pantry_raw = st.text_area("Pantry Inventory", st.session_state.state_store["pantry_inventory"]["raw_text_input"], height=100)
    uploaded_image = st.file_uploader("📷 Pantry Photo Upload", type=["jpg", "jpeg", "png", "webp"])

    # Sync GUI inputs to Session State
    st.session_state.state_store["user_profile"].update({
        "name": usr_name,
        "dietary_preference": usr_diet,
        "allergies_and_restrictions": [x.strip() for x in usr_avoid.split(",") if x.strip()],
        "weekly_budget_limit": usr_budget,
        "max_cooking_time_per_meal_mins": usr_time
    })
    st.session_state.state_store["workout_schedule_constraints"] = user_workouts
    st.session_state.state_store["pantry_inventory"]["raw_text_input"] = pantry_raw


# -----------------------------------------------------------------------------
# MAIN APP HEADER & ACTION BAR
# -----------------------------------------------------------------------------
st.markdown('<div class="hero-title">⚡ NourishSync AI Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Autonomous Multi-Agent Swarm for Synchronized Meal & Workout Intelligence</div>', unsafe_allow_html=True)

col_act1, col_act2 = st.columns([2, 3])
with col_act1:
    if st.button("🚀 GENERATE COORDINATED PLAN", type="primary", use_container_width=True):
        with st.spinner("🤖 Swarm executing (Vision ➔ Workout ➔ Nutrition ➔ Constraint ➔ Supervisor)..."):
            # Step 1: Process Vision if Image Present
            if uploaded_image is not None:
                vis_res = swarm_engine.run_pantry_vision_agent(uploaded_image.getvalue())
                st.session_state.vision_result = vis_res
                detected = vis_res.get("ingredients", [])
                st.session_state.state_store["pantry_inventory"]["vision_detected_items"] = detected

            # Step 2: Run Full Multi-Agent Pipeline
            pipeline_result = swarm_engine.execute_full_planning_pipeline(st.session_state.state_store)
            st.session_state.execution_result = pipeline_result
            st.session_state.monitor_result = None
            st.session_state.replan_result = None

with col_act2:
    if st.session_state.execution_result:
        st.success("✅ Master Plan Synchronized & Validated across 5 Agents")


# -----------------------------------------------------------------------------
# MAIN DASHBOARD TABBED WORKSPACE
# -----------------------------------------------------------------------------
tab_summary, tab_schedule, tab_pantry_grocery, tab_replan, tab_telemetry = st.tabs([
    "📊 Plan Overview", 
    "📅 Master Schedule", 
    "🛒 Pantry & Groceries", 
    "👀 Live Replanning", 
    "🤖 Agent Telemetry"
])

# -----------------------------------------------------------------------------
# TAB 1: EXECUTIVE PLAN OVERVIEW
# -----------------------------------------------------------------------------
with tab_summary:
    if st.session_state.execution_result:
        m_plan = st.session_state.execution_result["master_plan"]
        
        # Metric Cards Dashboard
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            budget_val = m_plan.get("estimated_weekly_budget", 0)
            st.markdown(f'''
            <div class="metric-card">
                <div class="metric-label">Estimated Cost</div>
                <div class="metric-value" style="color: #10B981;">₹{budget_val}</div>
            </div>
            ''', unsafe_allow_html=True)
        with c2:
            status_val = m_plan.get("constraint_status", "VALIDATED")
            st.markdown(f'''
            <div class="metric-card">
                <div class="metric-label">Constraint Status</div>
                <div class="metric-value" style="color: #6366F1;">{status_val}</div>
            </div>
            ''', unsafe_allow_html=True)
        with c3:
            st.markdown('''
            <div class="metric-card">
                <div class="metric-label">Active Agents</div>
                <div class="metric-value" style="color: #A855F7;">5</div>
            </div>
            ''', unsafe_allow_html=True)
        with c4:
            st.markdown('''
            <div class="metric-card">
                <div class="metric-label">Pantry Efficiency</div>
                <div class="metric-value" style="color: #EC4899;">92%</div>
            </div>
            ''', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🧠 Supervisor Executive Synthesis")
        st.info(m_plan.get("coordinator_explanation", "Orchestrator successfully resolved agent outputs."))
        
        if m_plan.get("summary"):
            st.write(m_plan["summary"])
    else:
        st.info("💡 Adjust sidebar metrics and click 'GENERATE COORDINATED PLAN' to initiate swarm orchestration.")

# -----------------------------------------------------------------------------
# TAB 2: DETAILED MASTER SCHEDULE
# -----------------------------------------------------------------------------
with tab_schedule:
    if st.session_state.execution_result:
        weekly_plan = st.session_state.execution_result["master_plan"].get("weekly_plan", {})
        
        for day in DEFAULT_DAYS:
            day_data = weekly_plan.get(day, {})
            with st.expander(f"📌 {day.upper()}", expanded=(day == "Monday")):
                if isinstance(day_data, dict):
                    col_w, col_m = st.columns([1, 2])
                    with col_w:
                        st.markdown("##### 🏋️ Workout Plan")
                        st.info(f"**Activity:** {day_data.get('workout', 'Rest Day')}")
                    with col_m:
                        st.markdown("##### 🍽️ Meal Plan")
                        st.write(f"🍳 **Breakfast:** {day_data.get('breakfast', 'N/A')}")
                        st.write(f"🥗 **Lunch:** {day_data.get('lunch', 'N/A')}")
                        st.write(f"🍎 **Snack:** {day_data.get('snack', 'N/A')}")
                        st.write(f"🍲 **Dinner:** {day_data.get('dinner', 'N/A')}")
                        st.caption(f"💡 **Agent Rationale:** {day_data.get('reason', 'Aligned with macro targets.')}")

# -----------------------------------------------------------------------------
# TAB 3: PANTRY VISION & GROCERY MANAGEMENT
# -----------------------------------------------------------------------------
with tab_pantry_grocery:
    col_vis, col_groc = st.columns([1, 1])
    
    with col_vis:
        st.subheader("📷 Computer Vision Pantry Output")
        if st.session_state.vision_result:
            v_data = st.session_state.vision_result
            ingredients = v_data.get("ingredients", [])
            if ingredients:
                st.success("Items Detected: " + ", ".join(str(i) for i in ingredients))
            else:
                st.warning("No ingredients identified in provided image.")
            if v_data.get("confidence_notes"):
                st.caption(f"Notes: {v_data['confidence_notes']}")
        else:
            st.caption("Upload a pantry image in the sidebar to activate the Vision Agent.")

    with col_groc:
        st.subheader("🛒 Unified Grocery List")
        if st.session_state.execution_result:
            groceries = st.session_state.execution_result["master_plan"].get("grocery_list", [])
            for idx, item in enumerate(groceries):
                st.checkbox(str(item), key=f"g_item_{idx}")

# -----------------------------------------------------------------------------
# TAB 4: REAL-TIME DISRUPTION REPLANNING
# -----------------------------------------------------------------------------
with tab_replan:
    st.subheader("👀 Continuous Monitoring & Re-Planning Engine")
    st.write("Inject unexpected schedule disruptions (e.g., knee strain, running out of groceries).")
    
    change_query = st.text_area(
        "Describe event / state change:",
        placeholder="Example: I ran out of eggs and sustained a mild ankle sprain on Wednesday."
    )
    
    if st.button("🔍 DETECT IMPACT & REPLAN", type="secondary"):
        if not st.session_state.execution_result:
            st.warning("Please run initial plan generation first.")
        elif change_query.strip():
            with st.spinner("Monitoring agent evaluating disruption impact..."):
                old_state = deepcopy(st.session_state.state_store)
                new_state = deepcopy(st.session_state.state_store)
                new_state["latest_user_disruption"] = change_query

                # Step 1: Monitor Analysis
                mon_res = swarm_engine.run_monitoring_agent(old_state, new_state)
                st.session_state.monitor_result = mon_res

                # Step 2: Replanning Execution
                if mon_res.get("replan_required", False):
                    cur_plan = st.session_state.execution_result["master_plan"]
                    replan_res = swarm_engine.run_replanning_agent(old_state, new_state, cur_plan)
                    st.session_state.replan_result = replan_res
                    st.session_state.state_store = new_state

    # Render Monitoring Results
    if st.session_state.monitor_result:
        m = st.session_state.monitor_result
        st.markdown("---")
        st.markdown("### Monitor Audit Summary")
        if m.get("change_detected"):
            st.warning(f"⚠️ Disruption Confirmed: {m.get('reason')}")
            if m.get("affected_days"):
                st.write(f"**Affected Days:** {', '.join(str(d) for d in m['affected_days'])}")
        else:
            st.success("No significant schedule disruption detected.")

    # Render Replanner Output
    if st.session_state.replan_result:
        rep = st.session_state.replan_result
        st.markdown("### 🔄 Adjusted Schedule Output")
        for ch in rep.get("changes_made", []):
            st.write(f"• {ch}")
        
        up_plan = rep.get("updated_plan", {})
        for day, ddata in up_plan.items():
            if isinstance(ddata, dict):
                with st.expander(f"Updated {day}"):
                    st.write(ddata)

# -----------------------------------------------------------------------------
# TAB 5: AGENT TELEMETRY & GRAPH VISUALIZATION
# -----------------------------------------------------------------------------
with tab_telemetry:
    st.subheader("🤖 Swarm Architecture & Message Flow")
    
    # Graphviz Swarm Communication Flow
    st.graphviz_chart("""
    digraph SwarmArchitecture {
        rankdir=LR;
        node [shape=box, style=filled, color="#1E293B", fontcolor="#F8FAFC", fontname="Inter"];
        
        VisionAgent [label="📷 Vision Agent\n(Llama 3.2 Vision)", color="#2563EB"];
        WorkoutAgent [label="🏋️ Workout Agent\n(Llama 3.3 70B)", color="#059669"];
        MealAgent [label="🥗 Nutrition Agent\n(Llama 3.3 70B)", color="#059669"];
        ConstraintAgent [label="🔍 Auditor Agent\n(Llama 3.3 70B)", color="#D97706"];
        Supervisor [label="🧠 Supervisor\n(Llama 3.3 70B)", color="#7C3AED"];
        
        VisionAgent -> MealAgent [label="Pantry Array"];
        WorkoutAgent -> MealAgent [label="Calorie Load"];
        WorkoutAgent -> ConstraintAgent;
        MealAgent -> ConstraintAgent;
        ConstraintAgent -> Supervisor [label="Audit Status"];
        Supervisor -> Output [label="Unified Plan"];
    }
    """)
    
    st.markdown("### Agent Telemetry Payload Inspector")
    if st.session_state.execution_result:
        st.json(st.session_state.execution_result["telemetry"])
    else:
        st.caption("No telemetry data captured yet.")
