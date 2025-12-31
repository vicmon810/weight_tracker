import subprocess
import requests
from datetime import datetime

API_URL = "http://localhost:8000/checkin"


def text_analysis(text:str):
    """
    simple emotion/stress analys
    """
    lower = text.lower()
    
    positive_words = ["good", "great", "relaxed", "happy", "excited", "calm"]
    negative_words = ["tired", "stressed", "anxious", "angry", "upset", "sad", "exhausted"]

    score = 3.0 #baseline

    for w in positive_words: 
        if w in lower:
            score -= 1
        
    for w in negative_words:
        if w in lower:
            score +=2

    #range 0 - 10
    score = max(0.0, min(10.0, score))

    if score >= 7:
        sentiment = "negtive"
    elif score <= 3:
        sentiment = "positive"
    else: 
        sentiment = "neutral"

    mood = text[:200]
    return mood, score, sentiment  

def record_audio(output_path="note.wav", seconds=30):
    """
    
    """
def transcribe_audio_to_text(audi="note.wav") -> str:
    """
    
    """
def main():
    text = input("Type what you would have said\n")
    # text =transcribe_audio_to_text()
    mood, stress_score, sentiment = text_analysis(text)

    print(f"[DEBUG] mood={mood}")
    print(f"[DEBUG] stress_score={stress_score}, sentiment={sentiment}")

    data = {
        "mood": text[:100],
        "diet_note": "",
        "exercise_minutes": None, 
        "exercise_note": None, 
        "sleep_hours": None, 
        "weight":None,
    }
    resp = requests.post(API_URL, json=data)
    print("Status:", resp.status_code)
    print("Response", resp.text)


if __name__ == "__main__":
    main()