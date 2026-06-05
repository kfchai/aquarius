# Aquarius shadow portal (Railway)

A live dashboard for the cross-sectional reversal basket, running in **paper mode — it generates
intended trades and an equity curve from real market data, and sends no orders.**

## What it shows
- **Stat cards** — net P&L, return (%/yr), Sharpe, max drawdown, win-rate, trades, open legs, net delta.
- **Capital** — the paper equity curve + drawdown.
- **Live butterfly** — the short-gamma tent with every open leg plotted where it sits *right now*
  (red = short the rich, blue = long the cheap), and the book's composite dislocation.
- **Live dislocations (swarm)** — each coin's current z vs the ±1.5σ entry and ±5σ stop bands.
- **Neutrality monitor** — the coin-leg tilt and the basket-hedge-zeroed net delta (= 0).
- **Positions table** + exit-reason tally.

It recomputes every hour (APScheduler) and the page auto-refreshes. `/refresh` forces a cycle;
`/api/state` returns JSON; `/health` is the Railway healthcheck.

## Deploy on Railway
**Option A — Railway CLI (fastest):**
```bash
npm i -g @railway/cli
railway login
railway init           # in the repo root
railway up             # uploads the repo, builds via Nixpacks
```
**Option B — GitHub:** push the repo, then in Railway → *New Project → Deploy from GitHub repo*.

Railway auto-detects `railway.json` / `Procfile` and starts:
```
gunicorn app:app --chdir web --workers 1 --threads 4 --timeout 180 --bind 0.0.0.0:$PORT
```
Then **Settings → Networking → Generate Domain** to get a public URL.

### Persist the track record (recommended)
Add a **Volume** (Railway → service → *Variables/Volumes → New Volume*), mount path `/data`, and set
`DATA_DIR=/data`. Without a volume the equity history resets on each redeploy (the app still works —
it rebuilds the window from live data each cycle).

### Environment variables
| var | default | notes |
|---|---|---|
| `SOURCE` | `live` | `live` = fetch via ccxt; `local` = read cached parquet (dev only) |
| `EXCHANGE` | `bybit` | ccxt venue. **If geo-blocked (empty dashboard / error), try `okx`, `kraken`, or `binance`.** |
| `N_COINS` | `20` | legs (top-N by volume from the built-in list) |
| `GROSS` | `100000` | gross book size in $ (paper) |
| `DAYS` | `30` | reporting window length |
| `REFRESH_HOURS` | `1` | worker cadence |
| `DATA_DIR` | repo `data/shadow` | set to `/data` with a volume to persist |

> ⚠️ Exchange geo-blocking is the most common issue: some venues 451/block cloud IPs. The app skips
> coins a venue rejects and errors only if <8 load — switch `EXCHANGE` if you see that.

## Run locally
```bash
pip install -r requirements.txt
SOURCE=local python web/app.py     # uses cached parquet, http://localhost:8000
# or live:
SOURCE=live EXCHANGE=bybit python web/app.py
```

**Paper only. No exchange keys, no orders, no funds. This is a measurement tool, not a trading bot.**
