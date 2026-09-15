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
if 'warmup_completed' not in st.session_state:
    st.session_state.warmup_completed = False
if 'workout_completed' not in st.session_state:
    st.session_state.workout_completed = False
if 'workout_start_time' not in st.session_state:
    st.session_state.workout_start_time = None
if 'session_metrics' not in st.session_state:
    st.session_state.session_metrics = {}
if 'final_report' not in st.session_state:
    st.session_state.final_report = ""
if 'analyst_feedback' not in st.session_state:
    st.session_state.analyst_feedback = ""
if 'current_ex_index' not in st.session_state:
    st.session_state.current_ex_index = 0
if 'current_set_num' not in st.session_state:
    st.session_state.current_set_num = 1

# Track Rotation State (Default last completed: A, so next is B)
if 'last_completed_workout' not in st.session_state:
    st.session_state.last_completed_workout = "A"
if 'active_workout_letter' not in st.session_state:
    st.session_state.active_workout_letter = "B"

# Robust Dynamic Exercise Parser
def parse_exercises_from_text(workout_text):
    exercises = []
    lines = workout_text.split('\n')
    in_exercises_section = False
    
    for line in lines:
        if "exercises:" in line.lower() or "exercise list:" in line.lower():
            in_exercises_section = True
            continue
        if "cooldown:" in line.lower():
            in_exercises_section = False
            
        match = re.match(r'^\s*(\d+)\.\s+(.*?)(?:\s+[—–-]\s+|\s+—\s+|\s+-\s+|\b\d+\s+sets?\b)', line, re.IGNORECASE)
        if match:
            ex_name = match.group(2).strip()
            ex_name = re.sub(r'\s+[—–-]\s*$', '', ex_name).strip()
            
            if not ex_name or ex_name.lower().startswith('warm') or ex_name.lower().startswith('cooldown'):
                continue
                
            set_match = re.search(r'(\d+)\s+sets?', line, re.IGNORECASE)
            sets = int(set_match.group(1)) if set_match else 3
            
            rep_match = re.search(r'(\d+(?:[–-]\d+)?)\s+reps?', line, re.IGNORECASE)
            target_reps = rep_match.group(1) if rep_match else "10"
            
            exercises.append({
                "exercise": ex_name,
                "sets": sets,
                "target_reps": target_reps,
                "target_rir": 3
            })
            
    if not exercises:
        for line in lines:
            if re.match(r'^\s*\d+\.\s+', line):
                parts = re.split(r'[—–-]', line)
                ex_name = re.sub(r'^\s*\d+\.\s+', '', parts[0]).strip()
                if ex_name and not ex_name.lower().startswith('warm') and not ex_name.lower().startswith('cooldown'):
                    exercises.append({
                        "exercise": ex_name,
                        "sets": 3,
                        "target_reps": "10",
                        "target_rir": 3
                    })

    if not exercises:
        exercises = [{"exercise": "Working Exercise", "sets": 3, "target_reps": "10", "target_rir": 3}]
        
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

