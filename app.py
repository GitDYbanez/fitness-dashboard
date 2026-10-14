import streamlit as st
import pandas as pd
import requests
import base64
import io
import datetime
import time
import re
import json
import plotly.express as px
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials

# 1. Page Config & API Setup
st.set_page_config(page_title="Fitness Dashboard & Assistant", layout="wide")
st.title("🏋️‍♂️ Workout Analyst & Live Gym Assistant")

# Direct REST API Setup (Bypasses all SDK version conflicts)
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
MODEL_ID = "gemini-3.6-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={API_KEY}"

# Force Local Timezone (UTC+8 for Asia/Manila)
tz_offset = datetime.timezone(datetime.timedelta(hours=8))
today_date = datetime.datetime.now(tz=tz_offset).date()

# 2. Google Sheets API Client & Cloud IO Helpers
@st.cache_resource
def get_gsheets_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    return gspread.authorize(credentials)

client = get_gsheets_client()
spreadsheet_name = "Workout_Analyst_Database"

@st.cache_data(ttl=10)
def load_database_from_sheets():
    try:
        sh = client.open(spreadsheet_name)
        
        # Load Profile Worksheet
        profile_ws = sh.worksheet("Profile")
        profile_records = [row for row in profile_ws.get_all_records() if any(row.values())]
        raw_profile = profile_records[-1] if profile_records else {}
        profile_data = {str(k).strip().lower(): v for k, v in raw_profile.items()}
        
        # Load Program Worksheet
        program_ws = sh.worksheet("Program")
        program_records = [row for row in program_ws.get_all_records() if any(row.values())]
        raw_program = program_records[-1] if program_records else {"last_completed_workout": "A", "active_workout_letter": "B"}
        program_data = {str(k).strip().lower(): v for k, v in raw_program.items()}
        
        # Load Active Session Worksheet
        session_ws = sh.worksheet("Active_Session")
        session_records = [row for row in session_ws.get_all_records() if any(row.values())]
        session_data = session_records[-1] if session_records else {}
        
        if "live_logs" in session_data and isinstance(session_data["live_logs"], str):
            try:
                session_data["live_logs"] = json.loads(session_data["live_logs"])
            except Exception:
                session_data["live_logs"] = []
                
        # Load Measurement History Worksheet
        history_ws = sh.worksheet("Measurement_History")
        history_data = history_ws.get_all_records()
        
        return {
            "profile": profile_data,
            "training_program": program_data,
            "active_session": session_data,
            "measurement_history": history_data
        }
    except Exception as e:
        # THIS WILL PRINT THE EXACT CRASH REASON TO YOUR DASHBOARD
        st.error(f"🚨 Google Sheets Sync Error: {repr(e)}")
        return {
            "profile": {},
            "training_program": {"last_completed_workout": "A", "active_workout_letter": "B"},
            "active_session": {},
            "measurement_history": []
        }

def sync_active_session_to_sheets():
    try:
        sh = client.open(spreadsheet_name)
        session_ws = sh.worksheet("Active_Session")
        session_ws.clear()
        
        session_payload = {
            "date": today_date.strftime('%Y-%m-%d'),
            "workout_letter": st.session_state.active_workout_letter,
            "cached_prescription": st.session_state.todays_workout,
            "workout_started": str(st.session_state.workout_started),
            "warmup_completed": str(st.session_state.warmup_completed),
            "workout_completed": str(st.session_state.workout_completed),
            "current_ex_index": st.session_state.current_ex_index,
            "current_set_num": st.session_state.current_set_num,
            "start_timestamp": st.session_state.workout_start_time or "",
            "live_logs": json.dumps(st.session_state.workout_logs),
            "final_report": st.session_state.final_report,
            "analyst_feedback": st.session_state.analyst_feedback
        }
        session_ws.append_row(list(session_payload.keys()))
        session_ws.append_row(list(session_payload.values()))
    except Exception:
        pass # Continue gracefully if temporary network glitch occurs

db = load_database_from_sheets()
profile_data = db.get("profile", {})
active_session_db = db.get("active_session", {})

# 3. State Hydration Across Session Breaks
if 'extracted_scale_metrics' not in st.session_state:
    st.session_state.extracted_scale_metrics = None
if 'extracted_sleep_metrics' not in st.session_state:
    st.session_state.extracted_sleep_metrics = None

is_today_session = (str(active_session_db.get("date")) == today_date.strftime('%Y-%m-%d'))

