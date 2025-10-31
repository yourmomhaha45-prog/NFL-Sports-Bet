import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURATION ---
SPORT = "americanfootball_nfl"
REGION = "us"
API_KEY = "558d1e3bfadf5243c8292da72801012f"  # Your provided API key
DEFAULT_BET = 100

# --- Utility functions ---
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

# --- Fetch available markets ---
@st.cache_data(ttl=3600)
def get_available_markets():
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={API_KEY}&regions={REGION}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        st.write("Available markets from API:", data)  # Debug log
        if data:
            return [m["key"] for m in data[0]["bookmakers"][0]["markets"]]
        else:
            return ["spreads"]
    except Exception as e:
        st.write("Error fetching markets:", e)
        return ["spreads"]

# --- Fetch upcoming games ---
@st.cache_data(ttl=3600)
def get_upcoming_games(markets):
    all_games = []
    for market in markets:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={API_KEY}&regions={REGION}&markets={market}"
            resp = requests.get(url)
            resp.raise_for_status()
            games = resp.json()
            st.write(f"API response for market '{market}':", games)  # Debug log
        except Exception as e:
            st.write(f"Error fetching data for market '{market}': {e}")
            continue

        if not games:
            continue

        for g in games:
            try:
                home_team = g['home_team']
                away_team = g['away_team']
                date_obj = datetime.fromisoformat(g['commence_time'].replace("Z", "+00:00"))
                week_num = date_obj.isocalendar()[1]
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
                all_games.append({
                    "Week": week_num,
                    "Date": date_obj,
                    "Home Team": home_team,
                    "Away Team": away_team,
                    "Market": market,
                    "Home EV": round(home_ev, 2),
                    "Away EV": round(away_ev, 2)
                })
            except Exception as e:
                st.write("Error parsing game:", e)
                continue
    if not all_games:
        return pd.DataFrame()
    df = pd.DataFrame(all_games)
    df.sort_values(by=["Week", "Date"], inplace=True)
    return df

# --- Main app ---
st.set_page_config(layout="wide", page_title="Futuristic NFL +EV Dashboard", page_icon="🏈")

# --- Custom CSS for futuristic look ---
st.markdown(
    """
    <style>
        body {
            background: linear-gradient(135deg, #0f0f0f, #1a1a1a);
            font-family: 'Orbitron', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #fff;
        }
        h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 4rem;
            text-align: center;
            margin-top: 30px;
            margin-bottom: 20px;
            color: #00ffff;
            text-shadow: 0 0 15px #00ffff, 0 0 30px #00ffff;
        }
        /* Sidebar styling */
        .sidebar .sidebar-content {
            background: rgba(20,20,20,0.8);
            padding: 20px;
            border-radius: 20px;
            box-shadow: 0 0 20px #00ffff55;
        }
        /* Inputs */
        .stSlider, .stNumberInput {
            background: #222;
            border-radius: 10px;
            border: none;
            color: #fff;
        }
        /* Cards container grid */
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            padding: 20px;
        }
        /* Individual card style */
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 20px;
            box-shadow: inset 0 0 10px #00ffff33, 0 0 20px #00ffff33;
            cursor: pointer;
            transition: all 0.4s ease;
            backdrop-filter: blur(8px);
        }
        .card:hover {
            box-shadow: inset 0 0 15px #00ffff66, 0 0 30px #00ffff66;
            transform: translateY(-4px);
        }
        /* Labels & badges */
        .label {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 10px;
            background: linear-gradient(45deg, #00ffff, #ff00ff);
            background-size: 200% 200%;
            animation: glow 2s linear infinite;
            font-weight: 600;
            font-size: 0.75rem;
            margin-top: 10px;
        }
        @keyframes glow {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        /* Modal overlay styles */
        .modal {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(15,15,15,0.9);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            opacity: 1;
            transition: opacity 0.3s ease;
        }
        /* Modal content box */
        .modal-box {
            background: rgba(20,20,20,0.95);
            padding: 30px;
            border-radius: 25px;
            max-width: 600px;
            width: 90%;
            box-shadow: 0 0 40px #00ffff66;
            color: #fff;
            position: relative;
            backdrop-filter: blur(10px);
        }
        /* Close button style */
        .close-btn {
            position: absolute;
            top: 10px;
            right: 15px;
            background: linear-gradient(135deg, #ff00ff, #00ffff);
            border: none;
            padding: 8px 14px;
            border-radius: 10px;
            cursor: pointer;
            font-weight: bold;
            box-shadow: 0 0 10px #ff00ff55, 0 0 20px #00ffff55;
            transition: all 0.3s ease;
        }
        .close-btn:hover {
            box-shadow: 0 0 20px #ff00ff88, 0 0 30px #00ffff88;
            transform: translateY(-2px);
        }
    </style>
    """, unsafe_allow_html=True
)

# --- HEADER ---
st.markdown("<h1>🏈 FUTURISTIC NFL +EV DASHBOARD</h1>", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("Filters & Settings")
ev_threshold = st.sidebar.slider("Minimum EV ($)", -50, 100, 0, 5)
bet_amount = st.sidebar.number_input("Bet Amount ($)", value=DEFAULT_BET, step=10)

# --- Fetch & process data ---
markets = get_available_markets()
df = get_upcoming_games(markets)

if df.empty:
    st.warning("No upcoming game data available. Check your API key, sport parameters, or if the API has current data.")
    st.stop()

# Compute best bets and filter
df = compute_bets(df, bet_amount)
df = df[df["Best EV"] >= ev_threshold]

# --- Display cards ---
st.markdown("<h2 style='text-align:center; margin-top:30px;'>Upcoming Matches & Bets</h2>", unsafe_allow_html=True)

cards_html = '<div class="cards-grid">'
for idx, row in df.iterrows():
    html = f"""
    <div class="card" onclick="window.parent.postMessage({{'type':'show_detail','index':{idx}}},'*')">
        <h3 style='margin-bottom:8px;'>{row['Away Team']} @ {row['Home Team']}</h3>
        <p style='opacity:0.7; font-size:0.9rem;'>{row['Date'].strftime('%b %d, %H:%M')}</p>
        <div class='label'>Market: {row['Market'].replace('_', ' ').title()}</div>
        <div style='margin-top:10px;'>
            <strong>Best Bet:</strong> {row['Best Bet']}<br>
            <strong>EV:</strong> ${row['Best EV']}
        </div>
    </div>
    """
    cards_html += html
cards_html += '</div>'
st.markdown(cards_html, unsafe_allow_html=True)

# --- Modal for game details ---
if st.session_state.get("show_detail_idx") is not None:
    idx = st.session_state["show_detail_idx"]
    game = df.iloc[idx]
    st.markdown(
        f"""
        <div class="modal">
            <div class="modal-box">
                <button class="close-btn" onclick="window.parent.postMessage({{'type':'close_modal'}},'*')">X</button>
                <h2 style='text-align:center;'>{game['Away Team']} @ {game['Home Team']}</h2>
                <p><strong>Date:</strong> {game['Date'].strftime('%b %d, %H:%M')}</p>
                <p><strong>Market:</strong> {game['Market'].replace('_', ' ').title()}</p>
                <p><strong>Home EV:</strong> ${game['Home EV']}</p>
                <p><strong>Away EV:</strong> ${game['Away EV']}</p>
                <div class='label'>Best Bet: {game['Best Bet']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True
    )