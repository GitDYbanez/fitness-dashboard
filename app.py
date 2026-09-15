import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from PIL import Image

# 1. Page Config & API Setup
st.set_page_config(page_title="Fitness & Workout Dashboard", layout="wide")
st.title("🏋️‍♂️ Fitness & Workout Analyst Dashboard")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# Initialize session state for extracted metrics
if 'extracted_scale_metrics' not in st.session_state:
    st.session_state.extracted_scale_metrics = None
if 'extracted_sleep_metrics' not in st.session_state:
    st.session_state.extracted_sleep_metrics = None

# 2. Sidebar Screenshot Uploaders
st.sidebar.header("📸 Log Metrics via Screenshots")

# --- Smart Scale Section ---
st.sidebar.subheader("1. Smart Scale Data")
scale_file = st.sidebar.file_uploader("Upload Scale Screenshot", type=["png", "jpg", "jpeg"], key="scale_upload")

if scale_file is not None:
    scale_image = Image.open(scale_file)
    st.sidebar.image(scale_image, caption="Scale Screenshot", use_column_width=True)
    
    if st.sidebar.button("Process Scale Screenshot"):
        with st.spinner("Extracting body composition data..."):
            scale_prompt = (
                "You are an expert fitness data analyst. "
                "Examine this smart scale app screenshot and extract EVERY available metric. "
                "Include Date, Weight (kg), Body Fat %, Muscle Mass, Skeletal Muscle Mass, "
                "Visceral Fat, Subcutaneous Fat, Body Water, BMR, Protein, Bone Mass, Heart Rate, and Body Age. "
                "Format the output as a clear bulleted list of key-value pairs."
            )
            response = model.generate_content([scale_prompt, scale_image])
            st.session_state.extracted_scale_metrics = response.text
            st.sidebar.success("Scale Data Extracted!")

# --- Sleep Tracker Section ---
st.sidebar.subheader("2. Sleep Tracker Data (Zepp / Any App)")
sleep_file = st.sidebar.file_uploader("Upload Sleep Screenshot", type=["png", "jpg", "jpeg"], key="sleep_upload")

if sleep_file is not None:
    sleep_image = Image.open(sleep_file)
    st.sidebar.image(sleep_image, caption="Sleep Screenshot", use_column_width=True)
    
    if st.sidebar.button("Process Sleep Screenshot"):
        with st.spinner("Extracting sleep performance data..."):
            sleep_prompt = (
                "You are an expert fitness data analyst. "
                "Examine this sleep tracking screenshot (e.g. Zepp, Garmin, Apple Health, Oura). "
                "Extract the following values: "
                "1. Total Sleep Duration (e.g., 9:40 or 9 hours 40 minutes) "
                "2. Overall Sleep Score and Rating (e.g., 71 FAIR) "
                "3. Any insights or sleep stage details mentioned (e.g., low deep sleep warning, REM, light sleep). "
                "Format the output as a clear bulleted list."
            )
            response = model.generate_content([sleep_prompt, sleep_image])
            st.session_state.extracted_sleep_metrics = response.text
            st.sidebar.success("Sleep Data Extracted!")

# Display Extracted Data in Sidebar
if st.session_state.extracted_scale_metrics:
    st.sidebar.markdown("### 📋 Body Composition")
    st.sidebar.write(st.session_state.extracted_scale_metrics)

if st.session_state.extracted_sleep_metrics:
    st.sidebar.markdown("### 😴 Sleep & Recovery")
    st.sidebar.write(st.session_state.extracted_sleep_metrics)

# 3. Main Dashboard Display
st.header("Goal Progress")
col1, col2, col3 = st.columns(3)

col1.metric(label="Target Weight", value="70.0 kg")
col2.metric(label="Target Body Fat", value="15 - 18%")
col3.metric(label="Milestone 1 Deadline", value="Late Nov 2026")

# 4. Full Workout Analyst Engine
st.header("Workout Analyst Engine")
if st.button("Run Full Analysis"):
    if st.session_state.extracted_scale_metrics or st.session_state.extracted_sleep_metrics:
        with st.spinner("Running full Workout Analyst workflow..."):
            
            body_data = st.session_state.extracted_scale_metrics or "No scale data uploaded."
            sleep_data = st.session_state.extracted_sleep_metrics or "No sleep data uploaded."
            
            analysis_prompt = (
                f"Perform full Workout Analyst workflow based on the latest metrics provided below.\n\n"
                f"--- SMART SCALE METRICS ---\n{body_data}\n\n"
                f"--- SLEEP & RECOVERY METRICS ---\n{sleep_data}\n\n"
                f"Analyze trends across body composition (weight, body fat, muscle mass, visceral fat, etc.) "
                f"and recovery (sleep duration, sleep score, readiness) to provide programming recommendations."
            )
            analysis_response = model.generate_content(analysis_prompt)
            st.write(analysis_response.text)
    else:
        st.warning("Please upload and process at least one screenshot first!")
