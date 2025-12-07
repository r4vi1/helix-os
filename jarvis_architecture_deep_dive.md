
# Project JARVIS – Architectural Deep Dive

## 1. Introduction

Project JARVIS is a **distributed, containerized AI operating layer** that runs on a local compute grid (home‑lab or SMB infrastructure) and orchestrates **ephemeral “Sub‑Agents”** to handle tasks on demand. The core philosophy is:

> **Just‑in‑Time Intelligence** – don’t keep giant monoliths always running; spin up specialized logic only when needed, cache what’s useful, and tear down the rest. fileciteturn0file0

This document captures a cohesive architectural design for JARVIS as a **general agent platform** that can power voice assistants *and* non‑voice workflows, running on top of k3s (Kubernetes) as the “OS”.

---

## 2. Goals and Non‑Goals

### 2.1 Goals

- **Local‑first agent platform** 
  - Primary: self‑hosters / home‑lab users.
  - Secondary: SMBs, via additional governance and management layers.
- **General agent runtime, not just voice**  
  - Voice is a first‑class ingress, but HTTP / API / events are equally important.
- **Container / k3s‑native design**  
  - Everything is a Kubernetes object; agents are packaged as containers.
- **Separation of concerns**
  - Control plane vs hot path.
  - Stateless agents vs centralized memory.
- **Cloud offload**  
  - Tasks too heavy for local hardware can be run as cloud Sub‑Agents in a VM with large foundation models.

### 2.2 Non‑Goals (for v1)

- Building a brand‑new OS or Linux distro. JARVIS assumes an existing OS and focuses on the **AI orchestration layer**.
- Handling every possible enterprise compliance scenario on day one (SOC2, HIPAA, etc.).
- Replacing full‑blown MLOps/inference platforms; JARVIS focuses on **agent orchestration** and home/SMB‑scale workloads.

---

## 3. System Overview

### 3.1 Hardware & Node Roles

JARVIS runs on a **k3s cluster** across one or more machines:

- **Primary Node (Control + Inference)**
  - Runs the k3s control plane.
  - Hosts GPU(s) for local inference (Router LLM, Whisper, small task models).
  - Runs core services: Router, NATS, Memory, Operator, API, Registry, etc.

- **Worker Nodes**
  - Old laptops, NUCs, servers, or Raspberry Pis.
  - Join k3s as agents.
  - Execute ephemeral Sub‑Agents and/or Utility Agents (warm pools).

- **Peripheral Layer**
  - Voice ingress devices (mics, speakers, wearables).
  - HTTP/Web clients, mobile apps, internal services that call JARVIS APIs.

### 3.2 Conceptual Layers

1. **Ingress Layer**
   - Voice (audio → Whisper)  
   - HTTP / gRPC / event webhooks

2. **Core “Brain” Layer**
   - Router LLM (intent classification & routing)
   - Memory service (central state)
   - NATS messaging bus
   - Jarvis Operator (agent orchestration)

3. **Agent Execution Layer**
   - Utility Agents (always‑on warm pool)
   - Ephemeral Sub‑Agents (spawned for complex tasks)
   - Cloud Agents (remote execution when offloaded)

4. **Persistence & Registry**
   - Postgres (relational state)
   - Vector store (embeddings)
   - Local container registry (agent images, base runtimes)

---

## 4. High‑Level Components

### 4.1 Ingress

- **Voice Ingress**
  - Audio from wearables / mics is sent to `Whisper Service` for transcription.
  - Transcripts are published onto the NATS bus for the Router to consume.

- **HTTP / API Ingress**
  - `API Gateway` exposes HTTP/gRPC endpoints for non‑voice tasks:
    - `/v1/tasks/submit`
    - `/v1/agents/invoke`
    - `/v1/memory/query` (for debugging/testing)

### 4.2 Core Services

