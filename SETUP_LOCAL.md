# Setup Guide for HelixOS Local MVP

This guide explains how to set up the environment for running HelixOS completely locally.

## 1. System Dependencies

### macOS (Homebrew)
You need `portaudio` for microphone access and `ffmpeg` for audio processing.

```bash
brew install portaudio ffmpeg
```

## 2. Python Dependencies

Install the required Python packages:

```bash
pip install -r mvp/requirements.txt
```

## 3. Ollama (Local LLM)

HelixOS uses **Ollama** to run the routing intelligence locally.

1.  **Download & Install**: [https://ollama.com/download](https://ollama.com/download)
2.  **Start Ollama**: Open the app or run `ollama serve` in a terminal.
3.  **Pull the Model**: We use `llama3` by default. Run this command:

    ```bash
    ollama pull llama3
    ```

    *Note: You can change the model in `mvp/mvp_router.py` if you prefer another one (e.g., `mistral`).*

## 4. Run HelixOS

Once everything is set up:

```bash
python3 mvp/mvp_runner.py
```

## Troubleshooting

*   **"No module named sounddevice"**: Ensure you installed the requirements.
*   **"Could not connect to Ollama"**: Ensure Ollama is running (`ollama serve`).
*   **"Error during transcription"**: Ensure `ffmpeg` is installed and accessible in your PATH.
