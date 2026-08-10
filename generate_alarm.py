"""
Generates alarm.wav — a short, sharp two-tone beep pattern used as the
software alarm sound. Uses only the Python standard library (wave + math),
so it needs no extra installs and works on Windows/Mac/Linux alike.

Run once:
    python generate_alarm.py
"""
import wave
import math
import struct

SAMPLE_RATE = 44100


def tone(freq, duration_sec, volume=0.95):
    n_samples = int(SAMPLE_RATE * duration_sec)
    return [volume * math.sin(2 * math.pi * freq * i / SAMPLE_RATE) for i in range(n_samples)]


def build_alarm():
    # Alternating high/low sharp beep pattern for maximum audibility
    samples = []
    for _ in range(4):
        samples += tone(1200, 0.18, volume=0.95)
        samples += tone(0, 0.04)         # brief pause
        samples += tone(1800, 0.18, volume=0.95)
        samples += tone(0, 0.04)
    return samples


def save_wav(path, samples):
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        frames = b"".join(struct.pack("<h", max(-32767, min(32767, int(s * 32767)))) for s in samples)
        wf.writeframes(frames)


if __name__ == "__main__":
    save_wav("alarm.wav", build_alarm())
    print("alarm.wav created successfully with high-volume sound pattern.")

