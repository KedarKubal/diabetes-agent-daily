# 2026-09-06 — Multi-task forecast + hypo flag (GVU)

Run:

```
python3 gvu_multitask.py
```

No API keys. Deterministic heuristic agents.

- Generator: linear 30-min extrapolation; hypo_flag = last < 70
- Verifier: max 3 mg/dL/min change; multi-task consistency (forecast < 70 ⇒ flag)
- Updater: clip rate + align flag with forecast and falling-toward-hypo rule
