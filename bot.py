# app.py
# Single-file Arbitrage Bet Finder prototype (backend + frontend)
# Requirements: fastapi, uvicorn, jinja2
# Install: pip install fastapi uvicorn jinja2
#
# Run: uvicorn app:app --reload
# Then open http://localhost:8000

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
from typing import Dict, Tuple
from math import isfinite
import pathlib

app = FastAPI()
BASE_DIR = pathlib.Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR))

# In-memory PoC store: {(event_id, market_key): {book_name: {outcome_key: odds}}}
ODDS_STORE: Dict[Tuple[str, str], Dict[str, Dict[str, float]]] = {}

# --- Fake data loader for demo purposes ---
async def fake_loader_once():
    # Example: 1x2 market (home, draw, away) and a 2-way market (playerA, playerB)
    ODDS_STORE[("ManU-Liv", "1x2")] = {
        "BookA": {"home": 2.10, "draw": 3.40, "away": 3.60},
        "BookB": {"home": 2.20, "draw": 3.10, "away": 3.40},
        "BookC": {"home": 2.05, "draw": 3.50, "away": 3.80},
    }
    ODDS_STORE[("Nadal-Federer", "moneyline")] = {
        "BookX": {"playerA": 1.95, "playerB": 2.05},
        "BookY": {"playerA": 2.00, "playerB": 2.00},
        "BookZ": {"playerA": 1.92, "playerB": 2.10},
    }
    # Example arb across 2-way (should produce an arb if best odds imply S < 1)
    # You can modify these to test different cases.

async def periodic_populate():
    # Initially populate once, then periodically refresh fake data (PoC)
    await fake_loader_once()
    while True:
        # in a real system you'd fetch/update from APIs here
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    # start background populate task
    asyncio.create_task(periodic_populate())

# --- Arb detection & stake sizing helpers ---
def detect_arbs_for_market(market_odds: Dict[str, Dict[str, float]]):
    """
    market_odds: {book_name: {outcome_key: odds_decimal}}
    Returns None if no arb; otherwise returns dict with best odds per outcome, S, profit_pct.
    """
    outcomes = set()
    for outmap in market_odds.values():
        outcomes.update(outmap.keys())
    outcomes = sorted(outcomes)
    # choose best odds per outcome
    best = {}
    for o in outcomes:
        best_book, best_odds = None, 0.0
        for book, outmap in market_odds.items():
            if o in outmap and outmap[o] > best_odds:
                best_book, best_odds = book, outmap[o]
        if best_odds <= 0:
            return None
        best[o] = (best_book, best_odds)
    # compute implied probability sum
    try:
        S = sum((1.0 / odds) for (_b, odds) in best.values())
    except Exception:
        return None
    if isfinite(S) and S < 1.0:
        profit_pct = (1.0 - S) * 100.0
        return {"best": best, "S": S, "profit_pct": profit_pct}
    return None

def compute_stakes_from_best(best_odds: Dict[str, Tuple[str, float]], budget: float):
    """
    best_odds: {outcome: (book, odds)}
    budget: total amount to allocate
    Returns stakes per outcome, payout, profit, profit_pct
    """
    invs = {o: 1.0 / odds for o, (_b, odds) in best_odds.items()}
    S = sum(invs.values())
    if S >= 1.0:
        return None
    stakes = {o: round(budget * invs[o] / S, 2) for o in invs}
    payout = round(budget / S, 2)
    profit = round(payout - budget, 2)
    profit_pct = round((profit / budget) * 100.0, 4)
    return {"stakes": stakes, "payout": payout, "profit": profit, "profit_pct": profit_pct, "S": round(S, 6)}

# --- API endpoints ---
@app.get("/arbs")
async def get_arbs():
    """
    Returns current arbitrage opportunities ranked by profit_pct.
    Response:
      [
        {
          "market": ["event_id", "market_key"],
          "arb": { "best": { outcome: [book, odds] }, "S": ..., "profit_pct": ... }
        },
        ...
      ]
    """
    results = []
    for key, market in ODDS_STORE.items():
        res = detect_arbs_for_market(market)
        if res:
            results.append({"market": list(key), "arb": res})
    results.sort(key=lambda r: r["arb"]["profit_pct"], reverse=True)
    return JSONResponse(results)

