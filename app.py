import streamlit as st
import pandas as pd
from google import genai
from PIL import Image

# 1. Page Config & API Setup
st.set_page_config(page_title="Fitness Dashboard & Assistant", layout="wide")
st.title("🏋️‍♂️ Workout Analyst & Live Gym Assistant")

# Initialize modern GenAI Client
api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)
MODEL_ID = 'gemini-1.5-flash'

# Session State Initialization
if 'extracted_scale_metrics' not in st.session_state:
    st.session_state.extracted_scale_metrics = None
if 'extracted_sleep_metrics' not in st.session_state:
    st.session_state.extracted_sleep_metrics = None
if 'todays_workout' not in st.session_state:
    st.session_state.todays_workout = ""
if 'workout_logs' not in st.session_state:
    st.session_state.workout_logs = []

# Sidebar Data Inputs
st.sidebar.header("📸 Log Metrics via Screenshots")

# Smart Scale Section
st.sidebar.subheader("1. Smart Scale Data")
scale_file = st.sidebar.file_uploader("Upload Scale Screenshot", type=["png", "jpg", "jpeg"], key="scale_upload")
if scale_file is not None:
    scale_image = Image.open(scale_file)
    if st.sidebar.button("Process Scale Screenshot"):
        with st.spinner("Extracting body composition..."):
            scale_prompt = (
                "Extract all smart scale metrics (Weight, Body Fat %, Muscle Mass, Visceral Fat, BMR, etc.) "
                "as a bulleted list of key-value pairs."
            )
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[scale_prompt, scale_image]
            )
            st.session_state.extracted_scale_metrics = response.text
            st.sidebar.success("Scale Data Logged!")

# Sleep Tracker Section
st.sidebar.subheader("2. Sleep Tracker Data")
sleep_file = st.sidebar.file_uploader("Upload Sleep Screenshot", type=["png", "jpg", "jpeg"], key="sleep_upload")
if sleep_file is not None:
    sleep_image = Image.open(sleep_file)
    if st.sidebar.button("Process Sleep Screenshot"):
        with st.spinner("Extracting sleep performance..."):
            sleep_prompt = (
                "Extract sleep metrics (Total Sleep Duration, Sleep Score, Quality Rating, Deep Sleep, etc.) "
                "from this screenshot as a bulleted list."
            )
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[sleep_prompt, sleep_image]
            )
            st.session_state.extracted_sleep_metrics = response.text
            st.sidebar.success("Sleep Data Logged!")

# Main Tabs Setup
tab1, tab2 = st.tabs(["📊 Workout Analyst", "🏋️ Live Workout Assistant"])

# --- TAB 1: WORKOUT ANALYST ---
with tab1:
    st.header("Program Continuity & Planning")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Target Weight", "70.0 kg")
    col2.metric("Target Body Fat", "15 - 18%")
    col3.metric("Milestone 1 Deadline", "Late Nov 2026")
    
    if st.button("Generate Today's Workout"):
        with st.spinner("Analyzing recovery & prescribing workout..."):
            body_data = st.session_state.extracted_scale_metrics or "No new scale data."
            sleep_data = st.session_state.extracted_sleep_metrics or "No new sleep data."
            
            prompt_text = (
                "Act as my Workout Analyst. "
                f"Latest Scale Data: {body_data}. "
                f"Latest Sleep Data: {sleep_data}. "
                "Generate Today's Workout following the A/B/C full-body split progression. "
                "Provide ONLY the raw Workout prescription with Warm-up, Exercises, Sets, Reps, RIR, Rest periods, and Cooldown. "
                "Do not include conversational greetings or setup intros."
            )
            
            # Explicit list payload structure prevents ClientError on generate_content
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[prompt_text]
            )
            st.session_state.todays_workout = response.text
            st.success("Today's Workout Generated! Switch to the Live Assistant tab to execute.")
            
    if st.session_state.todays_workout:
        st.subheader("Prescribed Routine")
        st.code(st.session_state.todays_workout, language="text")

# --- TAB 2: LIVE WORKOUT ASSISTANT ---
with tab2:
    st.header("Gym Execution & Dynamic Logging")
    
    if not st.session_state.todays_workout:
        st.info("Please generate Today's Workout in the Workout Analyst tab first!")
    else:
        st.markdown("### 📋 Current Session Plan")
        st.text(st.session_state.todays_workout)
        
        st.markdown("---")
        st.subheader("📝 Quick Log Set Execution")
        
        with st.form("set_logger"):
            ex_name = st.text_input("Exercise Name", placeholder="e.g., Flat Dumbbell Bench Press")
            col_weight, col_reps, col_rir = st.columns(3)
            actual_weight = col_weight.number_input("Weight Used (kg)", value=0.0, step=0.5)
            actual_reps = col_reps.number_input("Reps Completed", value=0, step=1)
            actual_rir = col_rir.number_input("RIR Left", value=2, step=1)
            notes = st.text_input("Execution Notes", placeholder="e.g., Good speed, form intact")
            
            submitted = st.form_submit_button("Log Completed Set")
            if submitted and ex_name:
                st.session_state.workout_logs.append({
                    "Exercise": ex_name,
                    "Weight (kg)": actual_weight,
                    "Reps": actual_reps,
                    "RIR": actual_rir,
                    "Notes": notes
                })
                st.success(f"Logged: {ex_name} - {actual_weight}kg x {actual_reps} reps")
        
        # Display Live Session Log
        if st.session_state.workout_logs:
            st.subheader("Session Progress")
            df_logs = pd.DataFrame(st.session_state.workout_logs)
            st.table(df_logs)
            
            if st.button("Finish Workout & Generate Execution Report"):
                report_text = (
                    "Act as the Workout Assistant. Generate a clean Workout Execution Report based on these actual set logs: "
                    f"{df_logs.to_string(index=False)}. "
                    "Format as a clear summary code block with Prescribed vs. Actual performance and completion status."
                )
                report_response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=[report_text]
                )
                st.markdown("### 🏆 Completed Workout Report")
                st.code(report_response.text, language="text")
