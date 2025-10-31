import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIG ---
SPORT = "americanfootball_nfl"
REGION = "us"
DEFAULT_BET = 100
ODDS_API_KEY = st.secrets["ODDS_API_KEY"]

# --- FUNCTIONS ---
def moneyline_to_multiplier(ml):
    return ml / 100 + 1 if ml > 0 else 100 / abs(ml) + 1

def spread_to_ev(point, bet_amount=100):
    prob = 0.5 + (point / 50)  # rough approximation
    ev = prob * bet_amount - (1 - prob) * bet_amount
    return round(ev, 2)

def total_to_ev(total, bet_amount=100):
    return round(0.5 * bet_amount - 0.5 * bet_amount, 2)

@st.cache_data(ttl=3600)
def get_available_markets():
    """Get available markets dynamically to avoid 422 errors"""
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={ODDS_API_KEY}&regions={REGION}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        if isinstance(resp.json(), dict) and resp.json().get("message"):
            st.warning("Check your API key and plan: some markets may be unavailable.")
            return ["spreads"]  # default safe market
        # detect markets present in first game
        first_game = resp.json()[0]
        available = [m["key"] for m in first_game["bookmakers"][0]["markets"]]
        return available
    except Exception:
        return ["spreads"]

@st.cache_data(ttl=3600)
def get_upcoming_games(markets):
    data = []
    for market in markets:
        url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={ODDS_API_KEY}&regions={REGION}&markets={market}"
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            games = resp.json()
        except:
            continue
        for g in games:
            try:
                home_team = g['home_team']
                away_team = g['away_team']
                game_time = datetime.fromisoformat(g['commence_time'].replace("Z","+00:00"))
                week_number = game_time.isocalendar()[1]

                if market == "moneyline":
                    home_ml = g['bookmakers'][0]['markets'][0]['outcomes'][0]['price']
                    away_ml = g['bookmakers'][0]['markets'][0]['outcomes'][1]['price']
                    home_ev = (1/moneyline_to_multiplier(home_ml))*DEFAULT_BET*(moneyline_to_multiplier(home_ml)-1) - (1-(1/moneyline_to_multiplier(home_ml)))*DEFAULT_BET
                    away_ev = (1/moneyline_to_multiplier(away_ml))*DEFAULT_BET*(moneyline_to_multiplier(away_ml)-1) - (1-(1/moneyline_to_multiplier(away_ml)))*DEFAULT_BET
                elif market == "spreads":
                    home_point = g['bookmakers'][0]['markets'][0]['outcomes'][0].get('point',0)
                    away_point = g['bookmakers'][0]['markets'][0]['outcomes'][1].get('point',0)
                    home_ev = spread_to_ev(home_point, DEFAULT_BET)
                    away_ev = spread_to_ev(away_point, DEFAULT_BET)
                elif market == "totals":
                    home_ev = total_to_ev(0, DEFAULT_BET)
                    away_ev = total_to_ev(0, DEFAULT_BET)

                data.append({
                    "Week": week_number,
                    "Date": game_time,
                    "Home Team": home_team,
                    "Away Team": away_team,
                    "Market": market,
                    "Home EV ($)": round(home_ev,2),
                    "Away EV ($)": round(away_ev,2)
                })
            except:
                continue
    df = pd.DataFrame(data)
    df.sort_values(by=["Week","Date"], inplace=True)
    return df

def calculate_best_bet(df):
    df["Best Bet"] = df.apply(lambda row: row["Home Team"] if row["Home EV ($)"]>row["Away EV ($)"] else row["Away Team"], axis=1)
    df["Best EV ($)"] = df[["Home EV ($)","Away EV ($)"]].max(axis=1)
    return df

# --- APP CONFIG ---
st.set_page_config(page_title="NFL +EV Bot", layout="wide", page_icon="🏈")
if "dark_mode" not in st.session_state: st.session_state.dark_mode = True

# --- SIDEBAR ---
st.sidebar.header("⚙️ Settings")
ev_filter = st.sidebar.slider("Minimum EV ($)", -50.0, 100.0, 0.0,5.0)
toggle_dark = st.sidebar.checkbox("🌙 Dark Mode", value=st.session_state.dark_mode)
bet_amount = st.sidebar.number_input("Bet Amount per Game ($)", value=DEFAULT_BET, step=10)
if toggle_dark != st.session_state.dark_mode: st.session_state.dark_mode = toggle_dark

