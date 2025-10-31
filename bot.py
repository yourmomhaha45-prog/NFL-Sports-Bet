import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.dataframe_explorer import dataframe_explorer

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(
    page_title="EV Sports Betting Dashboard",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_KEY = "558d1e3bfadf5243c8292da72801012f"

# -------------------------------
# STYLES
# -------------------------------
st.markdown("""
    <style>
    body {
        background-color: #0e1117;
        color: #f0f0f0;
    }
    .main-title {
        font-size: 2.4rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.5rem;
        color: #06d6a0;
    }
    .sub-text {
        text-align: center;
        font-size: 1.1rem;
        color: #8a8a8a;
        margin-bottom: 2rem;
    }
    .dataframe th {
        background-color: #20242b !important;
        color: #fafafa !important;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------
# FUNCTIONS
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
                        "Market": "spreads",
                        "Home EV ($)": home_ev,
                        "Away EV ($)": away_ev
                    })
            except:
                continue
        return pd.DataFrame(results).sort_values(by=["Week", "Date"])
    except:
        return pd.DataFrame()

# -------------------------------
# UI LAYOUT
# -------------------------------
st.markdown("<div class='main-title'>🏈 Sports Betting EV Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-text'>Analyze expected value for upcoming NFL games — profitable plays at a glance.</div>", unsafe_allow_html=True)

df = fetch_games()

if df.empty:
    st.error("No data available. Check your API key or wait for odds updates.")
else:
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    week_filter = st.sidebar.multiselect("Select Week", sorted(df["Week"].unique()), default=sorted(df["Week"].unique()))
    team_filter = st.sidebar.multiselect(
        "Select Teams",
        sorted(set(df["Home Team"].unique()) | set(df["Away Team"].unique())),
        default=[]
    )

    filtered_df = df[df["Week"].isin(week_filter)]
    if team_filter:
        filtered_df = filtered_df[
            filtered_df["Home Team"].isin(team_filter) | filtered_df["Away Team"].isin(team_filter)
        ]

    # KPIs
    avg_home_ev = filtered_df["Home EV ($)"].mean()
    avg_away_ev = filtered_df["Away EV ($)"].mean()
    best_bet = filtered_df.loc[
        (filtered_df["Home EV ($)"].abs() + filtered_df["Away EV ($)"].abs()).idxmax()
    ]

    col1, col2, col3 = st.columns(3)
    col1.metric("Average Home EV", f"${avg_home_ev:,.2f}")
    col2.metric("Average Away EV", f"${avg_away_ev:,.2f}")
    col3.metric("Top Game", f"{best_bet['Away Team']} @ {best_bet['Home Team']}")
    style_metric_cards(background_color="#20242b", border_color="#333", border_left_color="#06d6a0")

    # Display filtered table
    st.markdown("### 📊 Game Data")
    st.dataframe(
        filtered_df.style.applymap(
            lambda x: "color: #06d6a0; font-weight:600;" if isinstance(x, (int, float)) and x > 0 else ""
        ),
        use_container_width=True,
        hide_index=True
    )

    # Interactive explorer
    with st.expander("🔎 Explore and Search Games"):
        explored = dataframe_explorer(filtered_df)
        st.dataframe(explored, use_container_width=True, hide_index=True)

st.caption("Data provided by [The Odds API](https://the-odds-api.com). Built with ❤️ using Streamlit.")
