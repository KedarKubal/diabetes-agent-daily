# 2026-09-05 — Glycemic Window Verifier (GVU)

Educational prototype only. Not a medical device.

Run:

```
python gvu_glycemic.py
```

Generator drafts a hypo flag + risk score from mock CGM.
Verifier fails if any of the last 3 readings is <70 and the flag is false, or if risk <40 in that case.
Updater re-runs the generator with the critique (max 3 passes).
