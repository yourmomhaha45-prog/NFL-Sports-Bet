# -------- CONFIG --------
ODDS_API_KEY = "558d1e3bfadf5243c8292da72801012f"  # Your Odds API key
SPORT = "americanfootball_nfl"
REGION = "us"  # Use 'us' for US odds
MARKET = "spreads"  # Options: 'spreads', 'h2h', 'totals'

# -------- IMPORTS --------
import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# -------- FUNCTIONS --------
def get_upcoming_games():
    """Fetch upcoming NFL games from The Odds API"""
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={ODDS_API_KEY}&regions={REGION}&markets={MARKET}"
    response = requests.get(url)

    if response.status_code != 200:
        st.error(f"Error fetching data: {response.status_code}")
        return pd.DataFrame()

    games = response.json()
    data = []

    for g in games:
        home_team = g['home_team']
        away_team = g['away_team']

        # Use spreads as expected value
        home_ev = g['bookmakers'][0]['markets'][0]['outcomes'][0].get('point', 0)
        away_ev = g['bookmakers'][0]['markets'][0]['outcomes'][1].get('point', 0)

        # Parse game time
        game_time = datetime.fromisoformat(g['commence_time'].replace("Z", "+00:00"))

        # Optional: determine NFL week from game date (simple approximation)
        week_number = game_time.isocalendar()[1]  # ISO week number

        data.append({
            "Week": week_number,
            "Date": game_time,
            "Home Team": home_team,
            "Away Team": away_team,
            "Home EV": home_ev,
            "Away EV": away_ev
        })

    df = pd.DataFrame(data)
    df.sort_values(by=["Week", "Date"], inplace=True)
    return df

def calculate_best_bet(df):
    """Add a column for the team with the best expected value"""
    df["Best Bet"] = df.apply(lambda row: row["Home Team"] if row["Home EV"] > row["Away EV"] else row["Away Team"], axis=1)
    return df

def highlight_best_bet(row):
    """Highlight the best bet in the table"""
    return ['background-color: #d4edda' if row["Best Bet"] == row["Home Team"] else '' for _ in row]

# -------- STREAMLIT UI --------
st.set_page_config(page_title="NFL +EV Bot", layout="wide", page_icon="🏈")
st.markdown("<h1 style='text-align:center;'>NFL +EV Betting Bot 🏈</h1>", unsafe_allow_html=True)
st.markdown(
    """
    This bot fetches upcoming NFL games from **The Odds API** and calculates the best bets based on expected value (+EV).  
    Games are now **sorted by NFL week**.
    """,
    unsafe_allow_html=True
)

# Sidebar filters
st.sidebar.header("Filters")
market_option = st.sidebar.selectbox("Market", options=["spreads", "h2h", "totals"])
region_option = st.sidebar.selectbox("Region", options=["us", "uk", "eu"])

# Fetch games
with st.spinner("Fetching upcoming games..."):
    games_df = get_upcoming_games()

if not games_df.empty:
    games_df = calculate_best_bet(games_df)
    
    # Group by week
    weeks = games_df["Week"].unique()
    for week in weeks:
        st.subheader(f"Week {week} Games")
        week_df = games_df[games_df["Week"] == week]
        st.dataframe(week_df.style.apply(highlight_best_bet, axis=1), use_container_width=True)
        
        # Highlight the top EV team in that week
        top_game = week_df.loc[week_df[["Home EV", "Away EV"]].max(axis=1).idxmax()]
        st.markdown(f"**🔥 Top Bet for Week {week}: {top_game['Best Bet']}** in **{top_game['Away Team']} vs {top_game['Home Team']}**")
else:
    st.info("No upcoming games found.")
