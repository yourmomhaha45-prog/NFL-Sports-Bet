import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(
    page_title="NFL +EV Dashboard",
    page_icon="🏈",
    layout="wide"
)

API_KEY = "2aa294bcbd091e366f4249805fcf401e"

# -------------------------------
# UTILITY FUNCTIONS
# -------------------------------
def moneyline_to_prob(ml):
    return 100 / (ml + 100) if ml > 0 else abs(ml) / (abs(ml) + 100)

def moneyline_to_multiplier(ml):
    return ml / 100 + 1 if ml > 0 else 100 / abs(ml) + 1

def calculate_ev(prob, payout, bet=100):
    return round(prob * payout - (1 - prob) * bet, 2)

def get_moneyline_ev(ml, bet=100):
    prob = moneyline_to_prob(ml)
    payout = (moneyline_to_multiplier(ml) - 1) * bet
    return calculate_ev(prob, payout, bet)

# -------------------------------
# FETCH DATA FUNCTION
# -------------------------------
@st.cache_data(ttl=3600)
def fetch_games():
    url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/?apiKey={API_KEY}&regions=us&markets=moneyline,spreads"
    try:
        response = requests.get(url)
        if response.status_code == 422:
            st.warning("No odds available for NFL games at this time.")
            return pd.DataFrame()
        response.raise_for_status()
        data = response.json()
        results = []

        for g in data:
            try:
                home = g['home_team']
                away = g['away_team']
                dt = datetime.fromisoformat(g['commence_time'].replace("Z", "+00:00"))
                week = dt.isocalendar()[1]

                home_ev = away_ev = None
                # Loop through bookmakers to find first available market
                for bookmaker in g.get('bookmakers', []):
                    for market in bookmaker.get('markets', []):
                        outcomes = market.get('outcomes', [])
                        if len(outcomes) >= 2:
                            home_ml = next((o['price'] for o in outcomes if o['name'] == home), None)
                            away_ml = next((o['price'] for o in outcomes if o['name'] == away), None)
                            if home_ml is not None and away_ml is not None:
                                home_ev = get_moneyline_ev(home_ml)
                                away_ev = get_moneyline_ev(away_ml)
                                break
                    if home_ev is not None:
                        break

                if home_ev is not None and away_ev is not None:
                    results.append({
                        "Week": week,
                        "Date": dt.strftime("%b %d, %Y %I:%M %p"),
                        "Home Team": home,
                        "Away Team": away,
                        "Home EV": home_ev,
                        "Away EV": away_ev
                    })
            except Exception as e:
                continue

        # If no results, provide placeholder example games
        if not results:
            results = [
                {"Week": 1, "Date": "Sep 10, 2025 01:00 PM", "Home Team": "Patriots", "Away Team": "Jets", "Home EV": 25, "Away EV": -10},
                {"Week": 1, "Date": "Sep 10, 2025 04:25 PM", "Home Team": "Cowboys", "Away Team": "Giants", "Home EV": -5, "Away EV": 15},
                {"Week": 1, "Date": "Sep 11, 2025 01:00 PM", "Home Team": "Packers", "Away Team": "Bears", "Home EV": 10, "Away EV": 5},
            ]

        return pd.DataFrame(results).sort_values(by=["Week", "Date"])

    except Exception as e:
        st.error(f"Error fetching odds: {e}")
        return pd.DataFrame()

# -------------------------------
# STYLES FOR GLASSY CARDS
# -------------------------------
st.markdown("""
<style>
body {background: #0e1117; color: #f0f0f0; font-family: 'Helvetica', sans-serif;}
.game-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 1rem;
    margin-bottom: 1rem;
    transition: transform 0.2s, box-shadow 0.2s;
    border: 1px solid rgba(255,255,255,0.15);
}
.game-card:hover {
    transform: scale(1.02);
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}
.team {font-weight: 600; font-size: 1.2rem; margin-top: 0.2rem;}
.ev-positive {color: #06d6a0; font-weight: bold;}
.ev-negative {color: #ef476f; font-weight: bold;}
.game-date {color: #aaa; font-size: 0.9rem; margin-bottom: 0.5rem;}
.ev-bar {height: 15px; border-radius: 10px; margin-top: 2px; margin-bottom: 5px;}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# MAIN UI
# -------------------------------
df = fetch_games()

# Sidebar filters
st.sidebar.header("Filters")
week_filter = st.sidebar.multiselect("Select Week", sorted(df["Week"].unique()) if not df.empty else [], default=sorted(df["Week"].unique()) if not df.empty else [])
team_filter = st.sidebar.multiselect(
    "Select Teams",
    sorted(set(df["Home Team"].unique()) | set(df["Away Team"].unique())) if not df.empty else []
)
sort_option = st.sidebar.radio("Sort by", ["Highest EV", "Home EV", "Away EV", "Week", "Date"])

if not df.empty:
    filtered_df = df[df["Week"].isin(week_filter)]
    if team_filter:
        filtered_df = filtered_df[
            filtered_df["Home Team"].isin(team_filter) | filtered_df["Away Team"].isin(team_filter)
        ]

    # Sorting
    if sort_option == "Highest EV":
        filtered_df["Max EV"] = filtered_df[["Home EV", "Away EV"]].max(axis=1)
        filtered_df = filtered_df.sort_values(by="Max EV", ascending=False)
    elif sort_option == "Home EV":
        filtered_df = filtered_df.sort_values(by="Home EV", ascending=False)
    elif sort_option == "Away EV":
        filtered_df = filtered_df.sort_values(by="Away EV", ascending=False)
    elif sort_option == "Week":
        filtered_df = filtered_df.sort_values(by="Week")
    elif sort_option == "Date":
        filtered_df = filtered_df.sort_values(by="Date")

    # Display glassy cards
    for idx, row in filtered_df.iterrows():
        st.markdown(f"""
        <div class="game-card">
            <div class="game-date">{row['Date']} | Week {row['Week']}</div>
            <div class="team">{row['Away Team']} <span class="{'ev-positive' if row['Away EV']>0 else 'ev-negative'}">${row['Away EV']}</span></div>
            <div style="background: {'#06d6a0' if row['Away EV']>0 else '#ef476f'}; width: {min(abs(row['Away EV']),100)}%;"
                 class="ev-bar"></div>
            <div class="team">{row['Home Team']} <span class="{'ev-positive' if row['Home EV']>0 else 'ev-negative'}">${row['Home EV']}</span></div>
            <div style="background: {'#06d6a0' if row['Home EV']>0 else '#ef476f'}; width: {min(abs(row['Home EV']),100)}%;"
                 class="ev-bar"></div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No games to display yet. Check back when NFL odds are available.")

st.caption("Data provided by [The Odds API](https://the-odds-api.com). Built with ❤️ using Streamlit.")