1. **Router Service**
   - Deployment with 1–N replicas.
   - Consumes inbound transcripts/requests.
   - Uses a local LLM (e.g., Llama‑3 8B quantized) to:
     - Classify intent (hot vs cold vs cloud).
     - Assemble `TaskSpec` (agent type, tools, parameters).
   - Decides which path to take:
     - **Hot path** → Utility Agents.
     - **Cold path** → spawn Sub‑Agent via Operator.
     - **Cloud path** → offload to remote agents.

2. **Whisper Service**
   - GPU‑enabled service for audio → text.
   - Exposes HTTP/gRPC; can be disabled entirely for non‑voice deployments.

3. **Utility Agent Pool**
   - Long‑running Deployment.
   - Provides “fast path” handling for:
     - Smart‑home control.
     - Simple database operations.
     - Lightweight Q&A or automations.
   - Subscribed to a NATS subject for **hot tasks**, runs tools in‑process (no cold start).

4. **Jarvis Operator**
   - Custom controller running in the cluster.
   - Listens to NATS (or watches CRDs) for new `TaskSpec`s that require dedicated agents.
   - Creates:
     - `Job` resources for short‑lived tasks.
     - `Deployment` resources for longer‑lived agents.
   - (Later) handles snapshot → image commit → push to local registry.

5. **Memory Service**
   - Single entrypoint to persistent state.
   - Handles:
     - Fact storage (`User hates broccoli`) and retrieval.
     - Embedding generation and vector similarity search.
     - Scoping memories by user/tenant/organization.
   - Exposes request/reply RPC over NATS (agents don’t talk directly to DB).

6. **API Gateway**
   - HTTP/gRPC interface for non‑voice clients.
   - Performs auth, rate limiting, and request validation.

7. **NATS Messaging Bus**
   - Core messaging fabric for:
     - Ingress events.
     - Router decisions.
     - Agent requests/responses.
     - Memory queries.
   - Provides pub/sub, request/reply, and queue groups.

8. **Registry**
   - Local Docker registry (or Harbor) for:
     - Base AI images.
     - Agent images produced by the Operator’s commit logic (post‑v1).

### 4.3 Data Infrastructure

- **Postgres**
  - Source of truth for users, tenants, agents, and structured memories.

- **Vector Store (pgvector or Qdrant)**
  - Stores embeddings for semantic retrieval.

---

## 5. Cluster Topology

### 5.1 Home‑Lab Topology (Minimum Viable Cluster)

- **Node A (Primary)**  
  - k3s server
  - GPU for inference
  - Runs: Router, Whisper, Memory, NATS, Operator, API, Registry, Utility Agents, Postgres, vector store.

- **Node B..N (Workers)**
  - Joined via k3s token.
  - Run ephemeral Sub‑Agents and Utility Agents.
  - Optional GPUs if available.

This configuration is ideal for a single power user with a small cluster and minimal high‑availability requirements.

### 5.2 SMB Topology (Hardened Variant)

- **Control + GPU Node**
  - k3s server + Router + Whisper + NATS cluster member.
- **Worker Nodes**
  - Additional k3s agents; some may host GPUs.
- **External Data Services**
  - Managed Postgres (HA, backups).
  - External object store (backups, artifacts, logs).
- **NATS Cluster**
  - 3‑node NATS cluster (multiple pods or machines).

This setup decouples the control plane from data services and provides stronger resilience and scalability.

---

## 6. Messaging Bus – NATS Core

### 6.1 What NATS Core Provides

JARVIS uses **NATS Core** as the central nervous system:

- **Pub/Sub**
  - Many subscribers can listen to a subject; publishers don’t know who receives messages.
- **Request/Reply**
  - Implement RPC‑like patterns: one request, one response.
- **Queue Groups**
  - Multiple consumers in a queue group share messages (load‑balancing).

NATS Core is lightweight and low‑latency, perfect for real‑time voice and agent workloads.

### 6.2 Subject Naming Conventions

Use hierarchical, tenant‑scoped subjects:

