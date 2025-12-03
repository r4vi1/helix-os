import time
from mvp_whisper import transcribe_audio
from mvp_router import route_intent

def execute_action(intent):
    """
    Executes the action determined by the router.
    """
    print(f"[*] Executing Action: {intent['action']}")
    if intent['action'] == 'get_weather':
        print(f"    -> Fetching weather for {intent['params']['location']}...")
        # Stub: Call weather API
        print("    -> It is 22°C and Sunny.")
    elif intent['action'] == 'save_reminder':
        print(f"    -> Saving reminder: {intent['params']['content']}")
        # Stub: Save to DB
        print("    -> Reminder saved.")
    else:
        print("    -> Unknown command, logging.")

def main():
    print("=== HelixOS MVP Running ===")
    try:
        while True:
            # 1. Input
            text = transcribe_audio()
            print(f"[*] Heard: {text}")
            
            # 2. Route
            intent = route_intent(text)
            
            # 3. Execute
            execute_action(intent)
            
            print("-" * 30)
            # Break for demo purposes so it doesn't loop infinitely in a non-interactive way
            # In real life, this would wait for a wake word or button press
            user_input = input("Press Enter to listen again, or 'q' to quit: ")
            if user_input.lower() == 'q':
                break
                
    except KeyboardInterrupt:
        print("\nStopping HelixOS...")

if __name__ == "__main__":
    main()
