import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px

# 1. Page Config
st.set_page_config(page_title="Fitness & Workout Dashboard", layout="wide")
st.title("🏋️‍♂️ Fitness & Workout Analyst Dashboard")

# 2. Configure Gemini API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. Sidebar inputs for logging data
st.sidebar.header("Log Daily Metrics")
date = st.sidebar.date_input("Date")
weight = st.sidebar.number_input("Weight (kg)", value=75.5, step=0.1)
body_fat = st.sidebar.number_input("Body Fat (%)", value=27.1, step=0.1)
sleep = st.sidebar.number_input("Sleep (hours)", value=8.0, step=0.5)

# 4. Progress KPI Cards & Dials
st.header("Goal Progress")
col1, col2, col3 = st.columns(3)

start_weight = 75.5
target_weight = 70.0
weight_progress = min(max((start_weight - weight) / (start_weight - target_weight), 0.0), 1.0)

col1.metric(label="Current Weight", value=f"{weight} kg", delta=f"{round(weight - start_weight, 2)} kg")
col2.metric(label="Body Fat %", value=f"{body_fat}%")
col3.metric(label="Target Weight", value=f"{target_weight} kg")

st.progress(weight_progress, text=f"Milestone 1 Progress: {int(weight_progress * 100)}%")

# 5. Visual Charts
st.header("Trends & Analytics")
# Example dataframe - replace with your Google Sheets data loader
data = pd.DataFrame({
    'Date': ['2026-09-15', date.strftime('%Y-%m-%d')],
    'Weight': [75.5, weight],
    'BodyFat': [27.1, body_fat]
})

fig = px.line(data, x='Date', y=['Weight', 'BodyFat'], title="Weight & Body Fat Trajectory")
st.plotly_chart(fig, use_container_width=True)

# 6. Gemini Integration Button
st.header("Workout Analyst Prompting")
if st.button("Run Full Analysis"):
    prompt = f"Analyze my progress: Current Weight: {weight}kg, Body Fat: {body_fat}%, Sleep: {sleep}hrs."
    response = model.generate_content(prompt)
    st.write(response.text)
