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
        You are an expert Golang developer. Generate a Go program that acts as a proxy to the Gemini AI API.
        
        Task Context: {task_spec}
        
        The program MUST:
        1. Be a standalone `package main` using ONLY the standard library (`net/http`, `encoding/json`, `os`, `fmt`, `io`, `bytes`).
        2. Read the query from `os.Args[1]` (check `len(os.Args)` first, return JSON error if missing).
        3. Read the API key from the `GEMINI_API_KEY` environment variable (`os.Getenv`).
        4. Make an HTTP POST request to: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=<API_KEY>`
        5. The request body must be JSON: {{"contents": [{{"parts": [{{"text": "<user_query>"}}]}}]}}
        6. Parse the JSON response and extract the text from: response["candidates"][0]["content"]["parts"][0]["text"]
        7. Output the final result as JSON to stdout: {{"query": "<original_query>", "result": "<gemini_response>"}}
        8. Handle errors gracefully (network issues, API errors, missing key) and return JSON error objects.
        9. Set appropriate Content-Type header: application/json.
        10. Use `io.ReadAll` (not `ioutil.ReadAll` which is deprecated).
        
        Output ONLY the raw Go code. No markdown, no explanation, no backticks.
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        # Call the LLM helper
        return self._call_llm(payload)

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
    def fix_code(self, faulty_code, error_log):
        """
        Asks the LLM to fix the provided Go code based on the compiler error log.
        """
        print(f"[*] Asking LLM to fix code based on error...")
        prompt = f"""
        You are an expert Golang developer. The following code failed to compile or run.
        
        CODE:
        ```go
        {faulty_code}
        ```
        
        ERROR:
        {error_log}
        
        Task: Fix the code to resolve the error. Ensure it remains a standalone main package using only standard library.
        Checking `len(os.Args)` is CRITICAL.
        
        Output ONLY the raw Go code. No markdown, no explanation.
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        # Reuse the existing model fallback logic if possible, or simple call
        # For simplicity in this step, replicating the model call logic briefly or refactoring
        # to a private method would be best. Let's call the same logic.
        
        return self._call_llm(payload)

    def _call_llm(self, payload):
        """ Helper to call LLM with fallback strategy """
        models = [
            "gemini-3-pro-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash"
        ]
        
        if self.api_key:
            for model in models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                    response = requests.post(url, json=payload)
                    response.raise_for_status()
                    result = response.json()
                    code = result["candidates"][0]["content"]["parts"][0]["text"]
                    return code.replace("```go", "").replace("```", "").strip()
                except Exception as e:
                    print(f"    [!] Retrying model {model} due to error: {e}")
                    continue
                    
        return self._mock_generator("fix_code_fallback")
