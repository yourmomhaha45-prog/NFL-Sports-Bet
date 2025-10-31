import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(
    page_title="NFL EV Dashboard",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_KEY = "558d1e3bfadf5243c8292da72801012f"

# -------------------------------
# UTILITY FUNCTIONS
# -------------------------------
def moneyline_to_prob(ml):
    return 100 / (ml + 100) if ml > 0 else abs(ml) / (abs(ml) + 100)

def moneyline_to_multiplier(ml):
    return ml / 100 + 1 if ml > 0 else 100 / abs(ml) + 1

def calculate_ev(prob, payout, bet):
    return prob * payout - (1 - prob) * bet

def get_moneyline_ev(odds, bet=100):
    prob = moneyline_to_prob(odds)
    payout = (moneyline_to_multiplier(odds) - 1) * bet
    return round(calculate_ev(prob, payout, bet), 2)

def spread_to_ev(point, bet=100):
    prob = 0.5 + (point / 50)
    return round(prob * bet - (1 - prob) * bet, 2)

@st.cache_data(ttl=3600)
def fetch_games():
    url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/?apiKey={API_KEY}&regions=us&markets=spreads"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        results = []

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
                    results.append({
                        "Week": week,
                        "Date": dt.strftime("%b %d, %Y %I:%M %p"),
                        "Home Team": home,
                        "Away Team": away,
                        "Home EV": home_ev,
                        "Away EV": away_ev
                    })
            except:
                continue
        return pd.DataFrame(results).sort_values(by=["Week", "Date"])
    except:
        return pd.DataFrame()

# -------------------------------
# STYLES
# -------------------------------
st.markdown("""
    <style>
    body {background-color: #0e1117; color: #f0f0f0;}
    .game-card {background: #1b1f29; padding: 1rem; border-radius: 12px; margin-bottom: 1rem; transition: transform 0.2s;}
    .game-card:hover {transform: scale(1.02);}
    .team {font-weight: bold; font-size: 1.2rem;}
    .ev-positive {color: #06d6a0; font-weight: bold;}
    .ev-negative {color: #ef476f; font-weight: bold;}
    .game-date {color: #8a8a8a; font-size: 0.9rem;}
    </style>
""", unsafe_allow_html=True)

# -------------------------------
# MAIN UI
# -------------------------------
st.title("🏈 NFL +EV Dashboard")
st.markdown("Interactive game cards showing Home vs Away EV — hover over cards for a modern dashboard feel.")

df = fetch_games()
if df.empty:
    st.error("No data available. Check your API key or wait for odds updates.")
else:
    # Sidebar filters
    st.sidebar.header("Filters")
    week_filter = st.sidebar.multiselect("Select Week", sorted(df["Week"].unique()), default=sorted(df["Week"].unique()))
    team_filter = st.sidebar.multiselect(
        "Select Teams",
        sorted(set(df["Home Team"].unique()) | set(df["Away Team"].unique()))
    )
    sort_option = st.sidebar.radio("Sort by", ["Highest EV", "Home EV", "Away EV", "Week", "Date"])

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

    # Display interactive cards
    for idx, row in filtered_df.iterrows():
        st.markdown(f"""
        <div class="game-card">
            <div class="game-date">{row['Date']} | Week {row['Week']}</div>
            <div class="team">{row['Away Team']} <span class="{'ev-positive' if row['Away EV']>0 else 'ev-negative'}">${row['Away EV']}</span></div>
            <div class="team">{row['Home Team']} <span class="{'ev-positive' if row['Home EV']>0 else 'ev-negative'}">${row['Home EV']}</span></div>
        </div>
        """, unsafe_allow_html=True)

st.caption("Data provided by [The Odds API](https://the-odds-api.com). Built with ❤️ using Streamlit.")
