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
        3. The program must accept input via command-line arguments (os.Args).
        4. ALWAYS check `len(os.Args)` before accessing arguments. If missing, return a JSON error.
        5. Output the result to stdout as JSON.
        6. Code MUST be compatible with TinyGo. Do not use cgo.
        7. Ensure memory safety (no nil pointer dereferences).
        
        Output ONLY the raw Go code. No markdown formatting, no explanation.
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
