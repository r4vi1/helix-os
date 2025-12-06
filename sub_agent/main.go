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

// Config
const (
	OllamaURL = "http://host.docker.internal:11434/api/generate"
)

// Default Model (fallback)
var Model = "deepseek-r1:8b"

// RequestPayload structure for Ollama API
type RequestPayload struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
	Stream bool   `json:"stream"`
}

// ResponsePayload structure for Ollama API
type ResponsePayload struct {
	Response string `json:"response"`
	Done     bool   `json:"done"`
}

func main() {
	// 1. Parse Arguments
	taskPtr := flag.String("task", "", "The task description to execute")
	modelPtr := flag.String("model", "", "The model to use (optional)")
	flag.Parse()

	if *taskPtr == "" {
		fmt.Println("Error: No task provided. Use --task \"your task here\"")
		os.Exit(1)
	}

	if *modelPtr != "" {
		Model = *modelPtr
	}

	fmt.Printf("[Sub-Agent] Using Model: %s\n", Model)
	fmt.Printf("[Sub-Agent] Received Task: %s\n", *taskPtr)

	// 2. Prepare Payload
	payload := RequestPayload{
		Model:  Model,
		Prompt: *taskPtr,
		Stream: false,
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		fmt.Printf("Error marshaling JSON: %v\n", err)
		os.Exit(1)
	}

	// 3. Send Request to Host Ollama
	// Note: host.docker.internal works on Mac/Windows Docker Desktop.
	// For Linux, might need --network="host" and localhost, or specific IP.
	resp, err := http.Post(OllamaURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		fmt.Printf("Error connecting to Ollama at %s: %v\n", OllamaURL, err)
		fmt.Println("Ensure Ollama is running on the host and accessible.")
		os.Exit(1)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		fmt.Printf("Error: Ollama returned status %d: %s\n", resp.StatusCode, string(body))
		os.Exit(1)
	}

	// 4. Parse Response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("Error reading response body: %v\n", err)
		os.Exit(1)
	}

	var responsePayload ResponsePayload
	err = json.Unmarshal(body, &responsePayload)
	if err != nil {
		fmt.Printf("Error unmarshaling response: %v\n", err)
		os.Exit(1)
	}

	// 5. Clean Output (DeepSeek specific)
	cleanResponse := cleanDeepSeekOutput(responsePayload.Response)

	// 6. Output Result
	fmt.Println("--- Result ---")
	fmt.Println(cleanResponse)
}

func cleanDeepSeekOutput(text string) string {
	// Remove <think> tags
	if strings.Contains(text, "<think>") && strings.Contains(text, "</think>") {
		parts := strings.Split(text, "</think>")
		if len(parts) > 1 {
			text = strings.TrimSpace(parts[1])
		}
	}
	return text
}