- `tenant.<tenant_id>.ingress.transcript`  
  Inbound transcripts (text) from Whisper or HTTP.

- `tenant.<tenant_id>.router.decisions`  
  Router publishes decisions / TaskSpecs here (if you want introspection).

- `tenant.<tenant_id>.tasks.utility`  
  Request/Reply subject, Utility Agents subscribe as a queue group (e.g., `utility-workers`).

- `tenant.<tenant_id>.tasks.spawn`  
  Router publishes TaskSpecs needing new agents; Jarvis Operator subscribes.

- `tenant.<tenant_id>.memory.request`  
  Request/Reply subject for Memory Service.

- `tenant.<tenant_id>.events.broadcast`  
  Pub/Sub subject for global events like “stop music”.

### 6.3 Example Hot Path Flow (NATS)

1. **Ingress** publishes transcript:

   - Subject: `tenant.123.ingress.transcript`  
   - Payload:  
     ```json
     {
       "session_id": "s1",
       "user_id": "u123",
       "text": "turn on the kitchen lights",
       "source": "wearable-1"
     }
     ```

2. **Router** is subscribed to `tenant.123.ingress.transcript`, classifies intent as `home_assistant.toggle_device` with `HOT_PATH`.

3. Router issues a **NATS request** to `tenant.123.tasks.utility`:

   ```json
   {
     "session_id": "s1",
     "user_id": "u123",
     "intent": "home_assistant.toggle_device",
     "args": { "device": "kitchen_lights", "state": "on" }
   }
   ```

4. One Utility Agent in the `utility-workers` queue group processes the request, calls Home Assistant, and replies.

5. Router (or Ingress) uses the response to generate local feedback (TTS or UI response).

---

## 7. State & Memory Model

### 7.1 Centralized Memory Service

All stateful knowledge lives in a **central DB** managed by the Memory Service. Sub‑Agents are ephemeral and do **not** own long‑lived memory.

The Memory Service provides a simple API (over NATS) for:

- Writing facts (e.g., “User hates broccoli”).
- Querying user/org memories.
- Storing and retrieving context histories.

### 7.2 Suggested Data Model (Conceptual)

- `tenants(id, name, ...)`
- `users(id, tenant_id, ...)`
- `agents(id, name, version, image_ref, ...)`
- `agent_runs(id, agent_id, user_id, tenant_id, started_at, finished_at, status, ...)`
- `memories(id, tenant_id, user_id, scope, key, value, created_at, source_agent_id, confidence, embedding_vector)`

Where:

- `scope` ∈ `{ USER, ORG }`
- `key` is a logical key (e.g., `food_preferences`)
- `value` is JSON
- `embedding_vector` is used for semantic search

### 7.3 Agent SDK

Provide a simple SDK (e.g., Python) so agents never touch NATS or Postgres directly:

```python
# Pseudocode
sdk.memory.write_fact(
    user_id="u123",
    scope="USER",
    key="food_preferences",
    value={"hates": ["broccoli"]},
    confidence=0.9,
)

facts = sdk.memory.query(
    user_id="u123",
    query="what foods should I avoid suggesting?",
)
```

Under the hood, the SDK sends a request to `tenant.<tid>.memory.request` and receives a response from the Memory Service.

---

## 8. Agent Lifecycle and Runtime

### 8.1 Agent Types

1. **Utility Agents (Warm Pool)**
   - Long‑running pods for **low‑latency** tasks.
   - Handle frequent, simple operations (smart home, small DB actions, simple Q&A).
   - Subscribed to `tasks.utility` with a queue group; horizontally scalable.

2. **Ephemeral Sub‑Agents (Cold Path)**
   - Spawned by Jarvis Operator as Jobs or Deployments.
   - Used for complex or long‑running workflows:
     - Advanced data analysis.
     - Multi‑step planning.
     - Integrations that require separate runtimes.

3. **Cloud Agents**
   - Run in external environments (e.g., cloud VMs with large foundation models).
   - Communicate with local JARVIS via:
     - VPN / mesh (e.g., Tailscale) + NATS.
     - Or a secure HTTPS webhook mechanism.

