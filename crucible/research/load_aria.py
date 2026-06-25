"""Load real ARIA trades into Research Memory and run the brain on them."""
import os, psycopg2
from dotenv import load_dotenv
load_dotenv("/root/.env")
from genome import ResearchGenome
from insight import analyze_family
from propose import propose_child

DB = {"host":"localhost","port":5432,"dbname":"aria_db","user":"postgres",
      "password": os.getenv("ARIA_DB_PASSWORD")}

CRYPTO = {"BTC","ETH"}

def load_history():
    conn = psycopg2.connect(**DB); cur = conn.cursor()
    cur.execute("""
        SELECT symbol, regime_at_entry, direction, outcome, pnl_pct,
               EXTRACT(EPOCH FROM (exit_time - entry_time))/86400.0 AS lifetime_days
        FROM closed_trades
        WHERE outcome IN ('WIN','LOSS')
    """)
    rows = cur.fetchall(); cur.close(); conn.close()
    hist = []
    for sym, regime, direction, outcome, pnl, life in rows:
        g = ResearchGenome(
            family=f"{direction.lower()}_{(regime or 'normal').lower()}",
            domain="trading",
            market="crypto" if sym in CRYPTO else "equities",
            regime=(regime or "NORMAL").lower(),
            features=[sym.lower(), direction.lower(), (regime or "normal").lower()],
        )
        hist.append({
            "symbol": sym, "genome": g.to_dict(),
            "tags": [sym.lower(), "crypto" if sym in CRYPTO else "equities", direction.lower(), (regime or 'normal').lower()],
            "passed": outcome == "WIN",
            "lifetime_days": round(life,1) if life else None,
            "death_reason": None if outcome=="WIN" else f"{(regime or 'normal').lower()}_loss",
            "mutation": None,
        })
    return hist

if __name__ == "__main__":
    from resolution import multi_resolution
    hist = load_history()
    print(f"Loaded {len(hist)} real trades\n")
    target = ResearchGenome(family="short_crisis", market="crypto", regime="crisis", features=["short","crisis"])
    levels = [
      {"label":"GLOBAL (all crisis shorts)"},
      {"label":"MARKET (crypto crisis shorts)", "market":"crypto"},
      {"label":"SYMBOL (ETH crisis shorts)", "eth":"eth"},
    ]
    print(f'{"LEVEL":34} {"n":>4} {"success":>8}  verdict')
    for r in multi_resolution(target, hist, levels):
        sr = f'{r["success_rate"]:.1%}' if r["success_rate"] is not None else "n/a"
        print(f'  {r["level"]:32} {r["n"]:>4} {sr:>8}  {r["verdict"]}')
