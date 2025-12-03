import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "deepseek-r1:8b" # Using installed model

SYSTEM_PROMPT = """
You are the Router for HelixOS, a distributed AI operating system.
Your job is to analyze the user's voice command and output a JSON object representing the intent.

Output Format:
{
    "type": "active" | "passive" | "unknown",
    "action": "string_action_name",
    "params": { ... }
}

Examples:
1. "Turn on the kitchen lights." -> {"type": "active", "action": "control_lights", "params": {"location": "kitchen", "state": "on"}}
2. "Remind me to buy milk." -> {"type": "passive", "action": "save_reminder", "params": {"content": "buy milk"}}
3. "What is the weather in Tokyo?" -> {"type": "active", "action": "get_weather", "params": {"location": "Tokyo"}}

Do not output any text other than the JSON.
"""

def route_intent(text):
    """
    Sends the text to a local Ollama instance to determine intent.
    """
    print(f"[*] Routing intent for: '{text}'")
    
    if not text:
        return {"type": "unknown", "action": "empty_input", "params": {}}

    payload = {
        "model": MODEL,
        "prompt": text,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "format": "json" # Force JSON mode if model supports it, otherwise prompt handles it
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        
        result = response.json()
        response_text = result.get("response", "")
        print(f"[DEBUG] Raw LLM Response: {response_text}")

        # Parse the JSON from the LLM response
        try:
            intent = json.loads(response_text)
            return intent
        except json.JSONDecodeError:
            print(f"[!] Failed to parse JSON from LLM: {response_text}")
            return {"type": "unknown", "action": "parse_error", "params": {"raw": response_text}}

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"[!] Model '{MODEL}' not found. Please run 'ollama pull {MODEL}'")
            return {"type": "error", "action": "model_not_found", "params": {"model": MODEL}}
        else:
            print(f"[!] HTTP Error: {e}")
            return {"type": "error", "action": "http_error", "params": {"error": str(e)}}
            
    except requests.exceptions.ConnectionError:
        print("[!] Could not connect to Ollama. Is it running? (ollama serve)")
        return {"type": "error", "action": "ollama_connection_error", "params": {}}
    except Exception as e:
        print(f"[!] Error routing intent: {e}")
        return {"type": "error", "action": "unknown_error", "params": {"error": str(e)}}
