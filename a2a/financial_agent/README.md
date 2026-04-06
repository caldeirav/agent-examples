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
- Optional: **Kagenti on kind** – install the platform with the [kagenti Ansible installer](https://github.com/kagenti/kagenti/blob/main/deployments/ansible/README.md), then follow [Kagenti setup with Ansible installer on kind](#kagenti-setup-with-ansible-installer-on-kind) below

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

### Step 3: Configuration (defaults vs env files)

Settings are loaded by `Configuration` in `src/financial_agent/configuration.py` using [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). **Precedence (highest wins):**

1. **Shell / process environment variables** (e.g. `export PORT=9000`)
2. **`.env`** in the project directory (same folder as `pyproject.toml`)
3. **`.env.lmstudio`** (checked-in template; loaded if present)
4. **In-code defaults** (see table below)

Dotenv files are only read from the **current working directory** when you start the app—run `uv run server` from `a2a/financial_agent/` so `.env.lmstudio` is found.

The repo includes **`.env.lmstudio`** with a typical LM Studio + local finance-tool layout (including **`PORT=8001`** so the agent does not bind to 8000 while the finance MCP tool uses it). You do **not** need to copy it to `.env` unless you want overrides.

| Setting | In-code default | `.env.lmstudio` |
|---------|-----------------|-----------------|
| `MCP_URL` | `http://localhost:8000/mcp` | same |
| `LLM_API_BASE` | `http://localhost:1234/v1` | same |
| `LLM_MODEL` | `qwen/qwen3-30b-a3b-2507` | same (change if LM Studio shows a different id) |
| `PORT` | `8000` | `8001` (recommended when finance tool is on 8000) |

**Optional `.env`** — add only for secrets or overrides (not committed). Same keys as `.env.lmstudio`; `.env` wins over `.env.lmstudio` when both exist.

```bash
cd agent-examples/a2a/financial_agent
# Example: create .env with only overrides
echo 'LLM_MODEL=your-exact-lm-studio-model-id' >> .env
```

### Step 4: Financial Agent

**New terminal** (keep LM Studio and the finance tool running):

```bash
cd agent-examples/a2a/financial_agent
uv lock
uv run server
```

With **`.env.lmstudio`** in the tree, **`PORT=8001`** applies automatically. If you remove that file or want another port, use `PORT=8002 uv run server` or set `PORT` in `.env`.

If your LM Studio model id differs from the default, set **`LLM_MODEL`** in `.env.lmstudio`, in `.env`, or export it in the shell.

---

## Configuration reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_BASE` | `http://localhost:1234/v1` | LM Studio OpenAI-compatible endpoint |
| `LLM_MODEL` | `qwen/qwen3-30b-a3b-2507` | Model name (must match LM Studio) |
| `LLM_API_KEY` | `not-needed` | API key (LM Studio local needs none) |
| `MCP_URL` | `http://localhost:8000/mcp` | Finance MCP server URL |
| `MCP_TRANSPORT` | `streamable_http` | MCP transport protocol |
| `PORT` | `8000` | Agent HTTP port (`.env.lmstudio` sets `8001` when sharing the host with the finance tool on 8000) |
| `MLFLOW_TRACKING_URI` | `sqlite:///./mlflow.db` | MLflow backend (SQLite file in cwd) |
| `MLFLOW_LANGCHAIN_LOG_TRACES` | `true` | Set `false` to disable LangChain trace autolog (e.g. avoid async ContextVar noise on A2A server) |
| `MLFLOW_EXPERIMENT_NAME` | `financial-agent` | MLflow experiment name |

### Console scripts (`pyproject.toml`)

| Command | Entry point | Purpose |
|---------|-------------|---------|
| `uv run server` | `financial_agent.agent:run` | A2A HTTP server (uvicorn) |
| `uv run financial-agent-test` | `financial_agent.test:main` | Run graph tests / `USE_CASES` |
| `uv run test-agent` | same as `financial-agent-test` | Short alias |

The **distribution name** in `pyproject.toml` is `financial-agent`; only the script names above are valid `uv run …` targets unless you add more under `[project.scripts]`.

---

## Running the Agent

### A2A Server Mode

From `a2a/financial_agent/`:

```bash
uv run server
```

Starts the A2A agent server. Interact via A2A JSON-RPC (e.g. from Kagenti or a test client). **Listen port** comes from `PORT` (see configuration above).

### Direct test (no A2A server)

Run the LangGraph directly (still requires LM Studio + finance MCP tool). From `a2a/financial_agent/`:

```bash
uv run financial-agent-test
```

Runs all built-in use cases. (This is the console script from `[project.scripts]`; the distribution is named `financial-agent`, not a runnable command by itself. Short alias: `uv run test-agent`.)

Options:

```bash
# Single query
uv run financial-agent-test --query "What is AAPL's PE ratio?"

# Quiet mode (only final answers)
uv run financial-agent-test --quiet
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
uv run financial-agent-test -q "Your custom financial question here"
```

---

## MLflow tracing

The agent calls `mlflow.langchain.autolog()` at startup (`agent.py` and the `financial-agent-test` CLI). That integration records **Traces** for LangChain/LangGraph LLM and tool spans.

**Why the `langchain` package is required:** MLflow’s autolog path imports the **`langchain`** distribution for version checks before patching callbacks. This project uses `langchain-core` and friends directly; **`langchain`** is still listed in `pyproject.toml` so autolog can initialize. Without it, autolog fails and the UI shows **“No traces recorded”**.

**Default tracking URI** is **`sqlite:///./mlflow.db`** (under `a2a/financial_agent/`), which avoids MLflow’s **FutureWarning** about the deprecated `./mlruns` file store.

**View traces** (URI and experiment must match where the agent wrote data):

```bash
cd a2a/financial_agent
uv run mlflow ui --backend-store-uri sqlite:///$(pwd)/mlflow.db
```

On shells without `$(pwd)`, use an absolute path, e.g. `sqlite:////Users/you/Code/agent-examples/a2a/financial_agent/mlflow.db`.

In the UI:

1. Open **Experiments** and select **`financial-agent`** (or whatever you set in `MLFLOW_EXPERIMENT_NAME`).
2. Open the **Traces** tab for that experiment.
3. Generate load: send a request through the A2A server or run `uv run financial-agent-test -q "What is AAPL's PE ratio?"` while LM Studio and the finance MCP tool are up.

**Warnings you might see**

| Message | What to do |
|---------|------------|
| `FutureWarning: The filesystem tracking backend (e.g., './mlruns') is deprecated` | Use **`MLFLOW_TRACKING_URI=sqlite:///./mlflow.db`** (default in `.env.lmstudio`) or ignore if you intentionally use `./mlruns`. |
| `ContextVar ... was created in a different Context` from `mlflow.utils.autologging_utils` | Known **MLflow** + async LangGraph issue ([mlflow#22088](https://github.com/mlflow/mlflow/issues/22088)). **`setup_mlflow_tracing()` installs a logging filter** that drops only these messages so the console stays clean; trace autolog stays on. To **disable trace collection** entirely, set **`MLFLOW_LANGCHAIN_LOG_TRACES=false`**. |

**If you still see no traces**

- Confirm logs include `MLflow LangChain autolog enabled` (not the autolog **failed** warning).
- Run `mlflow ui` with the **same** `--backend-store-uri` as `MLFLOW_TRACKING_URI`.
- Tracing hooks fire on **LangChain** invocations inside the graph; ensure at least one successful run completed after autolog was enabled.

---

## Kagenti setup with Ansible installer on kind

Deploy the **Financial Agent** and **Finance MCP tool** on a local **kind** cluster running **Kagenti**. The supported way to install Kagenti on kind is the **Ansible installer** in the [kagenti](https://github.com/kagenti/kagenti) repository (not a hand-rolled `kind create` unless you know exactly what you are doing).

Installer reference: [`deployments/ansible/README.md`](https://github.com/kagenti/kagenti/blob/main/deployments/ansible/README.md) and [`deployments/ansible/run-install.sh`](https://github.com/kagenti/kagenti/blob/main/deployments/ansible/run-install.sh).

### Prerequisites

- **kagenti** repo cloned and Ansible collections installed per [deployments/ansible/README.md](https://github.com/kagenti/kagenti/blob/main/deployments/ansible/README.md) (`helm` **v3.x**, `kubectl`, `ansible-galaxy collection install -r collections-reqs.yml`, etc.)
- **kind** – `brew install kind` or `go install sigs.k8s.io/kind@latest`
- **Podman or Docker** – Playbook variable `container_engine` must match how you run kind (see below)
- **LM Studio** – On the host, model loaded (e.g. port 1234)

### Step 1: Install Kagenti with the Ansible installer

From your **kagenti** repository (paths are relative to that repo):

**Docker (default in `default_values.yaml`):**

```bash
cd /path/to/kagenti
deployments/ansible/run-install.sh --env dev
```

**Podman** – use the same provider for **all** `kind` commands on this machine. The installer sets `KIND_EXPERIMENTAL_PROVIDER=podman` on `kind` steps when `container_engine` is `podman`:

```bash
cd /path/to/kagenti
export KIND_EXPERIMENTAL_PROVIDER=podman
deployments/ansible/run-install.sh --env dev --extra-vars '{"container_engine": "podman"}'
```

Optional: `--preload` preloads images listed in kagenti’s `kind/preload-images.txt` (longer install); it does **not** replace the agent-examples images below unless you add them there.

When the playbook finishes:

- Default kind cluster name is **`kagenti`** (`kind_cluster_name` in `deployments/ansible/default_values.yaml`), context **`kind-kagenti`**.
- Confirm: `kubectl config current-context` → `kind-kagenti`, and `kind get clusters` lists `kagenti` (with the same `KIND_EXPERIMENTAL_PROVIDER` you used for Podman).

More detail: [Kagenti Developer’s Guide](https://github.com/kagenti/kagenti/blob/main/docs/dev-guide.md).

### Step 2: Recommended path — import from Git (no local `kind load`)

After Ansible install, use the Kagenti UI **Import New Tool** / **Import New Agent** with the Git repo and subfolders (see Steps 5–6 below). Shipwright/Tekton builds images **inside the cluster** from the repository, so you **do not** need to build images on your laptop or run `kind load` for that flow.

### Step 3 (optional): Pre-build images and load into kind

Use this only if you intentionally want local images on the nodes (e.g. iterating without pushing to Git, or air-gapped testing). The cluster name must match the installer: default **`kagenti`**, not a separate demo name.

On **Podman**, Kind must use the experimental provider for **every** `kind` command. Mismatch (cluster created under Docker, `kind load` under Podman, or the reverse) causes **`ERROR: no nodes found for cluster "…"`**.

From the **agent-examples** root:

```bash
# Finance MCP tool
cd mcp/finance_tool
podman build -t finance-tool:latest .
cd ../..

# Financial agent
cd a2a/financial_agent
podman build -t financial-agent:latest .
cd ../..

export KIND_EXPERIMENTAL_PROVIDER=podman   # omit if using Docker for kind

podman save -o /tmp/finance-tool.tar finance-tool:latest
podman save -o /tmp/financial-agent.tar financial-agent:latest

# Replace kagenti if you overrode kind_cluster_name in extra-vars
kind load image-archive /tmp/finance-tool.tar --name kagenti
kind load image-archive /tmp/financial-agent.tar --name kagenti

podman exec kagenti-control-plane crictl images | head   # or docker exec … on Docker
```

If you see **`no nodes found`**, fix provider/name: `kind get clusters`, `podman ps --filter name=kagenti-control-plane`, then `kind delete cluster --name kagenti` and re-run the Ansible installer with consistent `container_engine` / `KIND_EXPERIMENTAL_PROVIDER`.

### Step 4: Configure environment variable sets

The repo root defines **`mcp-finance`** and **`lmstudio`** in [`sample-environments.yaml`](../../sample-environments.yaml) (alongside `ollama`, `mcp-reservations`, etc.). Use that file as a reference or apply it to your cluster namespace.

Key entries for this agent:

```yaml
mcp-finance: |
  [
    {"name": "MCP_URL", "value": "http://finance-tool:8000/mcp"}
  ]

lmstudio: |
  [
    {"name": "LLM_API_BASE", "value": "http://host.docker.internal:1234/v1"},
    {"name": "LLM_MODEL", "value": "qwen/qwen3-30b-a3b-2507"},
    {"name": "LLM_API_KEY", "value": "not-needed"}
  ]
```

Apply to your **team** namespace (the dev Ansible values typically include **`team1`**; create the namespace in Kagenti if it does not exist) from the **agent-examples** root:

```bash
cd agent-examples
kubectl apply -n team1 -f sample-environments.yaml
# Or merge keys into the Kagenti environments ConfigMap — see Kagenti docs
```

**Linux note:** `host.docker.internal` may not resolve from kind on Linux. Use your host IP (e.g. `192.168.1.100:1234`) or configure extra hosts in the kind cluster config.

### Step 5: Import Finance MCP tool in Kagenti

1. Open the Kagenti UI (URL from your install, often something like `http://kagenti-ui.localtest.me:8080` — see Ansible / ingress notes in kagenti docs)
2. Go to **Import New Tool**
3. Configure:
   - **Namespace**: `team1` (or your namespace)
   - **Source Repository URL**: `https://github.com/kagenti/agent-examples` (or your fork)
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
   - **Agent Source Repository URL**: `https://github.com/kagenti/agent-examples` (or your fork)
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

**Option B – Port-forward and local test client**

```bash
# Port-forward agent service (adjust service name if your cluster differs)
kubectl port-forward -n team1 svc/financial-agent 8001:8000
```

Point an A2A client at `http://localhost:8001`, or from a **local clone** of this repo run the graph test (LM Studio + finance MCP must still be reachable from your machine):

```bash
cd a2a/financial_agent
uv run financial-agent-test --query "What is AAPL's PE ratio?"
```

### Troubleshooting Kagenti deployment

| Issue | Check |
|-------|-------|
| Ansible install fails or kind errors | [deployments/ansible/README.md](https://github.com/kagenti/kagenti/blob/main/deployments/ansible/README.md): Helm **v3** only; for Podman use `KIND_EXPERIMENTAL_PROVIDER=podman` and `--extra-vars '{"container_engine": "podman"}'` together |
| `no nodes found for cluster` on `kind load` | Cluster name must match installer (`kagenti` by default); same container runtime/provider as when the cluster was created |
| Agent can't reach MCP | `kubectl get svc -n team1` – ensure `finance-tool` service exists; verify `MCP_URL` in env sets |
| Agent can't reach LM Studio | LM Studio running on host; on Linux, replace `host.docker.internal` with host IP in `lmstudio` |
| Build fails | Kagenti/Shipwright build logs; `Dockerfile` / `pyproject.toml` under the subfolder |
| Image pull / not found | If you use **Git import**, the cluster builds the image—no `kind load` needed. If you use **optional Step 3**, re-run `kind load image-archive` with **`--name kagenti`** (or your `kind_cluster_name`) |

---

## Deployment in Kagenti (summary)

- **Platform**: Install Kagenti on kind with the **kagenti** repo Ansible installer (`deployments/ansible/run-install.sh --env dev`, optional Podman extra-vars above). Default kind cluster name: **`kagenti`**, context **`kind-kagenti`**.
- **Environments**: `mcp-finance` and `lmstudio` are defined in [`sample-environments.yaml`](../../sample-environments.yaml) at the agent-examples repo root; apply to namespace `team1` (or your team namespace).
- **Tool**: **Import New Tool** → subfolder `mcp/finance_tool`; cluster builds from Git (Step 5). Optional env set **`mcp-finance`** if you want `MCP_URL` from the ConfigMap.
- **Agent**: **Import New Agent** → subfolder `a2a/financial_agent`; env sets **`lmstudio`** + **`mcp-finance`**.
- **LLM**: LM Studio on the host (in-cluster `LLM_API_BASE` uses `host.docker.internal` where supported; adjust on Linux).

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

- Finance MCP tool: **8000** (default)
- Agent: **8001** when both run on one host — set via **`.env.lmstudio`** (`PORT=8001`), **`.env`**, or `PORT=8001 uv run server`

---

## Dependencies (high level)

Declared in `pyproject.toml`: **a2a-sdk** (provides the `a2a.*` imports), **langgraph**, **langchain** (metapackage so **MLflow** `langchain.autolog` can run), **langchain-openai**, **langchain-core**, **langchain-mcp-adapters**, **pydantic-settings**, **mlflow**, **uvicorn**, **openinference-instrumentation-langchain**. Use **`a2a-sdk`** only — do not add the unrelated PyPI package named `a2a`.

---

## IDE / type checking

If you use a **multi-root** workspace or open a parent folder, select the interpreter **`a2a/financial_agent/.venv/bin/python`** and run **`uv sync`** in `a2a/financial_agent/`. **`pyrightconfig.json`** in this directory points Pyright/Pylance at `.venv` and `src/`.

---

## Project structure

```
financial_agent/
├── src/financial_agent/
│   ├── agent.py          # A2A server entry point
│   ├── graph.py          # LangGraph workflow
│   ├── configuration.py  # pydantic-settings; .env.lmstudio + .env
│   ├── prompts.py
│   ├── observability.py  # MLflow setup
│   └── test.py           # Test runner + USE_CASES
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── pyrightconfig.json
├── .env.lmstudio         # Local LM Studio + MCP template (loaded automatically)
├── .gitignore            # mlruns/, mlflow.db, .env
└── README.md
```

## Related

- [Finance MCP Tool](../../mcp/finance_tool/) – Yahoo Finance MCP server
- [Reservation Service](../reservation_service/) – Similar agent pattern
- [Generic Agent](../generic_agent/) – Multi-MCP agent example

## License

Apache License 2.0
