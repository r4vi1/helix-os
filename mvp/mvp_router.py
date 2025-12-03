import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "deepseek-r1:8b" # Using installed model

SYSTEM_PROMPT = """
You are the Router for HelixOS, a distributed AI operating system.
Your job is to analyze the user's voice command and output a JSON object representing the intent.

Output Format:
{
    "type": "active" | "passive" | "sub_agent" | "unknown",
    "action": "string_action_name",
    "params": { ... }
}

Examples:
1. "Turn on the kitchen lights." -> {"type": "active", "action": "control_lights", "params": {"location": "kitchen", "state": "on"}}
2. "Remind me to buy milk." -> {"type": "passive", "action": "save_reminder", "params": {"content": "buy milk"}}
3. "Research the history of the internet." -> {"type": "sub_agent", "action": "spawn_agent", "params": {"task_spec": "You are a research assistant. Provide a comprehensive summary of the history of the internet, covering key milestones like ARPANET, TCP/IP, and the World Wide Web."}}

For 'sub_agent' tasks, you MUST generate a VERBOSE 'task_spec' that gives the sub-agent clear, detailed instructions on how to perform the task. Do not just repeat the user's input.
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
        "stream": False,
        # "format": "json" # Disable JSON mode for DeepSeek to allow <think> blocks
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        
        result = response.json()
        response_text = result.get("response", "")
        print(f"[DEBUG] Raw LLM Response: {response_text}")

        # Clean DeepSeek/Reasoning model output
        # 1. Remove <think>...</think> blocks
        if "<think>" in response_text and "</think>" in response_text:
            response_text = response_text.split("</think>")[-1].strip()
        
        # 2. Remove markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            
        print(f"[DEBUG] Cleaned Response: {response_text}")

        # Parse the JSON from the LLM response
        try:
            intent = json.loads(response_text)
            
            # Validate structure
            if "type" not in intent:
                intent["type"] = "unknown"
            if "action" not in intent:
                intent["action"] = "unknown_action"
                
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
