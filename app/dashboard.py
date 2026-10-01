import os
import sys

import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from urjamind.analytics import compute_carbon, detect_anomalies, generate_schedule, get_energy_summary
from urjamind.data_loader import load_csv_from_bytes, load_sample_data

st.set_page_config(page_title="UrjaMind", page_icon="⚡", layout="wide")
st.title("UrjaMind Dashboard")
st.caption("SME energy intelligence, waste diagnosis, and carbon visibility")

uploaded_file = st.file_uploader("Upload plant CSV", type=["csv"])

if uploaded_file is not None:
    df = load_csv_from_bytes(uploaded_file.read())
    st.success(f"Loaded {uploaded_file.name}")
else:
    df = load_sample_data()
    st.info("Using sample factory dataset")

summary = get_energy_summary(df)
anomalies = detect_anomalies(df)
carbon = compute_carbon(df)
schedule = generate_schedule(df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total energy", f"{summary['total_energy_kwh']} kWh")
col2.metric("Avg load", f"{summary['average_load_kw']} kW")
col3.metric("Peak load", f"{summary['peak_load_kw']} kW")
col4.metric("Specific energy", f"{summary['specific_energy_kwh_per_unit']} kWh/unit")

st.subheader("Plant overview")
if "timestamp" in df.columns:
    chart_df = df.set_index("timestamp")
    if "total_kw" in chart_df.columns:
        st.line_chart(chart_df["total_kw"])

st.subheader("Anomaly overview")
if anomalies:
    for item in anomalies:
        st.warning(f"{item['type']}: {item['detail']}")
else:
    st.success("No major anomalies detected in the uploaded data.")

st.subheader("Tariff-aware schedule suggestions")
for item in schedule:
    st.write(item)

st.subheader("Carbon report")
st.json(carbon)

st.subheader("Data preview")
st.dataframe(df.head(10))
