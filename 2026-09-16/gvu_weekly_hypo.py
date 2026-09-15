#!/usr/bin/env python3
"""
Day 2026-09-16 — Weekly excessive-hypoglycemia risk (GVU).

Generator: drafts next-week risk from last reading only (naive identity).
Verifier: GRADE-hypo + waveform length + TBR>4% rule from Cichosz 2024.
Updater: feeds critique back; 3 passes; logs each revision.

Success criterion (falsifiable):
  Flag HIGH iff ANY of:
    - TBR (<70 mg/dL) last week > 4%
    - GRADE_hypo component >= 2.0
    - waveform_length (sum |ΔG|) >= 400
  Else LOW. Draft must cite the firing features.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class WeekCGM:
    """Sparse daily-representative readings (mg/dL) over 7 days (~2–4 pts/day)."""

    readings: List[float]

    @property
    def n(self) -> int:
        return len(self.readings)

    @property
    def tbr_pct(self) -> float:
        if not self.readings:
            return 0.0
        return 100.0 * sum(1 for g in self.readings if g < 70.0) / self.n

    @property
    def grade_hypo(self) -> float:
        if not self.readings:
            return 0.0
        vals = [max(0.0, (70.0 - g) / 70.0) ** 2 * 10.0 for g in self.readings]
        return sum(vals) / len(vals)

    @property
    def waveform_length(self) -> float:
        if len(self.readings) < 2:
            return 0.0
        return sum(abs(self.readings[i] - self.readings[i - 1]) for i in range(1, len(self.readings)))

    @property
    def last(self) -> float:
        return self.readings[-1] if self.readings else 120.0


@dataclass
class Draft:
    risk: str
    rationale: str
    cited: List[str] = field(default_factory=list)


@dataclass
class Critique:
    passed: bool
    reason: str
    expected: str


def generate(week: WeekCGM, critique: Critique | None) -> Draft:
    last = week.last
    if critique is None:
        risk = "LOW" if last >= 70 else "HIGH"
        return Draft(
            risk=risk,
            rationale=f"Last reading {last:.0f} mg/dL → {risk} next-week risk.",
            cited=["last_glucose"],
        )

    must_high = "EXPECT HIGH" in critique.reason
    must_low = "EXPECT LOW" in critique.reason
    risk = "HIGH" if must_high else "LOW" if must_low else ("HIGH" if last < 70 else "LOW")
    cited = []
    bits = []
    if week.tbr_pct > 4.0:
        cited.append("TBR")
        bits.append(f"TBR={week.tbr_pct:.1f}%>4%")
    if week.grade_hypo >= 2.0:
        cited.append("GRADE_hypo")
        bits.append(f"GRADE_hypo={week.grade_hypo:.2f}>=2")
    if week.waveform_length >= 400:
        cited.append("waveform_length")
        bits.append(f"WL={week.waveform_length:.0f}>=400")
    if not bits:
        bits.append("no hypo-burden features fired")
    return Draft(
        risk=risk,
        rationale="Next-week risk " + risk + " because " + "; ".join(bits) + ".",
        cited=cited or ["none"],
    )


def verify(week: WeekCGM, draft: Draft) -> Critique:
    fire = week.tbr_pct > 4.0 or week.grade_hypo >= 2.0 or week.waveform_length >= 400
    expected = "HIGH" if fire else "LOW"
    ok_label = draft.risk == expected
    ok_cite = True
    if expected == "HIGH":
        needed = []
        if week.tbr_pct > 4.0:
            needed.append("TBR")
        if week.grade_hypo >= 2.0:
            needed.append("GRADE_hypo")
        if week.waveform_length >= 400:
            needed.append("waveform_length")
        ok_cite = any(n in draft.cited for n in needed)
    passed = ok_label and ok_cite
    reason = (
        f"{'PASS' if passed else 'FAIL'}: expected {expected}. "
        f"TBR={week.tbr_pct:.1f}% GRADE_hypo={week.grade_hypo:.2f} "
        f"WL={week.waveform_length:.0f}. "
        f"EXPECT {expected}. cited={draft.cited}"
    )
    return Critique(passed=passed, reason=reason, expected=expected)


def gvu_loop(week: WeekCGM, passes: int = 3) -> list[tuple[Draft, Critique]]:
    log: list[tuple[Draft, Critique]] = []
    critique: Critique | None = None
    for _ in range(passes):
        draft = generate(week, critique)
        critique = verify(week, draft)
        log.append((draft, critique))
        if critique.passed:
            break
    return log


def sample_week() -> WeekCGM:
    return WeekCGM(
        readings=[
            142, 88, 61, 155,
            130, 72, 58, 148,
            121, 95, 64, 171,
            110, 80, 59, 140,
            125, 118,
        ]
    )


def main() -> None:
    week = sample_week()
    print("=== Sample week stats ===")
    print(
        f"n={week.n} last={week.last:.0f} TBR={week.tbr_pct:.1f}% "
        f"GRADE_hypo={week.grade_hypo:.2f} WL={week.waveform_length:.0f}"
    )
    print("\n=== GVU passes ===")
    log = gvu_loop(week, passes=3)
    for i, (draft, crit) in enumerate(log, 1):
        print(f"\nPass {i}")
        print(f"  draft: {draft.risk} | {draft.rationale}")
        print(f"  verify: {crit.passed} | {crit.reason}")
    print("\nBefore:", log[0][0].risk, "|", log[0][0].rationale)
    print("After: ", log[-1][0].risk, "|", log[-1][0].rationale)


if __name__ == "__main__":
    main()
