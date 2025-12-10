# HelixOS Prerequisites & Installation Guide

A comprehensive guide to running HelixOS on Windows, Linux, and macOS.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation by Platform](#installation-by-platform)
   - [macOS](#macos)
   - [Linux (Ubuntu/Debian)](#linux-ubuntudebian)
   - [Linux (Fedora/RHEL)](#linux-fedorarhel)
   - [Windows](#windows)
3. [Memory System Dependencies](#memory-system-dependencies)
4. [Known Limitations](#known-limitations)
5. [Troubleshooting](#troubleshooting)

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4 cores | 8+ cores |
| **RAM** | 8 GB | 16+ GB |
| **Storage** | 10 GB free | 50+ GB (for Docker images) |
| **Python** | 3.10+ | 3.11 or 3.12 |
| **Docker** | 20.10+ | Latest |
| **Go** | 1.21+ | Latest |

### Required Software

- **Python 3.10+** - Core runtime
- **Docker** - Container runtime for sub-agents
- **Go 1.21+** - Sub-agent compilation
- **Ollama** - Local LLM inference (optional but recommended)
- **Git** - Version control

---

## Installation by Platform

### macOS

#### 1. Install Homebrew (if not installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install Dependencies
```bash
# Core dependencies
brew install python@3.12 go git

# Docker (choose one)
brew install --cask docker          # Docker Desktop
# OR
brew install --cask orbstack        # Lighter alternative (recommended)

# Ollama for local LLMs
brew install ollama
```

#### 3. Clone and Setup
```bash
git clone https://github.com/r4vi1/helix-os.git
cd helix-os

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r mvp/requirements.txt

# Install memory system dependencies (optional but recommended)
pip install sentence-transformers keyring
```

#### 4. Start Services
```bash
# Start Docker (if using Docker Desktop, open the app)
# OR for OrbStack:
orbctl start

# Start Ollama and pull a model
ollama serve &
ollama pull gemma3:4b  # or deepseek-r1:8b
```

---

### Linux (Ubuntu/Debian)

#### 1. Update System
```bash
sudo apt update && sudo apt upgrade -y
```

#### 2. Install Dependencies
```bash
# Core dependencies
sudo apt install -y python3 python3-pip python3-venv golang-go git

# Docker
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
# Log out and back in for group changes

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

#### 3. Clone and Setup
```bash
git clone https://github.com/r4vi1/helix-os.git
cd helix-os

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r mvp/requirements.txt

# Install memory system dependencies
pip install sentence-transformers keyring
```

#### 4. Start Services
```bash
# Ollama
ollama serve &
ollama pull gemma3:4b
```

---

### Linux (Fedora/RHEL)

#### 1. Install Dependencies
```bash
# Core dependencies
sudo dnf install -y python3 python3-pip golang git

# Docker
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

#### 2. Clone and Setup
```bash
git clone https://github.com/r4vi1/helix-os.git
cd helix-os

python3 -m venv venv
source venv/bin/activate
pip install -r mvp/requirements.txt
pip install sentence-transformers keyring
```

---

### Windows

#### 1. Install Package Manager (Chocolatey or winget)

**Using winget (Windows 11):**
```powershell
# Python
winget install Python.Python.3.12

# Go
winget install GoLang.Go

# Git
winget install Git.Git

# Docker Desktop
winget install Docker.DockerDesktop
```

**Using Chocolatey:**
```powershell
# Install Chocolatey first (run as Administrator)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install dependencies
choco install python312 golang git docker-desktop -y
```

#### 2. Install Ollama
Download from: https://ollama.com/download/windows

#### 3. Clone and Setup
```powershell
git clone https://github.com/r4vi1/helix-os.git
cd helix-os

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r mvp/requirements.txt
pip install sentence-transformers keyring
```

#### 4. Start Services
```powershell
# Start Docker Desktop (from Start Menu or)
& "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Start Ollama and pull model
ollama serve
ollama pull gemma3:4b
```

---

## Memory System Dependencies

The memory system provides learning and context for the main agent. Here are the optional dependencies:

| Package | Purpose | Required? |
|---------|---------|-----------|
| `sentence-transformers` | Semantic embeddings for memory search | Recommended |
| `keyring` | OS keychain for encryption keys | Recommended |
| `sqlcipher3` | Database encryption at rest | Optional (see limitations) |

### Install Memory Dependencies
```bash
pip install sentence-transformers keyring
```

### Without Memory Dependencies
The system will still work but with reduced functionality:
- **Without sentence-transformers**: Uses hash-based fallback (less accurate semantic search)
- **Without keyring**: Uses environment variable or ephemeral key
- **Without sqlcipher3**: Uses unencrypted SQLite (data still local)

---

## Known Limitations

### SQLCipher Encryption (Python 3.13)

> ⚠️ **SQLCipher Python bindings are not yet compatible with Python 3.13**

The `sqlcipher3` package uses deprecated Python C APIs that were removed in Python 3.13. 

**Workarounds:**
1. **Use Python 3.12** - SQLCipher works fine with Python 3.12
2. **Proceed without encryption** - Data is still stored locally, just not encrypted

**To use Python 3.12 on macOS:**
```bash
brew install python@3.12
python3.12 -m venv venv
source venv/bin/activate
pip install -r mvp/requirements.txt
pip install sentence-transformers keyring sqlcipher3
```

### Platform-Specific Notes

| Platform | Notes |
|----------|-------|
| **macOS (Apple Silicon)** | Fully supported. Use OrbStack for lighter Docker experience. |
| **macOS (Intel)** | Fully supported. |
| **Linux** | Fully supported. Ensure user is in `docker` group. |
| **Windows** | Requires WSL2 for Docker. Some Whisper features may have latency. |
| **Raspberry Pi** | Supported as worker node. Use 64-bit OS. Limited for main agent. |

---

## Troubleshooting

### Docker Issues

**"Cannot connect to Docker daemon"**
```bash
# Linux
sudo systemctl start docker

# macOS - ensure Docker Desktop or OrbStack is running
```

**"Permission denied" on Docker**
```bash
sudo usermod -aG docker $USER
# Then log out and back in
```

### Ollama Issues

**"Model not found"**
```bash
ollama list  # Check available models
ollama pull gemma3:4b  # Pull the model
```

**"Connection refused"**
```bash
ollama serve  # Start the Ollama server
```

### Python Issues

**"externally-managed-environment"**
```bash
# Use a virtual environment
python3 -m venv venv
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
```

### Memory System Issues

**"sentence-transformers not installed"**
```bash
pip install sentence-transformers
```

**"sqlcipher3 not installed" (Python 3.13)**
- This is expected. The system falls back to unencrypted SQLite.
- Use Python 3.12 if encryption is required.

---

## Verifying Installation

Run the following to verify everything is set up correctly:

```bash
# Activate virtual environment
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows

# Check Python
python --version  # Should be 3.10+

# Check Docker
docker --version
docker run hello-world

# Check Go
go version

# Check Ollama
ollama list

# Run HelixOS memory tests
python memory/tests/test_memory.py

# Run MVP (requires microphone)
python mvp/mvp_runner.py
```

---

## Quick Start Summary

```bash
# 1. Clone
git clone https://github.com/r4vi1/helix-os.git
cd helix-os

# 2. Setup Python
python3 -m venv venv
source venv/bin/activate
pip install -r mvp/requirements.txt
pip install sentence-transformers keyring

# 3. Start Ollama
ollama serve &
ollama pull gemma3:4b

# 4. Run
python mvp/mvp_runner.py
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HELIX_MODEL` | Override LLM model | Auto-detected |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `GEMINI_API_KEY` | Google Gemini API key | None |
| `GOOGLE_SEARCH_API_KEY` | Google Search API key | None |
| `HELIX_MEMORY_DB` | Memory database path | `~/.helix/memory.db` |
| `HELIX_MEMORY_KEY` | Encryption key (fallback) | Auto-generated |
