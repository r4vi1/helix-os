# HelixOS: Distributed AI Operating System

## What is this project?
HelixOS is a distributed, containerized AI operating system that utilizes a local compute grid to deploy ephemeral "Sub-Agents" for specific tasks. It embodies the philosophy of "Just-in-Time Intelligence," where resources are optimized by spinning up logic only when needed.

## Why does it exist?
To build an open, privacy-preserving alternative to cloud-locked AI assistants by using local compute, local LLMs, and on-demand intelligence. We believe in owning your data and your compute.

## Core Concepts
*   **Local Whisper → Router LLM → Sub-Agent**: The core pipeline for processing voice commands.
*   **Warm Pool**: A set of pre-warmed containers for zero-latency active commands (e.g., "Turn on lights").
*   **Cold Containers**: On-demand containers for complex tasks (e.g., "Research stock trends").
*   **Local K3s Cluster**: Lightweight Kubernetes for orchestrating the distributed agents.
*   **Local Registry**: A mechanism for caching and reusing successful agent images.

## ⚡️ Features

- **Local Voice Ingress**: Real-time speech-to-text using `openai-whisper`.
- **Local Intelligence**: Intent classification using `deepseek-r1:8b` (via Ollama).
- **Just-in-Time Sub-Agents**: Spawns ephemeral, lightweight **Go-based Docker containers** (<10MB) for complex tasks.
- **Privacy First**: All processing happens locally. No audio leaves your network.

## 🛠️ Tech Stack

- **Core**: Python 3.10+
- **LLM**: Gemma 3 / DeepSeek-R1 (via Ollama)
- **STT**: OpenAI Whisper
- **Sub-Agents**: Go 1.21+ (Containerized)
- **Orchestration**: Docker (MVP runs as local processes)

## 🚀 Getting Started

This guide will help you get the Minimum Viable Product (MVP) of HelixOS running on your local machine.

### Prerequisites
*   Python 3.10+
*   A microphone

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/helix-os.git
    cd helix-os
    ```

2.  **Install dependencies:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r mvp/requirements.txt
    ```

3.  **Run the MVP:**
    ```bash
    python mvp/mvp_runner.py
    ```

## 🤝 Contributing

We welcome contributions to help build the future of open-source, distributed AI!

### How to Contribute
1.  **Fork the repository** on GitHub.
2.  **Create a feature branch** for your changes.
3.  **Submit a Pull Request (PR)** with a clear description of your work.

For more details on coding conventions and open issues, please see [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap
1.  **MVP**: Basic loop with Audio -> Whisper -> Router -> Stub Execution.
2.  **Containerization**: Separating the Router from the Worker.
3.  **The Grid**: Implementing K3s orchestration.
4.  **The Brain**: Implementing the Registry and Context caching.
