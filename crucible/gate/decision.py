"""
Crucible — Decision Layer (v3: Adaptive Gating)
Same simple surface: decide(returns, regime="NORMAL").
Underneath, the strictness of the edge test FLEXES with market regime —
because the same statistical evidence means different things in calm vs chaos.

Adaptive Gating:
  In a volatile/crisis regime, noise is high, so we demand a STRICTER
  significance bar and more evidence before trusting a positive edge.
  In a calm regime, we relax slightly. The decision logic is unchanged —
  only the bar it must clear moves. It never freezes (breathing invariant).

Decisions: LEAVE | WATCH | LEAN_AWAY | RETIRE
"""
import math
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

TREND_MIN_N = 10
BASE_SIG_P = 0.10          # baseline significance bar (NORMAL regime)
BASE_CONF_FLOOR = 0.55     # baseline confidence needed to fully back a winner

# Regime strictness profile. >1 = stricter (harder to earn LEAVE), <1 = looser.
# Unknown/missing regime falls back to NORMAL (1.0) — never crashes.
REGIME_STRICTNESS = {
    "CRISIS":    1.6,
    "HIGH_VOL":  1.4,
    "FOMC_DAY":  1.25,
    "NORMAL":    1.0,
    "SIDEWAYS":  1.0,
    "CALM":      0.85,
    "LOW_VOL":   0.85,
}


def _strictness(regime: Optional[str]) -> float:
    if not regime:
        return 1.0
    return REGIME_STRICTNESS.get(str(regime).strip().upper(), 1.0)


@dataclass
class Decision:
    action: str
    confidence: float
    health: float
    reason: str
    n: int
    trend: Optional[float] = None
    p_value: Optional[float] = None
    regime: Optional[str] = None
    sig_bar: Optional[float] = None   # the regime-adjusted significance bar used


def _trimmed_mean(xs, trim=0.1):
    a = np.sort(np.asarray(xs, dtype=float))
    n = len(a)
    if n == 0:
        return 0.0
    k = int(n * trim)
    core = a[k:n - k] if n - 2 * k >= 1 else a
    return float(np.mean(core))


def _mean(xs):
    return float(np.mean(xs)) if len(xs) else 0.0


def _p_mean_gt_0(xs):
    a = np.asarray(xs, dtype=float)
    n = len(a)
    if n < 2:
        return 1.0
    sd = a.std(ddof=1)
    if sd < 1e-12:
        return 0.0 if a.mean() > 0 else 1.0
    t = a.mean() / (sd / np.sqrt(n))
    p = 0.5 * (1.0 - math.erf(t / np.sqrt(2)))
    return float(min(max(p, 0.0), 1.0))


def _trend(returns):
    if len(returns) < TREND_MIN_N:
        return None
    mid = len(returns) // 2
    first, second = _trimmed_mean(returns[:mid]), _trimmed_mean(returns[mid:])
    diff = second - first
    scale = (abs(first) + abs(second)) / 2 + 1e-9
    return float(np.clip(diff / scale, -1.0, 1.0))


def _confidence(n):
    return round(float(1.0 - np.exp(-n / 22.0)), 2)


def _trend_word(trend):
    if trend is None:
        return "trend n/a"
    if trend > 0.15:
        return "improving"
    if trend < -0.15:
        return "declining"
    return "flat"


def decide(returns: List[float], regime: str = "NORMAL",
           win_rate: float = None, soft_floor: int = 5) -> Decision:
    n = len(returns)
    strict = _strictness(regime)
    # regime-adjusted bars
    sig_bar = BASE_SIG_P / strict           # stricter regime => lower p needed
    conf_floor = min(0.9, BASE_CONF_FLOOR * strict)  # stricter => need more confidence

    if n < soft_floor:
        return Decision("WATCH", _confidence(n), 0.5,
                        f"only {n} outcomes — keep running and gather signal",
                        n, None, None, regime, round(sig_bar, 4))

    mean = _trimmed_mean(returns)
    wr = win_rate if win_rate is not None else float(np.mean([1.0 if r > 0 else 0.0 for r in returns]))
    trend = _trend(returns)
    conf = _confidence(n)
    p = _p_mean_gt_0(returns)
    tw = _trend_word(trend)
    significant = p < sig_bar
    sig_note = f"p={p:.3f} vs bar={sig_bar:.3f} [{regime}]"

    mean_score = float(1.0 / (1.0 + np.exp(-mean * 400)))
    trend_component = 0.5 if trend is None else (trend + 1) / 2
    sig_component = 1.0 - min(p, 1.0)
    health = float(np.clip(
        0.40 * mean_score + 0.20 * wr + 0.15 * trend_component + 0.25 * sig_component,
        0, 1))

    t = 0.0 if trend is None else trend

    if mean < -0.002 and t <= 0 and conf >= 0.7 and health < 0.4:
        return Decision("RETIRE", conf, round(health, 2),
                        f"sustained loss (mean={mean:+.4f}, {tw}, {sig_note}) — cut",
                        n, trend, round(p, 4), regime, round(sig_bar, 4))

    if mean < 0:
        return Decision("LEAN_AWAY", conf, round(health, 2),
                        f"negative (mean={mean:+.4f}, {tw}) — reduce exposure",
                        n, trend, round(p, 4), regime, round(sig_bar, 4))

    if t < -0.15:
        return Decision("LEAN_AWAY", conf, round(health, 2),
                        f"declining (mean={mean:+.4f}, {tw}) — lean away",
                        n, trend, round(p, 4), regime, round(sig_bar, 4))

    if mean > 0:
        if significant and conf >= conf_floor:
            return Decision("LEAVE", conf, round(health, 2),
                            f"significant edge (mean={mean:+.4f}, {sig_note}) — keep",
                            n, trend, round(p, 4), regime, round(sig_bar, 4))
        return Decision("WATCH", conf, round(health, 2),
                        f"positive but not significant for regime (mean={mean:+.4f}, {sig_note}) — watch",
                        n, trend, round(p, 4), regime, round(sig_bar, 4))

    return Decision("WATCH", conf, round(health, 2),
                    f"flat (mean={mean:+.4f}, {tw}) — observe",
                    n, trend, round(p, 4), regime, round(sig_bar, 4))
