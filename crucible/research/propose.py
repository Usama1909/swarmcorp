"""
Crucible — Hypothesis Proposer
The leap from Research MEMORY to Research SCIENTIST.

Memory says:  "this family dies of X, survives with Y"
Scientist says: "so try THIS next, expected survival Z, novelty N"

Takes a target idea + research history -> proposes a child experiment.
Deterministic and explainable: no LLM, every proposal traces to evidence.
"""
from typing import List, Dict, Any
from genome import ResearchGenome, find_relatives
from insight import analyze_family


def propose_child(target: ResearchGenome,
                  population: List[Dict[str, Any]],
                  threshold: float = 0.5) -> Dict[str, Any]:
    """
    Propose the next experiment to run, derived from what the family taught us.
    Returns a child genome + expected survival + novelty + the reasoning.
    """
    a = analyze_family(target, population, threshold=threshold)

    if a["relatives"] == 0:
        # nothing to learn from — propose the target itself as a fresh probe
        return {
            "child": target.to_dict(),
            "expected_survival": None,
            "novelty": 1.0,
            "reasoning": ["No relatives — this is unexplored. Test small as a fresh probe."],
            "base_family_stats": a,
        }

    # Build the child: inherit the target, ADD the winning mutation,
    # and add a guard feature against the top failure mode.
    child = ResearchGenome.from_dict(target.to_dict())
    reasoning = []

    win_mut = a.get("winning_mutations") or []
    if win_mut:
        mut = win_mut[0][0]
        if mut not in child.features:
            child.features = child.features + [mut]
        reasoning.append(f"Added '{mut}' — present in most survivors of this family.")

    common_fail = a.get("common_failures") or []
    if common_fail:
        fail = common_fail[0][0]
        guard = _guard_for(fail)
        if guard and guard not in child.features:
            child.features = child.features + [guard]
            reasoning.append(f"Added '{guard}' to guard against '{fail}' — top killer of the family.")

    # Expected survival: base family rate, lifted if we applied a proven mutation
    base = a.get("success_rate", 0.0)
    lift = 0.10 if win_mut else 0.0
    expected = round(min(0.95, base + lift), 3)
    if lift:
        reasoning.append(f"Expected survival lifted from {base:.0%} to ~{expected:.0%} by applying a proven mutation.")
    else:
        reasoning.append(f"Expected survival ~{expected:.0%} (family baseline, no proven mutation found).")

    # Novelty of the CHILD: re-measure how many relatives the mutated child has
    child_rel = find_relatives(child, population, threshold=threshold, top_n=10000)
    novelty = round(max(0.0, 1.0 - len(child_rel) / 100.0), 3)
    reasoning.append(f"Child novelty {novelty:.0%} ({len(child_rel)} close relatives).")

    return {
        "child": child.to_dict(),
        "expected_survival": expected,
        "novelty": novelty,
        "reasoning": reasoning,
        "base_family_stats": a,
    }


def _guard_for(failure_reason: str) -> str:
    """Map a known failure mode to a feature that mitigates it."""
    table = {
        "regime_shift": "regime_filter",
        "regime_instability": "regime_filter",
        "crowding": "capacity_check",
        "high_drawdown": "vol_target",
        "cost_sensitive": "cost_model",
        "sample_too_small": "more_data",
    }
    return table.get(failure_reason, "")

