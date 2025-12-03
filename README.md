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
