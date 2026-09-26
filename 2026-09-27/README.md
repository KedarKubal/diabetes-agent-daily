# 2026-09-27 — Soft-label hypoglycemia GVU

Monitoring angle. Prototypes the MT-HypoNet (iScience 2026) insight: do not treat 69 vs 71 mg/dL as a hard class cliff. Use a statistically guided soft score in the 65–75 band.

```
python3 gvu_softlabel_hypo.py
```

Verifier (all must hold):
- score in [0, 1]
- last < 65 → score ≥ 0.80 and HIGH
- last > 80 → score ≤ 0.20 and LOW
- 65–75 → score in [0.35, 0.65] and MEDIUM
- cites include `last_glucose` and `slope`