@app.get("/calculate")
async def calculate(market_event: str, market_key: str, budget: float = 100.0):
    """
    Lightweight stake calculation endpoint that calculates stake distribution for a specific market.
    Query params:
      market_event: event id string (example: ManU-Liv)
      market_key: market key (example: 1x2)
      budget: total to allocate (default 100)
    """
    key = (market_event, market_key)
    if key not in ODDS_STORE:
        return JSONResponse({"error": "market not found"}, status_code=404)
    res = detect_arbs_for_market(ODDS_STORE[key])
    if not res:
        return JSONResponse({"error": "no arbitrage found for market"}, status_code=400)
    stakes = compute_stakes_from_best(res["best"], budget)
    return JSONResponse({"market": list(key), "arb": res, "stakes": stakes})

# Serve a single-page frontend using Jinja template (embedded HTML)
INDEX_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Arbitrage Bet Finder — Prototype</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
      /* small UI polish */
      .card { @apply p-3 border rounded shadow-sm bg-white }
    </style>
  </head>
  <body class="bg-gray-50 min-h-screen font-sans">
    <div class="max-w-5xl mx-auto p-6">
      <header class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold">Arbitrage Bet Finder — Prototype</h1>
        <div class="text-sm text-gray-600">Demo — not for production</div>
      </header>

      <div class="mb-4 flex items-center space-x-3">
        <label class="text-sm">Budget $</label>
        <input id="budget" type="number" value="100" class="p-2 border rounded w-28" />
        <button id="refreshBtn" class="px-3 py-2 bg-slate-700 text-white rounded">Refresh</button>
        <div id="status" class="text-sm text-gray-600 ml-4">Idle</div>
      </div>

      <div id="arbsContainer" class="space-y-3"></div>

      <footer class="mt-8 text-xs text-gray-500">
        <div>Notes: This prototype uses fake demo data and demonstrates detection, ranking and stake sizing.</div>
        <div>Legal: Scraping bookmaker data can violate ToS; use licensed odds feeds in production.</div>
      </footer>
    </div>

    <script>
      async function fetchArbs(){
        const elStatus = document.getElementById('status');
        elStatus.textContent = 'Loading…';
        try {
          const r = await fetch('/arbs');
          const arbs = await r.json();
          renderArbs(arbs);
          elStatus.textContent = new Date().toLocaleTimeString();
        } catch (e) {
          elStatus.textContent = 'Error';
          console.error(e);
        }
      }

      function formatMarket(market){
        return market[0] + ' · ' + market[1];
      }

      function renderArbs(arbs){
        const container = document.getElementById('arbsContainer');
        container.innerHTML = '';
        const budget = Number(document.getElementById('budget').value) || 100;
        if(arbs.length === 0){
          container.innerHTML = '<div class="text-gray-500">No arbitrage opportunities found (demo).</div>';
          return;
        }
        arbs.forEach(a => {
          const best = a.arb.best;
          // compute stakes locally
          const invs = {};
          let S = 0;
          for(const o in best){
            const odds = best[o][1];
            invs[o] = 1/odds;
            S += invs[o];
          }
          const stakes = {};
          const payout = +(budget / S).toFixed(2);
          const profit = +(payout - budget).toFixed(2);
          for(const o in invs){
            stakes[o] = +(budget * invs[o] / S).toFixed(2);
          }

          const card = document.createElement('div');
          card.className = 'p-3 border rounded shadow-sm bg-white';

          card.innerHTML = `
            <div class="flex justify-between items-start">
              <div>
                <div class="font-semibold">${formatMarket(a.market)}</div>
                <div class="text-sm text-gray-600">Profit: ${a.arb.profit_pct.toFixed(3)}% &nbsp; • &nbsp; S = ${a.arb.S.toFixed(6)}</div>
              </div>
              <div class="text-right">
                <div class="text-sm">Payout: $${payout}</div>
                <div class="text-sm">Profit: $${profit}</div>
              </div>
            </div>
            <div class="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
              ${Object.entries(best).map(([o, bv]) => {
                const book = bv[0], odds = bv[1], stake = stakes[o];
                return `<div class="p-2 border rounded">
                          <div class="font-medium">${o}</div>
                          <div class="text-xs">book: ${book}</div>
                          <div class="text-xs">odds: ${odds}</div>
                          <div class="text-xs">stake: $${stake}</div>
                        </div>`;
              }).join('')}
            </div>
          `;

          container.appendChild(card);
        });
      }

      document.getElementById('refreshBtn').addEventListener('click', fetchArbs);
      // auto-refresh every 8 seconds
      setInterval(fetchArbs, 8000);
      // initial load
      fetchArbs();
    </script>
  </body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return HTMLResponse(INDEX_HTML)

# If you prefer templating with Jinja, templates.render can be used — here we inline HTML for simplicity.
