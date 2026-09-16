#!/usr/bin/env python3
"""
Day 2026-09-17 GVU prototype
Week-ahead RPM hypo-priority + night/day wearable feature shift.

Generator: drafts a care-queue priority from last CGM point only (naive).
Verifier: ADA level-2 hypo (CGM <54 mg/dL for >=15 min) OR
          night-window cardiac pattern (HR up + HRV down vs personal baseline).
Updater: feeds critique back; 3 passes.

Not medical advice. Synthetic sample only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


LEVEL2_MGDL = 54
LEVEL2_MINUTES = 15
CGM_INTERVAL_MIN = 5
LEVEL2_READINGS = LEVEL2_MINUTES // CGM_INTERVAL_MIN  # 3 consecutive


@dataclass
class WearableWindow:
    period: str  # "day" | "night"
    hr_bpm: float
    hrv_ms: float
    baseline_hr: float
    baseline_hrv: float


@dataclass
class PatientSample:
    patient_id: str
    cgm_mgdl: list[float]  # last-week 5-min series (short demo slice)
    wearable: WearableWindow


@dataclass
class Draft:
    priority: str  # LOW | MEDIUM | HIGH
    reason: str
    cited_features: list[str] = field(default_factory=list)
    week_ahead_hypo_prob: float = 0.0


def consecutive_level2(cgm: list[float]) -> int:
    """Longest run of readings < 54 mg/dL."""
    best = run = 0
    for v in cgm:
        if v < LEVEL2_MGDL:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def tbr_pct(cgm: list[float], thresh: float = 70.0) -> float:
    if not cgm:
        return 0.0
    return 100.0 * sum(1 for v in cgm if v < thresh) / len(cgm)


def night_cardiac_risk(w: WearableWindow) -> bool:
    if w.period != "night":
        return False
    hr_up = w.hr_bpm >= w.baseline_hr * 1.08
    hrv_down = w.hrv_ms <= w.baseline_hrv * 0.85
    return hr_up and hrv_down


def generate(sample: PatientSample, critique: str | None = None) -> Draft:
    last = sample.cgm_mgdl[-1]
    if critique is None:
        if last < 70:
            return Draft("MEDIUM", f"last CGM={last:.0f} <70", ["last_cgm"], 0.25)
        return Draft("LOW", f"last CGM={last:.0f} in range", ["last_cgm"], 0.10)

    run = consecutive_level2(sample.cgm_mgdl)
    tbr = tbr_pct(sample.cgm_mgdl)
    cardiac = night_cardiac_risk(sample.wearable)
    cited: list[str] = []
    score = 0.12
    if run >= LEVEL2_READINGS:
        cited.append(f"level2_run={run}*5min")
        score += 0.45
    if tbr >= 4.0:
        cited.append(f"TBR70={tbr:.1f}%")
        score += 0.18
    if cardiac:
        cited.append(
            f"night_HR={sample.wearable.hr_bpm:.0f}>{sample.wearable.baseline_hr:.0f}*1.08"
            f";HRV={sample.wearable.hrv_ms:.0f}<{sample.wearable.baseline_hrv:.0f}*0.85"
        )
        score += 0.28
    if sample.wearable.period == "night":
        cited.append("night_model_weight")
        score += 0.05
    score = min(score, 0.95)
    if score >= 0.55 or (run >= LEVEL2_READINGS and cardiac):
        pri = "HIGH"
    elif score >= 0.30:
        pri = "MEDIUM"
    else:
        pri = "LOW"
    return Draft(pri, critique.split(";")[0][:80], cited or ["revised"], score)


def verify(sample: PatientSample, draft: Draft) -> tuple[bool, str]:
    must_high = consecutive_level2(sample.cgm_mgdl) >= LEVEL2_READINGS or night_cardiac_risk(
        sample.wearable
    )
    reasons: list[str] = []
    if must_high and draft.priority != "HIGH":
        reasons.append(
            "FAIL: level-2 streak or night HR↑/HRV↓ present but priority "
            f"is {draft.priority}; escalate to HIGH and cite both CGM+wearable"
        )
    if not must_high and draft.priority == "HIGH":
        reasons.append("FAIL: HIGH without level-2 streak or night cardiac pattern")
    if must_high and draft.priority == "HIGH" and len(draft.cited_features) < 2:
        reasons.append("FAIL: HIGH requires >=2 cited features (week CGM + night cardiac)")
    if reasons:
        return False, "; ".join(reasons)
    return True, f"PASS: priority={draft.priority} features={draft.cited_features}"


def gvu_loop(sample: PatientSample, max_passes: int = 3) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    critique: str | None = None
    draft = Draft("LOW", "uninitialized")
    for i in range(1, max_passes + 1):
        draft = generate(sample, critique)
        ok, msg = verify(sample, draft)
        log.append(
            {
                "pass": i,
                "priority": draft.priority,
                "prob": round(draft.week_ahead_hypo_prob, 3),
                "cited": draft.cited_features,
                "verifier": "PASS" if ok else "FAIL",
                "detail": msg,
            }
        )
        if ok:
            break
        critique = msg
    return log


def main() -> None:
    sample = PatientSample(
        patient_id="demo-17",
        cgm_mgdl=[
            142, 138, 121, 98, 72, 58, 51, 49, 50, 63, 88, 110, 118
        ],
        wearable=WearableWindow(
            period="night",
            hr_bpm=86,
            hrv_ms=28,
            baseline_hr=72,
            baseline_hrv=42,
        ),
    )
    print("SAMPLE last_cgm=", sample.cgm_mgdl[-1], "period=", sample.wearable.period)
    log = gvu_loop(sample)
    print("BEFORE (pass 1):", log[0])
    print("AFTER  (last)  :", log[-1])
    for row in log:
        print(f"  pass {row['pass']}: {row['priority']} p={row['prob']} {row['verifier']} {row['cited']}")


if __name__ == "__main__":
    main()
