"""
Crucible — domain-agnostic proof.
NOT trading. Judges a population of A/B-test variants (or any candidates that
produce per-trial numeric outcomes) using the SAME gate + decision engine.

Scenario: 5 landing-page variants. Each "outcome" = revenue-per-visitor for one
visitor session. We KNOW the ground truth (some variants genuinely convert
better, some are noise) and check Crucible recovers it.
"""
import numpy as np
from crucible.gate.decision import decide

np.random.seed(20260620)

# Ground truth: per-visitor value distributions for 5 variants.
# variant -> (true_mean_uplift, noise_sd)
variants = {
    "control":        (0.000, 0.05),   # baseline, no edge
    "big_headline":   (0.015, 0.05),   # real winner
    "scary_popup":    (-0.020, 0.05),  # real loser (annoys users)
    "tiny_tweak":     (0.001, 0.05),   # negligible, basically noise
    "lucky_fluke":    (0.000, 0.05),   # no real edge — but we'll let it get lucky
}

N = 60  # visitors per variant

print("Crucible judging NON-TRADING candidates (A/B landing-page variants)\n")
print(f"  {'VARIANT':14} {'DECISION':10} {'CONF':>5} {'HEALTH':>7} {'mean':>8}   truth")
print("  " + "-" * 64)

for name, (mu, sd) in variants.items():
    outcomes = np.random.normal(mu, sd, N).tolist()
    if name == "lucky_fluke":
        # force an unlucky-good streak to test if Crucible resists noise
        outcomes = sorted(outcomes, reverse=True)
    d = decide(outcomes)
    truth = ("real winner" if mu > 0.01 else
             "real loser"  if mu < -0.01 else
             "no edge")
    print(f"  {name:14} {d.action:10} {d.confidence:5.2f} {d.health:7.2f} "
          f"{np.mean(outcomes):+8.4f}   {truth}")

print("\n  Same gate, same decision engine, zero trading code.")
print("  If winners->LEAVE, losers->RETIRE/LEAN_AWAY, noise->WATCH/LEAN_AWAY,")
print("  the engine is genuinely domain-agnostic.\n")
