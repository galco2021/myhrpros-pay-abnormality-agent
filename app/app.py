# app/app.py
import pandas as pd
import streamlit as st

from detect_pay_anomalies import detect

st.set_page_config(page_title="Payroll Pay Abnormality Agent (Demo)", layout="wide")
st.title("Payroll Pay Abnormality Agent (Demo)")
st.caption("Flag -> explain -> route (human final review). Demo uses synthetic data only.")

with st.sidebar:
    st.header("Inputs")
    st.write("Upload a payroll export CSV (required) and known events CSV (optional).")
    pay_file = st.file_uploader("Payroll export (CSV)", type=["csv"])
    events_file = st.file_uploader("Known events (CSV, optional)", type=["csv"])

    st.header("Thresholds")
    spike_mult = st.number_input("Spike multiplier (>=)", value=2.0, min_value=1.1, step=0.1)
    drop_mult  = st.number_input("Drop multiplier (<=)", value=0.5, min_value=0.1, max_value=0.99, step=0.05)
    baseline_periods = st.number_input("Baseline lookback periods", value=6, min_value=3, max_value=26, step=1)
    min_history = st.number_input("Min history periods", value=3, min_value=2, max_value=baseline_periods, step=1)

    st.header("Demo data")
    st.write("Or load the included synthetic examples:")
    if st.button("Load included sample files"):
        st.session_state["use_sample"] = True

# Option to load included sample files
use_sample = st.session_state.get("use_sample", False)

def read_optional_csv(upload):
    if upload is None:
        return None
    return pd.read_csv(upload)

if use_sample and pay_file is None:
    payroll_df = pd.read_csv("data/payroll_export.csv")
    events_df = pd.read_csv("data/known_events.csv")
    st.success("Loaded included synthetic sample files.")
elif pay_file is not None:
    payroll_df = pd.read_csv(pay_file)
    events_df = read_optional_csv(events_file)
else:
    st.info("Upload a payroll export CSV to begin, or click 'Load included sample files' in the sidebar.")
    st.stop()

# Basic validation
required_cols = {"employee_id", "pay_period_end", "gross_pay"}
missing = required_cols - set(payroll_df.columns)
if missing:
    st.error(f"Payroll export missing required columns: {sorted(list(missing))}")
    st.stop()

# Override thresholds for this run by temporarily setting module-level constants
# (keeps the demo simple; production would pass these as parameters)
import detect_pay_anomalies as mod
mod.SPIKE_MULTIPLIER = float(spike_mult)
mod.DROP_MULTIPLIER = float(drop_mult)

# Run detection
flagged = detect(
    payroll_df=payroll_df,
    events_df=events_df,
    baseline_periods=int(baseline_periods),
    min_history=int(min_history),
)

# Overview
left, right = st.columns([1, 1])
with left:
    st.subheader("Summary")
    st.metric("Employees in file", payroll_df["employee_id"].nunique())
    st.metric("Pay periods", payroll_df["pay_period_end"].nunique())
    st.metric("Flags generated", len(flagged))

with right:
    st.subheader("How to interpret")
    st.write("High/Medium severity is based on how far current gross pay deviates from the employee's baseline.")
    st.write("This tool **flags** and **explains**; humans review and decide.")

st.divider()
st.subheader("Flagged records")
if len(flagged) == 0:
    st.success("No anomalies flagged with current thresholds.")
else:
    st.dataframe(flagged, use_container_width=True)

    st.download_button(
        "Download flags CSV",
        flagged.to_csv(index=False).encode("utf-8"),
        file_name="pay_anomaly_flags.csv",
        mime="text/csv",
    )

st.divider()
st.subheader("Sample deliverable")
st.write("Download the one-page PDF deliverable that describes the workflow, guardrails, and sample flagged records.")
with open("docs/MyHRPros_Pay_Abnormality_Agent_1pager.pdf", "rb") as f:
    st.download_button(
        "Download 1-page PDF",
        f.read(),
        file_name="MyHRPros_Pay_Abnormality_Agent_1pager.pdf",
        mime="application/pdf",
    )

st.caption("Reminder: This demo repository uses synthetic data only. Do not upload real payroll data to a public app.")
