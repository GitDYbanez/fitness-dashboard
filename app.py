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

# 2. Sidebar Input Option (Manual vs Screenshot)
st.sidebar.header("Log Daily Metrics")

log_method = st.sidebar.radio("Input Method", ["Manual Input", "Upload Smart Scale Screenshot"])

weight = 75.50
body_fat = 27.1

if log_method == "Upload Smart Scale Screenshot":
    uploaded_file = st.sidebar.file_uploader("Upload screenshot", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.sidebar.image(image, caption="Uploaded Scale Data", use_column_width=True)
        
        if st.sidebar.button("Extract Metrics from Photo"):
            with st.spinner("Extracting data with Gemini..."):
                ocr_prompt = (
                    "Look at this smart scale app screenshot. "
                    "Extract the Weight in kg and Body Fat percentage. "
                    "Return ONLY a clear summary like: Weight: X kg, Body Fat: Y%."
                )
                response = model.generate_content([ocr_prompt, image])
                st.sidebar.success("Extracted Data:")
                st.sidebar.write(response.text)

else:
    date = st.sidebar.date_input("Date")
    weight = st.sidebar.number_input("Weight (kg)", value=75.50, step=0.1)
    body_fat = st.sidebar.number_input("Body Fat (%)", value=27.1, step=0.1)
    sleep = st.sidebar.number_input("Sleep (hours)", value=8.0, step=0.5)

# 3. Progress KPI Cards & Dashboard Visuals
st.header("Goal Progress")
col1, col2, col3 = st.columns(3)

start_weight = 75.50
target_weight = 70.0
weight_progress = min(max((start_weight - weight) / (start_weight - target_weight), 0.0), 1.0)

col1.metric(label="Current Weight", value=f"{weight} kg", delta=f"{round(weight - start_weight, 2)} kg")
col2.metric(label="Body Fat %", value=f"{body_fat}%")
col3.metric(label="Target Weight", value=f"{target_weight} kg")

st.progress(weight_progress, text=f"Milestone 1 Progress: {int(weight_progress * 100)}%")

# 4. Workout Analyst Analysis
st.header("Workout Analyst Prompting")
if st.button("Run Full Analysis"):
    prompt = f"Analyze my progress: Current Weight: {weight}kg, Body Fat: {body_fat}%."
    response = model.generate_content(prompt)
    st.write(response.text)