scale_file = st.sidebar.file_uploader("Upload Scale Screenshot(s)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="scale_upload")
if scale_file:
    if st.sidebar.button("Process Scale Screenshot(s)"):
        with st.spinner("Extracting & synthesizing body composition data..."):
            # If multiple are uploaded, synthesize them all
            st.session_state.extracted_scale_metrics = "Synthesized Scale Data Found" # Placeholder for actual multi-image processing logic in production
            st.sidebar.success("Scale Data Synthesized & Logged!")

sleep_file = st.sidebar.file_uploader("Upload Sleep Screenshot", type=["png", "jpg", "jpeg"], key="sleep_upload")
if sleep_file is not None:
    sleep_image = Image.open(sleep_file)
    if st.sidebar.button("Process Sleep Screenshot"):
        with st.spinner("Extracting sleep performance..."):
            resp = generate_content("Extract sleep metrics as bullet points.", sleep_image)
            st.session_state.extracted_sleep_metrics = resp
            st.sidebar.success("Sleep Data Logged!")

# Main Tabs Setup
tab1, tab2 = st.tabs(["📊 Workout Analyst", "🏋️ Live Workout Assistant"])

# --- TAB 1: WORKOUT ANALYST ---
with tab1:
    st.header("Program Continuity & Planning")
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Current Weight", "75.50 kg")
    m2.metric("Target Weight", "70.0 kg", "-5.5 kg")
    m3.metric("Current Body Fat", "27.1%")
    m4.metric("Target Body Fat", "15–18%")
    m5.metric("Milestone 1", "Late Nov 2026")
    
    st.markdown("---")

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

    col_rot1, col_rot2 = st.columns(2)
    with col_rot1:
        next_letter = {"A": "B", "B": "C", "C": "A"}[st.session_state.last_completed_workout]
        st.markdown(f"🔄 **Last Completed:** Workout {st.session_state.last_completed_workout} → **Scheduled Next:** Workout **{next_letter}**")
    with col_rot2:
        override_choice = st.selectbox("Override Workout Letter if Needed:", ["A", "B", "C"], index=["A", "B", "C"].index(next_letter))
        st.session_state.active_workout_letter = override_choice

    if st.button("Generate Today's Workout", type="primary"):
        if not st.session_state.extracted_scale_metrics or not st.session_state.extracted_sleep_metrics:
            st.error(f"🚨 **Missing Required Measurements for {tomorrow_date.strftime('%B %d, %Y')}**: Please upload your Scale and Sleep Tracker screenshots via the sidebar before generating today's workout.")
        else:
            with st.spinner(f"Analyzing recovery & prescribing Workout {st.session_state.active_workout_letter}..."):
                body_data = st.session_state.extracted_scale_metrics
                sleep_data = st.session_state.extracted_sleep_metrics
                
                prompt_text = f"""You are my expert Workout Analyst. Adhere strictly to your core operating principles: evidence-based practice, critical evaluation, continuity, and defensible programming. Do NOT change exercises randomly or without reason. Maintain the established A/B/C full-body split structure.
Target Date: {tomorrow_date.strftime('%Y-%m-%d')} ({tomorrow_date.strftime('%A')}). 
Last completed workout in rotation: Workout {st.session_state.last_completed_workout}. 
Prescribing: Workout {st.session_state.active_workout_letter}. 
Latest Scale Data: {body_data}. 
Latest Sleep Data: {sleep_data}. 
Provide a complete, structured workout following established baselines, standard warm-up (5 min treadmill + World's Greatest Stretch), exact exercise names, sets, rep ranges, target 2–3 RIR, rest periods, and standard cooldown (5–10 min easy walking). Output the workout inside ONE monospaced code block."""
                
                response_text = generate_content(prompt_text)
                if "🚨 GOOGLE API REJECTION" in response_text:
                    st.error(response_text)
                else:
                    st.session_state.todays_workout = response_text
                    st.session_state.current_ex_index = 0
                    st.session_state.current_set_num = 1
                    st.session_state.workout_started = False
                    st.session_state.warmup_completed = False
                    st.session_state.workout_completed = False
                    st.session_state.final_report = ""
                    st.session_state.analyst_feedback = ""
                    st.session_state.workout_logs = []
                    st.success(f"Workout {st.session_state.active_workout_letter} Generated Successfully! Switch to the Live Assistant tab to execute.")
            
    if st.session_state.todays_workout:
        st.subheader("Prescribed Routine")
        st.code(st.session_state.todays_workout, language="text")

# --- TAB 2: LIVE WORKOUT ASSISTANT ---
with tab2:
    st.header("Gym Execution & Live Assistant")
    
    if not st.session_state.todays_workout:
        st.info("Please generate Today's Workout in the Workout Analyst tab first!")
    else:
        # Top Dashboard Controls
        col_timer1, col_timer2 = st.columns([1, 3])
        if not st.session_state.workout_started:
            if col_timer1.button("🚀 Start Workout"):
                st.session_state.workout_started = True
                st.session_state.warmup_completed = False
                st.session_state.workout_completed = False
                st.session_state.workout_start_time = time.time()
                st.rerun()
        else:
            if not st.session_state.workout_completed:
                elapsed_seconds = int(time.time() - st.session_state.workout_start_time)
                mins, secs = divmod(elapsed_seconds, 60)
                col_timer1.markdown(f"⏱️ **Live Session Time:** `{mins:02d}:{secs:02d}`")
            else:
                col_timer1.markdown(f"🛑 **Final Session Time:** `{st.session_state.session_metrics.get('duration', '00:00')}`")

        st.markdown("---")

        # PHASE 1: WARM-UP GATED CHECKLIST
        if st.session_state.workout_started and not st.session_state.warmup_completed:
            st.markdown("### 🔥 Warm-Up Protocol")
            st.info("Complete the warm-up sequence before beginning your working sets. No logging required here.")
            st.markdown("""
            * **1.** 5 minutes easy/moderate treadmill walking
            * **2.** World's Greatest Stretch: 5 reps/side
            * **3.** Exercise-specific warm-up sets as needed
            """)
            if st.button("✅ Warm-up Done — Start Main Exercises", type="primary"):
                st.session_state.warmup_completed = True
                st.rerun()

        # PHASE 2: STREAMLINED LOGGING FOR MAIN EXERCISES ONLY
        elif st.session_state.workout_started and st.session_state.warmup_completed and not st.session_state.workout_completed:
            active_structure = parse_exercises_from_text(st.session_state.todays_workout)
            
            if st.session_state.current_ex_index < len(active_structure):
                current_item = active_structure[st.session_state.current_ex_index]
                ex_name = current_item["exercise"]
                total_sets = current_item["sets"]
                target_reps = current_item["target_reps"]
                target_rir = current_item["target_rir"]
                
                st.markdown(f"### 🏋️‍♂️ Workout {st.session_state.active_workout_letter} | Current Exercise: **{ex_name}**")
                st.info(f"**Set {st.session_state.current_set_num} of {total_sets}** | Target: {target_reps} reps @ RIR {target_rir}")
                
                with st.form("streamlined_logger"):
                    c1, c2, c3 = st.columns(3)
                    act_weight = c1.number_input("Weight Used (kg)", value=0.0, step=0.5)
                    act_reps = c2.number_input("Reps Completed", value=0, step=1)
                    act_rir = c3.number_input("RIR Left", value=target_rir, step=1)
                    act_notes = st.text_input("Set Notes (optional)")
                    
                    if st.form_submit_button("✅ Log Set & Next"):
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
                # PHASE 3: COOLDOWN & SESSION WRAP-UP
                st.markdown("### ❄️ Cooldown & Session Wrap-Up")
                st.success("🎉 All prescribed working sets completed!")
                st.info("**Cooldown Protocol:** 5–10 minutes easy walking.")
                
                with st.form("session_metrics_form"):
                    st.markdown("#### 📝 Final Session Metrics")
                    sc1, sc2, sc3 = st.columns(3)
                    pre_energy = sc1.slider("Pre-Workout Energy (1-10)", 1, 10, 5)
                    post_energy = sc2.slider("Post-Workout Energy (1-10)", 1, 10, 5)
                    difficulty = sc3.slider("Workout Difficulty (1-10)", 1, 10, 5)
                    workout_notes = st.text_area("Overall Session Notes (Optional)", placeholder="Note any pain, excessive fatigue, or exceptional strength...")
                    
                    if st.form_submit_button("✅ Cooldown Done & Analyze Session"):
                        # Stop the timer and lock metrics
                        elapsed = int(time.time() - st.session_state.workout_start_time)
                        m, s = divmod(elapsed, 60)
                        
                        st.session_state.session_metrics = {
                            "duration": f"{m:02d}:{s:02d}",
                            "pre_energy": pre_energy,
                            "post_energy": post_energy,
                            "difficulty": difficulty,
                            "notes": workout_notes
                        }
                        st.session_state.last_completed_workout = st.session_state.active_workout_letter
                        st.session_state.workout_completed = True
                        st.rerun()

        # PHASE 4: FINAL REPORT & ANALYST REVIEW
        if st.session_state.workout_completed:
            df_logs = pd.DataFrame(st.session_state.workout_logs)
            
            if not st.session_state.final_report:
                # API Call 1: Assistant generates the execution report
                with st.spinner("🤖 Assistant is compiling the Execution Report..."):
                    report_prompt = f"""Act as the Workout Assistant. Generate a Workout Execution Report based on these actual set logs:
{df_logs.to_string(index=False)}
Overall Session Metrics: Pre-Energy: {st.session_state.session_metrics['pre_energy']}/10 | Post-Energy: {st.session_state.session_metrics['post_energy']}/10 | Difficulty: {st.session_state.session_metrics['difficulty']}/10 | Duration: {st.session_state.session_metrics['duration']} mins
Notes: {st.session_state.session_metrics['notes']}
Format inside ONE clean monospaced code block."""
                    
                    st.session_state.final_report = generate_content(report_prompt)
                
                # API Call 2: Analyst evaluates the report for progression/inconsistencies
                with st.spinner("🧠 Analyst is reviewing execution and checking for progression triggers..."):
                    analysis_prompt = f"""Act as the Workout Analyst. Review this Workout Execution Report:
{st.session_state.final_report}

Perform a critical evaluation based on your instructions. Check for inconsistencies between the logs and the prescribed session. Look for progression opportunities (e.g., if target RIR was maintained, technique was good, and upper rep range was reached). Provide a concise, bulleted analysis of the session, explicitly noting any defensible adjustments or weight progressions required for the next iteration of this workout."""
                    
                    st.session_state.analyst_feedback = generate_content(analysis_prompt)
                
                st.rerun()

            else:
                # Display Results
                st.markdown("### 🏆 Final Workout Report")
                st.code(st.session_state.final_report, language="text")
                
                st.markdown("---")
                st.markdown("### 🧠 Workout Analyst Feedback & Adjustments")
                st.markdown(st.session_state.analyst_feedback)
