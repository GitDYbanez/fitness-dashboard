import streamlit as st
import pandas as pd
import requests
import base64
import io
import datetime
import time
import re
from PIL import Image

# 1. Page Config & API Setup
st.set_page_config(page_title="Fitness Dashboard & Assistant", layout="wide")
st.title("🏋️‍♂️ Workout Analyst & Live Gym Assistant")

API_KEY = st.secrets["GEMINI_API_KEY"]
MODEL_ID = "gemini-3.6-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={API_KEY}"

# Date Calculation (Tomorrow is Sep 16, 2026)
tomorrow_date = datetime.date(2026, 9, 16)

# Session State Initialization & Rotation Tracking
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

# Track Rotation State (Default last completed: A, so next is B)
if 'last_completed_workout' not in st.session_state:
    st.session_state.last_completed_workout = "A"
if 'active_workout_letter' not in st.session_state:
    st.session_state.active_workout_letter = "B"

# Helper Function to Dynamically Parse Exercises from Analyst Text Output
def parse_exercises_from_text(workout_text):
    exercises = []
    lines = workout_text.split('\n')
    for line in lines:
        # Matches lines like "1. 45° Leg Press — 3 sets × 10–12 reps..." or similar patterns
        match = re.match(r'^\s*(\d+)\.\s+(.*?)\s+[—–-]\s+(\d+)\s+sets?', line, re.IGNORECASE)
        if match:
            ex_name = match.group(2).strip()
            sets = int(match.group(3))
            
            # Extract rep range if present
            rep_match = re.search(r'(\d+(?:[–-]\d+)?)\s+reps?', line, re.IGNORECASE)
            target_reps = rep_match.group(1) if rep_match else "10"
            
            exercises.append({
                "exercise": ex_name,
                "sets": sets,
                "target_reps": target_reps,
                "target_rir": 3
            })
            
    # Fallback default if parsing finds nothing (e.g. custom format)
    if not exercises:
        exercises = [{"exercise": "General Working Exercise", "sets": 3, "target_reps": "10", "target_rir": 3}]
        
    return exercises

