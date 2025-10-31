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
    prob = 0.5 + (point / 50)
    ev = prob * bet_amount - (1 - prob) * bet_amount
    return round(ev, 2)

def total_to_ev(total, bet_amount=100):
    return round(0.5 * bet_amount - 0.5 * bet_amount, 2)

@st.cache_data(ttl=3600)
def get_available_markets():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={ODDS_API_KEY}&regions={REGION}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        first_game = resp.json()[0]
        return [m["key"] for m in first_game["bookmakers"][0]["markets"]]
    except:
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
                else:
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

# --- SIDEBAR ---
st.sidebar.header("⚙️ Settings")
ev_filter = st.sidebar.slider("Minimum EV ($)", -50.0, 100.0, 0.0,5.0)
bet_amount = st.sidebar.number_input("Bet Amount per Game ($)", value=DEFAULT_BET, step=10)

# --- MODERN DARK CSS ---
st.markdown("""
<style>
body { background-color: #12121a; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin:0; padding:0; }
h1,h2,h3 { color:#b67aff; margin-bottom:0.5rem; }
.card { background:#1f1f2a; border-radius:12px; padding:18px 24px; margin:12px 0; box-shadow:0 2px 8px rgba(0,0,0,0.5); transition: transform 0.2s ease, box-shadow 0.2s ease; }
.card:hover { transform: translateY(-4px); box-shadow:0 6px 20px rgba(0,0,0,0.7); }
.glow-badge { background: linear-gradient(135deg,#7f5af0,#b67aff); color:white; padding:4px 10px; border-radius:8px; font-size:0.85rem; text-transform:uppercase; box-shadow:0 0 12px rgba(182,122,255,0.6),0 0 24px rgba(127,90,240,0.4); animation:glow 1.8s infinite alternate; }
@keyframes glow { from { box-shadow:0 0 6px rgba(182,122,255,0.4),0 0 18px rgba(127,90,240,0.2); } to { box-shadow:0 0 18px rgba(182,122,255,0.8),0 0 36px rgba(127,90,240,0.6); } }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("<h1 style='text-align:center;'>🏈 NFL +EV Bot – Modern Edition</h1>", unsafe_allow_html=True)
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

# --- WEEK & MARKET TABS ---
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

                # --- CARD GRID ---
                cols = st.columns(3)
                c_idx = 0
                for idx, game in market_df.iterrows():
                    with cols[c_idx]:
                        st.markdown(f"""
                        <div class="card">
                            <h4>{game['Away Team']} @ {game['Home Team']}</h4>
                            <p style="font-size:0.9rem; opacity:0.75;">{game['Date'].strftime("%b %d, %I:%M %p")}</p>
                            <p><span class="glow-badge">Best Bet: {game['Best Bet']}</span></p>
                            <p style="margin-top:8px;">EV: <strong>${game['Best EV ($)']}</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                    c_idx = (c_idx + 1) % 3
