import streamlit as st
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Sports Arbitrage Dashboard", layout="wide")

st.title("🏀🏈 Sports Arbitrage Dashboard")

# --- Demo odds data ---
ODDS_STORE = [
    {
        "sport": "NFL",
        "date": "2025-11-05 13:00",
        "match": "Patriots vs Jets",
        "odds": {
            "BookA": {"home": 1.95, "away": 1.95},
            "BookB": {"home": 2.00, "away": 1.90},
        }
    },
    {
        "sport": "NBA",
        "date": "2025-11-06 19:30",
        "match": "Lakers vs Celtics",
        "odds": {
            "BookA": {"home": 1.85, "away": 2.05},
            "BookB": {"home": 1.90, "away": 2.00},
        }
    },
    {
        "sport": "NFL",
        "date": "2025-11-07 16:25",
        "match": "Cowboys vs Eagles",
        "odds": {
            "BookA": {"home": 2.10, "away": 1.80},
            "BookB": {"home": 2.05, "away": 1.85},
        }
    }
]

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

# --- Sidebar ---
budget = st.sidebar.number_input("Budget ($)", value=100, step=10)
st.sidebar.markdown("### Filter by sport")
sports = list(set([x["sport"] for x in ODDS_STORE]))
selected_sports = st.sidebar.multiselect("Sports", sports, default=sports)
refresh_rate = st.sidebar.slider("Auto-refresh interval (seconds)", 5, 60, 10)

# --- Main dashboard ---
def render_dashboard():
    arbs_list = []

    for game in [g for g in ODDS_STORE if g["sport"] in selected_sports]:
        arb = detect_arbs(game["odds"])
        if arb:
            stakes, payout, profit, profit_pct = compute_stakes(arb["best"], budget)
            arbs_list.append({
                "sport": game["sport"],
                "date": datetime.strptime(game["date"], "%Y-%m-%d %H:%M"),
                "match": game["match"],
                "arb": arb,
                "stakes": stakes,
                "profit_pct": profit_pct,
                "profit": profit
            })

    # Sort by highest profit %
    arbs_list.sort(key=lambda x: x["profit_pct"], reverse=True)

    for a in arbs_list:
        st.markdown(f"### {a['sport']} — {a['match']}")
        st.markdown(f"**Date:** {a['date'].strftime('%b %d %Y, %H:%M')}")
        cols = st.columns(len(a['arb']['best']))
        for idx, (outcome, (book, odd)) in enumerate(a['arb']['best'].items()):
            with cols[idx]:
                st.markdown(f"**{outcome.capitalize()}**")
                st.markdown(f"Book: {book}")
                st.markdown(f"Odds: {odd}")
                st.markdown(f"Stake: ${a['stakes'][outcome]}")
        st.markdown(f"**Profit %:** {a['profit_pct']:.2f}% — **Profit $:** {a['profit']}")
        st.markdown("---")
    if not arbs_list:
        st.info("No arbitrage opportunities found.")

# --- Auto-refresh ---
placeholder = st.empty()
while True:
    with placeholder.container():
        render_dashboard()
    time.sleep(refresh_rate)
