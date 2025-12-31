import subprocess
import requests
from datetime import datetime

API_URL = "http://localhost:8000/checkin"

def record_audio = (output_path = "note.wav", second = 30):
    cmd = [
        "arecord",
        "-f","cd",
        "-d", str(second),
        "-q",
        output_path,
    ]
    subprocess.run(cmd, check=True)