# 2026-09-12 — Explainable 60-min hypo/hyper flag (GVU)

Opportunity: Duckworth et al. 2024 SHAP-style per-user feature attributions for 60-min hypo/hyper prediction, turned into a self-improving Generator–Verifier–Updater loop.

Run:

```bash
python3 gvu_agent.py
```

Smoke-test sample: falling CGM still above 70 mg/dL plus recent bolus and long meal gap.
- Pass 1 (naive last-point): LOW — FAIL
- Pass 2 (slope + insulin + meal-gap citations): HIGH/hypo — PASS
