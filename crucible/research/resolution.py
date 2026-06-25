"""
Crucible — Multi-Resolution Analysis
Answer the same question at different zoom levels WITHOUT fragmenting families.

Global:  all crisis shorts
Market:  crypto crisis shorts
Symbol:  ETH crisis shorts

Same broad family, filtered by tags. This is what lets the signal show at
multiple resolutions instead of hardcoding symbol into the family ID.
"""
from typing import List, Dict, Any
from genome import ResearchGenome
from insight import analyze_family


def _matches(rec: Dict[str, Any], filters: Dict[str, str]) -> bool:
    """A record matches if its tags contain every requested filter value."""
    tags = set(rec.get("tags", []))
    return all(v in tags for v in filters.values())


def analyze_at(target: ResearchGenome,
               population: List[Dict[str, Any]],
               filters: Dict[str, str] = None,
               threshold: float = 0.4) -> Dict[str, Any]:
    """Run family analysis on the subset of population matching tag filters."""
    if filters:
        subset = [r for r in population if _matches(r, filters)]
    else:
        subset = population
    return analyze_family(target, subset, threshold=threshold)


def multi_resolution(target: ResearchGenome,
                     population: List[Dict[str, Any]],
                     levels: List[Dict[str, str]],
                     threshold: float = 0.4) -> List[Dict[str, Any]]:
    """
    Run analysis at several zoom levels. Each level is a label + tag filter.
    Returns one summary row per level so you SEE the signal sharpen.
    """
    out = []
    for lvl in levels:
        label = lvl.get("label", "level")
        filters = {k: v for k, v in lvl.items() if k != "label"}
        a = analyze_at(target, population, filters, threshold)
        out.append({
            "level": label,
            "n": a.get("relatives", 0),
            "success_rate": a.get("success_rate"),
            "top_failure": (a.get("common_failures") or [(None,)])[0][0],
            "verdict": a.get("verdict"),
        })
    return out
