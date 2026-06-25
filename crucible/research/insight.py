"""
Crucible — Research Insight
Turns relatives into KNOWLEDGE. This is the moat: not "have I seen this?"
but "what happens to ideas like this, and what should I try next?"
"""
from typing import List, Dict, Any
from collections import Counter
import statistics as st
from genome import ResearchGenome, find_relatives




def _confidence(n: int) -> str:
    """Sample-size confidence. Below 30 = LOW (statistically thin)."""
    if n >= 100: return "HIGH"
    if n >= 30:  return "MEDIUM"
    return "LOW"


def _weighted_success(rel) -> float:
    """Success rate weighted by similarity — closer relatives count more."""
    num = den = 0.0
    for r in rel:
        w = r.get("_similarity", 1.0)
        den += w
        if r.get("passed"): num += w
    return round(num / den, 3) if den else 0.0


def analyze_family(target: ResearchGenome,
                   population: List[Dict[str, Any]],
                   threshold: float = 0.5) -> Dict[str, Any]:
    """
    Given an idea + history, produce research knowledge about its family.
    Each population record should carry: genome, passed(bool),
    lifetime_days(int), death_reason(str), and optionally mutation(str).
    """
    rel = find_relatives(target, population, threshold=threshold, top_n=10000)
    n = len(rel)
    if n == 0:
        return {"relatives": 0, "verdict": "NOVEL",
                "note": "No similar ideas seen before — genuinely unexplored."}

    passed   = [r for r in rel if r.get("passed")]
    failed   = [r for r in rel if not r.get("passed")]
    lifetimes = [r["lifetime_days"] for r in rel if r.get("lifetime_days") is not None]
    deaths    = [r["death_reason"] for r in failed if r.get("death_reason")]
    # mutations present on SURVIVORS = what tends to work
    win_mut   = [r["mutation"] for r in passed if r.get("mutation")]

    success_rate = round(len(passed) / n, 3)
    common_fail  = Counter(deaths).most_common(3)
    best_mut     = Counter(win_mut).most_common(3)

    # novelty: many relatives = crowded idea; few = fresh
    novelty = round(max(0.0, 1.0 - n / 100.0), 3)

    return {
        "relatives": n,
        "success_rate": success_rate,
        "weighted_success_rate": _weighted_success(rel),
        "confidence": _confidence(n),
        "avg_lifetime_days": round(st.mean(lifetimes), 1) if lifetimes else None,
        "median_lifetime_days": round(st.median(lifetimes), 1) if lifetimes else None,
        "common_failures": common_fail,
        "winning_mutations": best_mut,
        "novelty_score": novelty,
        "verdict": _verdict(success_rate, n, novelty),
        "recommendation": _recommend(success_rate, common_fail, best_mut, novelty),
    }


def _verdict(success_rate, n, novelty):
    if novelty > 0.9:
        return "NOVEL — little prior evidence, high uncertainty"
    if success_rate >= 0.4:
        return "PROMISING FAMILY — relatives survive above average"
    if success_rate <= 0.15:
        return "GRAVEYARD FAMILY — relatives mostly die"
    return "MIXED FAMILY — survival depends on execution"


def _recommend(success_rate, common_fail, best_mut, novelty):
    tips = []
    if best_mut:
        tips.append(f"Add '{best_mut[0][0]}' — present in most survivors")
    if common_fail:
        tips.append(f"Guard against '{common_fail[0][0]}' — top killer of this family")
    if novelty > 0.9:
        tips.append("Few relatives — test small, high uncertainty")
    if success_rate <= 0.15 and not tips:
        tips.append("This family rarely works — consider a different approach")
    return tips or ["Insufficient signal for a strong recommendation"]
