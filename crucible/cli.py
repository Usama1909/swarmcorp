"""
Crucible CLI — read-only views over the live judgments.

  crucible status            ranked table of every strategy's current decision
  crucible explain <CELL>    death certificate / full reasoning for one cell
  crucible report            one-screen summary (counts + headline calls)

Reads the same tables the shadow service writes:
  crucible_decisions  (graded action: LEAVE/WATCH/LEAN_AWAY/RETIRE)
  crucible_verdicts   (DSR honesty-gate verdict + stats)
"""
import os
import sys
import json
import argparse
import psycopg2
from dotenv import load_dotenv

load_dotenv(os.getenv("CRUCIBLE_ENV", "/root/.env"))

DB = {"host": os.getenv("ARIA_DB_HOST", "localhost"), "port": 5432,
      "dbname": os.getenv("CRUCIBLE_DB", "aria_db"),
      "user": os.getenv("CRUCIBLE_DB_USER", "postgres"),
      "password": os.getenv("ARIA_DB_PASSWORD", "")}

ACTION_ICON = {"LEAVE": "✓ keep", "WATCH": "· watch",
               "LEAN_AWAY": "↓ reduce", "RETIRE": "✗ retire"}


def _conn():
    return psycopg2.connect(**DB)


def _latest_decisions(cur):
    cur.execute("""
        SELECT DISTINCT ON (cell) cell, action, confidence, health, trend,
               evidence_count, reason, cycle_ts
        FROM crucible_decisions
        ORDER BY cell, cycle_ts DESC
    """)
    return cur.fetchall()


def cmd_status(args):
    with _conn() as c:
        cur = c.cursor()
        rows = _latest_decisions(cur)
    rows.sort(key=lambda r: r[3], reverse=True)  # by health desc
    print(f"\n  {'STRATEGY':14} {'DECISION':10} {'CONF':>5} {'HEALTH':>7} {'N':>4}")
    print("  " + "-" * 48)
    for cell, action, conf, health, trend, n, reason, ts in rows:
        label = ACTION_ICON.get(action, action)
        print(f"  {cell:14} {label:10} {conf:5.2f} {health:7.2f} {n:4d}")
    print()


def cmd_explain(args):
    cell = args.cell
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""SELECT action, confidence, health, trend, evidence_count,
                              reason, cycle_ts
                       FROM crucible_decisions WHERE cell=%s
                       ORDER BY cycle_ts DESC LIMIT 1""", [cell])
        d = cur.fetchone()
        cur.execute("""SELECT verdict, confidence, evidence_count, stats, cycle_ts
                       FROM crucible_verdicts WHERE cell=%s
                       ORDER BY cycle_ts DESC LIMIT 1""", [cell])
        v = cur.fetchone()

    if not d and not v:
        print(f"\n  No record for '{cell}'. Run `crucible status` to list known cells.\n")
        return

    print(f"\n  ┌─ CRUCIBLE CERTIFICATE ─ {cell}")
    if d:
        action, conf, health, trend, n, reason, ts = d
        print(f"  │")
        print(f"  │  DECISION    {action}")
        print(f"  │  confidence  {conf:.2f}   health {health:.2f}   "
              f"trend {'n/a' if trend is None else f'{trend:+.2f}'}")
        print(f"  │  evidence    {n} outcomes")
        print(f"  │  reason      {reason}")
        print(f"  │  as of       {ts:%Y-%m-%d %H:%M}")
    if v:
        verdict, vconf, vn, stats, vts = v
        s = stats if isinstance(stats, dict) else json.loads(stats or "{}")
        print(f"  │")
        print(f"  │  GATE VERDICT  {verdict}  (DSR-corrected)")
        for k in ("sharpe", "dsr", "t_test_p", "judge_n"):
            if k in s:
                print(f"  │    {k:10} {s[k]}")
        if s.get("reason"):
            print(f"  │    {s['reason']}")
    print(f"  └{'─' * 40}\n")


def cmd_report(args):
    with _conn() as c:
        cur = c.cursor()
        rows = _latest_decisions(cur)
    counts = {}
    for r in rows:
        counts[r[1]] = counts.get(r[1], 0) + 1
    keep = [r[0] for r in rows if r[1] == "LEAVE"]
    retire = [r[0] for r in rows if r[1] == "RETIRE"]
    print(f"\n  CRUCIBLE REPORT — {len(rows)} strategies under governance\n")
    for a in ("LEAVE", "WATCH", "LEAN_AWAY", "RETIRE"):
        print(f"    {ACTION_ICON.get(a, a):10} {counts.get(a, 0)}")
    if keep:
        print(f"\n  Funding (proven edge): {', '.join(keep)}")
    if retire:
        print(f"  Retiring (no edge):    {', '.join(retire)}")
    print()


def main():
    p = argparse.ArgumentParser(prog="crucible",
        description="Tells you which strategies are real, which are overfit, "
                    "and which to retire — and why.")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("status", help="ranked decision table").set_defaults(fn=cmd_status)
    ex = sub.add_parser("explain", help="death certificate for one cell")
    ex.add_argument("cell")
    ex.set_defaults(fn=cmd_explain)
    sub.add_parser("report", help="one-screen summary").set_defaults(fn=cmd_report)
    args = p.parse_args()
    if not getattr(args, "fn", None):
        p.print_help()
        sys.exit(0)
    args.fn(args)


if __name__ == "__main__":
    main()
