"""
AI-Based Driver Drowsiness Detection -- FULL SOFTWARE VERSION (OpenCV-only)
----------------------------------------------------------------------------
No Arduino / buzzer / hardware required, and no MediaPipe -- this uses
only OpenCV's built-in Haar Cascade classifiers, which ship inside the
opencv-python package itself. This avoids a Windows "Application Control"
security policy that some managed/college laptops use to block MediaPipe's
internal native library file from loading.

WHAT THIS SCRIPT DOES
1. Captures live video from your webcam.
2. Uses OpenCV's Haar Cascade face + eye detectors (classic, well-proven
   computer-vision technique -- this is the "AI" layer of the project).
3. On each frame: finds the face, then looks for eyes inside the face.
4. If both eyes go undetected (i.e. closed) for N consecutive frames,
   the driver is classified as DROWSY.
5. On a DROWSY event:
     - Plays an alarm sound (alarm.wav) through your speakers.
     - Shows a large red "WAKE UP!" banner on the video window.
     - Logs the event (timestamp) to events.json.
   events.json is read live by dashboard.py, which serves a simple local
   web dashboard -- this plays the role of the "IoT cloud dashboard"
   from the project report, without needing any real cloud account or
   hardware.

INSTALL
    pip install opencv-python numpy flask --break-system-packages

ONE-TIME SETUP
    python generate_alarm.py       # creates alarm.wav
    python download_cascades.py    # downloads the 2 Haar Cascade XML files needed for detection

RUN
    python drowsiness_detection_software.py
    python drowsiness_detection_software.py --source video.mp4   # test on a video file

(Optional, in a second terminal, to see the live dashboard)
    python dashboard.py
    then open http://127.0.0.1:5000 in a browser
"""

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime

import cv2

# Sound playback: prefer Windows' built-in winsound (no install needed at all).
# Fall back to simpleaudio on Mac/Linux, and to a plain terminal beep if neither works.
try:
    import winsound
    SOUND_BACKEND = "winsound"
except ImportError:
    winsound = None
    try:
        import simpleaudio as sa
        SOUND_BACKEND = "simpleaudio"
    except ImportError:
        sa = None
        SOUND_BACKEND = None
        print("[Warning] No sound backend available - alarm will be silent (visual alert only).")
        print("          On Mac/Linux, install with: pip install simpleaudio --break-system-packages")

HERE = os.path.dirname(os.path.abspath(__file__))
EVENTS_FILE = os.path.join(HERE, "events.json")
ALARM_FILE = os.path.join(HERE, "alarm.wav")

CONSEC_FRAMES_CLOSED = 8    # ~0.3s of "no eyes detected" (more responsive)
ALERT_COOLDOWN_SEC = 3.0


def ensure_alarm_file():
    """Ensures alarm.wav exists; generates it automatically if missing."""
    if not os.path.exists(ALARM_FILE):
        print(f"[Info] {ALARM_FILE} not found. Generating default alarm sound...")
        try:
            from generate_alarm import save_wav, build_alarm
            save_wav(ALARM_FILE, build_alarm())
            print("[Info] alarm.wav created successfully.")
        except Exception as e:
            print(f"[Warning] Failed to generate alarm.wav automatically: {e}")


ensure_alarm_file()

face_cascade = cv2.CascadeClassifier(os.path.join(HERE, "haarcascade_frontalface_default.xml"))
eye_cascade = cv2.CascadeClassifier(os.path.join(HERE, "haarcascade_eye_tree_eyeglasses.xml"))

if face_cascade.empty() or eye_cascade.empty():
    print("Cascade files not found or failed to load.")
    print("Run this first:  python download_cascades.py")
    sys.exit(1)


