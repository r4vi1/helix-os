# HelixOS Project Status Tracker

**Reference Blueprint**: [Main_idea.md](./Main_idea.md)

## 🚀 Current Status
**Phase**: Milestone 2 - The Split (Containerization)
**Latest Update**: Implemented ephemeral Go-based sub-agents using Docker.

## 🏆 Milestone Progress

### ✅ Milestone 1: The MVP (The Monolith)
- [x] **Hardware**: Running on Local Mac (Primary Node).
- [x] **Ingress**: Local Microphone via `sounddevice`.
- [x] **Transcription**: Local Whisper (Base model).
- [x] **Router**: Local LLM (`deepseek-r1:8b` via Ollama).
- [x] **Action**: Basic local function execution (Weather, Reminders).

### 🔄 Milestone 2: The Split (Containerization)
- [x] **Infrastructure**: Docker installed and running.
- [x] **Sub-Agent Runtime**: Created lightweight Go-based agent (`helix-agent-go`).
- [x] **Orchestration (Lite)**: `mvp_runner.py` spawns ephemeral Docker containers for complex tasks.
- [ ] **Router Containerization**: Move `mvp_router.py` into a container (Pending).
- [ ] **Messaging Bus**: Implement NATS/MQTT for inter-container communication (Pending).

### ⏳ Milestone 3: The Grid (Orchestration)
- [ ] **Infrastructure**: Install K3s.
- [ ] **Worker Nodes**: Add external workers (e.g., Raspberry Pi).
- [ ] **Operator**: Write K8s operator for dynamic job creation.

### ⏳ Milestone 4: The Brain (Registry & Context)
- [ ] **Registry**: Local Docker Registry.
- [ ] **Feedback Loop**: Commit successful agent states to registry.
- [ ] **Garbage Collection**: Clean up unused images.

## 📝 Change Log

### [2025-12-04] Sub-Agent Implementation
- **Feature**: Implemented "Just-in-Time Intelligence" using ephemeral Docker containers.
- **Tech**: Go (Golang) for the sub-agent to minimize image size (<10MB).
- **Logic**:
    - Updated `mvp_router.py` to generate verbose "Task Specs" for `sub_agent` intent.
    - Updated `mvp_runner.py` to spawn `helix-agent-go` containers on demand.
    - Tuned Router for `deepseek-r1:8b` (stripped `<think>` tags).

### [2025-12-03] MVP Initialization & Fixes
- **Feature**: Initial Local MVP with Voice-to-Action pipeline.
- **Fix**: Switched default model to `deepseek-r1:8b` and fixed JSON parsing logic.
- **Fix**: Corrected git contribution identity.
