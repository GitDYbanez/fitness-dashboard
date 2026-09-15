import streamlit as st
import pandas as pd
import datetime
import time
from google import genai
from PIL import Image

# 1. Page Config & API Setup
st.set_page_config(page_title="Fitness Dashboard & Assistant", layout="wide")
st.title("🏋️‍♂️ Workout Analyst & Live Gym Assistant")

API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)
MODEL_ID = 'gemini-1.5-flash'

# Date Calculation (Tomorrow is Sep 16, 2026)
tomorrow_date = datetime.date(2026, 9, 16)

# Session State Initialization
if 'extracted_scale_metrics' not in st.session_state:
    st.session_state.extracted_scale_metrics = None
if 'extracted_sleep_metrics' not in st.session_state:
    st.session_state.extracted_sleep_metrics = None
if 'todays_workout' not in st.session_state:
    st.session_state.todays_workout = ""
if 'workout_logs' not in st.session_state:
    st.session_state.workout_logs = []
if 'workout_started' not in st.session_state:
    st.session_state.workout_started = False
if 'workout_start_time' not in st.session_state:
    st.session_state.workout_start_time = None
if 'current_ex_index' not in st.session_state:
    st.session_state.current_ex_index = 0
if 'current_set_num' not in st.session_state:
    st.session_state.current_set_num = 1

# Pre-defined structured exercises for Workout B (Sep 16, 2026) for streamlined logging
WORKOUT_B_STRUCTURE = [
    {"exercise": "45° Leg Press", "sets": 3, "target_reps": "10–12", "target_rir": 3},
    {"exercise": "Flat Dumbbell Bench Press", "sets": 3, "target_reps": "8–10", "target_rir": 3},
    {"exercise": "Chest-Supported Row", "sets": 3, "target_reps": "10–12", "target_rir": 3},
    {"exercise": "Smith-Machine Romanian Deadlift", "sets": 3, "target_reps": "10–12", "target_rir": 3},
    {"exercise": "Leg Extension", "sets": 2, "target_reps": "12–15", "target_rir": 3},
    {"exercise": "Reverse Pec Deck / Rear-Delt Machine", "sets": 3, "target_reps": "12–15", "target_rir": 3},
    {"exercise": "Single-Arm Cable Lateral Raise", "sets": 3, "target_reps": "12–15/side", "target_rir": 3},
    {"exercise": "Cable Biceps Curl", "sets": 2, "target_reps": "10–12", "target_rir": 3},
    {"exercise": "Cable Triceps Pressdown", "sets": 2, "target_reps": "10–12", "target_rir": 3},
    {"exercise": "Reverse Crunch", "sets": 2, "target_reps": "12–15", "target_rir": 3}
]

# Sidebar Data Inputs
st.sidebar.header("📸 Log Metrics via Screenshots")

scale_file = st.sidebar.file_uploader("Upload Scale Screenshot", type=["png", "jpg", "jpeg"], key="scale_upload")
if scale_file is not None:
    scale_image = Image.open(scale_file)
    if st.sidebar.button("Process Scale Screenshot"):
        with st.spinner("Extracting body composition..."):
            resp = client.models.generate_content(model=MODEL_ID, contents=["Extract scale metrics as key-value pairs.", scale_image])
            st.session_state.extracted_scale_metrics = resp.text
            st.sidebar.success("Scale Data Logged!")

sleep_file = st.sidebar.file_uploader("Upload Sleep Screenshot", type=["png", "jpg", "jpeg"], key="sleep_upload")
if sleep_file is not None:
    sleep_image = Image.open(sleep_file)
    if st.sidebar.button("Process Sleep Screenshot"):
        with st.spinner("Extracting sleep performance..."):
            resp = client.models.generate_content(model=MODEL_ID, contents=["Extract sleep metrics as bullet points.", sleep_image])
            st.session_state.extracted_sleep_metrics = resp.text
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
    
    # 1. Display Current User State Panel
    with st.expander("👤 View Master Current User State & Baselines", expanded=False):
        st.markdown("""
        * **Profile & Goals:** Male, 38 years old, 175 cm, 75.50 kg. Target: ~70 kg / ~20–22% BF (Milestone 1 by late Nov/Dec 2026). Secondary focus: Lateral delts.
        * **Current Program:** Default A/B/C Full-Body Split (Scheduled: **Workout B** for Sep 16, 2026).
        * **Key Equipment Adaptations:** Using 45° Leg Press and Smith-Machine RDL to bypass goblet squat and dumbbell forearm/grip bottlenecks.
        * **Conditioning:** Tue/Thu jog/walk intervals (2 min jog / 1 min walk).
        * **Supplements:** Whey Protein, Creatine, Fish Oil, Magnesium Glycinate, Wheyl Hydra electrolytes.
        """)
    
    st.markdown(f"**Target Date Detected:** `{tomorrow_date.strftime('%A, %B %d, %Y')}` (Automatically prescribes **Workout B**).")
    
    if st.button("Generate Today's Workout"):
        with st.spinner("Analyzing recovery & prescribing Workout B..."):
            body_data = st.session_state.extracted_scale_metrics or "Weight: 75.50 kg, BF: 27.1%"
            sleep_data = st.session_state.extracted_sleep_metrics or "Sleep: 9h 40m, Score: 71"
            
            prompt_text = f"""
            Act as my Workout Analyst. 
            Target Date: {tomorrow_date.strftime('%Y-%m-%d')} ({tomorrow_date.strftime('%A')}).
            Latest Scale Data: {body_data}
            Latest Sleep Data: {sleep_data}
            Based on the rotation and date, prescribe Workout B.
            Provide a complete workout structure with Warm-up, Exercises, Sets, Reps, RIR, Rest periods, and Cooldown.
            """
            response = client.models.generate_content(model=MODEL_ID, contents=[prompt_text])
            st.session_state.todays_workout = response.text
            st.success("Workout B Generated Successfully! Switch to the Live Assistant tab to execute.")
            
    if st.session_state.todays_workout:
        st.subheader("Prescribed Routine")
        st.code(st.session_state.todays_workout, language="text")

