def route_intent(text):
    """
    Analyzes the text and determines the intent.
    In a real implementation, this would call a local LLM (e.g., Llama 3).
    """
    print(f"[*] Routing intent for: '{text}'")
    
    text = text.lower()
    
    if "weather" in text:
        return {
            "type": "active",
            "action": "get_weather",
            "params": {"location": "Tokyo"} # Simplified extraction
        }
    elif "remind" in text:
        return {
            "type": "passive",
            "action": "save_reminder",
            "params": {"content": text}
        }
    else:
        return {
            "type": "unknown",
            "action": "log_query",
            "params": {"content": text}
        }
