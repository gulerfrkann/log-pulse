# LogPulse

LogPulse is an autonomous DevOps and AI-driven system management agent designed for real-time log monitoring, root cause analysis, and automated self-healing actions. Built with Go, RabbitMQ, Python, Docker SDK, and Google Gemini API.

---

##  Architecture & Workflow

1. **Log Producer (Go)**: Simulates microservice log generation (both normal operations and anomalous errors) and publishes them to a message broker.
2. **Message Broker (RabbitMQ)**: Handles reliable queueing and fair dispatch of system logs.
3. **AI Consumer & Agent (Python)**: Consumes logs from RabbitMQ, evaluates system metrics (CPU/Memory), and interfaces with the Gemini API when anomalies occur.
4. **Autonomous Self-Healing (Docker SDK)**: Automatically triggers container recovery actions (such as restarting degraded or crashed services) based on real-time AI diagnosis.

---

##  Tech Stack

* **Language (Producer)**: Go
* **Language (Consumer/AI Agent)**: Python
* **Message Broker**: RabbitMQ
* **Container Orchestration**: Docker & Docker SDK for Python
* **Artificial Intelligence**: Google Gemini API (`gemini-3.5-flash`)
* **Environment Management**: `python-dotenv`, `pika`

---

##  Getting Started

### Prerequisites

* Go (1.18+)
* Python (3.9+)
* Docker & Docker Compose
* Gemini API Key

### 1. Clone the Repository

```bash
git clone [https://github.com/gulerfrkann/log-pulse.git](https://github.com/gulerfrkann/log-pulse.git)
cd log-pulse