### 8.2 Agent Execution Flow (Cold Path)

1. Router decides task requires a Sub‑Agent.
2. Router publishes `TaskSpec` to `tenant.<tid>.tasks.spawn`.
3. Jarvis Operator receives TaskSpec and:
   - Creates appropriate Kubernetes Job/Deployment.
   - Injects configuration, tools, and task context.
4. Agent pod starts, subscribes to its own task subject or processes an initial payload.
5. When finished:
   - Writes results to Memory Service and/or external systems.
   - Emits completion event on NATS.
   - Job completes; pod is garbage‑collected.

### 8.3 Agent‑as‑Image Lifecycle (Future)

Later, the Operator can:

- Monitor agent runs.
- If an ad‑hoc agent performs well repeatedly, **commit its container state** into a new versioned image.
- Push the image to the local registry.
- Update routing so the Router can reuse the cached agent image instantly next time.

A garbage collector cleans up unused agent images based on recency and frequency.

---

## 9. Execution Paths and Latency Budgets

### 9.1 Hot Path (Utility Agents)

Used for: smart home control, quick checks, simple tasks.

**Target SLOs**

- **P50** ≤ 400 ms  
- **P95** ≤ 800 ms

**Rough Budget**

- Ingress + NATS: 20–50 ms
- Whisper (if voice) for short utterances: 150–300 ms
- Router LLM: 80–200 ms
- Utility Agent execution: 50–200 ms

Key constraints:

- **No container cold starts** in this path. Utility Agents must already be running.
- Router and Utility Agents connect via NATS (no extra network hops beyond the bus).

### 9.2 Cold Path (Ephemeral Sub‑Agents)

Used for: complex workflows, heavy analysis, long‑running tasks.

**Target SLOs (first response / task start)**

- **P50** ≈ 3–4 seconds  
- **P95** ≈ 6–8 seconds

Additional overhead:

- Operator / K8s scheduling: 200–500 ms
- Container cold start: 500–1500 ms
- Agent initialization: 500–1500 ms

Mitigations:

- Use a generic “agent‑runner” image that can be pre‑warmed on each node.
- Only spawn brand‑new pods when necessary.

### 9.3 Cloud Path (Offload)

Used when:

- Local hardware is insufficient.
- Tasks require very large foundation models.

**Target SLOs**

- **P50** ≈ 2–4 seconds  
- **P95** ≈ 8–10 seconds

Network latency and remote inference time dominate here. This path is acceptable for non‑interactive or less time‑critical tasks.

---

## 10. Resilience, Health, and Scaling

### 10.1 Router Resilience

- `jarvis-router` is a Deployment with ≥2 replicas (for SMB / important clusters).
- Each pod:
  - Implements **liveness probes** (LLM process check).
  - Implements **readiness probes** (model fully loaded and ready).
- If one pod crashes, k3s restarts it; other replicas continue processing traffic.
- Horizontal Pod Autoscaler (HPA) can scale based on CPU and/or custom metrics (e.g., NATS subject depth).

### 10.2 NATS Resilience

- Home‑lab: single NATS pod (simple, easy).
- SMB / prod: 3‑node NATS cluster across nodes with anti‑affinity.
- Later: use NATS JetStream for durable streams in critical workflows.

### 10.3 Watchdog Service

A lightweight **watchdog** periodically:

- Sends synthetic tasks via NATS to Router and Utility queue.
- Expects replies within a tight budget (e.g., 500 ms).
- Emits metrics, logs, or alerts (e.g., to a dashboard) if components misbehave.

### 10.4 Horizontal Scaling

- **Utility Agents**: scale via queue groups (more replicas → more throughput).
- **Sub‑Agents**: naturally parallelizable as Jobs across worker nodes.
- **Router**: scale read‑side LLM processing via HPA.

---

## 11. Security Considerations

