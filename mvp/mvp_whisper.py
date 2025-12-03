import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import whisper
import os
import tempfile

# Load the model once at startup to avoid reloading latency
print("[*] Loading Whisper model 'base'...")
model = whisper.load_model("base")
print("[*] Whisper model loaded.")

def record_audio(duration=5, fs=44100):
    """
    Records audio from the default microphone.
    """
    print(f"[*] Listening for {duration} seconds...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()  # Wait until recording is finished
    return recording, fs

def transcribe_audio(duration=5):
    """
    Records audio and uses local Whisper to transcribe it.
    """
    # 1. Record
    recording, fs = record_audio(duration)
    
    # 2. Save to temporary WAV file (Whisper expects a file or path)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        temp_wav_path = temp_wav.name
        # sounddevice returns float32, wavfile expects int16 or float32. 
        # Whisper handles it, but let's be safe and save as is.
        wav.write(temp_wav_path, fs, recording)
    
    # 3. Transcribe
    print("[*] Transcribing...")
    try:
        result = model.transcribe(temp_wav_path)
        text = result["text"].strip()
    except Exception as e:
        print(f"[!] Error during transcription: {e}")
        text = ""
    finally:
        # Cleanup
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
            
    return text
