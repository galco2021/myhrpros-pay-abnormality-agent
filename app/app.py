# app/app.py
import pandas as pd
import streamlit as st

from detect_pay_anomalies import detect


def validate_payroll_export(df: pd.DataFrame):
    """
    Validate payroll export input.
    Required columns: employee_id, pay_period_end, gross_pay
    Returns: (errors: list[str], warnings: list[str])
    """
    errors, warnings = [], []

    required = {"employee_id", "pay_period_end", "gross_pay"}
    missing = required - set(df.columns)
    if missing:
        errors.append(f"Missing required columns: {sorted(list(missing))}")
        return errors, warnings

    # employee_id: no blanks
    emp = df["employee_id"].astype(str)
    if df["employee_id"].isna().any() or (emp.str.strip() == "").any():
        errors.append("employee_id has blank values. Each row must have an employee_id.")

    # pay_period_end: parseable dates
    parsed_dates = pd.to_datetime(df["pay_period_end"], errors="coerce")
    if parsed_dates.isna().any():
        bad = df.loc[parsed_dates.isna(), "pay_period_end"].head(5).tolist()
        errors.append(f"pay_period_end has un-parseable dates (examples): {bad}")

    # gross_pay: numeric
    gross = pd.to_numeric(df["gross_pay"], errors="coerce")
    if gross.isna().any():
        bad = df.loc[gross.isna(), "gross_pay"].head(5).tolist()
        errors.append(f"gross_pay has non-numeric values (examples): {bad}")
    else:
        if (gross < 0).any():
            warnings.append("gross_pay contains negative values. Verify reversals/adjustments are intended.")

    # duplicates: employee_id + pay period
    if not parsed_dates.isna().all():
        tmp = df.copy()
        tmp["_pp"] = parsed_dates.dt.date.astype(str)
        dupes = tmp.duplicated(subset=["employee_id", "_pp"], keep=False)
        if dupes.any():
            examples = tmp.loc[dupes, ["employee_id", "_pp"]].head(5).to_dict("records")
            warnings.append(
                "Duplicate employee_id + pay_period_end rows found (examples): "
                f"{examples}. If multiple rows per employee/period are expected, aggregate first."
            )

    return errors, warnings


def validate_known_events(df: pd.DataFrame):
    """
    Validate known events input (optional).
    Required columns: employee_id, effective_date, event_type
    Returns: (errors: list[str], warnings: list[str])
    """
    errors, warnings = [], []

    required = {"employee_id", "effective_date", "event_type"}
    missing = required - set(df.columns)
    if missing:
        errors.append(f"Known events file missing required columns: {sorted(list(missing))}")
        return errors, warnings

    parsed = pd.to_datetime(df["effective_date"], errors="coerce")
    if parsed.isna().any():
        bad = df.loc[parsed.isna(), "effective_date"].head(5).tolist()
        warnings.append(f"effective_date has un-parseable values (examples): {bad}")

    return errors, warnings


# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="Payroll Pay Abnormality Agent (Demo)", layout="wide")
st.title("Payroll Pay Abnormality Agent (Demo)")
st.caption("Flag → explain → route (human final review). Demo uses synthetic data only.")

with st.sidebar:
    st.header("Inputs")
    st.write("Upload a payroll export CSV (required) and known events CSV (optional).")
    pay_file = st.file_uploader("Payroll export (CSV)", type=["csv"])
    events_file = st.file_uploader("Known events (CSV, optional)", type=["csv"])

    st.header("Thresholds")
    spike_mult = st.number_input("Spike multiplier (≥)", value=2.0, min_value=1.1, step=0.1)
    drop_mult = st.number_input("Drop multiplier (≤)", value=0.5, min_value=0.1, max_value=0.99, step=0.05)
    baseline_periods = st.number_input("Baseline lookback periods", value=6, min_value=3, max_value=26, step=1)
    min_history = st.number_input("Min history periods", value=3, min_value=2, max_value=int(baseline_periods), step=1)

    st.header("Demo data")
    st.write("Or load the included synthetic examples:")
    if st.button("Load included sample files"):
        st.session_state["use_sample"] = True

use_sample = st.session_state.get("use_sample", False)


def read_optional_csv(upload):
    if upload is None:
        return None
    return pd.read_csv(upload)


# Load data
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

# ----------------------------
# Validation
# ----------------------------
pay_errors, pay_warnings = validate_payroll_export(payroll_df)
for w in pay_warnings:
    st.warning(w)
if pay_errors:
    for e in pay_errors:
        st.error(e)
    st.stop()

if events_df is not None:
    ev_errors, ev_warnings = validate_known_events(events_df)
    for w in ev_warnings:
        st.warning(w)
    if ev_errors:
        for e in ev_errors:
            st.warning(e)
        st.warning("Known events file will be ignored due to format issues.")
        events_df = None

# ----------------------------
# Run detection
# ----------------------------
# Override thresholds (keeps the demo simple; production would pass these as parameters)
import detect_pay_anomalies as mod  # noqa: E402

mod.SPIKE_MULTIPLIER = float(spike_mult)
mod.DROP_MULTIPLIER = float(drop_mult)

flagged = detect(
    payroll_df=payroll_df,
    events_df=events_df,
    baseline_periods=int(baseline_periods),
    min_history=int(min_history),
)

# ----------------------------
# Output
# ----------------------------
left, right = st.columns([1, 1])
with left:
    st.subheader("Summary")
    st.metric("Employees in file", payroll_df["employee_id"].nunique())
    st.metric("Pay periods", payroll_df["pay_period_end"].nunique())
    st.metric("Flags generated", len(flagged))

with right:
    st.subheader("How to interpret")
    st.write("High/Medium severity is based on how far current gross pay deviates from the employee's baseline.")
    st.write("This tool flags and explains; humans review and decide.")

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

try:
    with open("docs/MyHRPros_Pay_Abnormality_Agent_1pager.pdf", "rb") as f:
        st.download_button(
            "Download 1-page PDF",
            f.read(),
            file_name="MyHRPros_Pay_Abnormality_Agent_1pager.pdf",
            mime="application/pdf",
        )
except FileNotFoundError:
    st.warning("PDF not found at docs/MyHRPros_Pay_Abnormality_Agent_1pager.pdf. Check your repo file paths.")

st.caption("Reminder: This demo repository uses synthetic data only. Do not upload real payroll data to a public app.")
