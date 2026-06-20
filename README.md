# Crucible

**Tells you which strategies are real, which are overfit, and which to retire — and why.**

Crucible is a governance engine for populations of strategies (or any
candidates that produce measurable outcomes). It judges each one for *real
edge vs. luck*, grades it, and decides what to do with it — keep funding it,
watch it, lean away, or retire it — and writes down **why**.

It has been running live, in shadow mode, over a real multi-asset trading
system (ARIA) — continuously judging that system's strategies every 15 minutes
and governing its capital allocation.

---

## The problem it solves

You have 100 backtests, or 20 live strategies. Which ones have a real edge?
Which are overfit? Which are quietly dying? Which deserve more capital, and
which should be cut? Most people answer this with spreadsheets, notebooks, and
manual review. Crucible answers it as one tool, continuously, with an
explanation for every call.

---

## How it works

Each strategy is a **candidate** with a stream of **outcomes** (e.g. per-trade
returns). Crucible runs two layers over them:

1. **Honesty gate** — a statistical test that corrects for luck-of-many-tries
   using the Deflated Sharpe Ratio (Bailey & López de Prado, 2014). It only
   blesses an edge that survives the correction. Deliberately strict.

2. **Decision layer** — a graded, always-actionable read that never freezes or
   over-reacts. Confidence grows with evidence; action scales with confidence.
   Robust to outliers (trimmed mean) so one freak result can't fake a winner.

Every candidate ends each cycle with one decision:

| Decision    | Meaning                                  |
|-------------|------------------------------------------|
| `LEAVE`     | proven edge — keep funding               |
| `WATCH`     | not enough signal yet — keep running     |
| `LEAN_AWAY` | weak / declining — reduce exposure       |
| `RETIRE`    | sustained, evidence-backed failure — cut |

A retired strategy gets a **death certificate**: the decision, the confidence,
the evidence count, the trajectory, and the statistics behind the call.

---

## CLI

```bash
crucible status            # ranked table of every strategy's current decision
crucible explain <CELL>    # death certificate / full reasoning for one strategy
crucible report            # one-screen summary
```

Example — `crucible explain GLD_LONG`:

```
┌─ CRUCIBLE CERTIFICATE ─ GLD_LONG
│
│  DECISION    RETIRE
│  confidence  0.73   health 0.15   trend -1.00
│  evidence    29 outcomes
│  reason      sustained loss (mean=-0.0040, declining) at confidence 0.73 — cut
│
│  GATE VERDICT  UNPROVEN  (DSR-corrected)
│    the strict gate abstains (29 < 30); the decision layer acts on the trend
└────────────────────────────────────────
```

---

## Architecture

```
crucible/
  core/         vocabulary, lifecycle state machine, allocator, memory, ledger
  gate/         honesty gate (DSR) + decision layer
  adapters/     plug a domain in here (ARIA trading is the reference adapter)
  cli.py        status / explain / report
```

The core is **domain-blind**. A domain plugs in through an adapter that exposes
its candidates and their outcomes — trading is the first one; the same engine
judges any candidate population that produces measurable results.

---

## What's novel here

The individual pieces are not new — the Deflated Sharpe Ratio, strategy
lifecycle management, and retire-on-decay all exist in the literature. What
Crucible packages is the **integration**: spawn → prove → allocate → retire,
as a reusable engine, with **death certificates** that explain every decision,
**proven live on a real system** rather than only in backtests.

---

## Status

Live in shadow + governance mode over a production trading system. The decision
layer is hardened against degenerate inputs (empty, single-sample, zero-variance,
outliers) — it never crashes and never returns a nonsensical call.

## License

MIT