if 'todays_workout' not in st.session_state:
    st.session_state.todays_workout = active_session_db.get("cached_prescription", "") if is_today_session else ""

if 'workout_logs' not in st.session_state:
    st.session_state.workout_logs = active_session_db.get("live_logs", []) if is_today_session else []

if 'workout_started' not in st.session_state:
    st.session_state.workout_started = (str(active_session_db.get("workout_started")).lower() == "true") if is_today_session else False

if 'warmup_completed' not in st.session_state:
    st.session_state.warmup_completed = (str(active_session_db.get("warmup_completed")).lower() == "true") if is_today_session else False

if 'workout_completed' not in st.session_state:
    st.session_state.workout_completed = (str(active_session_db.get("workout_completed")).lower() == "true") if is_today_session else False

if 'workout_start_time' not in st.session_state:
    try:
        st.session_state.workout_start_time = float(active_session_db.get("start_timestamp")) if is_today_session else None
    except Exception:
        st.session_state.workout_start_time = None

if 'current_ex_index' not in st.session_state:
    try:
        st.session_state.current_ex_index = int(active_session_db.get("current_ex_index", 0)) if is_today_session else 0
    except Exception:
        st.session_state.current_ex_index = 0

if 'current_set_num' not in st.session_state:
    try:
        st.session_state.current_set_num = int(active_session_db.get("current_set_num", 1)) if is_today_session else 1
    except Exception:
        st.session_state.current_set_num = 1

if 'final_report' not in st.session_state:
    st.session_state.final_report = active_session_db.get("final_report", "") if is_today_session else ""

if 'analyst_feedback' not in st.session_state:
    st.session_state.analyst_feedback = active_session_db.get("analyst_feedback", "") if is_today_session else ""

if 'session_metrics' not in st.session_state:
    st.session_state.session_metrics = {}

if 'last_completed_workout' not in st.session_state:
    st.session_state.last_completed_workout = str(db.get("training_program", {}).get("last_completed_workout", "A")).upper()

if 'active_workout_letter' not in st.session_state:
    st.session_state.active_workout_letter = str(db.get("training_program", {}).get("active_workout_letter", "B")).upper()

# 4. Dynamic Exercise Parser
def parse_exercises_from_text(workout_text):
    exercises = []
    lines = workout_text.split('\n')
    
    for line in lines:
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
def generate_content(prompt, images=None):
    parts = [{"text": prompt}]
    if images:
        if not isinstance(images, list):
            images = [images]
            
        for img in images:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_str}})
    
    payload = {"contents": [{"parts": parts}]}
    try:
        response = requests.post(API_URL, headers={'Content-Type': 'application/json'}, json=payload, timeout=30)
        if response.status_code == 200:
            try:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                return f"API Parsing Error: {str(e)} \n\n {response.text}"
        else:
            return f"🚨 GOOGLE API REJECTION ({response.status_code}): {response.text}"
    except requests.exceptions.RequestException as e:
        return f"🚨 API NETWORK TIMEOUT ERROR: {str(e)}"

# Sidebar Data Inputs
st.sidebar.header("📸 Log Metrics via Screenshots")

