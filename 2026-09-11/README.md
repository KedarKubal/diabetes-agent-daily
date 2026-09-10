# 2026-09-11 — Night Low 7-hour GVU

Monitoring angle. Prototype of a 7-hour nocturnal hypoglycemia risk flag that refuses last-point-only scoring.

```
python gvu_nocturnal_hypo.py
```

Pass 1: last=72 → MEDIUM (fails verifier).
Pass 2: slope + TB80 → HIGH (passes).
