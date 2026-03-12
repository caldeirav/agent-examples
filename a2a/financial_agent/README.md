# Financial Agent

An AI-powered financial analysis agent built with **LangGraph**, **MCP tools** (Yahoo Finance), and **MLflow** for observability. Answers stock market questions using real-time data via the yfinance library.

## Features

- **Natural Language Interface** – Ask questions about stocks, fundamentals, and market data
- **Yahoo Finance Tools** – PE ratio, market cap, dividends, historical prices, financial statements, news
- **LangGraph Workflow** – Assistant + tool-calling loop
- **MCP Integration** – Connects to finance MCP server via streamable HTTP
- **MLflow Tracing** – Agent execution traces for debugging and analysis
- **Extensible Use Cases** – Built-in test scenarios you can extend

## Architecture

```
User Query → Assistant (LLM) → [Tool calls?] → Finance MCP Tools → Assistant → Response
                                    ↑_______________|
```

- **Assistant**: LangChain ChatOpenAI (LM Studio) with tool binding
- **Tools**: 4 Yahoo Finance tools from MCP (`get_stock_fundamentals`, `get_historical_prices`, `get_financial_statements`, `get_company_news`)

## Prerequisites

- **Python 3.11+** and **uv**
- **LM Studio** – Local LLM serving with OpenAI-compatible API
- **Model**: Load `qwen/qwen3-30b-a3b-2507` (or Qwen3-30B-A3B-Instruct) in LM Studio
- Optional: **Podman** and **kind** for containerized/Kubernetes deployment

---

## End-to-End Local Setup

### Step 1: LM Studio (Model Serving)

