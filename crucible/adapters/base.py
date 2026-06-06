"""
Crucible — Base Adapter
The contract every domain plugin implements.
The core engine never knows what domain it's in — it only calls these methods.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from crucible.core.vocabulary import Candidate, Outcome


class BaseAdapter(ABC):
    """
    Domain plugin contract.
    Trading, prompt-tuning, A/B testing, hyperparameter search — all subclass this.
    """

    name: str = "base"

    @abstractmethod
    def spawn(self, context: Dict[str, Any]) -> List[Candidate]:
        """Generate new candidates given current context.
        Returns a list of Candidate objects (id=None — engine assigns IDs)."""
        ...

    @abstractmethod
    def act(self, candidate: Candidate, context: Dict[str, Any]) -> Dict[str, Any]:
        """Have a candidate take its action in the current context.
        Returns the action taken (will be recorded in the Outcome)."""
        ...

    @abstractmethod
    def measure(self, candidate: Candidate, action: Dict[str, Any],
                reality: Dict[str, Any]) -> Outcome:
        """Measure what happened. Returns Outcome with result_value NET of cost.
        Adapter owns the cost model."""
        ...

    @abstractmethod
    def context(self) -> Dict[str, Any]:
        """Current state of the world the adapter cares about.
        Used to drive Dormant (if context doesn't fit a candidate, it pauses)."""
        ...

    @abstractmethod
    def is_time_ordered(self) -> bool:
        """True if outcomes have natural time ordering (trading, A/B over time).
        Tells the gate which validation scheme to use (chronological vs sealed flag)."""
        ...

    def applies_to(self, candidate: Candidate, context: Dict[str, Any]) -> bool:
        """Optional override: whether a candidate's DNA matches current context.
        Default: always applies. Override to drive Dormant transitions."""
        return True
        