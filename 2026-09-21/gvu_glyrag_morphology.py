#!/usr/bin/env python3
"""Day 2026-09-21 — GlyRAG-style CGM morphology context + retrieval hypo flag.

Generator-Verifier-Updater prototype of the underexploited insight in
GlyRAG (context-aware RAG for glucose forecasting): CGM is not just a
number series. An agent that *names the waveform morphology* and retrieves
similar past windows can correct a last-point-only risk flag.

Success criterion (falsifiable):
  PASS only if ALL of:
    1. morphology tags include every feature that is true on the window
       among {descending_run, low_valley, high_cv}
    2. retrieved_id matches the library neighbor with the same tag set
    3. risk == HIGH iff descending_run and (low_valley or last_glucose < 90)
    4. citations include >= 2 of {slope_20min, min_glucose, cv, retrieved_id}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


# Falling late-afternoon window: last point still 92 (looks "ok") but
# steep descent + valley + high CV — last-point generator would say LOW.
SAMPLE_WINDOW = [148, 142, 131, 118, 104, 96, 88, 92]

LIBRARY = [
    {
        "id": "win_rebound_ok",
        "tags": frozenset({"high_cv"}),
        "risk": "LOW",
    },
    {
        "id": "win_steep_valley",
        "tags": frozenset({"descending_run", "low_valley", "high_cv"}),
        "risk": "HIGH",
    },
    {
        "id": "win_flat_eugly",
        "tags": frozenset(),
        "risk": "LOW",
    },
]


def features(window: list[float]) -> dict[str, Any]:
    last = window[-1]
    minutes = 20.0
    slope = (window[-1] - window[-5]) / minutes
    mn = min(window)
    mean = sum(window) / len(window)
    var = sum((x - mean) ** 2 for x in window) / len(window)
    cv = (var ** 0.5) / mean if mean else 0.0
    tags = set()
    if slope < -1.0:
        tags.add("descending_run")
    if mn < 90:
        tags.add("low_valley")
    if cv > 0.15:
        tags.add("high_cv")
    expected_risk = (
        "HIGH"
        if ("descending_run" in tags and ("low_valley" in tags or last < 90))
        else "LOW"
    )
    neighbor = next(
        (w for w in LIBRARY if w["tags"] == frozenset(tags)),
        LIBRARY[-1],
    )
    return {
        "last": last,
        "slope_20min": round(slope, 3),
        "min_glucose": mn,
        "cv": round(cv, 3),
        "true_tags": tags,
        "expected_risk": expected_risk,
        "retrieved_id": neighbor["id"],
    }


@dataclass
class Draft:
    risk: str
    tags: list[str]
    retrieved_id: str
    citations: list[str]
    rationale: str


def generator(window: list[float], critique: str | None = None) -> Draft:
    feat = features(window)
    if critique is None:
        risk = "HIGH" if feat["last"] < 70 else "LOW"
        return Draft(
            risk=risk,
            tags=["last_point_ok"] if risk == "LOW" else ["last_point_low"],
            retrieved_id="none",
            citations=["last_glucose"],
            rationale=f"Last CGM={feat['last']} mg/dL; draft {risk} without morphology.",
        )

    tags = sorted(feat["true_tags"])
    return Draft(
        risk=feat["expected_risk"],
        tags=tags,
        retrieved_id=feat["retrieved_id"],
        citations=["slope_20min", "min_glucose", "cv", "retrieved_id"],
        rationale=(
            f"Morphology {tags} retrieved {feat['retrieved_id']}; "
            f"slope={feat['slope_20min']} min={feat['min_glucose']} cv={feat['cv']}. "
            f"Critique: {critique}"
        ),
    )


def verifier(draft: Draft, window: list[float]) -> dict[str, Any]:
    feat = features(window)
    reasons: list[str] = []
    missing = feat["true_tags"] - set(draft.tags)
    if missing:
        reasons.append(f"missing morphology tags: {sorted(missing)}")
    if draft.retrieved_id != feat["retrieved_id"]:
        reasons.append(
            f"retrieved_id {draft.retrieved_id!r} != {feat['retrieved_id']!r}"
        )
    if draft.risk != feat["expected_risk"]:
        reasons.append(f"risk {draft.risk} != expected {feat['expected_risk']}")
    needed = {"slope_20min", "min_glucose", "cv", "retrieved_id"}
    if len(set(draft.citations) & needed) < 2:
        reasons.append("need >=2 of slope_20min/min_glucose/cv/retrieved_id")
    passed = len(reasons) == 0
    return {
        "pass": passed,
        "reasons": reasons if reasons else ["ok: morphology+retrieval consistent"],
        "critique": (
            "Name descending_run/low_valley/high_cv from slope/min/cv; "
            "retrieve matching library window; set HIGH if descent+valley."
            if not passed
            else "meets success criterion"
        ),
        "features": {
            k: (sorted(v) if isinstance(v, set) else v) for k, v in feat.items()
        },
    }


def run_gvu(window: list[float], max_passes: int = 3) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    draft = generator(window, critique=None)
    for i in range(max_passes):
        verdict = verifier(draft, window)
        log.append({"pass": i, "draft": asdict(draft), "verifier": verdict})
        if verdict["pass"]:
            break
        draft = generator(window, critique=verdict["critique"])
    return log


def main() -> None:
    log = run_gvu(SAMPLE_WINDOW)
    out_dir = Path(__file__).resolve().parent
    (out_dir / "run_log.json").write_text(json.dumps(log, indent=2))
    first = log[0]["draft"]
    last = log[-1]["draft"]
    smoke = (
        f"BEFORE pass0: risk={first['risk']} tags={first['tags']} "
        f"retrieved={first['retrieved_id']}\n"
        f"AFTER  pass{log[-1]['pass']}: risk={last['risk']} tags={last['tags']} "
        f"retrieved={last['retrieved_id']}\n"
        f"verifier_final_pass={log[-1]['verifier']['pass']}\n"
    )
    (out_dir / "SMOKE.txt").write_text(smoke)
    print(smoke)
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
