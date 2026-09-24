# 2026-09-25 — Time-to-hypoglycemia GVU

Monitoring angle. Seed: Onwuchekwa et al., EMBC 2024 — time-to-event bins, not a binary hypo flag.

```
python3 gvu_time_to_hypo.py
```

Verifier requires `time_bin` ∈ {0-30, 30-60, 60-120, >120} plus slope and HR citations matching a deterministic rule.
