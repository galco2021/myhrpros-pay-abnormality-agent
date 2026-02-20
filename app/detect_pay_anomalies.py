# app/detect_pay_anomalies.py
# Synthetic demo: Payroll pay abnormality detector (flag -> explain -> route).
# NOTE: For demo/portfolio use only. Do not run on real payroll data without explicit permission and secure handling.

from __future__ import annotations
import pandas as pd
import numpy as np

# Defaults tuned for weekly payroll demos; adjust per organization policy.
BASELINE_PERIODS = 6           # rolling lookback (prior periods)
MIN_HISTORY = 3               # minimum history required to score
SPIKE_MULTIPLIER = 2.0        # >=2x baseline is a spike
DROP_MULTIPLIER = 0.5         # <=0.5x baseline is a drop
HIGH_SPIKE_MULT = 3.0         # >=3x baseline is high severity
HIGH_DROP_MULT = 0.33         # <=0.33x baseline is high severity
EVENT_WINDOW_DAYS = 21        # "recent event" lookup window

def _median(series: pd.Series) -> float:
    s = series.dropna()
    return float(s.median()) if len(s) else np.nan

def _severity(ratio: float) -> str:
    if np.isnan(ratio):
        return "insufficient_history"
    if ratio >= HIGH_SPIKE_MULT or ratio <= HIGH_DROP_MULT:
        return "high"
    if ratio >= SPIKE_MULTIPLIER or ratio <= DROP_MULTIPLIER:
        return "medium"
    return "none"

def _explanation(current: float, baseline: float, ratio: float, rules: list[str]) -> str:
    base = f"Current gross pay ${current:,.2f} vs baseline ${baseline:,.2f} ({ratio:.2f}x)."
    if rules:
        return base + " Triggered: " + "; ".join(rules) + "."
    return base

def detect(
    payroll_df: pd.DataFrame,
    events_df: pd.DataFrame | None = None,
    baseline_periods: int = BASELINE_PERIODS,
    min_history: int = MIN_HISTORY
) -> pd.DataFrame:
    """Return one row per flagged pay period with explainability fields.

    Required payroll_df columns:
      - employee_id
      - pay_period_end (date or date-like string)
      - gross_pay (numeric)

    Optional payroll_df columns:
      - earning_codes (string)
    """
    df = payroll_df.copy()
    df["pay_period_end"] = pd.to_datetime(df["pay_period_end"])
    df = df.sort_values(["employee_id", "pay_period_end"])

    if events_df is None:
        events_df = pd.DataFrame(columns=["employee_id", "effective_date", "event_type", "notes"])
    else:
        events_df = events_df.copy()
        events_df["effective_date"] = pd.to_datetime(events_df["effective_date"])

    flags: list[dict] = []

    for emp_id, g in df.groupby("employee_id", sort=False):
        g = g.copy()
        g["prior_gross"] = g["gross_pay"].shift(1)
        g["baseline_gross"] = (
            g["prior_gross"]
            .rolling(window=baseline_periods, min_periods=min_history)
            .apply(_median, raw=False)
        )

        emp_events = events_df[events_df["employee_id"] == emp_id].copy()

        for _, row in g.iterrows():
            baseline = row["baseline_gross"]
            if pd.isna(baseline) or float(baseline) <= 0:
                continue

            current = float(row["gross_pay"])
            ratio = current / float(baseline)
            period_end = row["pay_period_end"]

            rules: list[str] = []
            if ratio >= SPIKE_MULTIPLIER:
                rules.append(f"pay_spike >= {SPIKE_MULTIPLIER}x baseline")
            if ratio <= DROP_MULTIPLIER:
                rules.append(f"pay_drop <= {DROP_MULTIPLIER}x baseline")

            # earning code hint (not a suppression; just context for reviewers)
            earning_codes = str(row.get("earning_codes", "")).upper()
            has_known_spike_codes = any(x in earning_codes for x in ["BONUS", "COMMISSION", "RETRO"])
            if has_known_spike_codes and ratio >= SPIKE_MULTIPLIER:
                rules.append("note: bonus/commission/retro code present (may be expected)")

            # recent known events hint
            has_event = not emp_events[
                (emp_events["effective_date"] <= period_end) &
                (emp_events["effective_date"] >= (period_end - pd.Timedelta(days=EVENT_WINDOW_DAYS)))
            ].empty
            if has_event:
                rules.append("note: recent known change event on file")

            sev = _severity(ratio)
            if sev in ["medium", "high"]:
                flags.append({
                    "employee_id": emp_id,
                    "pay_period_end": period_end.date().isoformat(),
                    "severity": sev,
                    "current_gross_pay": round(current, 2),
                    "baseline_gross_pay": round(float(baseline), 2),
                    "ratio_vs_baseline": round(float(ratio), 3),
                    "triggered_rules": " | ".join(rules),
                    "explanation": _explanation(current, float(baseline), float(ratio), rules),
                    "recommended_checks": (
                        "Verify earning codes; verify hours; verify rate change approval; "
                        "verify proration/new hire/term; confirm manager sign-off"
                    )
                })

    out = pd.DataFrame(flags)
    if len(out):
        out = out.sort_values(["severity", "pay_period_end"], ascending=[False, False])
    return out
