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
- **Orchestration**: Docker (Moving to K3s in v2)
- **Sub-Agents**: Go (Golang) + Scratch images
- **LLM**: DeepSeek-R1 / Llama 3
- **STT**: OpenAI Whisper

## Technology Stack
*   **Python**: The primary language for the agent runtime and Whisper integration.
*   **K3s**: Lightweight Kubernetes for orchestration.
*   **Docker**: Containerization for sub-agents.
*   **NATS/MQTT**: Low-latency messaging bus.
*   **Tailscale**: Network mesh for secure device communication.

## Roadmap
1.  **MVP**: Basic loop with Audio -> Whisper -> Router -> Stub Execution.
2.  **Containerization**: Separating the Router from the Worker.
3.  **The Grid**: Implementing K3s orchestration.
4.  **The Brain**: Implementing the Registry and Context caching.
