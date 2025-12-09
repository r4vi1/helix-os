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

    def generate_go_code(self, task_spec, agent_type="synthesis_agent", required_apis=None, output_schema=None):
        """
        Generates specialized Go code based on agent type and requirements.
        """
        print(f"[*] Generating Go code for: {task_spec} (Type: {agent_type})")
        
        if required_apis is None:
            required_apis = []
        
        # specific instructions based on agent type
        type_instructions = ""
        if agent_type == "research_agent":
            type_instructions = """
            - You MUST access the Google Search API (or SerpAPI) using the provided API Key.
            - Input: A search query string.
            - Logic: Perform a search, extract snippets/URLs.
            """
        elif agent_type == "compute_agent":
            type_instructions = """
            - You MUST perform precise mathematical calculations or logic.
            - Input: A math expression or logic problem.
            - Logic: Parse the input and compute the result using relevant math libraries.
            """
        elif agent_type == "synthesis_agent":
            type_instructions = """
            - You are a Gemini Proxy. Call the Gemini API.
            - Input: A complex query.
            - Logic: Forward query to Gemini and return response.
            """
        
        apis_str = ", ".join(required_apis)
        schema_str = json.dumps(output_schema, indent=2) if output_schema else "{}"

        prompt = f"""
        You are an expert Golang developer. Generate a specialized Go agent.
        
        Task Context: {task_spec}
        Agent Type: {agent_type}
        Required APIs to use: {apis_str}
        
        Type-Specific Logic:
        {type_instructions}

        Requirements:
        1. Standalone `package main` using ONLY standard library (net/http, encoding/json, etc).
        2. Input: Read `os.Args[1]` as the primary input (query/expression). Check len(os.Args).
        3. Authentication: Read required API keys from environment variables: {apis_str}.
        4. Output: The program MUST output JSON to stdout adhering strictly to this schema:
        {schema_str}
        
        5. Error Handling: Return a JSON object with an "error" key if anything fails.
        6. HTTP Client: Use `http.Client` with timeout ($10s$).
        
        Output ONLY the raw Go code. No markdown.
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

    def _call_llm(self, payload_or_prompt):
        """ Helper to call LLM with fallback strategy """
        if isinstance(payload_or_prompt, str):
            payload = {"contents": [{"parts": [{"text": payload_or_prompt}]}]}
        else:
            payload = payload_or_prompt
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
