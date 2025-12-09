
# Helper Config for HelixOS

import os
import sys
import subprocess
import requests

# --- Configuration ---
HELIX_MODEL = os.getenv("HELIX_MODEL")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_URL = f"{OLLAMA_HOST}/api/generate"

# Hybrid Intelligence Config
HELIX_SUB_AGENT_PROVIDER = os.getenv("HELIX_SUB_AGENT_PROVIDER", "local") # local | cloud
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX")  # Custom Search Engine ID

def get_installed_models():
    """
    Fetches the list of installed models from Ollama.
    """
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags")
        response.raise_for_status()
        data = response.json()
        # Extract model names (e.g., "deepseek-r1:8b", "llama3:latest")
        return [model["name"] for model in data.get("models", [])]
    except Exception as e:
        print(f"[!] Warning: Could not fetch models from Ollama at {OLLAMA_HOST}: {e}")
        return []

def select_model():
    """
    Selects the best available model directly.
    1. HELIX_MODEL env var
    2. deepseek-r1:8b (Preferred)
    3. llama3
    4. mistral
    5. First available model
    """
    env_model = os.getenv("HELIX_MODEL")
    if env_model:
        return env_model

    installed_models = get_installed_models()
    
    if not installed_models:
        print("[!] No models detected in Ollama. Please run 'ollama pull deepseek-r1:8b'")
        return "deepseek-r1:8b" # Fallback default

    # Preference list
    preferences = ["gemma3:4b", "deepseek-r1:8b", "llama3:latest", "llama3", "mistral:latest", "mistral"]
    
    for pref in preferences:
        # Check for exact match or match ignoring tag if not specified
        for installed in installed_models:
            if installed == pref or installed.startswith(pref + ":"):
                return installed

    # Fallback to the first one found
    return installed_models[0]

# Global Constants
MODEL_NAME = select_model()
print(f"[*] HelixOS Configuration Loaded. Using Model: {MODEL_NAME}")
