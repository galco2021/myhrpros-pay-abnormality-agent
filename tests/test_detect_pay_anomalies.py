import sys
from pathlib import Path
import pandas as pd

# Allow tests to import from /app
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "app"))

from detect_pay_anomalies import detect  # noqa


def make_weekly_dates(start="2026-01-02", periods=7):
    return pd.date_range(start=start, periods=periods, freq="W-FRI")


def test_flags_unexplained_spike_as_high():
    dates = make_weekly_dates(periods=7)
    df = pd.DataFrame(
        {
            "employee_id": ["E1"] * 7,
            "pay_period_end": dates.astype(str),
            "gross_pay": [500, 500, 500, 500, 500, 500, 1500],  # 3.0x spike
            "earning_codes": ["REG"] * 7,
        }
    )

    out = detect(df, events_df=None)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["employee_id"] == "E1"
    assert row["pay_period_end"] == str(dates[-1].date())
    assert row["severity"] == "high"
    assert row["ratio_vs_baseline"] >= 3.0


def test_flags_drop_as_medium():
    dates = make_weekly_dates(periods=7)
    df = pd.DataFrame(
        {
            "employee_id": ["E2"] * 7,
            "pay_period_end": dates.astype(str),
            "gross_pay": [800, 800, 800, 800, 800, 800, 300],  # 0.375x
            "earning_codes": ["REG"] * 7,
        }
    )

    out = detect(df, events_df=None)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["severity"] == "medium"
    assert row["ratio_vs_baseline"] <= 0.5


def test_insufficient_history_produces_no_flags():
    # Only 3 periods total: not enough prior periods for baseline (min_history=3 requires 3 prior rows)
    dates = make_weekly_dates(periods=3)
    df = pd.DataFrame(
        {
            "employee_id": ["E3"] * 3,
            "pay_period_end": dates.astype(str),
            "gross_pay": [500, 500, 1500],  # would be a spike, but insufficient prior history
            "earning_codes": ["REG"] * 3,
        }
    )

    out = detect(df, events_df=None)
    assert len(out) == 0


def test_known_event_adds_context_note():
    dates = make_weekly_dates(periods=7)
    df = pd.DataFrame(
        {
            "employee_id": ["E4"] * 7,
            "pay_period_end": dates.astype(str),
            "gross_pay": [500, 500, 500, 500, 500, 500, 1500],
            "earning_codes": ["REG"] * 7,
        }
    )

    # Event within 21 days of last pay period
    events = pd.DataFrame(
        {
            "employee_id": ["E4"],
            "effective_date": [str((dates[-1] - pd.Timedelta(days=7)).date())],
            "event_type": ["bonus_payment"],
            "notes": ["Bonus approved"],
        }
    )

    out = detect(df, events_df=events)
    assert len(out) == 1
    assert "recent known change event" in out.iloc[0]["triggered_rules"]


def test_bonus_earning_code_adds_context_note():
    dates = make_weekly_dates(periods=7)
    df = pd.DataFrame(
        {
            "employee_id": ["E5"] * 7,
            "pay_period_end": dates.astype(str),
            "gross_pay": [500, 500, 500, 500, 500, 500, 1500],
            "earning_codes": ["REG", "REG", "REG", "REG", "REG", "REG", "BONUS"],
        }
    )

    out = detect(df, events_df=None)
    assert len(out) == 1
    assert "bonus/commission/retro" in out.iloc[0]["triggered_rules"].lower()