Even in a home‑lab, agent code can be dangerous. Baseline practices:

- **Least privilege containers**
  - Run as non‑root by default.
  - Avoid hostPath and privileged containers unless required.
- **Network egress control**
  - Namespace‑level policies limiting where agents can call out to.
- **Tool / API whitelisting**
  - Explicit configuration of what each agent is allowed to do (e.g., which Home Assistant entities, which HTTP domains).
- **Optional sandboxing**
  - For untrusted, LLM‑generated code, support more isolated runtimes (gVisor, Kata, Firecracker) in advanced configurations.

For SMBs, additional features (like audit logs, RBAC, and action approvals) will be added on top of this baseline.

---

## 12. Installation & Operational Modes

### 12.1 Mode 1 – “I already have k3s” (Power Users)

- Provide a **Helm chart** or Kustomize setup:
  - `jarvis-nats`, `jarvis-router`, `jarvis-memory`, `jarvis-operator`, `jarvis-utility`, `jarvis-api`, `jarvis-whisper`, `jarvis-postgres`, `jarvis-vector`, `jarvis-registry`.
- Power users run:
  ```bash
  helm repo add jarvis-os https://...
  helm install jarvis jarvis-os/jarvis
  ```

### 12.2 Mode 2 – “I just have machines” (Most Users / SMBs)

- Provide a simple `install.sh` script that:
  - Installs k3s on the primary node.
  - Joins additional nodes via token (optional step).
  - Deploys the JARVIS stack with sensible defaults.
- Longer term: ship preconfigured images for Talos/Fedora CoreOS that auto‑bootstrap the cluster with JARVIS.

---

## 13. Roadmap

### 13.1 v1 – First Public Open‑Source Release

- Core services deployed via Helm:
  - Router, Whisper, Utility Agents, NATS, Memory Service, Operator, API, Postgres, vector store, registry.
- Agent SDK and base agent image.
- Centralized, tenant‑aware memory with basic schema.
- NATS subject conventions and message formats.
- Hot path + cold path flows working end‑to‑end.
- Basic observability:
  - Logs, metrics, simple watchdog checks.
- Documentation:
  - Architecture overview.
  - Getting started (home‑lab and SMB examples).
  - Sample agents (e.g., “Hello World” and a simple data‑processing agent).

### 13.2 Post‑v1 – Advanced Features

- **Multi‑tenant governance**
  - RBAC, org/tenant scoping, SSO integration.
- **Image commit & GC pipeline**
  - Evaluate agent utility and bake successful behaviors into images.
  - Automated image pruning policies.
- **Cloud offload connector**
  - Seamless offloading to cloud agents using foundation models.
- **NATS JetStream / durable workflows**
  - Reliability for mission‑critical tasks.
- **UI & dashboard**
  - Visual graph of agents, live metrics, logs, and per‑tenant usage.
- **Vertical bundles**
  - Curated agents for common verticals (e.g., helpdesk, note‑taking, simple CRM workflows).

---

## 14. Appendix – Example NATS Subjects

```text
# Ingress
tenant.<tid>.ingress.transcript         # text from Whisper or HTTP
tenant.<tid>.ingress.event              # generic event ingress

# Router output
tenant.<tid>.router.decisions           # optional, for debugging/analytics

# Hot path tasks (fast)
tenant.<tid>.tasks.utility              # request/reply; utility worker queue

# Cold path tasks (spawn)
tenant.<tid>.tasks.spawn                # publish TaskSpec for Operator

# Memory
tenant.<tid>.memory.request             # request/reply for Memory Service

# Broadcast events
tenant.<tid>.events.broadcast           # "stop music", "room empty", etc.
```

This structured architecture gives you a clear path to implement JARVIS as a **local‑first, containerized agent platform** that can serve both home‑lab users and SMBs, while remaining grounded in proven infrastructure (k3s, NATS, Postgres, containers) and leaving room for advanced features like cloud offload and agent image lifecycle management.
