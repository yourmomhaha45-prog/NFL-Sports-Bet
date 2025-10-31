import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Constants
SPORT = "americanfootball_nfl"
REGION = "us"
DEFAULT_BET = 100
ODDS_API_KEY = "558d1e3bfadf5243c8292da72801012f"

# Helper functions
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

# --- UI & Styling ---

st.set_page_config(layout="wide", page_title="NFL +EV Modern Dashboard", page_icon="🏈")

# Custom CSS for a futuristic look
st.markdown(
    """
    <style>
        body {
            background: linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 100%);
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #fff;
            margin: 0;
            padding: 0;
        }
        h1 {
            font-family: 'Orbitron', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-size: 4rem;
            text-align: center;
            margin-top: 30px;
            color: #00ffff;
            text-shadow: 0 0 10px #00ffff, 0 0 20px #00ffff;
        }
        /* Sidebar style */
        .sidebar .sidebar-content {
            background: #111;
            padding: 20px;
            border-radius: 20px;
            box-shadow: 0 0 20px #000;
        }
        /* Filters & control inputs */
        .stSlider, .stNumberInput {
            background: #222;
            border-radius: 10px;
        }
        /* Cards grid layout */
        .cards-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            padding: 20px;
        }
        /* Individual card style */
        .card {
            background: #1f1f2e;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 0 30px rgba(0,255,255,0.2);
            transition: all 0.3s ease;
            cursor: pointer;
            backdrop-filter: blur(10px);
        }
        .card:hover {
            box-shadow: 0 0 50px rgba(0,255,255,0.4);
            transform: translateY(-4px);
        }
        /* Badges & labels */
        .badge {
            display: inline-block;
            background-color: #00ffff;
            color: #000;
            padding: 4px 12px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.75rem;
            margin-top: 10px;
            margin-bottom: 10px;
        }
        /* Modal overlay for details */
        .modal {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            opacity: 1;
            transition: opacity 0.3s ease;
        }
        /* Modal content box */
        .modal-box {
            background: #222;
            padding: 30px;
            border-radius: 25px;
            max-width: 600px;
            width: 90%;
            box-shadow: 0 0 40px rgba(0,255,255,0.3);
            position: relative;
            color: #fff;
        }
        /* Close button */
        .close-btn {
            position: absolute;
            top: 15px;
            right: 20px;
            background: #00ffff;
            border: none;
            border-radius: 8px;
            padding: 8px 14px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s;
        }
        .close-btn:hover {
            background: #0ff;
        }
    </style>
    """, unsafe_allow_html=True
)

# HEADER
st.markdown("<h1>🏈 NFL +EV Dashboard</h1>", unsafe_allow_html=True)

# SIDEBAR filters
st.sidebar.header("Filters & Settings")
ev_threshold = st.sidebar.slider("Minimum EV ($)", -50, 100, 0, 5)
bet_amount = st.sidebar.number_input("Bet Amount ($)", value=DEFAULT_BET, step=10)

# Get data
markets = get_available_markets()
df = get_upcoming_games(markets)

if df.empty:
    st.warning("No upcoming games data.")
    st.stop()

# Compute best bets
df = calculate_best_bet(df, bet_amount)
df = df[df["Best EV ($)"] >= ev_threshold]

# Display in a grid of cards
st.markdown(f"<h2 style='text-align:center;'>Upcoming Matches & Bets</h2>", unsafe_allow_html=True)

# Container for cards
container = st.container()
with container:
    # Use HTML + CSS grid for modern look
    st.markdown('<div class="cards-container">', unsafe_allow_html=True)
    for idx, row in df.iterrows():
        html = f"""
        <div class="card" onclick="window.parent.postMessage({{'type':'show_detail','index':{idx}}},'*')">
            <h3 style='margin-bottom:10px;'>{row['Away Team']} @ {row['Home Team']}</h3>
            <p style='opacity:0.7;'>{row['Date'].strftime("%b %d, %H:%M")}</p>
            <div class='badge'>Best Bet: {row['Best Bet']}</div>
            <p style='margin-top:10px;'>EV: <b>${row['Best EV ($)']}</b></p>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Handle modal popup via custom JavaScript
if st.session_state.get("show_detail_idx") is not None:
    idx = st.session_state["show_detail_idx"]
    game = df.iloc[idx]
    st.markdown(
        f"""
        <div class="modal" style="display:flex;">
            <div class="modal-box">
                <button class="close-btn" onclick="window.parent.postMessage({{'type':'close_modal'}},'*')">X</button>
                <h2>{game['Away Team']} @ {game['Home Team']}</h2>
                <p><b>Date:</b> {game['Date'].strftime("%b %d, %H:%M")}</p>
                <p><b>Market:</b> {game['Market']}</p>
                <p><b>Home EV:</b> ${game['Home EV ($)']}</p>
                <p><b>Away EV:</b> ${game['Away EV ($)']}</p>
                <div class='badge'>Best Bet: {game['Best Bet']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True
    )