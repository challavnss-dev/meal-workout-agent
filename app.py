import streamlit as st

st.set_page_config(
    page_title="FitFuel AI",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
.main .block-container {
    max-width: 1250px;
    padding-top: 2rem;
}

.hero {
    padding: 35px;
    border-radius: 20px;
    background: linear-gradient(
        135deg,
        rgba(16,185,129,.15),
        rgba(99,102,241,.15)
    );
    margin-bottom: 30px;
}

.hero h1 {
    font-size: 42px;
    font-weight: 800;
}

.card {
    padding: 25px;
    border-radius: 18px;
    border: 1px solid rgba(255,255,255,.1);
    background: rgba(255,255,255,.03);
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="hero">
    <h1>⚡ FitFuel AI</h1>
    <p>
        Real-world pantry-aware meal and workout coordination system
    </p>
</div>
""", unsafe_allow_html=True)


st.markdown("""
<div class="card">
<h2>Welcome 👋</h2>

<p>
FitFuel AI creates a meal and workout plan using the foods that are
actually available in your pantry.
</p>

<p>
The application also uses separate specialist agents for meal planning,
workout planning, portion control, constraint checking and replanning.
</p>
</div>
""", unsafe_allow_html=True)


col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 👤 Profile")
    st.write("Set your food role and personal preferences.")

    if st.button("Open Profile →", use_container_width=True):
        st.switch_page("pages/1_Profile.py")


with col2:
    st.markdown("### 🥫 Pantry")
    st.write("Enter the foods currently available at home.")

    if st.button("Open Pantry →", use_container_width=True):
        st.switch_page("pages/2_Pantry.py")


with col3:
    st.markdown("### 🏋️ Workout")
    st.write("Configure your workout for every day.")

    if st.button("Open Workout →", use_container_width=True):
        st.switch_page("pages/3_Workout.py")


st.divider()

st.markdown("## 🚀 Start Planning")

if st.button(
    "Generate My Meal & Workout Plan →",
    type="primary",
    use_container_width=True
):
    st.switch_page("pages/4_Daily_Plan.py")
