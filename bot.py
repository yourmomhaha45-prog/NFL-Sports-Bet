import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Your existing functions...
def moneyline_to_multiplier(ml):
    return ml / 100 + 1 if ml > 0 else 100 / abs(ml) + 1

def spread_to_ev(point, bet_amount=100):
    prob = 0.5 + (point / 50)
    ev = prob * bet_amount - (1 - prob) * bet_amount
    return round(ev, 2)

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
                bookmaker = g['bookmakers'][0]
                market_data = bookmaker['markets'][0]
                outcomes = market_data['outcomes']
                if market == "moneyline" and len(outcomes) >= 2:
                    home_ml = outcomes[0]['price']
                    away_ml = outcomes[1]['price']
                    home_ev = (1/moneyline_to_multiplier(home_ml))*DEFAULT_BET*(moneyline_to_multiplier(home_ml)-1) - (1-(1/moneyline_to_multiplier(home_ml)))*DEFAULT_BET
                    away_ev = (1/moneyline_to_multiplier(away_ml))*DEFAULT_BET*(moneyline_to_multiplier(away_ml)-1) - (1-(1/moneyline_to_multiplier(away_ml)))*DEFAULT_BET
                else:
                    home_point = outcomes[0].get('point',0)
                    away_point = outcomes[1].get('point',0)
                    home_ev = spread_to_ev(home_point, DEFAULT_BET)
                    away_ev = spread_to_ev(away_point, DEFAULT_BET)
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

# Streamlit page setup
st.set_page_config(page_title="NFL +EV Bot", layout="wide", page_icon="🏈")
if "modal_open" not in st.session_state:
    st.session_state["modal_open"] = None

# Custom CSS for modern look
st.markdown(
    """
    <style>
        /* Body background & font */
        body {
            background-color: #0d0d14;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #e5e5e5;
        }

        /* Header styles */
        h1 {
            text-align: center;
            font-size: 2.5rem;
            margin-top: 20px;
            margin-bottom: 10px;
            color: #a573ff;
        }

        /* Sidebar */
        .sidebar .sidebar-content {
            background-color: #1f1f2e;
            padding: 20px;
            border-radius: 12px;
        }

        /* Filters & sliders */
        .stSlider, .stNumberInput {
            background-color: #2e2e3e;
            border-radius: 8px;
        }

        /* Card styles */
        .game-card {
            background-color: #1f1f2e;
            border-radius: 12px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }

        /* Hover effect for cards */
        .game-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        }

        /* Badge styles */
        .badge {
            background-color: #a573ff;
            color: #fff;
            padding: 4px 12px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            display: inline-block;
            margin-top: 8px;
        }

        /* Modal styles */
        .modal {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(18, 18, 18, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }
        .modal-content {
            background-color: #2e2e3e;
            padding: 30px;
            border-radius: 12px;
            max-width: 600px;
            width: 90%;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            color: #e0e0e0;
            position: relative;
        }
        .close-btn {
            position: absolute;
            top: 10px; right: 10px;
            background: #a573ff;
            border: none;
            color: #fff;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Title
st.markdown("<h1>🏈 NFL +EV Bot – Modern Interactive</h1>", unsafe_allow_html=True)

# Sidebar filters
st.sidebar.header("⚙️ Settings")
ev_filter = st.sidebar.slider("Minimum EV ($)", -50.0, 100.0, 0.0, 5.0)
bet_amount = st.sidebar.number_input("Bet Amount per Game ($)", value=DEFAULT_BET, step=10)

# Fetch data
available_markets = get_available_markets()
games_df = get_upcoming_games(available_markets)
if games_df.empty:
    st.warning("No upcoming games found.")
    st.stop()

games_df = calculate_best_bet(games_df)
games_df = games_df[games_df["Best EV ($)"] >= ev_filter]

# Tab layout for weeks
weeks = sorted(games_df["Week"].unique())
week_tabs = st.tabs([f"Week {w}" for w in weeks])

for i, week in enumerate(weeks):
    with week_tabs[i]:
        week_df = games_df[games_df["Week"] == week]
        market_tabs = st.tabs([m.title() for m in available_markets])
        for j, market in enumerate(available_markets):
            with market_tabs[j]:
                market_df = week_df[week_df["Market"] == market]
                st.markdown(f"<h2 style='text-align:center;'>Week {week} - {market.title()}</h2>", unsafe_allow_html=True)
                total_ev = market_df["Best EV ($)"].sum()
                num_bets = market_df.shape[0]
                st.markdown(f"<p style='text-align:center; font-weight:600;'>Simulated Bets: {num_bets} | Total Expected Profit: ${total_ev}</p>", unsafe_allow_html=True)

                # Display games in a grid (3 columns)
                cols = st.columns(3)
                for idx, (_, game) in enumerate(market_df.iterrows()):
                    col = cols[idx % 3]
                    with col:
                        # Render each game as a clickable card
                        st.markdown(
                            f"""
                            <div class="game-card" onclick="document.querySelector('[data-key={idx}] button').click();">
                                <h4>{game['Away Team']} @ {game['Home Team']}</h4>
                                <p style="opacity:0.7;">{game['Date'].strftime("%b %d, %I:%M %p")}</p>
                                <div class="badge">Best Bet: {game['Best Bet']}</div>
                                <p style="margin-top:4px;">EV: <strong>${game['Best EV ($)']}</strong></p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        # Invisible button to trigger modal
                        if st.button("", key=f"btn_{idx}_{week}_{market}"):
                            st.session_state["modal_open"] = idx
                        st.markdown(f"<div data-key='{idx}'></div>", unsafe_allow_html=True)

# Show modal if a game is clicked
if st.session_state.get("modal_open") is not None:
    idx = st.session_state["modal_open"]
    game = games_df.iloc[idx]
    st.markdown(
        f"""
        <div class="modal" style="display:flex;">
            <div class="modal-content">
                <button class="close-btn" onclick="document.querySelector('.modal').style.display='none';">Close</button>
                <h2>{game['Away Team']} @ {game['Home Team']}</h2>
                <p>Date: {game['Date'].strftime("%b %d, %I:%M %p")}</p>
                <p>Market: {game['Market']}</p>
                <p>Home EV: ${game['Home EV ($)']}</p>
                <p>Away EV: ${game['Away EV ($)']}</p>
                <div class="badge">Best Bet: {game['Best Bet']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )