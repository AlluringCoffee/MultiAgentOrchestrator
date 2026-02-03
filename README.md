# Multi-Agent Orchestrator

[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg)](https://opensource.org/licenses/ISC)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

**Multi-Agent Orchestrator** is a premium visual workflow designer and execution engine for building complex multi-agent LLM systems. It provides a drag-and-drop interface to orchestrate autonomous agents, auditors, routers, and system tools into seamless, intelligent pipelines.

![Multi-Agent Orchestrator Hero](/assets/final_ui_audit_1770132491281.webp)

---

## 🚀 Key Features

* **Premium Visual Canvas**: A node-based editor with smooth animations, celestial backgrounds, and intuitive drag-and-drop orchestration.
* **Multi-LLM Native**: Native support for **Ollama**, **Groq**, and **Google AI (Gemini)** with easy provider switching.
* **Specialized Agent Roles**:
  * **Autonomous Agents**: Goal-oriented LLM handlers.
  * **Auditors & Directors**: Nodes for content validation, approval loops, and human-in-the-loop intervention.
  * **Routers**: Intelligent traffic control to branch workflows based on intent.
  * **Utilities**: Reroute nodes, groups, and global blackboard state management.
* **"God Mode" Developer Tools**: Agents can interact directly with the system via integrated CLI, Git, and HuggingFace tools.
* **Real-time Live Stream**: Watch agents' "Thought Streams" and system logs in real-time via WebSockets.
* **Production Ready**: Export workflows to standalone Python scripts or deploy directly to Docker containers.

---

## 🛠️ How It Works

### The Architecture

Multi-Agent Orchestrator uses a **Directed Acyclic Graph (DAG)** approach (with optional feedback loops) to manage agent communication.

1. **Nodes**: Represent specific actions (LLM Inference, Tool Execution, Approval).
2. **Edges**: Define the flow of data and control. Specialized **Feedback Edges** allow for iterative refinement.
3. **Blackboard**: A global shared state that all nodes can read from and write to, enabling complex multi-step reasoning.
4. **Traffic Controller**: Manages concurrency and agent rate limits to prevent provider exhaustion.

### Example Workflow: Narrative Generation

To represent what's happening under the hood, consider this common flow:

1. **Input**: "Write a cyberpunk short story about a neon-lit city."
2. **Director Node**: Receives the prompt and creates a "Session" on the blackboard.
3. **Agent (Architect)**: Drafts the world-building details (neon districts, factions).
4. **Agent (Narrator)**: Writes the story based on the Architect's draft.
5. **Critic Node**: Iterates with the Narrator until the quality threshold is met.
6. **Auditor**: Performs a final check for safety and consistency.
7. **Output**: Saves the final story to the `exports/` folder.

You can load this exact pattern using the `enterprise_studio_v11_template.json` from the `workflows` folder.

---

## ⚙️ Installation

### Prerequisites

* Python 3.9+
* Node.js & npm (for front-end dependencies)

### Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/AlluringCoffee/MultiAgentOrchestrator.git
   cd MultiAgentOrchestrator
   ```

2. **Install Python backend dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Install Front-end dependencies**:

   ```bash
   npm install
   ```

4. **Configure Environment**:
   Copy the example environment file and add your API keys.

   ```bash
   cp .env.example .env
   ```

---

## 🚀 Quickstart

Start the server using the provided batch file or directly with Python:

```bash
python server.py
```

Open [http://localhost:8000](http://localhost:8000) to access the Visual Designer.

---

## 🎨 Visual Designer

![Providers Modal](/assets/providers_modal_1770136042129.png)

The designer allows you to:

* **Search & Filter** the agent palette.
* **Tidy** your layout with one click using the auto-layout engine.
* **Fit View** to instantly center your complex graphs.
* **Live Debug**: Open the "Live Execution Logs" to see the engine in action.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **ISC License**. See `LICENSE` for more information.
