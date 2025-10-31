import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone

# -------- CONFIG --------
SPORT = "americanfootball_nfl"
REGION = "us"
MARKETS = ["moneyline", "spreads", "totals"]  # Multiple markets
DEFAULT_BET = 100
ODDS_API_KEY = st.secrets["ODDS_API_KEY"]

# -------- FUNCTIONS --------
def moneyline_to_multiplier(ml):
    return ml / 100 + 1 if ml > 0 else 100 / abs(ml) + 1

def spread_to_ev(point, bet_amount=100):
    # Simple mock: assume point spreads translate to 50/50 probability if spread=0
    prob = 0.5 + (point / 50)  # crude approximation
    ev = prob * bet_amount - (1 - prob) * bet_amount
    return round(ev, 2)

def total_to_ev(total, bet_amount=100):
    # Simple mock: assume even probability for over/under
    return round(0.5 * bet_amount - 0.5 * bet_amount, 2)

@st.cache_data(ttl=3600)
def get_upcoming_games():
    """Fetch NFL odds for multiple markets"""
    data = []
    url_base = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={ODDS_API_KEY}&regions={REGION}&markets="
    for market in MARKETS:
        url = url_base + market
        response = requests.get(url)
        if response.status_code != 200:
            st.error(f"Error fetching {market} data: {response.status_code}")
            continue
        games = response.json()
        for g in games:
            try:
                home_team = g['home_team']
                away_team = g['away_team']
                game_time = datetime.fromisoformat(g['commence_time'].replace("Z", "+00:00"))
                week_number = game_time.isocalendar()[1]

                if market == "moneyline":
                    home_ml = g['bookmakers'][0]['markets'][0]['outcomes'][0]['price']
                    away_ml = g['bookmakers'][0]['markets'][0]['outcomes'][1]['price']
                    home_ev = (1 / moneyline_to_multiplier(home_ml)) * DEFAULT_BET * (moneyline_to_multiplier(home_ml)-1) - (1-(1 / moneyline_to_multiplier(home_ml))) * DEFAULT_BET
                    away_ev = (1 / moneyline_to_multiplier(away_ml)) * DEFAULT_BET * (moneyline_to_multiplier(away_ml)-1) - (1-(1 / moneyline_to_multiplier(away_ml))) * DEFAULT_BET
                elif market == "spreads":
                    home_point = g['bookmakers'][0]['markets'][0]['outcomes'][0].get('point', 0)
                    away_point = g['bookmakers'][0]['markets'][0]['outcomes'][1].get('point', 0)
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
                    "Home EV ($)": round(home_ev, 2),
                    "Away EV ($)": round(away_ev, 2)
                })
            except Exception:
                continue

    df = pd.DataFrame(data)
    df.sort_values(by=["Week", "Date"], inplace=True)
    return df

def calculate_best_bet(df):
    df["Best Bet"] = df.apply(lambda row: row["Home Team"] if row["Home EV ($)"] > row["Away EV ($)"] else row["Away Team"], axis=1)
    df["Best EV ($)"] = df[["Home EV ($)", "Away EV ($)"]].max(axis=1)
    return df

# -------- APP CONFIG --------
st.set_page_config(page_title="NFL +EV Bot", layout="wide", page_icon="🏈")

# -------- SESSION STATE --------
if "selected_game" not in st.session_state: st.session_state.selected_game = None
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False

# -------- SIDEBAR --------
st.sidebar.header("⚙️ Settings")
ev_filter = st.sidebar.slider("Minimum EV ($)", -50.0, 100.0, 0.0, 5.0)
bet_amount = st.sidebar.number_input("Bet Amount per Game ($)", value=DEFAULT_BET, step=10)
toggle_dark = st.sidebar.checkbox("🌙 Dark Mode", value=st.session_state.dark_mode)
if toggle_dark != st.session_state.dark_mode:
    st.session_state.dark_mode = toggle_dark

# -------- COLORS --------
if st.session_state.dark_mode:
    bg_color, card_bg, text_color, accent_color = "#0f0f17", "#1b1b2a", "#f1f1f1", "#007bff"
else:
    bg_color, card_bg, text_color, accent_color = "#f5f7fb", "#ffffff", "#1a1a1a", "#0056d6"

# -------- CSS --------
st.markdown(f"""
<style>
body {{background-color: {bg_color}; color: {text_color}; font-family: 'Inter', sans-serif;}}
h1,h2,h3 {{color:{accent_color}; font-weight:600;}}
.card {{background:{card_bg}; border-radius:16px; padding:20px; margin-bottom:20px; box-shadow:0 4px 12px rgba(0,0,0,0.1); transition: all 0.15s ease;}}
.card:hover {{transform: translateY(-3px); box-shadow:0 8px 24px rgba(0,0,0,0.25);}}
.badge {{background:linear-gradient(135deg, #4cd137,#44bd32); color:white; padding:6px 10px; border-radius:10px; font-size:12px;}}
</style>
""", unsafe_allow_html=True)

# -------- DATA --------
games_df = get_upcoming_games()
if games_df.empty: st.warning("No upcoming games found."); st.stop()

games_df = calculate_best_bet(games_df)
games_df = games_df[games_df["Best EV ($)"] >= ev_filter]
weeks = sorted(games_df["Week"].unique())

# -------- HEADER --------
st.markdown("<h1 style='text-align:center;'>🏈 NFL +EV Multi-Market Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; opacity:0.8;'>Weekly EV, Moneyline, Spread & Totals bets with simulated profit.</p>", unsafe_allow_html=True)

# -------- WEEK TABS --------
week_tabs = st.tabs([f"Week {w}" for w in weeks])
for i, week in enumerate(weeks):
    with week_tabs[i]:
        week_df = games_df[games_df["Week"]==week]

        # -------- MARKET TABS --------
        market_tabs = st.tabs(MARKETS)
        for j, market in enumerate(MARKETS):
            with market_tabs[j]:
                market_df = week_df[week_df["Market"]==market]
                st.markdown(f"<h2 style='text-align:center;'>Week {week} - {market.title()}</h2>", unsafe_allow_html=True)

                # Simulation
                total_ev = market_df["Best EV ($)"].sum()
                num_bets = market_df.shape[0]
                st.markdown(f"<p style='text-align:center; font-weight:600;'>Simulated Bets: {num_bets} | Total Expected Profit: ${total_ev}</p>", unsafe_allow_html=True)

                cols = st.columns(3)
                c_idx = 0
                for idx, game in market_df.iterrows():
                    with cols[c_idx]:
                        st.markdown(
                            f"""
                            <div class="card">
                                <h4>{game['Away Team']} @ {game['Home Team']}</h4>
                                <p style="font-size:13px; opacity:0.8;">{game['Date'].strftime("%b %d, %I:%M %p")}</p>
                                <p><span class="badge">Best Bet: {game['Best Bet']}</span></p>
                                <p>EV: ${game['Best EV ($)']}</p>
                            </div>
                            """, unsafe_allow_html=True
                        )
                    c_idx = (c_idx+1)%3
