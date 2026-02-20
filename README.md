![tests](https://github.com/galco2021/myhrpros-pay-abnormality-agent/actions/workflows/tests.yml/badge.svg)
# Payroll Pay Abnormality Agent (Demo)

A lightweight **flag → explain → route** prototype that detects paycheck outliers (e.g., $1,500 this week vs typical $500) and produces an explainable exception list for human review.

**Design stance:** AI supports the process; humans make decisions (final review, approvals, and corrections).  
**Data policy:** This repository includes **synthetic demo data only**. Do not upload real payroll data to a public app.
**Live demo:** https://myhrpros-pay-abnormality-agent-4azhvqffjgj7ubrzqosjrz.streamlit.app/

## What it does
- Flags pay spikes/drops vs an employee baseline (median of prior periods)
- Adds explainability: ratio vs baseline, triggered rules, reviewer checklist
- Provides a Streamlit UI to upload CSVs and download `pay_anomaly_flags.csv`
- Includes a one-page PDF sample deliverable and a Laserfiche-style “review packet” export pattern

## Repo layout
```
/app
  app.py                    # Streamlit UI
  detect_pay_anomalies.py   # core detection logic
/data
  payroll_export.csv        # synthetic sample payroll export
  known_events.csv          # synthetic approved change events
/docs
  MyHRPros_Pay_Abnormality_Agent_1pager.pdf
/outputs
  pay_anomaly_flags.csv     # sample output from the synthetic dataset
requirements.txt
```

## Run locally
```bash
pip install -r requirements.txt
streamlit run app/app.py
```

## Deploy on Streamlit Community Cloud
1. Push this repo to GitHub (public is OK because data is synthetic)
2. Go to Streamlit Community Cloud → **New app**
3. Select your repo and set **Main file path** to:
   - `app/app.py`
4. Deploy

## CSV formats

**Payroll export (required columns):**
- `employee_id`
- `pay_period_end`
- `gross_pay`

**Optional payroll columns:**
- `earning_codes` (e.g., `REG`, `BONUS`, `RETRO`)

**Known events (optional):**
- `employee_id`
- `effective_date`
- `event_type` (e.g., `rate_change`, `loa_unpaid`, `bonus_payment`)
- `notes`

![Demo screenshot](docs/screenshots/Screenshot 2026-02-20 160218.png)

## Notes for a production implementation
- Keep this tool private and behind authentication
- Store outputs as an auditable “review packet” (e.g., Laserfiche template + metadata fields)
- Add governance: human final review, audit trail, data minimization, threshold tuning