def _play_alarm_audio():
    """Background thread function to reliably play alarm audio across Windows sound devices."""
    print("[Alarm] Playing alarm sound...")
    played = False

    if SOUND_BACKEND == "winsound":
        # 1. Play alarm.wav synchronously inside background thread
        abs_path = os.path.abspath(ALARM_FILE)
        if os.path.exists(abs_path):
            try:
                winsound.PlaySound(abs_path, winsound.SND_FILENAME)
                played = True
            except Exception as e:
                print(f"[Alarm] winsound.PlaySound error: {e}")

        # 2. Hardware speaker beep backup
        try:
            for _ in range(2):
                winsound.Beep(1200, 160)
                time.sleep(0.03)
                winsound.Beep(1800, 160)
                time.sleep(0.03)
            played = True
        except Exception as e:
            print(f"[Alarm] winsound.Beep error: {e}")

        # 3. PowerShell SoundPlayer fallback
        if not played:
            try:
                import subprocess
                ps_cmd = f'powershell -c "(New-Object System.Media.SoundPlayer \'{abs_path}\').PlaySync()"'
                subprocess.run(ps_cmd, shell=True, timeout=3)
            except Exception as e:
                print(f"[Alarm] PowerShell sound fallback error: {e}")

    elif SOUND_BACKEND == "simpleaudio" and os.path.exists(ALARM_FILE):
        try:
            wave_obj = sa.WaveObject.from_wave_file(ALARM_FILE)
            play_obj = wave_obj.play()
            play_obj.wait_done()
        except Exception as e:
            print(f"[Alarm] simpleaudio error: {e}")
    else:
        print("\a")


class VirtualIoTLayer:
    """Software-only stand-in for the hardware IoT layer. Instead of
    triggering a physical buzzer over serial, it plays a sound, and
    logs every drowsy event to a local JSON file that acts as the
    'cloud dashboard' data source (see dashboard.py)."""

    def __init__(self):
        self._play_obj = None
        self._load_events()

    def _load_events(self):
        if os.path.exists(EVENTS_FILE):
            with open(EVENTS_FILE, "r") as f:
                try:
                    self.events = json.load(f)
                except json.JSONDecodeError:
                    self.events = []
        else:
            self.events = []

    def trigger_alert(self):
        # Sound playback in non-blocking background thread
        try:
            threading.Thread(target=_play_alarm_audio, daemon=True).start()
        except Exception as e:
            print(f"[Alarm] Could not start sound thread: {e}")

        # Log event (this is the "IoT data upload" simulated locally)
        event = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "DROWSY_ALERT",
        }
        self.events.append(event)
        self.events = self.events[-200:]  # keep the log from growing forever
        with open(EVENTS_FILE, "w") as f:
            json.dump(self.events, f, indent=2)

        print(f"[ALERT] Drowsiness detected at {event['timestamp']}")


def detect_eyes_open(gray_frame):
    """Returns (eyes_open: bool, face_box) for the largest face found."""
    faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(90, 90))
    if len(faces) == 0:
        return None, None

    # Use the largest detected face (closest to camera / most confident)
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_roi = gray_frame[y:y + h, x:x + w]

    eyes = eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=6, minSize=(20, 20))
    return len(eyes) >= 1, (x, y, w, h)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=0, help="Camera index or video file path")
    parser.add_argument("--test-sound", action="store_true", help="Test the alert sound immediately and exit")
    args = parser.parse_args()

    if args.test_sound:
        print("[Test] Triggering test alert sound...")
        iot = VirtualIoTLayer()
        iot.trigger_alert()
        time.sleep(2.5)  # allow sound to complete playback
        print("[Test] Sound test completed.")
        return

    source = int(args.source) if str(args.source).isdigit() else args.source
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Could not open video source: {source}")
        sys.exit(1)

    iot = VirtualIoTLayer()

    closed_frame_count = 0
    last_alert_time = 0
    drowsy_events = 0

    print("Starting drowsiness monitor (full software mode, OpenCV Haar Cascades). Press 'q' to quit.")

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        eyes_open, face_box = detect_eyes_open(gray)

        status_text = "No face detected"
        status_color = (0, 165, 255)
        show_banner = False

        if face_box is not None:
            fx, fy, fw, fh = face_box
            cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), (255, 200, 0), 2)

            if not eyes_open:
                closed_frame_count += 1
            else:
                closed_frame_count = max(0, closed_frame_count - 1)

            if closed_frame_count >= CONSEC_FRAMES_CLOSED:
                status_text = "DROWSY! Eyes closed"
                status_color = (0, 0, 255)
                show_banner = True
                now = time.time()
                if now - last_alert_time > ALERT_COOLDOWN_SEC:
                    iot.trigger_alert()
                    last_alert_time = now
                    drowsy_events += 1
            else:
                status_text = "Alert - Eyes open" if eyes_open else "Alert"
                status_color = (0, 200, 0)

        cv2.putText(frame, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, status_color, 2)
        cv2.putText(frame, f"Drowsy events: {drowsy_events}", (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        if show_banner:
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, h - 80), (w, h), (0, 0, 255), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
            cv2.putText(frame, "WAKE UP!", (w // 2 - 120, h - 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3)

        cv2.imshow("AI Driver Drowsiness Detection (Software Mode)", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
