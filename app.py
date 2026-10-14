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

# 1. Page Config & Boostcamp Custom UI CSS Injection
st.set_page_config(page_title="Workout Analyst & Live Gym Assistant", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Boostcamp Dark Mode Core Palette */
    .stApp {
        background-color: #0b0c10;
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Main Header & Title */
    h1 {
        font-weight: 900 !important;
        letter-spacing: -0.5px !important;
        background: -webkit-linear-gradient(45deg, #38bdf8, #4ade80);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem !important;
    }
    h2, h3, h4 {
        color: #f1f5f9 !important;
        font-weight: 700 !important;
    }

    /* Metric Cards / Boostcamp Stat Cards */
    [data-testid="stMetric"] {
        background: #141622;
        border-radius: 16px;
        padding: 18px 22px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        border: 1px solid #232738;
        text-align: left;
        transition: all 0.25s ease-in-out;
    }
    [data-testid="stMetric"]:hover {
        border-color: #38bdf8;
        transform: translateY(-2px);
    }
    [data-testid="stMetricValue"] {
        font-size: 2.1rem !important;
        font-weight: 800 !important;
        color: #38bdf8 !important;
        font-feature-settings: "tnum";
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        color: #94a3b8 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }

    /* Boostcamp Pill / Tag Badges */
    .badge-pill {
        display: inline-block;
        background-color: #1e2235;
        color: #38bdf8;
        border: 1px solid #2e354f;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-pill-green {
        background-color: #142e23;
        color: #4ade80;
        border: 1px solid #1f523b;
    }
    .badge-pill-orange {
        background-color: #2e1d14;
        color: #fb923c;
        border: 1px solid #52311f;
    }

    /* Primary Boostcamp Buttons */
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 12px 24px !important;
        transition: all 0.2s ease-in-out !important;
        border: none !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5) !important;
    }

    /* Tab Bar Custom Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: #11131c;
        padding: 8px;
        border-radius: 14px;
        border: 1px solid #1e2233;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 10px;
        color: #94a3b8;
        font-weight: 700;
        padding: 0 20px;
        background-color: transparent;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e2338 !important;
        color: #38bdf8 !important;
        border: 1px solid #38bdf8 !important;
    }

    /* Smooth Progress Bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #38bdf8 0%, #4ade80 100%);
        border-radius: 8px;
    }

    /* Clean Container Cards */
    .boostcamp-card {
        background: #141622;
        border: 1px solid #232738;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Boostcamp Fitness Analyst")
st.caption("AI-Driven Personal Training Engine & Real-Time Gym Assistant")

# API Setup
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
MODEL_ID = "gemini-1.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={API_KEY}"

# Force Local Timezone (UTC+8 for Asia/Manila)
tz_offset = datetime.timezone(datetime.timedelta(hours=8))
today_date = datetime.datetime.now(tz=tz_offset).date()

# 2. Google Sheets API Client
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
        
        profile_ws = sh.worksheet("Profile")
        profile_records = [row for row in profile_ws.get_all_records() if any(row.values())]
        raw_profile = profile_records[-1] if profile_records else {}
        profile_data = {str(k).strip().lower(): v for k, v in raw_profile.items()}
        
        program_ws = sh.worksheet("Program")
        program_records = [row for row in program_ws.get_all_records() if any(row.values())]
        raw_program = program_records[-1] if program_records else {"last_completed_workout": "A", "active_workout_letter": "B"}
        program_data = {str(k).strip().lower(): v for k, v in raw_program.items()}
        
        session_ws = sh.worksheet("Active_Session")
        session_records = [row for row in session_ws.get_all_records() if any(row.values())]
        session_data = session_records[-1] if session_records else {}
        
        if "live_logs" in session_data and isinstance(session_data["live_logs"], str):
            try:
                session_data["live_logs"] = json.loads(session_data["live_logs"])
            except Exception:
                session_data["live_logs"] = []
                
        history_ws = sh.worksheet("Measurement_History")
        history_data = history_ws.get_all_records()
        
        return {
            "profile": profile_data,
            "training_program": program_data,
            "active_session": session_data,
            "measurement_history": history_data
        }
    except Exception as e:
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
        pass 

db = load_database_from_sheets()
profile_data = db.get("profile", {})
active_session_db = db.get("active_session", {})

# Session State Hydration
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
            exercises.append({"exercise": ex_name, "sets": sets, "target_reps": target_reps, "target_rir": 3})
            
    if not exercises:
        for line in lines:
            if re.match(r'^\s*\d+\.\s+', line):
                parts = re.split(r'[—–-]', line)
                ex_name = re.sub(r'^\s*\d+\.\s+', '', parts[0]).strip()
                if ex_name and not ex_name.lower().startswith('warm') and not ex_name.lower().startswith('cooldown'):
                    exercises.append({"exercise": ex_name, "sets": 3, "target_reps": "10", "target_rir": 3})

    if not exercises:
        exercises = [{"exercise": "Working Exercise", "sets": 3, "target_reps": "10", "target_rir": 3}]
    return exercises

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
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"🚨 GOOGLE API REJECTION ({response.status_code}): {response.text}"
    except requests.exceptions.RequestException as e:
        return f"🚨 API NETWORK TIMEOUT ERROR: {str(e)}"

# Main App Navigation Tabs
tab1, tab2 = st.tabs(["📊 Executive Dashboard", "🏋️ Live Session Tracker"])

# --- TAB 1: EXECUTIVE DASHBOARD ---
with tab1:
    raw_w = str(profile_data.get("current_weight", "74.0 kg")).strip()
    display_weight = raw_w if "kg" in raw_w.lower() else f"{raw_w} kg"
    raw_bf = str(profile_data.get("current_body_fat", "26.40%")).strip()
    display_bf = raw_bf if "%" in raw_bf else f"{raw_bf}%"
