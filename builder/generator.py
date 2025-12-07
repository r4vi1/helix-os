import os
import requests
import json

import sys
import os

# Add root to sys.path to allow importing from mvp
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from mvp.config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Using Gemini 3 Pro Preview as requested.
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-preview:generateContent?key={GEMINI_API_KEY}"

class CodeGenerator:
    def __init__(self, api_key=GEMINI_API_KEY):
        self.api_key = api_key

    def generate_go_code(self, task_spec):
        """
        Generates robust, TinyGo-compatible Go code for the given task.
        """
        print(f"[*] Generating Go code for: {task_spec}")
        
        prompt = f"""
        You are an expert Golang developer specializing in high-performance, dependency-free CLIs for TinyGo.
        
        Task: {task_spec}
        
        Requirements:
        1. Write a complete, standalone Go program (`package main`).
        2. Use only the standard library. NO external modules.
        3. The program must accept input via command-line arguments or stdin.
        4. Output the result to stdout as JSON.
        5. Code MUST be compatible with TinyGo (avoid extensive reflection `encoding/json` is okay but keep it simple).
        
        Output ONLY the raw Go code. No markdown formatting, no explanation.
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        # Model Priority List
        models = [
            "gemini-3-pro-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash"
        ]

        # 1. Try Real Models
        if self.api_key:
            for model in models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                    print(f"    -> [LLM] Trying model: {model}...")
                    
                    response = requests.post(url, json=payload)
                    response.raise_for_status()
                    
                    result = response.json()
                    code = result["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # Clean up markdown if present
                    code = code.replace("```go", "").replace("```", "").strip()
                    return code
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        print(f"    [!] Rate Limit (429) hit for {model}. Trying fallback...")
                        continue # Try next model
                    elif e.response.status_code == 404:
                         print(f"    [!] Model {model} not found or access denied. Trying fallback...")
                         continue
                    else:
                        print(f"    [!] API Error with {model}: {e}")
                        # Don't break immediately, try next just in case
                        continue
                except Exception as e:
                    print(f"    [!] Unexpected error with {model}: {e}")
                    continue

        # 2. Fallback to Mock
        print("[!] All LLM attempts failed or API Key missing. Using Mock Generator.")
        return self._mock_generator(task_spec)

    def _mock_generator(self, task_spec):
        if "fibonacci" in task_spec.lower():
            return """
package main

import (
	"fmt"
	"os"
	"strconv"
)

func fib(n int) int {
	if n <= 1 {
		return n
	}
	return fib(n-1) + fib(n-2)
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println(`{"error": "provide a number"}`)
		return
	}
	n, _ := strconv.Atoi(os.Args[1])
	res := fib(n)
	fmt.Printf(`{"input": %d, "result": %d}`, n, res)
}
"""
        return """package main; import "fmt"; func main() { fmt.Println("Hello, Agent!") }"""
