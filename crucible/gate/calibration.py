"""
Crucible — Self-Calibrating Regime Strictness
Replaces hardcoded strictness constants with values DERIVED from ARIA's own
outcome history per regime. Number-based, bounded, smoothed — adapts over time
without whipsawing.

strictness(regime) is driven by two measured quantities:
  noise   = std / (|mean| + eps)   how much randomness drowns the signal
  penalty = extra strictness if the regime's mean outcome is negative
            (a losing regime's "edges" should be trusted LESS, even if clean)

Guardrails:
  CLAMP        result kept in [0.7, 2.0]
  MIN_DATA     regime needs >= MIN_OUTCOMES before it moves off 1.0
  SLOW_BLEND   new value blended with previous (EMA) so it drifts, never jumps
"""
import numpy as np

CLAMP_LO, CLAMP_HI = 0.7, 2.0
MIN_OUTCOMES = 25
BLEND = 0.25            # weight on the new reading; 0.75 keeps the old => slow
NOISE_REF = 20.0        # noise ratio that maps to ~baseline strictness


def _raw_strictness(mean: float, std: float, n: int) -> float:
    """Map measured noise + sign-of-mean to a strictness multiplier."""
    noise = std / (abs(mean) + 1e-9)
    # noise term: more noise => stricter. log-scaled so extremes don't explode.
    noise_term = 1.0 + 0.5 * np.log1p(noise / NOISE_REF)
    # losing-regime penalty: negative mean adds strictness proportional to size
    penalty = 1.0 + (8.0 * abs(mean) if mean < 0 else 0.0)
    return float(noise_term * penalty)


def calibrate(history_by_regime: dict, prev: dict = None) -> dict:
    """
    history_by_regime: {regime: [pnl_pct, ...]}
    prev:              {regime: strictness} from last cycle (for smoothing)
    returns:           {regime: strictness} clamped + smoothed
    """
    prev = prev or {}
    out = {}
    for regime, vals in history_by_regime.items():
        a = np.asarray(vals, dtype=float)
        n = len(a)
        if n < MIN_OUTCOMES:
            out[regime] = prev.get(regime, 1.0)      # not enough data -> hold
            continue
        raw = _raw_strictness(float(a.mean()), float(a.std()), n)
        raw = float(np.clip(raw, CLAMP_LO, CLAMP_HI))
        old = prev.get(regime, 1.0)
        blended = (1 - BLEND) * old + BLEND * raw     # EMA: slow drift
        out[regime] = round(float(np.clip(blended, CLAMP_LO, CLAMP_HI)), 3)
    return out

