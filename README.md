# ThingsBoard Intelligent Agent Service (TIA)

[![Enterprise Documentation](https://img.shields.io/badge/Documentation-Enterprise-blue.svg)](https://your-docs-link.com)
[![Protocol](https://img.shields.io/badge/Protocol-MCP-green.svg)](https://modelcontextprotocol.io)
[![API Runtime](https://img.shields.io/badge/Runtime-FastAPI-009688.svg)](https://fastapi.tiangolo.com)

## 📋 Executive Summary
ThingsBoard Intelligent Agent (TIA) is an enterprise-grade middleware service that bridges Large Language Models (LLMs) with the ThingsBoard IoT ecosystem. Leveraging the **Model Context Protocol (MCP)**, TIA enables natural language interaction with complex IoT datasets, automated telemetry analysis, and proactive device management through a secure, scalable API layer.

---

## 🏗 Enterprise Architecture

### 1. High-Level System Architecture
The following diagram illustrates the layered approach, highlighting the separation of concerns between the API Gateway, Agent Orchestration, and Downstream Connectivity.

```mermaid
graph TB
    subgraph "External Consumer Layer"
        UI["UI Applications (Web/Mobile)"]
        Postman["Integration Tools"]
    end

    subgraph "API Service Layer (FastAPI / Gateway)"
        Auth["JWT Validator (TB Auth)"]
        SSE["SSE Streamer"]
        SyncAPI["REST Sync API"]
    end

    subgraph "AI Agent Layer (Orchestration)"
        Agent["AI Orchestrator (Ollama / Gemini)"]
        History["Stateful History Manager"]
        ToolRegistry["Tool Registry (50+ Wrappers)"]
    end

    subgraph "Feature Modules (Modular TB Wrappers)"
        direction LR
        TM["Telemetry (tb_telemetry)"]
        DV["Device (tb_device)"]
        AT["Attributes (tb_attributes)"]
        AS["Assets (tb_assets)"]
        CU["Customer (tb_customer)"]
        US["User (tb_user)"]
    end

    subgraph "Infrastructure Layer (MCP Abstraction)"
        MCP_Client["MCP Client (JSON-RPC/SSE)"]
    end

    subgraph "Data & IoT Layer"
        MCP_Server["ThingsBoard MCP Server"]
        TB_Platform["ThingsBoard Platform"]
    end

    UI <--> Auth
    Auth <--> SSE
    Auth <--> SyncAPI
    SSE <--> Agent
    SyncAPI <--> Agent
    Agent <--> ToolRegistry
    Agent <--> History
    
    ToolRegistry --- TM
    ToolRegistry --- DV
    ToolRegistry --- AT
    ToolRegistry --- AS
    ToolRegistry --- CU
    ToolRegistry --- US

    TM & DV & AT & AS & CU & US <--> MCP_Client
    MCP_Client <--> MCP_Server
    MCP_Server <--> TB_Platform
```

### 2. Sequence Flow: Autonomous Tool Execution Loop
TIA employs an autonomous loop where the agent iteratively calls tools until a comprehensive answer is reached.

```mermaid
sequenceDiagram
    participant UI as UI Application
    participant API as API Server (TIA)
    participant Agent as AI Agent (Ollama)
    participant Tool as Modular Toolbox
    participant MCP as MCP Client
    participant TB as ThingsBoard
    
    UI->>API: POST /api/chat (Bearer JWT)
    API->>TB: GET /api/pilti/checkTokenStatus
    TB-->>API: 200 OK (Token Valid)
    
    API->>Agent: ask_stream(question)
    
    loop Autonomous Reasoning Phase
        Agent->>Agent: Analyze Intent & Context
        Agent->>Tool: Invoke Tool (e.g., getDeviceByName)
        Tool->>MCP: call_tool(arguments)
        MCP->>TB: REST/RPC Request
        TB-->>MCP: JSON Response
        MCP-->>Tool: Raw Data
        Tool-->>Agent: Formatted Context
        Agent-->>API: Yield Thinking...
        API-->>UI: SSE (Thought Update)
    end
    
    Agent-->>API: Yield Final Synthesized Answer
    API-->>UI: SSE Message (Final Answer)
    API-->>UI: SSE Event: Done
```

### 3. Data Flow: From IoT to Intelligence
This diagram shows how data from various entities is transformed from raw platform metrics into natural language insights.

```mermaid
graph LR
    subgraph "ThingsBoard Platform"
        direction TB
        subgraph "Entities"
            D["Device"]
            U["User"]
            A["Asset"]
        end
        attr["Fetch Attributes"]
        tele["Fetch Telemetry"]
        
        D & U & A --> attr
        D & U & A --> tele
    end

    subgraph "MCP Bridge"
        S["MCP Server"]
        C["MCP Client"]
    end

    subgraph "Intelligent Agent"
        W["Modular Wrappers"]
        LLM["LLM (Ollama/Gemini)"]
    end

    attr & tele --> S
    S --> C
    C --> W
    W -- "Enriched Context" --> LLM
    LLM -- "Natural Language" --> UserNode((User))
```

---

## 🛡 Security & Authentication
TIA implements a **Zero-Trust Delegation** model. It does not store user credentials. Instead, it delegates authentication to the primary ThingsBoard instance.

- **Authentication Method**: JWT (JSON Web Token) via Bearer Header.
- **Validation**: Every request is validated against the internal `/api/pilti/checkTokenStatus` endpoint.
- **Access Control**: The agent's capabilities are restricted by the permissions associated with the provided JWT token.

---

## 🚀 API Specification

### 1. Streaming Interaction (SSE)
Designed for responsive UIs where the AI's "thought process" and response are shown incrementally.
- **URL**: `/api/chat`
- **Method**: `POST`
- **Auth**: `Authorization: Bearer <JWT>`
- **Request Body**: 
  ```json
  {
    "question": "What is the frequency of Telemetry for device 'Main-Probe'?"
  }
  ```
- **Response**: `text/event-stream` (SSE)
  ```text
  data: {"content": "Thinking..."}
  data: {"content": "The device 'Main-Probe' sends telemetry every 60 seconds."}
  data: [DONE]
  ```

### 2. Standard Synchronous Interaction
Designed for integration with automated systems or simple REST consumers.
- **URL**: `/api/chat/sync`
- **Method**: `POST`
- **Auth**: `Authorization: Bearer <JWT>`
- **Request Body**: 
  ```json
  {
    "question": "Get me the inventory of all sensors."
  }
  ```
- **Response**: `application/json`
  ```json
  {
    "content": "The inventory shows 15 active sensors across 3 zones."
  }
  ```

### 3. Health Check
Used to verify the service status and active AI agent type.
- **URL**: `/api/health`
- **Method**: `GET`
- **Auth**: None
- **Response**: `application/json`
  ```json
  {
    "status": "ok",
    "agent": "ollama"
  }
  ```

---

## 🛠 Feature Modules

| Module | Description | Technical Focus |
| :--- | :--- | :--- |
| **`tb_telemetry`** | Timeseries & Analytics | Accurate 24h windows, client-side aggregation. |
| **`tb_device`** | Device Inventory | Bulk search, info retrieval, connection status. |
| **`tb_attributes`** | Entity Metadata | Shared vs Server attributes management. |
| **`tb_assets`** | Hierarchy Management | Asset relation and grouping navigation. |
| **`tb_user`** | User Management | User profile, role verification, and details. |
| **`auth_service`** | Security Layer | ThingsBoard identity delegation. |

---

## 🔄 IoT Device Lifecycles (Enterprise Ecosystem)
TIA provides specialized handling and LLM-ready context for a diverse range of IoT hardware. The following lifecycles are supported through modular feature wrappers.

### 1. Vital Health Monitoring (ECG & Bio-Probes)
- **ECG Monitor**: Real-time heartbeat amplitude streaming and historical waveform analysis.
- **Heartbeat Probe**: Comprehensive vital tracking (BPM, BP, SpO2) with integrated predictive analytics for 24-72h trends.

### 2. Industrial Environmental Probes
- **Universal Probe**: High-precision tracking of Temperature, Humidity, AQI, and Air Quality (CO, NH3, NO2, O3, PM2.5).
- **WL (Water Level)**: Real-time distance measurement with automated tank volume calculations (Liters/Gallons).
- **Tag Probe**: Ultra-compact temperature sensing for mobile or space-constrained assets.

### 3. Server Infrastructure Monitoring
- **Pilti Server**: Performance tracking for backend nodes, covering CPU load, memory pressure, and Disk I/O.
- **Advanced Inspection**: Integration with the Beszel/Grafana dashboards for system-level analytics.

### 4. Security & Access Control
- **RFID Scanner**: Perimeter security with remote RPC trigger support (`OpenLock`) and access audit logs.
- **Access Cards**: Detailed credential management and historical audit trails for individual cardholders.

### 5. Network & Offline Management
- **Local Config**: Bootstrap provisioning via SoftAP and local HTTP handshake (Port 233) for secure SSID/MacID exchange.

---

## ⚙️ Enterprise Configuration
System configuration is centralized in `config.py`.

```python
# Deployment targets
THINGSBOARD_URL = "https://tb-test.example.com"
MCP_SERVER_URL  = "http://192.168.1.165:8090"

# AI Inference Engine
AGENT_TYPE = "ollama"  # 'ollama' or 'gemini'

# Ollama Config
OLLAMA_BASE_URL = "http://192.168.1.40:11434"
OLLAMA_MODEL = "qwen2.5:7b"

# Gemini Config
GEMINI_API_KEY = "AIzaSy..."
```

---

## 📦 Deployment Guide

### Industrial Deployment (Docker/Linux)
1. **Clone & Environment**:
   ```bash
   git clone <repo-url>
   cd agent
   ```
2. **Runtime Setup**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Run Production Server**:
   ```bash
   uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 4
   ```

---

*TIA is maintained by the Advanced AI Solutions Team. For enterprise support, contact your system administrator.*