# --- STYLING ---
bg_img = "https://fireart.studio/wp-content/uploads/2022/05/lostmine.jpg"
if st.session_state.dark_mode:
    card_bg = "rgba(30,30,30,0.85)"
    text_color = "#f5e6c8"
    accent_color = "#d4af37"
else:
    card_bg = "#ffffff"
    text_color = "#1a1a1a"
    accent_color = "#0056d6"

st.markdown(f"""
<style>
body {{
    background: url('{bg_img}') no-repeat center center fixed;
    background-size: cover;
    color: {text_color};
    font-family: 'Cinzel', serif;
}}
h1,h2,h3 {{color:{accent_color}; text-shadow: 2px 2px 6px #000000;}}
.card {{
    background: {card_bg};
    border: 2px solid #a57c32;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.6);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}}
.card:hover {{
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 16px 36px rgba(0,0,0,0.9);
}}
.glow-badge {{
    background: linear-gradient(135deg, #d4af37, #ffd700);
    color: #1b1b1b;
    padding: 6px 10px;
    border-radius: 10px;
    font-size: 12px;
    box-shadow: 0 0 10px #ffd700, 0 0 20px #d4af37, 0 0 30px #ffd700;
    animation: glow 1.5s infinite alternate;
}}
@keyframes glow {{
    0% {{ box-shadow: 0 0 5px #ffd700, 0 0 10px #d4af37, 0 0 15px #ffd700; }}
    50% {{ box-shadow: 0 0 15px #ffd700, 0 0 25px #d4af37, 0 0 35px #ffd700; }}
    100% {{ box-shadow: 0 0 5px #ffd700, 0 0 10px #d4af37, 0 0 15px #ffd700; }}
}}
/* Animated gold particles */
.particle {{
    position: absolute;
    width: 4px; height: 4px;
    background: gold;
    border-radius: 50%;
    animation: float 5s infinite linear;
    opacity: 0.7;
}}
@keyframes float {{
    0% {{ transform: translateY(0) translateX(0); opacity:0.5; }}
    50% {{ transform: translateY(-80px) translateX(30px); opacity:1; }}
    100% {{ transform: translateY(-160px) translateX(-20px); opacity:0; }}
}}
</style>
""", unsafe_allow_html=True)

# Add particles
for i in range(30):
    x = st.session_state.get(f"x{i}", None)
    if not x:
        import random
        x = random.randint(0, 100)
        st.session_state[f"x{i}"] = x
    st.markdown(f'<div class="particle" style="left:{x}%; top:100%;"></div>', unsafe_allow_html=True)

# --- HEADER ---
st.markdown("<h1 style='text-align:center;'>🏈 NFL +EV Bot – Lost Mine Edition</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; opacity:0.8;'>Weekly EV, Moneyline, Spread & Totals bets</p>", unsafe_allow_html=True)

# --- DATA ---
available_markets = get_available_markets()
games_df = get_upcoming_games(available_markets)
if games_df.empty:
    st.warning("No upcoming games found.")
    st.stop()

games_df = calculate_best_bet(games_df)
games_df = games_df[games_df["Best EV ($)"]>=ev_filter]
weeks = sorted(games_df["Week"].unique())

# --- WEEK TABS ---
week_tabs = st.tabs([f"Week {w}" for w in weeks])
for i, week in enumerate(weeks):
    with week_tabs[i]:
        week_df = games_df[games_df["Week"]==week]
        market_tabs = st.tabs(available_markets)
        for j, market in enumerate(available_markets):
            with market_tabs[j]:
                market_df = week_df[week_df["Market"]==market]
                st.markdown(f"<h2 style='text-align:center;'>Week {week} - {market.title()}</h2>", unsafe_allow_html=True)
                total_ev = market_df["Best EV ($)"].sum()
                num_bets = market_df.shape[0]
                st.markdown(f"<p style='text-align:center; font-weight:600;'>Simulated Bets: {num_bets} | Total Expected Profit: ${total_ev}</p>", unsafe_allow_html=True)

                cols = st.columns(3)
                c_idx = 0
                for idx, game in market_df.iterrows():
                    with cols[c_idx]:
                        st.markdown(
                            f"""
                           
