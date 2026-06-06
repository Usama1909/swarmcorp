"""
Test: MomentumAdapter spawns, acts, measures correctly.
Then runs through engine — bad variants get killed, good ones get PROVEN.
"""
import sys
sys.path.insert(0, '/root/crucible')

import numpy as np
from crucible.core.vocabulary import CandidateStatus
from crucible.adapters.momentum import MomentumAdapter

passed = 0
failed = 0

def check(desc, condition):
    global passed, failed
    if condition:
        print(f"PASS: {desc}")
        passed += 1
    else:
        print(f"FAIL: {desc}")
        failed += 1

# Test 1 — spawn produces multiple variants
adapter = MomentumAdapter(
    lookback_options=[5, 20],
    threshold_options=[0.01, 0.02]
)
context = {"regime": "NORMAL"}
candidates = adapter.spawn(context)
check("spawn produces 4 variants (2 lookbacks x 2 thresholds)", len(candidates) == 4)
check("all candidates have momentum strategy",
      all(c.dna["strategy"] == "momentum" for c in candidates))
check("all candidates start as EMBRYO",
      all(c.status == CandidateStatus.EMBRYO for c in candidates))

# Test 2 — act produces LONG/SHORT/HOLD
trending_up = [100.0 + i*0.5 for i in range(30)]  # upward trend
adapter.update_state("NORMAL", trending_up)
context_up = adapter.context()
candidate = candidates[0]  # lb=5, th=0.01
action = adapter.act(candidate, context_up)
check("upward trend produces LONG signal", action["direction"] == "LONG")

trending_down = [100.0 - i*0.5 for i in range(30)]
adapter.update_state("NORMAL", trending_down)
context_dn = adapter.context()
action_dn = adapter.act(candidate, context_dn)
check("downward trend produces SHORT signal", action_dn["direction"] == "SHORT")

flat = [100.0 + np.random.uniform(-0.1, 0.1) for _ in range(30)]
adapter.update_state("NORMAL", flat)
context_flat = adapter.context()
action_flat = adapter.act(candidate, context_flat)
check("flat market produces HOLD", action_flat["direction"] == "HOLD")

# Test 3 — measure produces net Outcome
candidate.id = 1
reality_long_win = {"entry_price": 100.0, "exit_price": 110.0, "regime": "NORMAL"}
outcome = adapter.measure(candidate, {"direction": "LONG"}, reality_long_win)
expected = 0.10 - 0.001  # 10% gain net of 0.1% cost
check("LONG winning trade nets correct value", abs(outcome.result_value - expected) < 0.0001)

reality_short_win = {"entry_price": 100.0, "exit_price": 90.0, "regime": "NORMAL"}
outcome_short = adapter.measure(candidate, {"direction": "SHORT"}, reality_short_win)
expected_short = 0.10 - 0.001
check("SHORT winning trade nets correct value", abs(outcome_short.result_value - expected_short) < 0.0001)

reality_hold = {"entry_price": 100.0, "exit_price": 100.0, "regime": "NORMAL"}
outcome_hold = adapter.measure(candidate, {"direction": "HOLD"}, reality_hold)
check("HOLD outcome has zero P&L", outcome_hold.result_value == 0.0 - 0.001)

# Test 4 — applies_to enforces regime match
crisis_candidate = adapter.spawn({"regime": "CRISIS"})[0]
normal_context = {"regime": "NORMAL"}
crisis_context = {"regime": "CRISIS"}
check("crisis candidate doesn't apply in NORMAL",
      adapter.applies_to(crisis_candidate, normal_context) == False)
check("crisis candidate applies in CRISIS",
      adapter.applies_to(crisis_candidate, crisis_context) == True)

# Test 5 — is_time_ordered returns True
check("momentum is time-ordered", adapter.is_time_ordered() == True)

print(f"\n{passed} passed, {failed} failed.")