"""Flask portal for the shadow trader — live dashboard + hourly worker. Paper only, sends no orders.

Routes:  /  dashboard · /health  healthcheck · /refresh  force a cycle · /api/state  JSON
Run locally:  SOURCE=local python web/app.py
Deploy:       gunicorn web.app:app --workers 1 --threads 4 --bind 0.0.0.0:$PORT   (workers=1!)
"""

import os
import threading
import traceback

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, redirect, render_template_string

import portal_core as pc

app = Flask(__name__)
_lock = threading.Lock()
_status = {"running": False, "last_error": None}


def cycle():
    if _status["running"]:
        return
    with _lock:
        _status["running"] = True
        try:
            pc.compute()
            _status["last_error"] = None
        except Exception:  # noqa: BLE001
            _status["last_error"] = traceback.format_exc().splitlines()[-1]
        finally:
            _status["running"] = False


PAGE = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="180">
<title>Aquarius · shadow portal</title>
<style>
 body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#0b1020;color:#e5e7eb}
 .wrap{max-width:1180px;margin:0 auto;padding:18px}
 h1{font-size:18px;margin:0 0 2px} .sub{color:#94a3b8;font-size:12px;margin-bottom:14px}
 .cards{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px}
 .card{background:#131a2e;border:1px solid #1f2a44;border-radius:10px;padding:10px 14px;min-width:120px}
 .card .k{color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
 .card .v{font-size:20px;font-weight:600;margin-top:3px}
 .pos{color:#22c55e}.neg{color:#ef4444}
 .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
 .panel{background:#131a2e;border:1px solid #1f2a44;border-radius:10px;padding:8px}
 img{width:100%;border-radius:6px;display:block}
 table{width:100%;border-collapse:collapse;font-size:13px} th,td{padding:5px 8px;text-align:right}
 th:first-child,td:first-child{text-align:left} tr:nth-child(even){background:#0f1626}
 .btn{background:#2563eb;color:#fff;border:none;padding:7px 12px;border-radius:7px;cursor:pointer;font-size:13px}
 a{color:#60a5fa} .err{background:#3b1414;border:1px solid #7f1d1d;color:#fca5a5;padding:10px;border-radius:8px;margin-bottom:14px}
 @media(max-width:780px){.grid{grid-template-columns:1fr}}
</style></head><body><div class="wrap">
<h1>Aquarius · shadow portal <span style="color:#64748b;font-weight:400;font-size:12px">paper — no orders sent</span></h1>
<div class="sub">cross-sectional reversal basket · {{s.exchange}}/{{s.source}} · {{s.n_coins}} legs ·
 ${{ '{:,.0f}'.format(s.gross) }} gross · {{s.window_days}}d window · updated {{s.updated[:16].replace('T',' ')}}Z</div>
{% if err %}<div class="err">last cycle error: {{err}} &nbsp; (try EXCHANGE=okx or kraken if geo-blocked)</div>{% endif %}
<div class="cards">
  <div class="card"><div class="k">Net P&L</div><div class="v {{'pos' if s.net_pnl>=0 else 'neg'}}">${{ '{:,}'.format(s.net_pnl) }}</div></div>
  <div class="card"><div class="k">Return</div><div class="v {{'pos' if s.pct>=0 else 'neg'}}">{{s.pct}}% <span style="font-size:12px;color:#94a3b8">({{s.ann_pct}}%/yr)</span></div></div>
  <div class="card"><div class="k">Sharpe</div><div class="v">{{s.sharpe}}</div></div>
  <div class="card"><div class="k">Max DD</div><div class="v neg">{{s.maxdd_pct}}%</div></div>
  <div class="card"><div class="k">Win rate</div><div class="v">{{s.win_rate}}%</div></div>
  <div class="card"><div class="k">Trades</div><div class="v">{{s.n_trades}}</div></div>
  <div class="card"><div class="k">Open legs</div><div class="v">{{s.open_legs}}</div></div>
  <div class="card"><div class="k">Net delta</div><div class="v pos">$0</div></div>
</div>
<div class="grid">
  <div class="panel"><img src="data:image/png;base64,{{s.img_capital}}"></div>
  <div class="panel"><img src="data:image/png;base64,{{s.img_butterfly}}"></div>
  <div class="panel"><img src="data:image/png;base64,{{s.img_swarm}}"></div>
  <div class="panel"><img src="data:image/png;base64,{{s.img_neutral}}"></div>
</div>
<div class="panel" style="margin-top:14px">
  <table><tr><th>coin</th><th>side</th><th>z now</th><th>entry z</th><th>unrealized $</th></tr>
  {% for p in s.positions %}<tr><td>{{p.coin}}</td><td>{{p.side}}</td><td>{{p.z}}</td><td>{{p.entry_z}}</td>
   <td class="{{'pos' if p.unreal>=0 else 'neg'}}">{{ '{:+,}'.format(p.unreal) }}</td></tr>{% endfor %}
  </table>
</div>
<div class="sub" style="margin-top:12px">exit reasons: {% for k,v in s.reasons.items() %}{{k}}={{v}} {% endfor %}
 &nbsp;·&nbsp; <form action="/refresh" method="post" style="display:inline"><button class="btn">Refresh now</button></form>
 &nbsp;·&nbsp; <a href="/api/state">JSON</a></div>
</div></body></html>
"""

EMPTY = """<!doctype html><meta http-equiv="refresh" content="5"><body style="font-family:sans-serif;
background:#0b1020;color:#e5e7eb;padding:40px"><h2>Aquarius shadow portal</h2>
<p>First cycle is computing on real data… this page auto-refreshes.</p>
{% if err %}<p style="color:#fca5a5">error: {{err}}</p>{% endif %}</body>"""


@app.route("/")
def home():
    s = pc.load_state()
    if not s:
        return render_template_string(EMPTY, err=_status["last_error"])
    return render_template_string(PAGE, s=s, err=_status["last_error"])


@app.route("/health")
def health():
    return "ok", 200


@app.route("/refresh", methods=["POST", "GET"])
def refresh():
    threading.Thread(target=cycle, daemon=True).start()
    return redirect("/")


@app.route("/api/state")
def api_state():
    s = pc.load_state() or {}
    return jsonify({k: v for k, v in s.items() if not k.startswith("img_")})


def _boot():
    if pc.load_state() is None:
        threading.Thread(target=cycle, daemon=True).start()   # populate first paint
    sched = BackgroundScheduler(daemon=True)
    hrs = float(os.environ.get("REFRESH_HOURS", "1"))
    sched.add_job(cycle, "interval", hours=hrs, id="cycle", max_instances=1, coalesce=True)
    sched.start()


_boot()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
