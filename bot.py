import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Your API key
API_KEY = "558d1e3bfadf5243c8292da72801012f"

# Utility functions
def moneyline_to_prob(ml):
    if ml > 0:
        return 100 / (ml + 100)
    else:
        return abs(ml) / (abs(ml) + 100)

def calculate_ev(prob, payout, bet):
    return prob * payout - (1 - prob) * bet

def get_moneyline_ev(odds, bet=100):
    prob = moneyline_to_prob(odds)
    payout = (moneyline_to_multiplier(odds) - 1) * bet
    return round(calculate_ev(prob, payout, bet), 2)

def spread_to_ev(point, bet=100):
    prob = 0.5 + (point / 50)
    return round(prob * bet - (1 - prob) * bet, 2)

def moneyline_to_multiplier(ml):
    return ml / 100 + 1 if ml > 0 else 100 / abs(ml) + 1

# Fetch data with debug logs
@st.cache_data(ttl=3600)
def fetch_games():
    url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/?apiKey={API_KEY}&regions=us&markets=spreads"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        st.write("API response data:", data)  # Debug: show raw data
        games_list = []

        for g in data:
            try:
                home = g['home_team']
                away = g['away_team']
                dt = datetime.fromisoformat(g['commence_time'].replace("Z", "+00:00"))
                week = dt.isocalendar()[1]
                outcomes = g['bookmakers'][0]['markets'][0]['outcomes']
                if len(outcomes) >= 2:
                    if 'price' in outcomes[0]:
                        home_ml = outcomes[0]['price']
                        away_ml = outcomes[1]['price']
                        home_ev = get_moneyline_ev(home_ml)
                        away_ev = get_moneyline_ev(away_ml)
                    else:
                        home_point = outcomes[0].get('point', 0)
                        away_point = outcomes[1].get('point', 0)
                        home_ev = spread_to_ev(home_point)
                        away_ev = spread_to_ev(away_point)
                    games_list.append({
                        "Week": week,
                        "Date": dt,
                        "Home Team": home,
                        "Away Team": away,
                        "Market": "spreads",
                        "Home EV": home_ev,
                        "Away EV": away_ev
                    })
            except Exception as e:
                st.write("Error processing a game:", e)
        if not games_list:
            st.write("No games found.")
        df = pd.DataFrame(games_list).sort_values(by=["Week", "Date"])
        return df
    except Exception as e:
        st.write("Error fetching data from API:", e)
        return pd.DataFrame()

# --- UI Setup ---
st.set_page_config(
    layout="wide",
    page_title="NFL +EV Dashboard",
    page_icon="🏈"
)

# Custom CSS for sleek futuristic look
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');

body {
    background: linear-gradient(135deg, #000000, #1a1a1a);
    font-family: 'Orbitron', sans-serif;
    color: #fff;
    margin: 0;
}
h1 {
    font-family: 'Orbitron', sans-serif;
    font-size: 3.5rem;
    text-align: center;
    margin-top: 20px;
    margin-bottom: 30px;
    color: #00ffff;
    text-shadow: 0 0 10px #00ffff, 0 0 20px #00ffff;
}
.sidebar .sidebar-content {
    background: rgba(20,20,20,0.8);
    padding: 20px;
    border-radius: 20px;
    box-shadow: 0 0 20px #00ffff44;
}
.stSlider, .stNumberInput {
    background: #222;
    border-radius: 8px;
    border: none;
    color: #fff;
}
.cards-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
    padding: 20px;
}
.card {
    background: rgba(255,255,255,0.05);
    border-radius: 20px;
    padding: 20px;
    box-shadow: inset 0 0 10px #00ffff33, 0 0 20px #00ffff33;
    cursor: pointer;
    transition: all 0.4s ease;
    backdrop-filter: blur(8px);
    border: 1px solid #00ffff44;
}
.card:hover {
    box-shadow: inset 0 0 15px #00ffff66, 0 0 30px #00ffff66;
    transform: translateY(-4px);
}
.label {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 10px;
    background: linear-gradient(45deg, #00ffff, #ff00ff);
    font-weight: 600;
    font-size: 0.75rem;
    margin-top: 10px;
    box-shadow: 0 0 10px #00ffff44;
    animation: pulse 2s infinite alternate;
}
@keyframes pulse {
    from { box-shadow: 0 0 10px #00ffff44; }
    to { box-shadow: 0 0 20px #00ffff88; }
}
.modal {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(10,10,10,0.9);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 9999;
    opacity: 1;
    transition: opacity 0.3s ease;
}
.modal-box {
    background: rgba(20,20,20,0.95);
    padding: 30px;
    border-radius: 20px;
    max-width: 600px;
    width: 90%;
    box-shadow: 0 0 30px #00ffff66;
    color: #fff;
    position: relative;
    backdrop-filter: blur(10px);
}
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
}
.close-btn:hover {
    box-shadow: 0 0 20px #ff00ff88, 0 0 30px #00ffff88;
    transform: translateY(-2px);
}
</style>
""", unsafe_allow_html=True)

# --- Title ---
st.markdown("<h1>🏈 FUTURISTIC NFL +EV DASHBOARD</h1>", unsafe_allow_html=True)

# --- Sidebar filters ---
st.sidebar.header("Filters & Settings")
ev_threshold = st.sidebar.slider("Minimum EV ($)", -50, 100, 0, 5)
bet_amount = st.sidebar.number_input("Bet Amount ($)", value=100, step=10)

# --- Fetch data ---
df = fetch_games()

if df.empty:
    st.warning("No data available. Make sure your API key is correct and NFL games are scheduled.")
    st.stop()

# --- Compute best bets ---
df['Best Bet'] = df.apply(
    lambda row: row['Home Team'] if row['Home EV'] > row['Away EV'] else row['Away Team'], axis=1)
df['Best EV'] = df[['Home EV', 'Away EV']].max(axis=1)
df = df[df['Best EV'] >= ev_threshold]

# --- Show cards ---
st.markdown("<h2 style='text-align:center;'>Upcoming Games & Bets</h2>", unsafe_allow_html=True)

html_cards = '<div class="cards-container">'
for idx, row in df.iterrows():
    html_cards += f"""
    <div class='card' onclick="window.parent.postMessage({{'type':'show_detail','index':{idx}}},'*')">
        <h3>{row['Away Team']} @ {row['Home Team']}</h3>
        <p style='opacity:0.7;'>{row['Date'].strftime('%b %d, %H:%M')}</p>
        <div class='label'>Market: {row['Market'].replace('_', ' ').title()}</div>
        <p><b>Bet:</b> {row['Best Bet']} | EV: ${row['Best EV']}</p>
    </div>
    """
html_cards += '</div>'
st.markdown(html_cards, unsafe_allow_html=True)

# --- Modal popup to show details ---
if st.session_state.get("show_detail_idx") is not None:
    idx = st.session_state["show_detail_idx"]
    game = df.iloc[idx]
    st.markdown(
        f"""
        <div class='modal'>
            <div class='modal-box'>
                <button class='close-btn' onclick="window.parent.postMessage({{'type':'close_modal'}},'*')">X</button>
                <h2 style='text-align:center;'>{game['Away Team']} @ {game['Home Team']}</h2>
                <p><b>Date:</b> {game['Date'].strftime('%b %d, %H:%M')}</p>
                <p><b>Market:</b> {game['Market'].replace('_', ' ').title()}</p>
                <p><b>Home EV:</b> ${game['Home EV']}</p>
                <p><b>Away EV:</b> ${game['Away EV']}</p>
                <div class='label'>Best Bet: {game['Best Bet']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True
    )