scale_files = st.sidebar.file_uploader("Upload Scale Screenshot(s)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="scale_upload")
if scale_files:
    if st.sidebar.button("Process Scale Screenshot(s)"):
        with st.spinner(f"Extracting & synthesizing {len(scale_files)} scale screenshot(s)..."):
            images = [Image.open(f) for f in scale_files]
            resp = generate_content("Extract all scale metrics as key-value pairs. Synthesize across all images into one key-value list.", images)
            st.session_state.extracted_scale_metrics = resp
            
            try:
                sh = client.open(spreadsheet_name)
                history_ws = sh.worksheet("Measurement_History")
                w_match = re.search(r'(?:Weight)[\s:]*(\d+(?:\.\d+)?)\s*(?:kg|lbs)?', resp, re.IGNORECASE)
                bf_match = re.search(r'(?:Body\s*Fat|Fat|BF)[\s:]*(\d+(?:\.\d+)?)\s*%', resp, re.IGNORECASE)
                
                if w_match:
                    new_w = float(w_match.group(1))
                    new_bf = float(bf_match.group(1)) if bf_match else 27.0
                    history_ws.append_row([today_date.strftime('%Y-%m-%d'), new_w, new_bf])
            except Exception:
                pass
            
            st.sidebar.success("Scale Data Logged & Synced!")

sleep_file = st.sidebar.file_uploader("Upload Sleep Screenshot", type=["png", "jpg", "jpeg"], key="sleep_upload")
if sleep_file is not None:
    sleep_image = Image.open(sleep_file)
    if st.sidebar.button("Process Sleep Screenshot"):
        with st.spinner("Extracting sleep performance..."):
            resp = generate_content("Extract sleep duration, score, and quality as bullet points.", sleep_image)
            st.session_state.extracted_sleep_metrics = resp
            st.sidebar.success("Sleep Data Logged!")

# Main Tabs Setup
tab1, tab2 = st.tabs(["📊 Workout Analyst", "🏋️ Live Workout Assistant"])

# --- TAB 1: WORKOUT ANALYST ---
with tab1:
    st.header("Program Continuity & Planning")
    
    # Safe Value Formatting from Google Sheets Profile Record
    raw_w = str(profile_data.get("current_weight", "75.20 kg")).strip()
    display_weight = raw_w if "kg" in raw_w.lower() else f"{raw_w} kg"
    
    raw_bf = str(profile_data.get("current_body_fat", "26.9%")).strip()
    display_bf = raw_bf if "%" in raw_bf else f"{raw_bf}%"
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Current Weight", display_weight)
    m2.metric("Target Weight", "70.0 kg")
    m3.metric("Current Body Fat", display_bf)
    m4.metric("Target Body Fat", "15–18%")
    m5.metric("Milestone 1", "Late Nov 2026")
    
    st.markdown("---")

    # Time-Series Chart
    history_data = db.get("measurement_history", [])
    if history_data:
        df_hist = pd.DataFrame(history_data)
        if "weight_kg" in df_hist.columns and "date" in df_hist.columns:
            fig = px.line(df_hist, x="date", y="weight_kg", title="Weight Progress Trajectory (kg)", markers=True)
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("👤 View Master Current User State & Baselines", expanded=False):
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            st.markdown("### 📋 Profile & Goals")
            st.markdown(f"""
            * **Age / Sex:** {profile_data.get('age', 38)} years old, {profile_data.get('sex', 'Male')}
            * **Height:** {profile_data.get('height_cm', 175)} cm
            * **Current Weight:** {display_weight}
            * **Current Body Fat:** {display_bf}
            * **Primary Goal:** {profile_data.get('primary_goal', 'Fat loss')}
            * **Secondary Goal:** {profile_data.get('secondary_goal', 'Lateral delt development')}
            """)
            st.markdown("### 💤 Recovery & Conditioning")
            st.markdown(f"""
            * **Recent Sleep:** {profile_data.get('current_sleep', 'No recent sleep data logged.')}
            * **Last Measurement Date:** {profile_data.get('last_measurement_date', 'Unknown')}
            """)
        with col_u2:
            st.markdown("### 🏋️ Training & Equipment")
            st.markdown("""
            * **Structure:** A/B/C Full-Body Rotation
            * **Intensity Target:** ~2–3 RIR
            * **Key Adaptations:** 45° Leg Press & Smith-Machine RDL used to bypass grip bottlenecks.
            """)

    st.markdown("---")

    col_rot1, col_rot2 = st.columns(2)
    with col_rot1:
        next_letter = {"A": "B", "B": "C", "C": "A"}[st.session_state.last_completed_workout]
        st.markdown(f"🔄 **Last Completed:** Workout {st.session_state.last_completed_workout} → **Scheduled Next:** Workout **{next_letter}**")
    with col_rot2:
        override_choice = st.selectbox("Override Workout Letter if Needed:", ["A", "B", "C"], index=["A", "B", "C"].index(next_letter))
        st.session_state.active_workout_letter = override_choice
        sync_active_session_to_sheets()

    if st.button("Generate Today's Workout", type="primary"):
        current_date_str = today_date.strftime('%Y-%m-%d')
        last_record_date = str(profile_data.get("last_measurement_date", ""))
        
        has_new_uploads = st.session_state.extracted_scale_metrics and st.session_state.extracted_sleep_metrics
        has_valid_history = (last_record_date == current_date_str)
        
        if not has_new_uploads and not has_valid_history:
            st.error(f"🚨 **Missing Required Measurements for {today_date.strftime('%B %d, %Y')}**: Please upload your Scale and Sleep screenshots via the sidebar or update your database record.")
        else:
            with st.spinner(f"Analyzing recovery & prescribing Workout {st.session_state.active_workout_letter}..."):
                body_data = st.session_state.extracted_scale_metrics or f"Weight: {display_weight}, BF: {display_bf}"
                sleep_data = st.session_state.extracted_sleep_metrics or profile_data.get("current_sleep", "No sleep logged.")
                
                prompt_text = f"""You are my expert Workout Analyst. Adhere strictly to your core operating principles: evidence-based practice, critical evaluation, continuity, and defensible programming. Do NOT change exercises randomly or without reason.

Here is my Master Baseline Database:
{json.dumps(db, indent=2)}

Target Date: {today_date.strftime('%Y-%m-%d')} ({today_date.strftime('%A')}). 
Last completed workout in rotation: Workout {st.session_state.last_completed_workout}. 
Prescribing: Workout {st.session_state.active_workout_letter}. 
Latest Scale Data: {body_data}. 
Latest Sleep Data: {sleep_data}. 

Provide a complete, structured workout following established baselines, standard warm-up (5 min treadmill + World's Greatest Stretch), exact exercise names, sets, rep ranges, target 2–3 RIR, rest periods, and standard cooldown (5–10 min easy walking). Output the workout inside ONE monospaced code block."""
                
                response_text = generate_content(prompt_text)
                if "🚨" in response_text:
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
                    sync_active_session_to_sheets()
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
        col_timer1, col_timer2 = st.columns([1, 3])
        if not st.session_state.workout_started:
            if col_timer1.button("🚀 Start Workout"):
                st.session_state.workout_started = True
                st.session_state.warmup_completed = False
                st.session_state.workout_completed = False
                st.session_state.workout_start_time = time.time()
                sync_active_session_to_sheets()
                st.rerun()
        else:
            if not st.session_state.workout_completed:
                elapsed_seconds = int(time.time() - (st.session_state.workout_start_time or time.time()))
                mins, secs = divmod(elapsed_seconds, 60)
                col_timer1.markdown(f"⏱️ **Live Session Time:** `{mins:02d}:{secs:02d}`")
            else:
                col_timer1.markdown(f"🛑 **Final Session Time:** `{st.session_state.session_metrics.get('duration', '00:00')}`")

        st.markdown("---")

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
                sync_active_session_to_sheets()
                st.rerun()

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
                        
                        sync_active_session_to_sheets()
                        st.rerun()
            else:
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
                        elapsed = int(time.time() - (st.session_state.workout_start_time or time.time()))
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
                        sync_active_session_to_sheets()
                        st.rerun()

        if st.session_state.workout_completed:
            df_logs = pd.DataFrame(st.session_state.workout_logs)
            
            if not st.session_state.final_report:
                # Step 1: Assistant compiles Execution Report
                with st.spinner("🤖 Assistant compiling execution report..."):
                    report_prompt = f"""Act as the Workout Assistant. Generate a Workout Execution Report based on these actual set logs:
{df_logs.to_string(index=False)}
Overall Session Metrics: Pre-Energy: {st.session_state.session_metrics.get('pre_energy', 5)}/10 | Post-Energy: {st.session_state.session_metrics.get('post_energy', 5)}/10 | Difficulty: {st.session_state.session_metrics.get('difficulty', 5)}/10 | Duration: {st.session_state.session_metrics.get('duration', '00:00')} mins
Notes: {st.session_state.session_metrics.get('notes', '')}
Format inside ONE clean monospaced code block."""
                    
                    st.session_state.final_report = generate_content(report_prompt)
                
                # Step 2: Analyst evaluates performance & decides progressions
                with st.spinner("🧠 Analyst reviewing execution & progression triggers..."):
                    analysis_prompt = f"""Act as the Workout Analyst. Review this Workout Execution Report:
{st.session_state.final_report}

Perform a critical evaluation based on your core guidelines:
1. Evaluate progression opportunities (e.g., if target 2–3 RIR was maintained, technique was good, and upper rep range was reached across all sets).
2. Explicitly declare required weight progressions or load holds for the next iteration of this workout.
3. Update baseline working weights for any newly performed exercises."""
                    
                    st.session_state.analyst_feedback = generate_content(analysis_prompt)
                
                sync_active_session_to_sheets()
                st.rerun()

            else:
                st.markdown("### 🏆 Final Workout Report")
                st.code(st.session_state.final_report, language="text")
                
                st.markdown("---")
                st.markdown("### 🧠 Workout Analyst Evaluation & Progression Decisions")
                st.markdown(st.session_state.analyst_feedback)
