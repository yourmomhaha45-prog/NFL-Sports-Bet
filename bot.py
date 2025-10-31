import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- Constants ---
SPORT = "americanfootball_nfl"
REGION = "us"
DEFAULT_BET = 100
API_KEY = "YOUR_API_KEY"  # Replace with your actual API key

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

# --- Data fetching with robustness ---
@st.cache_data(ttl=3600)
def get_available_markets():
    try:
        resp = requests.get(f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={API_KEY}&regions={REGION}")
        resp.raise_for_status()
        data = resp.json()
        return [m["key"] for m in data[0]["bookmakers"][0]["markets"]]
    except:
        return ["spreads"]

@st.cache_data(ttl=3600)
def get_upcoming_games(markets):
    all_games = []
    for market in markets:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={API_KEY}&regions={REGION}&markets={market}"
            resp = requests.get(url)
            resp.raise_for_status()
            games = resp.json()
        except:
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
            except:
                continue
    if not all_games:
        return pd.DataFrame()
    df = pd.DataFrame(all_games)
    df.sort_values(by=["Week", "Date"], inplace=True)
    return df

def compute_bets(df, bet_amount):
    df['Best Bet'] = df.apply(
        lambda row: row['Home Team'] if row['Home EV'] > row['Away EV'] else row['Away Team'], axis=1)
    df['Best EV'] = df[['Home EV', 'Away EV']].max(axis=1)
    return df

# --- Custom CSS for futuristic UI ---
st.set_page_config(
    layout="wide",
    page_title="Futuristic NFL +EV Dashboard",
    page_icon="🏈"
)

st.markdown(
    """
    <style>
        /* Background gradient with glow */
        body {
            background: linear-gradient(135deg, #0f0f0f, #1a1a1a);
            font-family: 'Orbitron', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #fff;
            margin: 0;
            padding: 0;
        }
        /* Title with glow effect */
        h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 4rem;
            text-align: center;
            margin-top: 30px;
            margin-bottom: 20px;
            color: #00ffff;
            text-shadow: 0 0 10px #00ffff, 0 0 20px #00ffff;
        }
        /* Sidebar style */
        .sidebar .sidebar-content {
            background: rgba(20, 20, 20, 0.8);
            padding: 20px;
            border-radius: 20px;
            box-shadow: 0 0 20px #00ffff55;
        }
        /* Inputs style */
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
        /* Label styles */
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
        /* Modal overlay style */
        .modal {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(15, 15, 15, 0.9);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            opacity: 1;
            transition: opacity 0.3s ease;
        }
        /* Modal content style */
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
st.sidebar.header("Settings & Filters")
ev_threshold = st.sidebar.slider("Minimum EV ($)", -50, 100, 0, 5)
bet_amount = st.sidebar.number_input("Bet Amount ($)", value=DEFAULT_BET, step=10)

# --- Fetch & Process Data ---
markets = get_available_markets()
df_games = get_upcoming_games(markets)

if df_games.empty:
    st.warning("No upcoming game data available.")
    st.stop()

df_games = compute_bets(df_games, bet_amount)
df_games = df_games[df_games["Best EV"] >= ev_threshold]

# --- Display Cards ---
st.markdown("<h2 style='text-align:center; margin-top:30px;'>Upcoming Matches & Bets</h2>", unsafe_allow_html=True)

grid_html = '<div class="cards-grid">'
for idx, row in df_games.iterrows():
    html = f"""
    <div class="card" onclick="window.parent.postMessage({{'type':'show_detail','index':{idx}}},'*')">
        <div style="display:flex; justify-content: space-between; align-items: center;">
            <h3 style="margin:0;">{row['Away Team']} @ {row['Home Team']}</h3>
            <div class="label">{row['Market'].replace('_', ' ').title()}</div>
        </div>
        <p style="opacity:0.7; margin-top:8px;">{row['Date'].strftime('%b %d, %H:%M')}</p>
        <div style="margin-top:10px;">
            <div style="margin-bottom:8px;">
                <strong>Best Bet:</strong> {row['Best Bet']}
            </div>
            <div class="label" style="background: linear-gradient(45deg, #00ffff, #ff00ff); font-size:0.8rem;">
                EV: ${row['Best EV']}
            </div>
        </div>
    </div>
    """
    grid_html += html
grid_html += '</div>'
st.markdown(grid_html, unsafe_allow_html=True)

# --- Modal for details ---
if st.session_state.get("show_detail_idx") is not None:
    idx = st.session_state["show_detail_idx"]
    game = df_games.iloc[idx]
    st.markdown(
        f"""
        <div class="modal">
            <div class="modal-box">
                <button class="close-btn" onclick="window.parent.postMessage({{'type':'close_modal'}},'*')">X</button>
                <h2 style="text-align:center;">{game['Away Team']} @ {game['Home Team']}</h2>
                <p><strong>Date:</strong> {game['Date'].strftime('%b %d, %H:%M')}</p>
                <p><strong>Market:</strong> {game['Market'].replace('_', ' ').title()}</p>
                <p><strong>Home EV:</strong> ${game['Home EV']}</p>
                <p><strong>Away EV:</strong> ${game['Away EV']}</p>
                <div class="label">Best Bet: {game['Best Bet']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True
    )