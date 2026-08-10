"""
Local IoT-style dashboard for the drowsiness detection project.
------------------------------------------------------------------
This plays the role of "ThingSpeak / Blynk" from the report, entirely
in software: it reads events.json (written by drowsiness_detection_software.py)
and shows a live-updating table + chart of drowsiness alerts in your browser.

RUN
    python dashboard.py
Then open:  http://127.0.0.1:5000

Leave drowsiness_detection_software.py running in one terminal, and this
dashboard running in another -- alerts will appear here within a couple
of seconds of being triggered.
"""
import json
import os
from flask import Flask, jsonify, render_template_string

EVENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "events.json")

app = Flask(__name__)

PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Driver Monitoring Dashboard (IoT Simulation)</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; background: #0f1b2b; color: #eaf2fb; margin: 0; padding: 24px; }
        h1 { color: #6fb1e8; display: flex; align-items: center; justify-content: space-between; }
        .stat-row { display: flex; gap: 20px; margin-bottom: 24px; }
        .card { background: #1b2a3a; padding: 16px 24px; border-radius: 10px; border: 1px solid #2c5f8a; flex: 1; }
        .card .num { font-size: 32px; font-weight: bold; color: #ff6b6b; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #2c5f8a; }
        th { background: #2c5f8a; }
        tr:hover { background: #16283a; }
        .empty { color: #7f97ad; font-style: italic; }
        .btn { background: #ff4757; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; margin-left: 10px; }
        .btn:hover { background: #ff6b81; }
        .btn-toggle { background: #2ed573; }
        .btn-toggle.disabled { background: #747d8c; }
    </style>
</head>
<body>
    <h1>
        <span>🚗 Driver Monitoring Dashboard <span style="font-size:14px; color:#7f97ad;">(local IoT simulation)</span></span>
        <div>
            <button id="toggleSoundBtn" class="btn btn-toggle" onclick="toggleSound()">🔔 Sound Alert: Enabled</button>
            <button class="btn" onclick="playWebAlarm()">🔊 Test Sound</button>
        </div>
    </h1>
    <div class="stat-row">
        <div class="card"><div>Total Alerts</div><div class="num" id="count">0</div></div>
        <div class="card"><div>Last Alert</div><div class="num" id="last" style="font-size:18px;">--</div></div>
    </div>
    <table>
        <thead><tr><th>#</th><th>Timestamp</th><th>Status</th></tr></thead>
        <tbody id="rows"><tr><td colspan="3" class="empty">No alerts yet -- waiting for data...</td></tr></tbody>
    </table>

    <script>
        let lastCount = null;
        let soundEnabled = true;
        let audioCtx = null;

        function getAudioContext() {
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
            return audioCtx;
        }

        function playTone(freq, durationMs, delayMs) {
            setTimeout(() => {
                try {
                    const ctx = getAudioContext();
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = 'sawtooth';
                    osc.frequency.setValueAtTime(freq, ctx.currentTime);
                    gain.gain.setValueAtTime(0.3, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + (durationMs / 1000));
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + (durationMs / 1000));
                } catch(e) {
                    console.error("Audio error:", e);
                }
            }, delayMs);
        }

        function playWebAlarm() {
            if (!soundEnabled) return;
            playTone(1200, 180, 0);
            playTone(1800, 180, 220);
            playTone(1200, 180, 440);
            playTone(1800, 180, 660);
        }

        function toggleSound() {
            soundEnabled = !soundEnabled;
            const btn = document.getElementById('toggleSoundBtn');
            if (soundEnabled) {
                btn.innerText = "🔔 Sound Alert: Enabled";
                btn.className = "btn btn-toggle";
                playWebAlarm();
            } else {
                btn.innerText = "🔕 Sound Alert: Disabled";
                btn.className = "btn btn-toggle disabled";
            }
        }

        async function refresh() {
            try {
                const res = await fetch('/events');
                const data = await res.json();
                document.getElementById('count').innerText = data.length;
                document.getElementById('last').innerText = data.length ? data[data.length-1].timestamp : '--';
                
                if (lastCount !== null && data.length > lastCount) {
                    playWebAlarm();
                }
                lastCount = data.length;

                const rows = document.getElementById('rows');
                if (data.length === 0) {
                    rows.innerHTML = '<tr><td colspan="3" class="empty">No alerts yet -- waiting for data...</td></tr>';
                    return;
                }
                rows.innerHTML = data.slice().reverse().map((e, i) =>
                    `<tr><td>${data.length - i}</td><td>${e.timestamp}</td><td><span style="color:#ff4757; font-weight:bold;">${e.status}</span></td></tr>`
                ).join('');
            } catch(e) {
                console.error("Refresh error:", e);
            }
        }
        refresh();
        setInterval(refresh, 2000);

        // Resume Audio Context on initial user click anywhere on page
        document.body.addEventListener('click', () => { getAudioContext(); }, { once: true });
    </script>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(PAGE)


@app.route("/events")
def events():
    if os.path.exists(EVENTS_FILE):
        with open(EVENTS_FILE, "r") as f:
            try:
                return jsonify(json.load(f))
            except json.JSONDecodeError:
                return jsonify([])
    return jsonify([])


if __name__ == "__main__":
    app.run(debug=False, port=5000)
