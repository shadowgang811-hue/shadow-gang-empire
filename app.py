"""
Shadow Gang Empire — Railway Cloud Backend
===========================================
This runs 24/7 on Railway (free).
It serves the dashboard and relays signals.
Your local MT5 bridge connects to this server
to push live account data and receive trade commands.
"""

import os, time, json, threading
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get("PORT", 5000))

# ── IN-MEMORY STATE (updated by your local MT5 bridge) ──
state = {
    "account": {
        "login": "—",
        "server": "Exness-Real9",
        "balance": 3.00,
        "equity": 3.00,
        "margin": 0.00,
        "free_margin": 3.00,
        "float": 0.00,
        "currency": "USD",
        "leverage": 2000,
        "connected": False,
        "last_update": None,
    },
    "trades": [],
    "signals": [],
    "log": [],
    "growth": [3.00],
    "daily_pnl": 0.00,
    "trades_today": 0,
    "daily_locked": False,
}

SECRET = os.environ.get("BRIDGE_SECRET", "shadowgang2024")

def add_log(type_, msg):
    state["log"].insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": type_,
        "msg": msg
    })
    if len(state["log"]) > 50:
        state["log"].pop()

# ════════════════════════════════════════════════════════
#  DASHBOARD ROUTES (called by browser)
# ════════════════════════════════════════════════════════

@app.route("/")
def index():
    return jsonify({"status": "Shadow Gang Empire Server running 🙏", "connected": state["account"]["connected"]})

@app.route("/ping")
def ping():
    return jsonify({
        "ok": True,
        "connected": state["account"]["connected"],
        "ts": time.time()
    })

@app.route("/status")
def status():
    return jsonify(state["account"])

@app.route("/trades")
def trades():
    return jsonify(state["trades"])

@app.route("/signals")
def signals():
    return jsonify(state["signals"])

@app.route("/log")
def get_log():
    return jsonify(state["log"])

@app.route("/growth")
def growth():
    return jsonify(state["growth"])

@app.route("/stats")
def stats():
    return jsonify({
        "daily_pnl":    state["daily_pnl"],
        "trades_today": state["trades_today"],
        "daily_locked": state["daily_locked"],
    })

# ════════════════════════════════════════════════════════
#  BRIDGE ROUTES (called by your local MT5 bridge.py)
# ════════════════════════════════════════════════════════

def auth(req):
    return req.headers.get("X-Secret") == SECRET

@app.route("/bridge/push", methods=["POST"])
def bridge_push():
    """Local bridge pushes live MT5 data here every 3s."""
    if not auth(request):
        return jsonify({"error": "unauthorized"}), 401
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400

    if "account" in data:
        state["account"].update(data["account"])
        state["account"]["connected"] = True
        state["account"]["last_update"] = datetime.now().strftime("%H:%M:%S")

    if "trades" in data:
        state["trades"] = data["trades"]

    if "signals" in data:
        state["signals"] = data["signals"]

    if "daily_pnl" in data:
        state["daily_pnl"] = data["daily_pnl"]

    if "trades_today" in data:
        state["trades_today"] = data["trades_today"]

    if "balance" in data:
        g = state["growth"]
        if not g or abs(data["balance"] - g[-1]) > 0.001:
            g.append(round(data["balance"], 2))
            if len(g) > 100:
                g.pop(0)

    return jsonify({"ok": True})

@app.route("/bridge/log", methods=["POST"])
def bridge_log():
    if not auth(request):
        return jsonify({"error": "unauthorized"}), 401
    data = request.json
    if data:
        add_log(data.get("type","info"), data.get("msg",""))
    return jsonify({"ok": True})

@app.route("/bridge/execute", methods=["POST"])
def bridge_execute():
    """Dashboard requests a trade — queued for local bridge to pick up."""
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400
    state.setdefault("pending_trades", []).append(data)
    add_log("bull", f"Trade queued: {data.get('direction')} {data.get('symbol')}")
    return jsonify({"ok": True, "queued": True})

@app.route("/bridge/pending")
def bridge_pending():
    """Local bridge polls this to get pending trade commands."""
    if not auth(request):
        return jsonify({"error": "unauthorized"}), 401
    pending = state.pop("pending_trades", [])
    return jsonify(pending)

@app.route("/bridge/close/<int:ticket>", methods=["POST"])
def bridge_close(ticket):
    state.setdefault("pending_closes", []).append(ticket)
    return jsonify({"ok": True})

@app.route("/bridge/pending_closes")
def bridge_pending_closes():
    if not auth(request):
        return jsonify({"error": "unauthorized"}), 401
    closes = state.pop("pending_closes", [])
    return jsonify(closes)

# ════════════════════════════════════════════════════════
#  OFFLINE HEARTBEAT
# ════════════════════════════════════════════════════════
def check_connection():
    """Mark as disconnected if no push in 30s."""
    while True:
        time.sleep(30)
        last = state["account"].get("last_update")
        if last:
            try:
                t = datetime.strptime(last, "%H:%M:%S").replace(
                    year=datetime.now().year,
                    month=datetime.now().month,
                    day=datetime.now().day
                )
                if (datetime.now() - t).seconds > 30:
                    state["account"]["connected"] = False
            except:
                pass

threading.Thread(target=check_connection, daemon=True).start()

add_log("info", "Shadow Gang Empire Server started 🙏")
add_log("info", "Waiting for MT5 bridge connection...")

if __name__ == "__main__":
    print("=" * 50)
    print("  🙏 Shadow Gang Empire — Cloud Server")
    print("=" * 50)
    print(f"[OK] Running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
