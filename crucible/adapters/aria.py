"""
Crucible — ARIA Adapter
Candidate = strategy cell (symbol x direction x regime).
Outcome   = closed trade in that cell (result = pnl_pct).
Context   = ARIA's current meta_regime. Read-only against aria_db.
"""
import os
import json
import zlib
import psycopg2
from typing import Dict, Any, List
from dotenv import load_dotenv
from crucible.core.vocabulary import Candidate, CandidateStatus, Outcome

load_dotenv("/root/.env")
ARIA_DB = {"host": os.getenv("ARIA_DB_HOST", "localhost"), "port": 5432,
           "dbname": "aria_db", "user": "postgres",
           "password": os.getenv("ARIA_DB_PASSWORD", "")}

def _cell_id(name: str) -> int:
    return zlib.crc32(name.encode())

class AriaCellAdapter:
    name = "aria_cells"

    def _db(self):
        return psycopg2.connect(**ARIA_DB)

    def load_candidates(self, min_trades: int = 1) -> List[Candidate]:
        conn = self._db()
        try:
            cur = conn.cursor()
            cur.execute("""SELECT symbol, direction, regime_at_entry, COUNT(*)
                           FROM closed_trades
                           WHERE regime_at_entry IS NOT NULL
                           GROUP BY 1,2,3 HAVING COUNT(*) >= %s""", [min_trades])
            out = []
            for sym, dirn, regime, n in cur.fetchall():
                cname = f"{sym}_{dirn}_{regime}"
                out.append(Candidate(
                    name=cname, adapter=self.name, id=_cell_id(cname),
                    dna={"symbol": sym, "direction": dirn, "regime": regime},
                    status=CandidateStatus.EMBRYO,
                    spawn_reason="bootstrapped from closed_trades history"))
            return out
        finally:
            conn.close()

    def outcomes_for(self, candidate: Candidate) -> List[Outcome]:
        d = candidate.dna
        conn = self._db()
        try:
            cur = conn.cursor()
            cur.execute("""SELECT pnl_pct, exit_time FROM closed_trades
                           WHERE symbol=%s AND direction=%s AND regime_at_entry=%s
                           ORDER BY exit_time ASC""",
                        [d["symbol"], d["direction"], d["regime"]])
            return [Outcome(candidate_id=candidate.id,
                            action={"symbol": d["symbol"], "direction": d["direction"]},
                            result_value=float(p), cost=0.0,
                            context={"regime": d["regime"]}, ts=t)
                    for p, t in cur.fetchall() if p is not None]
        finally:
            conn.close()

    def context(self) -> Dict[str, Any]:
        conn = self._db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT value FROM aria_config WHERE key='meta_regime' LIMIT 1")
            row = cur.fetchone()
            return {"regime": row[0].strip() if row else "UNKNOWN"}
        finally:
            conn.close()

    def applies_to(self, candidate: Candidate, ctx: Dict[str, Any]) -> bool:
        return candidate.dna.get("regime") == ctx.get("regime")

    def current_kill_list(self) -> List[str]:
        conn = self._db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT value FROM aria_config WHERE key='signal_feedback' LIMIT 1")
            row = cur.fetchone()
            if not row:
                return []
            return [k.get("key") for k in json.loads(row[0]).get("KILL", [])]
        finally:
            conn.close()
