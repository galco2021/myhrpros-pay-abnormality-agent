![tests](https://github.com/galco2021/myhrpros-pay-abnormality-agent/actions/workflows/tests.yml/badge.svg)

# Payroll Pay Abnormality Agent (Demo)

**Live demo:** https://myhrpros-pay-abnormality-agent-4azhvqffjgj7ubrzqosjrz.streamlit.app/

A lightweight **flag → explain → route** prototype that detects paycheck outliers (e.g., $1,500 this week vs a typical $500 baseline) and produces an explainable exception list for **human review**.

**Design stance:** AI supports the process; humans make decisions (final review, approvals, and corrections).  
**Data policy:** This repo uses **synthetic demo data only**. Do not upload real payroll data to a public app.

## What it does
- Flags pay spikes/drops vs an employee baseline (median of prior periods)
- Adds explainability: baseline, ratio, triggered rules, and reviewer checklist
- Includes input validation (clear errors/warnings for missing columns, bad dates, duplicates)
- Provides a Streamlit UI to upload CSVs and download `pay_anomaly_flags.csv`
- Includes a one-page PDF sample deliverable and a Laserfiche-style “review packet” export pattern

 ## How to try it in 30 seconds
1. Open the **Live demo** link above.
2. In the left sidebar, click **Load included sample files** (synthetic data).
3. Scroll to **Flagged records** to see the anomalies (including a $1,500 vs ~$500 spike).
4. Use **Download flags CSV** to export the exception list (for review/audit workflow).

> Tip: Upload your own CSV to test validation—missing columns, bad dates, and duplicate employee+period rows return clear errors/warnings.

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

## Notes for a production implementation
- Keep this tool private and behind authentication
- Store outputs as an auditable “review packet” (e.g., Laserfiche template + metadata fields)
- Add governance: human final review, audit trail, data minimization, threshold tuning