1. Download [LM Studio](https://lmstudio.ai/)
2. Search for and download `qwen/qwen3-30b-a3b-2507` or `Qwen3-30B-A3B-Instruct`
3. Open **Developer** tab → **Start Server** (default: `http://localhost:1234/v1`)
4. Load the model so the server can serve requests

**Verify:**
```bash
curl http://localhost:1234/v1/models
```

### Step 2: Finance MCP Tool

```bash
cd agent-examples/mcp/finance_tool
uv lock
uv run finance_tool.py
```

Runs on `http://0.0.0.0:8000` with streamable-http MCP transport.

### Step 3: Financial Agent

**New terminal** (keep the finance tool running):

```bash
cd agent-examples/a2a/financial_agent
uv lock
export MCP_URL=http://localhost:8000/mcp
export LLM_API_BASE=http://localhost:1234/v1
export LLM_MODEL=qwen/qwen3-30b-a3b-2507   # Use the model name shown in LM Studio
# Use port 8001 for local dev (finance tool uses 8000)
PORT=8001 uv run server
```

### Step 4: Environment File (Optional)

Copy and edit the example env:

```bash
cp .env.lmstudio .env
# Edit .env if needed (LLM_MODEL must match LM Studio's loaded model name)
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_BASE` | `http://localhost:1234/v1` | LM Studio OpenAI-compatible endpoint |
| `LLM_MODEL` | `qwen/qwen3-30b-a3b-2507` | Model name (match LM Studio) |
| `LLM_API_KEY` | `not-needed` | API key (LM Studio local needs none) |
| `MCP_URL` | `http://localhost:8000/mcp` | Finance MCP server URL |
| `MCP_TRANSPORT` | `streamable_http` | MCP transport protocol |
| `PORT` | `8000` | Agent HTTP port (use 8001 for local dev with finance tool on 8000) |
| `MLFLOW_TRACKING_URI` | `./mlruns` | MLflow tracking directory |
| `MLFLOW_EXPERIMENT_NAME` | `financial-agent` | MLflow experiment name |

---

## Running the Agent

### A2A Server Mode

```bash
uv run server
```

Starts the A2A agent server. Interact via A2A JSON-RPC (e.g. from Kagenti or a test client).

### Direct Test (No A2A Server)

Run the graph directly for quick local testing:

```bash
uv run test-agent
```

Runs all built-in use cases. Options:

```bash
# Single query
uv run test-agent --query "What is AAPL's PE ratio?"

# Quiet mode (only final answers)
uv run test-agent --quiet
```

---

## Use Cases

Built-in test scenarios in `src/financial_agent/test.py`:

| # | Query |
|---|-------|
| 1 | What is AAPL's PE ratio? |
| 2 | Compare the market caps of Microsoft and Apple |
| 3 | What's the dividend yield for NVDA? |
| 4 | Show me TSLA price performance over the past month |
| 5 | What's the latest news about Meta? |
| 6 | Get the key financial metrics for GOOGL |

### Extending Use Cases

Edit `USE_CASES` in `src/financial_agent/test.py`:

```python
USE_CASES = [
    "What is AAPL's PE ratio?",
    "Compare the market caps of Microsoft and Apple",
    # Add your own:
    "What is the free cash flow for AMZN?",
    "How has JPM stock performed over the past year?",
]
```

Or pass any query via CLI:

```bash
uv run test-agent -q "Your custom financial question here"
```

---

## MLflow Tracing

Agent runs are traced automatically when MLflow is configured.

**View traces:**
```bash
cd a2a/financial_agent
mlflow ui --backend-store-uri ./mlruns
```

Open http://localhost:5000 to see traces, spans, and tool calls.

---

## Kagenti Setup with Podman and kind

End-to-end deployment of the Financial Agent and Finance MCP tool in Kagenti, using a local **kind** cluster and **Podman** for building container images.

### Prerequisites

- **Podman** – Container runtime (e.g. `brew install podman` on macOS)
- **kind** – Kubernetes in Docker (`go install sigs.k8s.io/kind@latest` or `brew install kind`)
- **kubectl** – Kubernetes CLI
- **Kagenti** – Deployed in the kind cluster ([Kagenti Developer's Guide](https://github.com/kagenti/kagenti/blob/main/docs/dev-guide.md))
- **LM Studio** – Running on the host with model loaded (port 1234)

### Step 1: Create kind cluster

```bash
kind create cluster --name financial-agent-demo
kubectl cluster-info --context kind-financial-agent-demo
```

### Step 2: Build images with Podman

From the `agent-examples` root:

```bash
# Finance MCP tool
cd mcp/finance_tool
podman build -t finance-tool:latest .
cd ../..

# Financial agent
cd a2a/financial_agent
podman build -t financial-agent:latest .
cd ../..
```

### Step 3: Load images into kind

`kind load` expects images from the Docker daemon. With Podman, save to a tar and load from archive:

```bash
# Save Podman images to tar
podman save -o /tmp/finance-tool.tar finance-tool:latest
podman save -o /tmp/financial-agent.tar financial-agent:latest

# Load into kind cluster
kind load image-archive /tmp/finance-tool.tar --name financial-agent-demo
kind load image-archive /tmp/financial-agent.tar --name financial-agent-demo

# Verify
docker images  # if Docker is available, or: kind get nodes then exec into node
```

### Step 4: Configure environment variable sets

Ensure `sample-environments.yaml` (or your Kagenti ConfigMap) includes `mcp-finance` and `lmstudio`:

```yaml
# Already in sample-environments.yaml:
mcp-finance: |
  [
    {"name": "MCP_URL", "value": "http://finance-tool:8000/mcp"}
  ]

# Add lmstudio for LM Studio (local host):
lmstudio: |
  [
    {"name": "LLM_API_BASE", "value": "http://host.docker.internal:1234/v1"},
    {"name": "LLM_MODEL", "value": "qwen/qwen3-30b-a3b-2507"},
    {"name": "LLM_API_KEY", "value": "not-needed"}
  ]
```

Apply to your namespace (e.g. `team1`):

```bash
kubectl apply -n team1 -f sample-environments.yaml
# Or merge into existing ConfigMap - see Kagenti docs
```

**Linux note:** `host.docker.internal` may not resolve from kind on Linux. Use your host IP (e.g. `192.168.1.100:1234`) or configure extra hosts in the kind cluster config.

### Step 5: Import Finance MCP tool in Kagenti

1. Open the Kagenti UI (e.g. `http://kagenti-ui.localtest.me:8080` or your configured URL)
2. Go to **Import New Tool**
3. Configure:
   - **Namespace**: `team1` (or your namespace)
   - **Source Repository URL**: `https://github.com/kagenti/agent-examples`
   - **Branch/Tag**: `main`
   - **Source Subfolder**: `mcp/finance_tool`
   - **Environment Variable Sets**: *(none required – no API keys)*
   - **Target Port**: `8000`
4. Click **Build & Deploy New Tool**
5. Wait for the build and deployment to complete

Verify the tool is running:

```bash
kubectl get pods -n team1 -l app=finance-tool
kubectl logs -n team1 deployment/finance-tool -f
```

### Step 6: Import Financial Agent in Kagenti

1. Go to **Import New Agent**
2. Fill in:
   - **Namespace**: `team1`
   - **Agent Source Repository URL**: `https://github.com/kagenti/agent-examples`
   - **Git Branch or Tag**: `main`
   - **Protocol**: `a2a`
   - **Source Subfolder**: `a2a/financial_agent`
   - **Environment Variable Sets**: Select **`lmstudio`** and **`mcp-finance`**
3. Click **Build & Deploy New Agent**
4. Wait for the build (2–5 minutes)
5. Agent appears in the Agent Catalog

### Step 7: LM Studio must be running

Before testing, ensure LM Studio is serving on the host:

- Developer tab → **Start Server**
- Model loaded: `qwen/qwen3-30b-a3b-2507` (or the name you use in `LLM_MODEL`)

From the host:

```bash
curl http://localhost:1234/v1/models
```

### Step 8: Test the agent

**Option A – Kagenti UI**

Use the Agent Catalog / chat interface to send a message such as:

```
What is AAPL's PE ratio?
```

**Option B – Port-forward and A2A client**

```bash
# Port-forward agent service
kubectl port-forward -n team1 svc/financial-agent 8001:8000

# Use test_agent.py or any A2A client against http://localhost:8001
```

### Troubleshooting Kagenti deployment

| Issue | Check |
|-------|-------|
| Agent can't reach MCP | `kubectl get svc -n team1` – ensure `finance-tool` service exists; verify `MCP_URL` |
| Agent can't reach LM Studio | Ensure LM Studio is running; on Linux, replace `host.docker.internal` with host IP |
| Build fails | Check build logs in Kagenti; verify `pyproject.toml` and Dockerfile paths |
| Image not found | Re-run `kind load image-archive` with correct cluster name |

---

## Deployment in Kagenti (Summary)

- **Tool**: Import via **Import New Tool** → subfolder `mcp/finance_tool`, env `mcp-finance` (optional)
- **Agent**: Import via **Import New Agent** → subfolder `a2a/financial_agent`, envs `lmstudio` + `mcp-finance`
- **LLM**: LM Studio on host at `http://localhost:1234/v1` (use `host.docker.internal` in Kubernetes)

---

## Troubleshooting

### Agent can't connect to MCP server

- Check finance tool is running: `curl http://localhost:8000/mcp`
- Ensure `MCP_URL` is correct (include `/mcp` path)

### LLM connection errors

- Confirm LM Studio server is running: `curl http://localhost:1234/v1/models`
- Ensure `LLM_MODEL` matches the loaded model name in LM Studio
- On Mac/Windows with kind, use `host.docker.internal` for `LLM_API_BASE`

### Agent responds but doesn't use tools

- Check MCP tools are registered: logs should show `MCP tools available: [get_stock_fundamentals, ...]`
- Use a model that supports tool calling (e.g. Qwen3-30B-A3B)
- Verify the system prompt and tool descriptions are clear

### Port conflicts

- Finance tool: 8000
- Agent: 8001 (via `PORT=8001`)

---

## Project Structure

```
financial_agent/
├── src/financial_agent/
│   ├── agent.py       # A2A server entry point
│   ├── graph.py       # LangGraph workflow
│   ├── configuration.py
│   ├── prompts.py
│   ├── observability.py  # MLflow setup
│   └── test.py        # Test runner + USE_CASES
├── pyproject.toml
├── Dockerfile
├── .env.lmstudio
└── README.md
```

## Related

- [Finance MCP Tool](../../mcp/finance_tool/) – Yahoo Finance MCP server
- [Reservation Service](../reservation_service/) – Similar agent pattern
- [Generic Agent](../generic_agent/) – Multi-MCP agent example

## License

Apache License 2.0