# --- TAB 2: LIVE WORKOUT ASSISTANT ---
with tab2:
    st.header("Gym Execution & Dynamic Logging")
    
    if not st.session_state.todays_workout:
        st.info("Please generate Today's Workout in the Workout Analyst tab first!")
    else:
        # 4. Workout Start & Stopwatch Timer
        col_timer1, col_timer2 = st.columns([1, 3])
        if not st.session_state.workout_started:
            if col_timer1.button("🚀 Start Workout"):
                st.session_state.workout_started = True
                st.session_state.workout_start_time = time.time()
                st.rerun()
        else:
            elapsed_seconds = int(time.time() - st.session_state.workout_start_time)
            mins, secs = divmod(elapsed_seconds, 60)
            col_timer1.markdown(f"⏱️ **Session Time:** `{mins:02d}:{secs:02d}`")
            if col_timer2.button("🛑 Finish Session"):
                st.session_state.workout_started = False

        st.markdown("---")
        
        # 3. Streamlined Active Set Logger (No manual exercise typing required)
        if st.session_state.current_ex_index < len(WORKOUT_B_STRUCTURE):
            current_item = WORKOUT_B_STRUCTURE[st.session_state.current_ex_index]
            ex_name = current_item["exercise"]
            total_sets = current_item["sets"]
            target_reps = current_item["target_reps"]
            target_rir = current_item["target_rir"]
            
            st.markdown(f"### 🔥 Current Exercise: **{ex_name}**")
            st.info(f"**Set {st.session_state.current_set_num} of {total_sets}** | Target: {target_reps} reps @ RIR {target_rir}")
            
            with st.form("streamlined_logger"):
                c1, c2, c3 = st.columns(3)
                act_weight = c1.number_input("Weight Used (kg)", value=0.0, step=0.5)
                act_reps = c2.number_input("Reps Completed", value=0, step=1)
                act_rir = c3.number_input("RIR Left", value=target_rir, step=1)
                act_notes = st.text_input("Execution Notes (optional)", placeholder="e.g., Good form, smooth lockout")
                
                submitted = st.form_submit_button("✅ Log Set & Next")
                if submitted:
                    st.session_state.workout_logs.append({
                        "Exercise": ex_name,
                        "Set": st.session_state.current_set_num,
                        "Weight (kg)": act_weight,
                        "Reps": act_reps,
                        "RIR": act_rir,
                        "Notes": act_notes
                    })
                    
                    # Advance set or exercise automatically
                    if st.session_state.current_set_num < total_sets:
                        st.session_state.current_set_num += 1
                    else:
                        st.session_state.current_ex_index += 1
                        st.session_state.current_set_num = 1
                    st.rerun()
        else:
            st.success("🎉 All prescribed sets completed for today's session!")

        # Display Live Session Log Table
        if st.session_state.workout_logs:
            st.subheader("📋 Session Progress Log")
            df_logs = pd.DataFrame(st.session_state.workout_logs)
            st.table(df_logs)
            
            if st.button("Generate Final Workout Execution Report"):
                report_prompt = f"""
                Act as the Workout Assistant. Generate a clean Workout Execution Report based on these actual set logs:
                {df_logs.to_string(index=False)}
                Format inside ONE clean monospaced code block ready to copy back to the Analyst.
                """
                report_resp = client.models.generate_content(model=MODEL_ID, contents=[report_prompt])
                st.markdown("### 🏆 Final Workout Report")
                st.code(report_resp.text, language="text")
