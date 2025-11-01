import streamlit as st
import requests
import pandas as pd

# --- Streamlit Page Config ---
st.set_page_config(page_title="Devigger Odds Analyzer", layout="wide", page_icon="🎯")

st.title("🎯 Devigger Odds Analyzer")
st.markdown("A modern, interactive UI for analyzing sportsbook odds using the Devigger API.")

# --- Tabs for clean separation ---
tabs = st.tabs(["Inputs", "Results", "Advanced Options"])

# --- Sidebar or collapsible inputs ---
with tabs[0]:
    st.header("Basic Inputs")
    col1, col2 = st.columns(2)

    with col1:
        leg_odds = st.text_area("Leg Odds", "1.9, 2.0", help="Comma-separated odds for each leg")
        final_odds = st.text_input("Final Odds", "1.95")
        correlation_bool = st.selectbox("Include Correlation?", [0, 1])
        correlation_text = st.text_input("Correlation Text", "")

    with col2:
        boost_bool = st.selectbox("Include Boost?", [0, 1])
        boost_text = st.text_input("Boost Text", "")
        boost_type = st.selectbox("Boost Type", [0, 1])
        devig_method = st.selectbox(
            "Devig Method",
            {
                "Multiplicative": 0,
                "Additive": 1,
                "Power": 2,
                "Shin": 3,
                "Worst Case": 4,
                "Weighted Average": 5,
            },
        )
        args = st.text_input(
            "Additional Outputs",
            "ev_p,fb_p,fo_o,kelly,dm,ev_d,url",
            help="Comma-separated additional outputs like EV%, Free Bet%, etc."
        )

# --- Advanced options in expandable tab ---
with tabs[2]:
    st.header("Advanced Options")
    col1, col2 = st.columns(2)
    with col1:
        worstcase_multiplicative = st.selectbox("WorstCase Multiplicative", [0, 1])
        worstcase_additive = st.selectbox("WorstCase Additive", [0, 1])
        worstcase_power = st.selectbox("WorstCase Power", [0, 1])
        worstcase_shin = st.selectbox("WorstCase Shin", [0, 1])
    with col2:
        weighted_avg_multiplicative = st.text_input("WeightedAverage Multiplicative", "")
        weighted_avg_additive = st.text_input("WeightedAverage Additive", "")
        weighted_avg_power = st.text_input("WeightedAverage Power", "")
        weighted_avg_shin = st.text_input("WeightedAverage Shin", "")

# --- Function to fetch API results ---
@st.cache_data(ttl=60)
def fetch_devigger_results():
    api_url = "http://api.crazyninjaodds.com/api/devigger/v1/sportsbook_devigger.aspx?api=open"
    params = {
        "LegOdds": leg_odds,
        "FinalOdds": final_odds,
        "Correlation_Bool": correlation_bool,
        "Correlation_Text": correlation_text,
        "Boost_Bool": boost_bool,
        "Boost_Text": boost_text,
        "Boost_Type": boost_type,
        "DevigMethod": devig_method,
        "WorstCase_Multiplicative": worstcase_multiplicative,
        "WorstCase_Additive": worstcase_additive,
        "WorstCase_Power": worstcase_power,
        "WorstCase_Shin": worstcase_shin,
        "WeightedAverage_Multiplicative": weighted_avg_multiplicative,
        "WeightedAverage_Additive": weighted_avg_additive,
        "WeightedAverage_Power": weighted_avg_power,
        "WeightedAverage_Shin": weighted_avg_shin,
        "Args": args,
    }

    try:
        response = requests.get(api_url, params=params, timeout=10)
        data = response.json()
        return data
    except Exception as e:
        st.error(f"Error fetching API: {e}")
        return None

# --- Results Tab ---
with tabs[1]:
    st.header("Results")
    results = fetch_devigger_results()
    if results:
        df = pd.json_normalize(results)
        # Color-coding key metrics
        def highlight_profit(val):
            try:
                if isinstance(val, (int, float)):
                    return 'background-color: #d4edda' if val > 0 else 'background-color: #f8d7da'
                return ''
            except:
                return ''
        st.dataframe(df.style.applymap(highlight_profit, subset=["ev_d", "kelly"]), use_container_width=True)
    else:
        st.info("Fill in the inputs and wait for results.")

