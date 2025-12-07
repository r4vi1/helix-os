package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
)

// Config flags
var (
	task     string
	model    string
	provider string
	apiKey   string
)

// Ollama Config
const DefaultOllamaHost = "http://host.docker.internal:11434"

// Gemini Config
const GeminiBaseURL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"

// Data structs for Ollama
type OllamaRequest struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
	Stream bool   `json:"stream"`
}

type OllamaResponse struct {
	Response string `json:"response"`
}

// Data structs for Gemini
type GeminiRequest struct {
	Contents []GeminiContent `json:"contents"`
}

type GeminiContent struct {
	Parts []GeminiPart `json:"parts"`
}

type GeminiPart struct {
	Text string `json:"text"`
}

type GeminiResponse struct {
	Candidates []GeminiCandidate `json:"candidates"`
}

type GeminiCandidate struct {
	Content GeminiContent `json:"content"`
}

func main() {
	flag.StringVar(&task, "task", "", "The task description")
	flag.StringVar(&model, "model", "", "Ollama model name (e.g., deepseek-r1:8b)")
	flag.StringVar(&provider, "provider", "local", "Provider: 'local' (Ollama) or 'cloud' (Gemini)")
	flag.StringVar(&apiKey, "api-key", "", "Gemini API Key (required for cloud provider)")

	// Parse flags first
	flag.Parse()
    
    // Check ENV for API Key if not passed via flag
    if apiKey == "" {
        apiKey = os.Getenv("GEMINI_API_KEY")
    }

	if task == "" {
		fmt.Println("Error: --task flag is required")
		os.Exit(1)
	}

	fmt.Printf("[Sub-Agent] Provider: %s\n", provider)
	fmt.Printf("[Sub-Agent] Received Task: %s\n", task)

	var result string
	var err error

	if provider == "cloud" {
		result, err = callGemini(task, apiKey)
	} else {
		// Default to Local
		if model == "" {
			model = os.Getenv("HELIX_MODEL")
			if model == "" {
				model = "deepseek-r1:8b" 
			}
		}
		fmt.Printf("[Sub-Agent] Using Model: %s\n", model)
		result, err = callLocalOllama(task, model)
	}

	if err != nil {
		fmt.Printf("Error: %v\n", err)
		os.Exit(1)
	}

	// Clean output (remove <think> tags if present)
	cleaned := cleanOutput(result)

	fmt.Println("--- Result ---")
	fmt.Println(cleaned)
}

func callLocalOllama(prompt, modelName string) (string, error) {
	// 1. Construct Payload
	payload := OllamaRequest{
		Model:  modelName,
		Prompt: prompt,
		Stream: false,
	}
	jsonData, _ := json.Marshal(payload)

	// 2. Call Ollama
	resp, err := http.Post(DefaultOllamaHost+"/api/generate", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return "", fmt.Errorf("connecting to Ollama at %s/api/generate: %v\nEnsure Ollama is running on the host and accessible.", DefaultOllamaHost, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("ollama returned status: %s", resp.Status)
	}

	// 3. Parse Response
	body, _ := io.ReadAll(resp.Body)
	var oResp OllamaResponse
	if err := json.Unmarshal(body, &oResp); err != nil {
		return "", fmt.Errorf("parsing response: %v", err)
	}

	return oResp.Response, nil
}

func callGemini(prompt, key string) (string, error) {
	if key == "" {
		return "", fmt.Errorf("missing Gemini API Key. Set GEMINI_API_KEY env var")
	}

	// 1. Construct Payload
	payload := GeminiRequest{
		Contents: []GeminiContent{
			{
				Parts: []GeminiPart{
					{Text: prompt},
				},
			},
		},
	}
	jsonData, _ := json.Marshal(payload)

	// 2. Call Gemini API
	url := fmt.Sprintf("%s?key=%s", GeminiBaseURL, key)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return "", fmt.Errorf("connecting to Gemini API: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("gemini API returned status: %s, body: %s", resp.Status, string(body))
	}

	// 3. Parse Response
	body, _ := io.ReadAll(resp.Body)
	var gResp GeminiResponse
	if err := json.Unmarshal(body, &gResp); err != nil {
		return "", fmt.Errorf("parsing Gemini response: %v", err)
	}

	if len(gResp.Candidates) > 0 && len(gResp.Candidates[0].Content.Parts) > 0 {
		return gResp.Candidates[0].Content.Parts[0].Text, nil
	}

	return "", fmt.Errorf("empty response from Gemini")
}

func cleanOutput(text string) string {
	// Simple removal of <think>...</think> blocks common in reasoning models
	// Note: A robust implementation would use a regex or parser
	if start := strings.Index(text, "<think>"); start != -1 {
		if end := strings.Index(text, "</think>"); end != -1 {
			return strings.TrimSpace(text[end+8:])
		}
	}
	return text
}
