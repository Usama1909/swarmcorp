"""
Crucible — Research Genome
Turns a strategy/experiment into a structured, comparable fingerprint.

This is the foundation of Research Memory: instead of asking
"have I seen THIS EXACT thing?" (hash match), we ask
"what FAMILY of idea is this, and what happened to its relatives?"

Domain-blind: works for trading strategies, ML experiments, prompts, A/B tests.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json


@dataclass
class ResearchGenome:
    """Structured identity of an idea — what KIND of thing it is."""
    family:    str                      # "momentum", "mean_reversion", "ml_model", "prompt", ...
    domain:    str       = "trading"    # "trading", "ml", "ab_test", "prompt_eval"
    market:    Optional[str] = None     # "crypto", "equities", "fx", or None for non-trading
    horizon:   Optional[str] = None     # "short", "medium", "long"
    features:  List[str] = field(default_factory=list)  # ["rsi","macd","volume","regime"]
    regime:    Optional[str] = None     # "bull","bear","crisis","normal"
    risk_model: Optional[str] = None
    parent_id:  Optional[int] = None    # lineage — which idea this descended from
    extra:      Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResearchGenome":
        known = {f for f in cls.__dataclass_fields__}
        base = {k: v for k, v in d.items() if k in known}
        extra = {k: v for k, v in d.items() if k not in known}
        if extra:
            base.setdefault("extra", {}).update(extra)
        return cls(**base)


def similarity(a: ResearchGenome, b: ResearchGenome) -> float:
    """
    0.0 (unrelated) to 1.0 (identical family).
    Weighted: family and domain matter most; features are a Jaccard overlap.
    This is what lets Crucible find RELATIVES, not just exact matches.
    """
    score = 0.0
    weights_used = 0.0

    def cmp(av, bv, weight):
        nonlocal score, weights_used
        if av is None and bv is None:
            return
        weights_used += weight
        if av == bv:
            score += weight

    # family is the strongest signal of "same kind of idea"
    cmp(a.family, b.family, 3.0)
    cmp(a.domain, b.domain, 2.0)
    cmp(a.market, b.market, 1.5)
    cmp(a.horizon, b.horizon, 1.0)
    cmp(a.regime, b.regime, 1.0)
    cmp(a.risk_model, b.risk_model, 0.5)

    # features: Jaccard overlap (set similarity)
    if a.features or b.features:
        sa, sb = set(a.features), set(b.features)
        jac = len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0
        score += 2.0 * jac
        weights_used += 2.0

    return round(score / weights_used, 4) if weights_used else 0.0


def find_relatives(target: ResearchGenome,
                   population: List[Dict[str, Any]],
                   threshold: float = 0.5,
                   top_n: int = 50) -> List[Dict[str, Any]]:
    """
    Given a target idea and a population of past experiments (each a dict with
    a 'genome' key), return the closest relatives sorted by similarity.
    This is the heart of "I've seen 847 similar ideas."
    """
    scored = []
    for rec in population:
        g = rec.get("genome")
        if g is None:
            continue
        other = g if isinstance(g, ResearchGenome) else ResearchGenome.from_dict(g)
        sim = similarity(target, other)
        if sim >= threshold:
            scored.append((sim, rec))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{**rec, "_similarity": sim} for sim, rec in scored[:top_n]]
