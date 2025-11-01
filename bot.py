import streamlit as st
import pandas as pd
from datetime import datetime, timezone
import requests
import time

st.set_page_config(page_title="Live Arbitrage Dashboard", layout="wide")
st.markdown("<h1 style='text-align: center;'>⚡ Live Sports Arbitrage Dashboard</h1>", unsafe_allow_html=True)

# ------------------------
# Sidebar
# ------------------------
budget = st.sidebar.number_input("Budget ($)", value=100, step=10)
selected_sports = st.sidebar.multiselect(
    "Filter by sport", ["NFL", "NBA", "MLB", "Soccer"], default=["NFL", "NBA"]
)
top_n = st.sidebar.slider("Show top N arbitrage opportunities", 1, 20, 5)
refresh_interval = st.sidebar.slider("Auto-refresh interval (seconds)", 5, 60, 15)

# ------------------------
# Odds API setup
# ------------------------
# DIRECTLY USE THE API KEY YOU PROVIDED
THEODDS_KEY = "2aa294bcbd091e366f4249805fcf401e"

sport_map = {
    "NFL": "americanfootball_nfl",
    "NBA": "basketball_nba",
    "MLB": "baseball_mlb",
    "Soccer": "soccer_epl"
}

sport_icons = {
    "NFL": "🏈",
    "NBA": "🏀",
    "MLB": "⚾",
    "Soccer": "⚽"
}

# ------------------------
# Functions
# ------------------------
def fetch_live_odds_theoddsapi(sports_to_fetch, regions="us", markets="h2h", odds_format="decimal"):
    base = "https://api.the-odds-api.com/v4/sports"
    results = []
    headers = {"Accept": "application/json"}

    for sport_key in sports_to_fetch:
        url = f"{base}/{sport_key}/odds"
        params = {
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
            "dateFormat": "iso",
            "apiKey": THEODDS_KEY
        }
        try:
            r = requests.get(url, params=params, timeout=10, headers=headers)
            if r.status_code == 429:
                time.sleep(1.5)
                r = requests.get(url, params=params, timeout=10, headers=headers)
            r.raise_for_status()
        except requests.RequestException as e:
            st.warning(f"Odds fetch failed for {sport_key}: {e}")
            continue

        data = r.json()
        for ev in data:
            commence = ev.get("commence_time")
            try:
                date = datetime.fromisoformat(commence.replace("Z", "+00:00")).astimezone(timezone.utc)
            except Exception:
                date = datetime.utcnow()

            normalized = {}
            for book in ev.get("bookmakers", []):
                book_name = book.get("title") or book.get("key")
                book_odds = {}
                for m in book.get("markets", []):
                    if m.get("key") == "h2h":
                        for o in m.get("outcomes", []):
                            name = o.get("name")
                            price = o.get("price")
                            if name == ev.get("home_team"):
                                book_odds["home"] = price
                            elif name == ev.get("away_team"):
                                book_odds["away"] = price
                            else:
                                book_odds[name] = price
                if book_odds:
                    normalized[book_name] = book_odds

            if normalized:
                match_label = f"{ev.get('home_team')} vs {ev.get('away_team')}"
                results.append({
                    "sport": sport_key,
                    "date": date,
                    "match": match_label,
                    "odds": normalized,
                    "raw": ev
                })
        time.sleep(0.3)
    return results

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

def render_dashboard():
    sports_to_fetch = [sport_map[s] for s in selected_sports if s in sport_map]
    live_odds = fetch_live_odds_theoddsapi(sports_to_fetch)
    arbs_list = []

    for game in live_odds:
        arb = detect_arbs(game["odds"])
        if arb:
            stakes, payout, profit, profit_pct = compute_stakes(arb["best"], budget)
            arbs_list.append({
                "sport": game["sport"],
                "date": game["date"],
                "match": game["match"],
                "arb": arb,
                "stakes": stakes,
                "profit_pct": profit_pct,
                "profit": profit
            })

    arbs_list.sort(key=lambda x: x["profit_pct"], reverse=True)
    top_arbs = arbs_list[:top_n]

    if not top_arbs:
        st.info("No arbitrage opportunities found at the moment.")
        return

    for idx, a in enumerate(top_arbs):
        icon = sport_icons.get(a['sport'], "")
        highlight = "3px solid gold" if idx < 5 else "1px solid lightgray"
        color_intensity = min(255, int(a['profit_pct']*25))
        card_style = f"""
            background-color: rgba(0,{color_intensity},0,0.1);
            padding: 14px; border-radius: 14px; 
            margin-bottom: 12px;
            border: {highlight};
            transition: transform 0.2s;
        """
        st.markdown(f"<div style='{card_style}'>", unsafe_allow_html=True)
        st.markdown(f"### {icon} {a['sport']} — {a['match']}")
        st.markdown(f"**Date:** {a['date'].strftime('%b %d %Y, %H:%M')}")

        cols = st.columns(len(a['arb']['best']))
        for col_idx, (outcome, (book, odd)) in enumerate(a['arb']['best'].items()):
            with cols[col_idx]:
                hover_style = """
                    <style>
                    div:hover { transform: scale(1.05); }
                    </style>
                """
                st.markdown(hover_style, unsafe_allow_html=True)
                st.markdown(f"**{outcome.capitalize()}**")
                st.markdown(f"Book: {book}")
                st.markdown(f"Odds: {odd}")
                st.markdown(f"Stake: ${a['stakes'][outcome]}")

        st.markdown(f"<span style='background-color: rgba(0,{color_intensity},0,0.2); padding:4px 8px; border-radius:8px;'>Profit %: {a['profit_pct']:.2f}% — Profit $: {a['profit']}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------
# Auto-refresh loop
# ------------------------
placeholder = st.empty()
while True:
    with placeholder.container():
        render_dashboard()
    time.sleep(refresh_interval)
