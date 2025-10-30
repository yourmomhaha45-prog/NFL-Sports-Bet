# -------- CONFIG --------
ODDS_API_KEY = "558d1e3bfadf5243c8292da72801012f"  # Your Odds API key
SPORT = "americanfootball_nfl"
REGION = "us"  # Use 'us' for US odds
MARKET = "spreads"  # You can use 'spreads', 'h2h', or 'totals'

# -------- IMPORTS --------
import streamlit as st
import pandas as pd
import requests

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

        # Example: use spreads as expected value (mock calculation)
        home_ev = g['bookmakers'][0]['markets'][0]['outcomes'][0].get('point', 0)
        away_ev = g['bookmakers'][0]['markets'][0]['outcomes'][1].get('point', 0)

        data.append({
            "HomeTeam": home_team,
            "AwayTeam": away_team,
            "HomeEV": home_ev,
            "AwayEV": away_ev
        })

    return pd.DataFrame(data)

def calculate_best_bet(df):
    """Add a column for the team with the best expected value"""
    def best(row):
        return row["HomeTeam"] if row["HomeEV"] > row["AwayEV"] else row["AwayTeam"]
    
    df["BestBet"] = df.apply(best, axis=1)
    return df

# -------- STREAMLIT UI --------
st.set_page_config(page_title="NFL +EV Bot", layout="wide")
st.title("NFL +EV Betting Bot 🏈")
st.write("This bot fetches upcoming games from The Odds API and calculates the best bets based on expected value (+EV).")

# Fetch games
games_df = get_upcoming_games()

if not games_df.empty:
    games_df = calculate_best_bet(games_df)
    st.subheader("Upcoming +EV Bets")
    st.dataframe(games_df)

    # Highlight best bet
    best_bet_game = games_df.loc[games_df["BestBet"] == games_df["BestBet"].max()]
    st.subheader("Recommended Bet")
    st.write(games_df[["HomeTeam", "AwayTeam", "BestBet"]])
else:
    st.write("No upcoming games found.")
