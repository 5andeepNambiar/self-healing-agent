# 🤖 Autonomous Self-Healing Code Review Agent

An autonomous, cyclical AI engineering agent built with **LangGraph**, **Gemini 3.8 Flash**, **Langfuse**, and **GitPython**.

When test suites fail, the agent intercepts the test execution stack, dynamically identifies root causes across repository files, applies deterministic surgical patches using **Pydantic structured schemas**, and cuts atomic Git commits upon verified test passage.

---

## 🏗 Architecture & Workflow

```mermaid
flowchart TD
    Start([Run Agent]) --> RunTests[1. Test Execution Node\nRun pytest across repository]
    RunTests --> CheckPass{Tests Pass?}
    
    CheckPass -- Yes --> GitCommit[3. Git Commit Node\nStage diff & commit: 'fix(agent): ...']
    GitCommit --> End([🎉 Done: Green Build])
    
    CheckPass -- No --> CheckRetries{Attempts < 3?}
    CheckRetries -- No --> FailEnd([⚠️ Max Retries Reached])
    
    CheckRetries -- Yes --> TracebackParser[Extract files & AST context from traceback]
    TracebackParser --> LLMNode[2. Surgical Patch Node (Gemini)\nGenerate exact search & replace diff]
    LLMNode --> ApplyPatch[Apply patch to target file]
    ApplyPatch --> RunTests
```

---

## ✨ Key Capabilities

- **Stateful Cyclic Loops (LangGraph):** Employs directed acyclic and cyclic graphs to manage agent state, conditional edges, and bounded retry ceilings.
- **Dynamic Multi-File Discovery:** Resolves cross-file import dependencies and stack trace line numbers without hardcoded targets.
- **Surgical Diff Patching:** Uses strict Pydantic schemas to output exact `search_block` and `replace_block` pairs, avoiding full-file hallucinations or code corruption.
- **Production Observability (Langfuse):** Complete telemetry tracing of every LLM prompt, token budget, latency waterfall, and dollar cost per healing session.
- **Automated Version Control (GitPython):** Generates conventional commit messages and commits changes to Git automatically once all tests pass.

---

## 🚀 Quickstart

### 1. Clone & Set Up Environment
```bash
git clone <your-repo-url>
cd self-healing-agent

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy the template and fill in your keys:
```bash
cp .env.example .env
```
Edit `.env`:
```ini
GEMINI_API_KEY=your_key_here
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 3. Run the Agent
```bash
python agent.py
```

---

## 📊 Observability with Langfuse
Every run streams full graph telemetry to Langfuse:
- Input / Output token counts
- Latency per node
- Exact prompt inputs and structured outputs
- Cumulative cost tracking

---

## 🛠 Tech Stack
- **Agent Orchestration:** LangGraph
- **Frontier LLM:** Google Gemini 3.8 Flash (`langchain-google-genai`)
- **Data Validation & Schemas:** Pydantic v2
- **Observability:** Langfuse
- **VCS Integration:** GitPython
- **Test Runner:** Pytest
