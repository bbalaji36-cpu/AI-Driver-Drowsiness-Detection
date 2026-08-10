"""
Downloads the two Haar Cascade XML files needed by drowsiness_detection_software.py,
straight from the official OpenCV GitHub repo. This works around a packaging bug
in opencv-python 5.0.0's Windows wheel, which ships without its cascade data files.

Run once:
    python download_cascades.py
"""
import urllib.request
import os

HERE = os.path.dirname(os.path.abspath(__file__))

FILES = {
    "haarcascade_frontalface_default.xml":
        "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml",
    "haarcascade_eye_tree_eyeglasses.xml":
        "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_eye_tree_eyeglasses.xml",
}

if __name__ == "__main__":
    for filename, url in FILES.items():
        dest = os.path.join(HERE, filename)
        print(f"Downloading {filename} ...")
        urllib.request.urlretrieve(url, dest)
        size_kb = os.path.getsize(dest) / 1024
        print(f"  -> saved to {dest} ({size_kb:.0f} KB)")
    print("Done.")
