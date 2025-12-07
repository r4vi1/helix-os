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
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}" # Using 1.5 Pro as proxy for 3-pro-preview in MVP code

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
        
        try:
            # Simulated response for local verification if API key is missing
            if not self.api_key:
                print("[!] No GEMINI_API_KEY found. using Mock content.")
                return self._mock_generator(task_spec)

            response = requests.post(GEMINI_URL, json=payload)
            response.raise_for_status()
            
            result = response.json()
            code = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # Clean up markdown if present
            code = code.replace("```go", "").replace("```", "").strip()
            return code
            
        except Exception as e:
            print(f"[!] Error producing code: {e}")
            raise

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
