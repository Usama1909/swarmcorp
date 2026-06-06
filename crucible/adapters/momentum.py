"""
Crucible — Momentum Adapter
First real domain plugin. Trades momentum on price series.
Spawns variants with different lookback periods. Gate decides which survive.
"""
import numpy as np
from typing import List, Dict, Any
from datetime import datetime, timezone
from crucible.core.vocabulary import Candidate, Outcome, CandidateStatus
from crucible.adapters.base import BaseAdapter


class MomentumAdapter(BaseAdapter):
    """
    A candidate's DNA: {strategy, timeframe, lookback, threshold, regime}
    - strategy: always "momentum"
    - timeframe: SCALP | INTRADAY | SWING
    - lookback: how many bars to compute momentum over
    - threshold: minimum momentum to trigger a trade
    - regime: which market regime this variant works in
    """
    name = "momentum"

    def __init__(self,
                 cost_per_trade: float = 0.001,
                 lookback_options: List[int] = None,
                 threshold_options: List[float] = None):
        self.cost_per_trade    = cost_per_trade
        self.lookback_options  = lookback_options or [5, 10, 20, 50]
        self.threshold_options = threshold_options or [0.005, 0.01, 0.02]
        self._current_regime: str = "NORMAL"
        self._current_price_history: List[float] = []

    def spawn(self, context: Dict[str, Any]) -> List[Candidate]:
        """Spawn one candidate per (lookback × threshold) combination."""
        regime = context.get("regime", "NORMAL")
        candidates = []
        for lookback in self.lookback_options:
            for threshold in self.threshold_options:
                dna = {
                    "strategy":  "momentum",
                    "timeframe": "INTRADAY",
                    "lookback":  lookback,
                    "threshold": threshold,
                    "regime":    regime,
                    "adapter":   self.name,
                }
                name = f"momentum_lb{lookback}_th{threshold}_{regime}"
                candidates.append(Candidate(
                    name=name,
                    adapter=self.name,
                    dna=dna,
                    spawn_reason=f"Spawned in {regime} regime"
                ))
        return candidates

    def act(self, candidate: Candidate, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compute momentum signal. Returns {direction: LONG|SHORT|HOLD, strength: float}."""
        prices = context.get("price_history", [])
        lookback = candidate.dna["lookback"]
        threshold = candidate.dna["threshold"]

        if len(prices) < lookback + 1:
            return {"direction": "HOLD", "strength": 0.0, "reason": "insufficient history"}

        recent = prices[-lookback:]
        momentum = (recent[-1] - recent[0]) / recent[0]

        if momentum > threshold:
            return {"direction": "LONG", "strength": momentum,
                    "reason": f"momentum {momentum:.4f} > {threshold}"}
        elif momentum < -threshold:
            return {"direction": "SHORT", "strength": abs(momentum),
                    "reason": f"momentum {momentum:.4f} < -{threshold}"}
        else:
            return {"direction": "HOLD", "strength": 0.0,
                    "reason": f"momentum {momentum:.4f} below threshold"}

    def measure(self, candidate: Candidate, action: Dict[str, Any],
                reality: Dict[str, Any]) -> Outcome:
        """Compute return net of cost."""
        direction = action.get("direction", "HOLD")
        entry_price = reality.get("entry_price", 0)
        exit_price  = reality.get("exit_price", 0)

        if direction == "HOLD" or entry_price <= 0:
            result_value = 0.0
        elif direction == "LONG":
            result_value = (exit_price - entry_price) / entry_price
        else:  # SHORT
            result_value = (entry_price - exit_price) / entry_price

        net_value = result_value - self.cost_per_trade

        return Outcome(
            candidate_id=candidate.id,
            action=action,
            result_value=net_value,
            cost=self.cost_per_trade,
            context={
                "regime": reality.get("regime", "UNKNOWN"),
                "entry_price": entry_price,
                "exit_price":  exit_price,
            },
            is_sealed=reality.get("is_sealed", False)
        )

    def context(self) -> Dict[str, Any]:
        """Return current world state for this adapter."""
        return {
            "regime": self._current_regime,
            "price_history": list(self._current_price_history),
        }

    def is_time_ordered(self) -> bool:
        return True

    def applies_to(self, candidate: Candidate, context: Dict[str, Any]) -> bool:
        """A candidate only applies if its regime matches current regime."""
        return candidate.dna.get("regime") == context.get("regime")

    def update_state(self, regime: str, price_history: List[float]):
        """Caller updates adapter state before each cycle."""
        self._current_regime = regime
        self._current_price_history = price_history