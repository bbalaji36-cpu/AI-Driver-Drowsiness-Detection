from flask import Flask, render_template, request, jsonify
from detector import detect_drowsiness
import os
import threading
import time

try:
    import winsound
except ImportError:
    winsound = None


app = Flask(__name__)

last_alarm_time = 0
ALARM_COOLDOWN = 3

ALARM_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "alarm.wav"
)


def play_alarm():

    try:

        if winsound and os.path.exists(ALARM_FILE):

            print("Playing alarm...")

            winsound.PlaySound(
                ALARM_FILE,
                winsound.SND_FILENAME
            )

        else:

            print("Alarm file not found:", ALARM_FILE)

    except Exception as e:

        print("Alarm error:", e)


def start_alarm():

    threading.Thread(
        target=play_alarm,
        daemon=True
    ).start()


@app.route("/")
def home():

    return render_template("index.html")


@app.route("/detect", methods=["POST"])
def detect():

    global last_alarm_time

    try:

        image = request.files.get("frame")

        if image is None:

            return jsonify({
                "status": "ERROR",
                "message": "No camera frame received"
            }), 400

        image_bytes = image.read()

        result = detect_drowsiness(image_bytes)

        print("Detection result:", result)

        if result.get("status") == "DROWSY":

            current_time = time.time()

            if current_time - last_alarm_time > ALARM_COOLDOWN:

                print("DROWSY detected - starting alarm")

                start_alarm()

                last_alarm_time = current_time

        return jsonify(result)

    except Exception as e:

        print("Detection error:", e)

        return jsonify({
            "status": "ERROR",
            "message": str(e)
        }), 500


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )