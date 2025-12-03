# Getting Started with HelixOS MVP

This guide will help you get the Minimum Viable Product (MVP) of HelixOS running on your local machine.

## Prerequisites
*   Python 3.10+
*   A microphone

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/helix-os.git
    cd helix-os
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r mvp/requirements.txt
    ```

## Run the MVP

Execute the runner script:

```bash
python mvp/mvp_runner.py
```

## What to Expect
1.  The application will start listening for audio input.
2.  Speak a command (e.g., "What is the weather?").
3.  The system will transcribe your audio using a local Whisper instance.
4.  The Router will classify your intent.
5.  A dummy executor will print the "task execution" to the console.

*Note: This MVP is a proof-of-concept for the core logic loop and does not yet involve Docker or K3s.*
