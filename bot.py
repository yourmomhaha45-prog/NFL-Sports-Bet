import streamlit as st
import pandas as pd

# --- Demo odds data ---
ODDS_STORE = {
    "ManU-Liv 1x2": {
        "BookA": {"home": 2.10, "draw": 3.40, "away": 3.60},
        "BookB": {"home": 2.20, "draw": 3.10, "away": 3.40},
        "BookC": {"home": 2.05, "draw": 3.50, "away": 3.80},
    },
    "Nadal-Federer moneyline": {
        "BookX": {"playerA": 1.95, "playerB": 2.05},
        "BookY": {"playerA": 2.00, "playerB": 2.00},
        "BookZ": {"playerA": 1.92, "playerB": 2.10},
    }
}

# --- Arbitrage detection ---
def detect_arbs(market_odds):
    outcomes = set()
    for outmap in market_odds.values():
        outcomes.update(outmap.keys())
    best = {}
    for o in outcomes:
        best_book, best_odds = None, 0.0
        for book, outmap in market_odds.items():
            if o in outmap and outmap[o] > best_odds:
                best_book, best_odds = book, outmap[o]
        best[o] = (best_book, best_odds)
    S = sum(1/odds for _, odds in best.values())
    if S < 1:
        profit_pct = (1 - S) * 100
        return {"best": best, "S": S, "profit_pct": profit_pct}
    return None

def compute_stakes(best_odds, budget):
    invs = {o: 1/odds for o, (_b, odds) in best_odds.items()}
    S = sum(invs.values())
    stakes = {o: round(budget*invs[o]/S,2) for o in invs}
    payout = round(budget/S,2)
    profit = round(payout - budget,2)
    profit_pct = round((profit/budget)*100,4)
    return stakes, payout, profit, profit_pct

# --- Streamlit UI ---
st.set_page_config(page_title="Arbitrage Bot Demo")
st.title("Arbitrage Bot Demo")

budget = st.number_input("Budget ($)", value=100.0, step=10.0)

arbs_list = []
for market_name, market_odds in ODDS_STORE.items():
    arb = detect_arbs(market_odds)
    if arb:
        stakes, payout, profit, profit_pct = compute_stakes(arb["best"], budget)
        arbs_list.append({
            "Market": market_name,
            "Profit %": round(arb["profit_pct"],3),
            "S": round(arb["S"],6),
            "Payout": payout,
            "Profit $": profit,
            "Stakes": stakes
        })

if arbs_list:
    df = pd.DataFrame(arbs_list)
    df = df.sort_values("Profit %", ascending=False)
    st.dataframe(df)
else:
    st.info("No arbitrage opportunities found (demo data).")
