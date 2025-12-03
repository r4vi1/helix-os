import time

def transcribe_audio(duration=5):
    """
    Simulates recording and transcribing audio.
    In a real implementation, this would use 'sounddevice' to record
    and 'openai-whisper' to transcribe.
    """
    print(f"[*] Listening for {duration} seconds...")
    time.sleep(duration)  # Simulate recording time
    
    # Mock return for MVP - in reality this comes from Whisper
    print("[*] Transcribing...")
    time.sleep(1) # Simulate processing
    
    # For the MVP demo, we'll return a hardcoded string or random choice
    # to show the flow.
    return "What is the weather in Tokyo"