# REST API Helper
def generate_content(prompt, image=None):
    parts = [{"text": prompt}]
    if image:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_str}})
    
    payload = {"contents": [{"parts": parts}]}
    response = requests.post(API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    
    if response.status_code == 200:
        try:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            return f"API Parsing Error: {str(e)} \n\n {response.text}"
    else:
        return f"🚨 GOOGLE API REJECTION ({response.status_code}): {response.text}"

# Sidebar Data Inputs
st.sidebar.header("📸 Log Metrics via Screenshots")

scale_file = st.sidebar.file_uploader("Upload Scale Screenshot", type=["png", "jpg", "jpeg"], key="scale_upload")
if scale_file is not None:
    scale_image = Image.open(scale_file)
    if st.sidebar.button("Process Scale Screenshot"):
        with st.spinner("Extracting body composition..."):
            resp = generate_content("Extract scale metrics as key-value pairs.", scale_image)
            st.session_state.extracted_scale_metrics = resp
            st.sidebar.success("Scale Data Logged!")

sleep_file = st.sidebar.file_uploader("Upload Sleep Screenshot", type=["png", "jpg", "jpeg"], key="sleep_upload")
if sleep_file is not None:
    sleep_image = Image.open(sleep_file)
    if st.sidebar.button("Process Sleep Screenshot"):
        with st.spinner("Extracting sleep performance..."):
            resp = generate_content("Extract sleep metrics as bullet points.", sleep_image)
            st.session_state.extracted_sleep_metrics = resp
            st.sidebar.success("Scale Data Logged!")

# Main Tabs Setup
tab1, tab2 = st.tabs(["📊 Workout Analyst", "🏋️ Live Workout Assistant"])

# --- TAB 1: WORKOUT ANALYST ---
with tab1:
    st.header("Program Continuity & Planning")
    
    # Side-by-Side Clean Metrics Layout
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Current Weight", "75.50 kg")
    m2.metric("Target Weight", "70.0 kg", "-5.5 kg")
    m3.metric("Current Body Fat", "27.1%")
    m4.metric("Target Body Fat", "15–18%")
    m5.metric("Milestone 1", "Late Nov 2026")
    
    st.markdown("---")

    # Cleaned-Up Readable User State Panel
    with st.expander("👤 View Master Current User State & Baselines", expanded=False):
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            st.markdown("### 📋 Profile & Goals")
            st.markdown("""
            * **Age / Sex:** 38 years old, Male
            * **Height:** 175 cm
            * **Primary Goal:** Fat loss (abdominal / love handles)
            * **Secondary Goal:** Lateral delt development
            * **Milestone 1 Target:** ~70 kg / ~20–22% BF
            """)
            
            st.markdown("### 💤 Recovery & Conditioning")
            st.markdown("""
            * **Conditioning:** Tue/Thu jog/walk (2m jog / 1m walk)
            * **Recent Sleep:** 9h 40m (Score: 71)
            """)
        
        with col_u2:
            st.markdown("### 🏋️ Training & Equipment")
            st.markdown("""
            * **Structure:** A/B/C Full-Body Rotation
            * **Intensity Target:** ~2–3 RIR
            * **Key Adaptations:** 45° Leg Press & Smith-Machine RDL used to bypass grip bottlenecks.
            """)
            
            st.markdown("### 💊 Supplements")
            st.markdown("""
            * Whey Protein, Creatine, Fish Oil, Magnesium Glycinate, Wheyl Hydra electrolytes.
            """)

    st.markdown("---")

    # Rotation Status & Manual Override Control
    col_rot1, col_rot2 = st.columns(2)
    with col_rot1:
        next_letter = {"A": "B", "B": "C", "C": "A"}[st.session_state.last_completed_workout]
        st.markdown(f"🔄 **Last Completed:** Workout {st.session_state.last_completed_workout} → **Scheduled Next:** Workout **{next_letter}**")
    with col_rot2:
        override_choice = st.selectbox("Override Workout Letter if Needed:", ["A", "B", "C"], index=["A", "B", "C"].index(next_letter))
        st.session_state.active_workout_letter = override_choice

    if st.button("Generate Today's Workout", type="primary"):
        with st.spinner(f"Analyzing recovery & prescribing Workout {st.session_state.active_workout_letter}..."):
            body_data = st.session_state.extracted_scale_metrics or "Weight: 75.50 kg, BF: 27.1%"
            sleep_data = st.session_state.extracted_sleep_metrics or "Sleep: 9h 40m, Score: 71"
            
            prompt_text = f"""Act as my Workout Analyst. 
Target Date: {tomorrow_date.strftime('%Y-%m-%d')} ({tomorrow_date.strftime('%A')}). 
Last completed workout in rotation: Workout {st.session_state.last_completed_workout}. 
Prescribing: Workout {st.session_state.active_workout_letter}. 
Latest Scale Data: {body_data}. 
Latest Sleep Data: {sleep_data}. 
Provide a complete workout structure with Warm-up, Exercises, Sets, Reps, RIR, Rest periods, and Cooldown."""
            
            response_text = generate_content(prompt_text)
            if "🚨 GOOGLE API REJECTION" in response_text:
                st.error(response_text)
            else:
                st.session_state.todays_workout = response_text
                # Reset logger index when a new workout is generated
                st.session_state.current_ex_index = 0
                st.session_state.current_set_num = 1
                st.success(f"Workout {st.session_state.active_workout_letter} Generated Successfully! Switch to the Live Assistant tab to execute.")
            
    if st.session_state.todays_workout:
        st.subheader("Prescribed Routine")
        st.code(st.session_state.todays_workout, language="text")

# --- TAB 2: LIVE WORKOUT ASSISTANT ---
with tab2:
    st.header("Gym Execution & Dynamic Logging")
    
    if not st.session_state.todays_workout:
        st.info("Please generate Today's Workout in the Workout Analyst tab first!")
    else:
        # Workout Stopwatch / Timer
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
                st.session_state.last_completed_workout = st.session_state.active_workout_letter

        st.markdown("---")
        
        # Dynamically parse exercises directly from the Analyst's generated workout text
        active_structure = parse_exercises_from_text(st.session_state.todays_workout)
        
        if st.session_state.current_ex_index < len(active_structure):
            current_item = active_structure[st.session_state.current_ex_index]
            ex_name = current_item["exercise"]
            total_sets = current_item["sets"]
            target_reps = current_item["target_reps"]
            target_rir = current_item["target_rir"]
            
            st.markdown(f"### 🔥 Workout {st.session_state.active_workout_letter} | Current Exercise: **{ex_name}**")
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
                        "Workout": f"Workout {st.session_state.active_workout_letter}",
                        "Exercise": ex_name,
                        "Set": st.session_state.current_set_num,
                        "Weight (kg)": act_weight,
                        "Reps": act_reps,
                        "RIR": act_rir,
                        "Notes": act_notes
                    })
                    
                    if st.session_state.current_set_num < total_sets:
                        st.session_state.current_set_num += 1
                    else:
                        st.session_state.current_ex_index += 1
                        st.session_state.current_set_num = 1
                    st.rerun()
        else:
            st.success(f"🎉 All prescribed sets completed for Workout {st.session_state.active_workout_letter}!")
            if st.button("Mark Workout as Completed & Advance Rotation"):
                st.session_state.last_completed_workout = st.session_state.active_workout_letter
                st.success(f"Rotation updated! Next session will advance past Workout {st.session_state.active_workout_letter}.")

        # Display Live Session Log Table
        if st.session_state.workout_logs:
            st.subheader("📋 Session Progress Log")
            df_logs = pd.DataFrame(st.session_state.workout_logs)
            st.table(df_logs)
            
            if st.button("Finish Workout & Generate Execution Report"):
                report_prompt = f"""Act as the Workout Assistant. Generate a clean Workout Execution Report for Workout {st.session_state.active_workout_letter} based on these actual set logs: 
{df_logs.to_string(index=False)}. 
Format inside ONE clean monospaced code block ready to copy back to the Analyst."""
                
                report_resp = generate_content(report_prompt)
                if "🚨 GOOGLE API REJECTION" in report_resp:
                    st.error(report_resp)
                else:
                    st.markdown("### 🏆 Final Workout Report")
                    st.code(report_resp, language="text")
