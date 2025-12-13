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

    def generate_go_code(self, task_spec, agent_type="synthesis_agent", required_apis=None, output_schema=None, memory_context=""):
        """
        Generates specialized Go code based on agent type and requirements.
        
        Args:
            task_spec: The task specification
            agent_type: Type of agent to generate
            required_apis: List of API keys needed
            output_schema: Expected output JSON schema
            memory_context: Context from memory system (past experiences, patterns)
        """
        print(f"[*] Generating Go code for: {task_spec} (Type: {agent_type})")
        
        if required_apis is None:
            required_apis = []
        
        # specific instructions based on agent type
        type_instructions = ""
        if agent_type == "research_agent":
            type_instructions = """
            - You MUST use the Google Custom Search JSON API.
            - API Endpoint: https://www.googleapis.com/customsearch/v1
            - Parameters: key=<GOOGLE_SEARCH_API_KEY>, cx=<SEARCH_ENGINE_ID>, q=<query>
            - Read GOOGLE_SEARCH_API_KEY from environment variable.
            - Read GOOGLE_SEARCH_CX from environment variable (Search Engine ID).
            - Input: A search query string.
            - Logic: Make HTTP GET request, parse JSON response, extract titles and snippets.
            - Do NOT use SerpAPI. Use Google Custom Search API ONLY.
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
            - CRITICAL: The API endpoint MUST be exactly: 
              https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=<API_KEY>
            - Do NOT use "gemini-pro" or any other model name. Use "gemini-2.5-flash" ONLY.
            """
        
        apis_str = ", ".join(required_apis)
        schema_str = json.dumps(output_schema, indent=2) if output_schema else "{}"
        
        # Include memory context if available
        context_section = ""
        if memory_context:
            context_section = f"""
        Context from Past Experiences:
        {memory_context}
        
        Use this context to improve your approach, but generate fresh code.
        """

        prompt = f"""
        You are an expert Golang developer. Generate a GENERIC, REUSABLE Go agent.
        
        Agent Type: {agent_type}
        Required APIs to use: {apis_str}
        {context_section}
        CRITICAL: This agent must be REUSABLE for ANY query of its type.
        - Do NOT hardcode any specific topic, query, or task.
        - The agent receives its query/input at RUNTIME via os.Args[1].
        - Example: A research agent should research WHATEVER topic is passed via os.Args[1].
        
        Type-Specific Logic:
        {type_instructions}

        Requirements:
        1. Standalone `package main` using ONLY standard library (net/http, encoding/json, etc).
        2. Input: Read `os.Args[1]` as the primary input (query/expression). Check len(os.Args).
           - This is the RUNTIME query - use this for API calls, not any hardcoded value.
        3. Authentication: Read required API keys from environment variables: {apis_str}.
        4. Output: The program MUST output JSON to stdout adhering strictly to this schema:
        {schema_str}
        
        5. Error Handling: Return a JSON object with an "error" key if anything fails.
        6. HTTP Client: Use `http.Client` with timeout of 120 seconds (2 minutes).
        
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
        # Only use gemini-2.5-flash - other models not supported by current API key
        models = [
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
