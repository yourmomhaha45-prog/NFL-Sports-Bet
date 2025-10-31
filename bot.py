import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Constants
SPORT = "americanfootball_nfl"
REGION = "us"
DEFAULT_BET = 100
ODDS_API_KEY = "558d1e3bfadf5243c8292da72801012f"

# Utility functions
def moneyline_to_prob(ml):
    if ml > 0:
        return 100 / (ml + 100)
    else:
        return abs(ml) / (abs(ml) + 100)

def calculate_ev(prob, payout, bet):
    return prob * payout - (1 - prob) * bet

def get_moneyline_ev(odds, bet=DEFAULT_BET):
    prob = moneyline_to_prob(odds)
    payout = (moneyline_to_multiplier(odds) - 1) * bet
    return calculate_ev(prob, payout, bet)

def spread_to_ev(point, bet=DEFAULT_BET):
    prob = 0.5 + (point / 50)
    return round(prob * bet - (1 - prob) * bet, 2)

def moneyline_to_multiplier(ml):
    return ml / 100 + 1 if ml > 0 else 100 / abs(ml) + 1

@st.cache_data(ttl=3600)
def get_available_markets():
    try:
        resp = requests.get(f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={ODDS_API_KEY}&regions={REGION}")
        resp.raise_for_status()
        data = resp.json()
        if data:
            return [m["key"] for m in data[0]["bookmakers"][0]["markets"]]
        else:
            return ["spreads"]
    except:
        return ["spreads"]

@st.cache_data(ttl=3600)
def get_upcoming_games(markets):
    all_data = []
    for market in markets:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={ODDS_API_KEY}&regions={REGION}&markets={market}"
            resp = requests.get(url)
            resp.raise_for_status()
            games = resp.json()
        except:
            continue
        for g in games:
            try:
                home_team = g['home_team']
                away_team = g['away_team']
                game_time = datetime.fromisoformat(g['commence_time'].replace("Z", "+00:00"))
                week_num = game_time.isocalendar()[1]
                bookmaker = g['bookmakers'][0]
                market_data = bookmaker['markets'][0]
                outcomes = market_data['outcomes']
                if market == "moneyline" and len(outcomes) >= 2:
                    home_ml = outcomes[0]['price']
                    away_ml = outcomes[1]['price']
                    home_ev = get_moneyline_ev(home_ml, DEFAULT_BET)
                    away_ev = get_moneyline_ev(away_ml, DEFAULT_BET)
                else:
                    home_point = outcomes[0].get('point', 0)
                    away_point = outcomes[1].get('point', 0)
                    home_ev = spread_to_ev(home_point, DEFAULT_BET)
                    away_ev = spread_to_ev(away_point, DEFAULT_BET)
                all_data.append({
                    "Week": week_num,
                    "Date": game_time,
                    "Home Team": home_team,
                    "Away Team": away_team,
                    "Market": market,
                    "Home EV ($)": round(home_ev, 2),
                    "Away EV ($)": round(away_ev, 2),
                })
            except:
                continue
    if not all_data:
        return pd.DataFrame()
    df = pd.DataFrame(all_data)
    df.sort_values(by=["Week", "Date"], inplace=True)
    return df

def calculate_best_bet(df, bet):
    df["Best Bet"] = df.apply(lambda row: row["Home Team"] if row["Home EV ($)"] > row["Away EV ($)"] else row["Away Team"], axis=1)
    df["Best EV ($)"] = df[["Home EV ($)", "Away EV ($)"]].max(axis=1)
    return df

# --- UI & Style ---
st.set_page_config(layout="wide", page_title="NFL +EV Modern Dashboard", page_icon="🏈")

# Custom CSS for ultra-modern look
st.markdown(
    """
    <style>
        body {
            background-color: #0f0f0f;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #fff;
        }
        h1 {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-size: 3rem;
            text-align: center;
            margin-top: 30px;
            margin-bottom: 20px;
            letter-spacing: 2px;
            color: #00ffff;
        }
        /* Sidebar */
        .sidebar .sidebar-content {
            background-color: #1c1c1c;
            padding: 20px;
            border-radius: 20px;
        }
        /* Filters inputs */
        .stSlider, .stNumberInput {
            background-color: #2a2a2a;
            border-radius: 10px;
        }
        /* Card grid */
        .card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        /* Card styles */
        .card {
            background-color: #1f1f2e;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .card:hover {
            transform: translateY(-8px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        /* Badge */
        .badge {
            display: inline-block;
            background-color: #00ffff;
            color: #000;
            padding: 5px 12px;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-top: 10px;
        }
        /* Modal overlay for details */
        .modal {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            opacity: 1;
            transition: opacity 0.3s ease;
        }
        /* Modal content box */
        .modal-box {
            background-color: #2e2e3e;
            padding: 30px;
            border-radius: 15px;
            max-width: 600px;
            width: 90%;
            box-shadow: 0 8px 40px rgba(0,0,0,0.5);
            color: #fff;
            position: relative;
        }
        /* Close button */
        .close-btn {
            position: absolute;
            top: 10px;
            right: 15px;
            background: #00ffff;
            border: none;
            padding: 8px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True
)

# Page title
st.markdown("<h1>🏈 NFL +EV — Modern Dashboard</h1>", unsafe_allow_html=True)

# Filters sidebar
st.sidebar.header("⚙️ Filters")
ev_threshold = st.sidebar.slider("Minimum EV ($)", -50.0, 100.0, 0.0, 5.0)
bet_amount = st.sidebar.number_input("Bet per Game ($)", value=DEFAULT_BET, step=10)

# Fetch data
markets = get_available_markets()
df_games = get_upcoming_games(markets)

# Check data
if df_games.empty:
    st.warning("No upcoming games found.")
    st.stop()

# Calculate best bets
df_games = calculate_best_bet(df_games, bet_amount)
df_games = df_games[df_games["Best EV ($)"] >= ev_threshold]

# Display
st.markdown("## Upcoming Games & Bets")
# Grid layout
import math
col_count = 3
cols = st.columns(col_count)

# Store selected game for modal
if "selected_game_idx" not in st.session_state:
    st.session_state["selected_game_idx"] = None

for i, (_, game) in enumerate(df_games.iterrows()):
    col = cols[i % col_count]
    with col:
        # create a card with hover effect
        st.markdown(
            f"""
            <div class="card" onclick="window.parent.postMessage({{'type':'select_game','index':{i}}},'*')">
                <h3 style="margin-bottom:10px;">{game['Away Team']} @ {game['Home Team']}</h3>
                <p style="font-size:0.9rem; opacity:0.7;">{game['Date'].strftime('%b %d, %H:%M')}</p>
                <div class="badge">Best Bet: {game['Best Bet']}</div>
                <p style="margin-top:8px;">EV: ${game['Best EV ($)']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        # invisible button to trigger modal
        if st.button("🔍", key=f"btn_{i}"):
            st.session_state["selected_game_idx"] = i

# Modal for game details
if st.session_state["selected_game_idx"] is not None:
    idx = st.session_state["selected_game_idx"]
    game = df_games.iloc[idx]
    st.markdown(
        f"""
        <div class="modal" style="display:flex;">
            <div class="modal-box">
                <button class="close-btn" onclick="window.parent.postMessage({{'type':'close_modal'}},'*')">Close</button>
                <h2>{game['Away Team']} @ {game['Home Team']}</h2>
                <p><b>Date:</b> {game['Date'].strftime('%b %d, %H:%M')}</p>
                <p><b>Market:</b> {game['Market']}</p>
                <p><b>Home EV:</b> ${game['Home EV ($)']}</p>
                <p><b>Away EV:</b> ${game['Away EV ($)']}</p>
                <div class="badge">Best Bet: {game['Best Bet']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )