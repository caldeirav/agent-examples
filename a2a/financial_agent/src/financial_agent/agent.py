"""A2A agent entry point for the Financial Agent."""

import logging
from textwrap import dedent

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, TaskState, TextPart
from a2a.utils import new_agent_text_message, new_task
from langchain_core.messages import HumanMessage
from openinference.instrumentation.langchain import LangChainInstrumentor
from starlette.routing import Route

from financial_agent.configuration import Configuration
from financial_agent.graph import get_graph, get_mcpclient
from financial_agent.observability import setup_mlflow_tracing

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

LangChainInstrumentor().instrument()
setup_mlflow_tracing()


def get_agent_card(host: str, port: int) -> AgentCard:
    """Returns the Agent Card for the Financial Agent."""
    capabilities = AgentCapabilities(streaming=True)
    skill = AgentSkill(
        id="financial_analyst",
        name="Financial Analyst",
        description="**Financial Analyst** – AI-powered stock market analysis assistant.",
        tags=["finance", "stocks", "investing", "market data"],
        examples=[
            "What is AAPL's PE ratio?",
            "Compare the market caps of Microsoft and Apple",
            "What's the dividend yield for NVDA?",
            "Show me the price performance of TSLA over the past month",
            "What's the latest news about Meta?",
        ],
    )
    return AgentCard(
        name="Financial Analyst",
        description=dedent(
            """\
            This agent provides financial analysis and stock market data through natural language.

            ## Capabilities
            - **Stock Fundamentals** – PE ratio, market cap, dividends, sector info
            - **Historical Prices** – Price history, returns, moving averages
            - **Financial Statements** – Balance sheet, income, cash flow
            - **Company News** – Recent headlines and sentiment
            - **Multi-Stock Comparison** – Compare fundamentals across tickers

            ## Input Parameters
            - **prompt** (string) – Your financial question in natural language

            ## Key Features
            - **MCP Tool Calling** – Connects to Yahoo Finance MCP tools
            - **Real-time Data** – Uses yfinance for current market data
            - **Disclaimers** – Informational only, not financial advice
            """
        ),
        url=f"http://{host}:{port}/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=capabilities,
        skills=[skill],
    )


class A2AEvent:
    """Emit events for A2A task updates."""

    def __init__(self, task_updater: TaskUpdater):
        self.task_updater = task_updater

    async def emit_event(
        self, message: str, final: bool = False, failed: bool = False
    ) -> None:
        logger.info("Emitting event %s", message[:80] + "..." if len(message) > 80 else message)
        if final or failed:
            parts = [TextPart(text=message)]
            await self.task_updater.add_artifact(parts)
            if final:
                await self.task_updater.complete()
            if failed:
                await self.task_updater.failed()
        else:
            await self.task_updater.update_status(
                TaskState.working,
                new_agent_text_message(
                    message,
                    self.task_updater.context_id,
                    self.task_updater.task_id,
                ),
            )


class FinancialExecutor(AgentExecutor):
    """Execute financial agent queries."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if not task:
            task = new_task(context.message)  # type: ignore
            await event_queue.enqueue_event(task)
        task_updater = TaskUpdater(event_queue, task.id, task.context_id)
        event_emitter = A2AEvent(task_updater)

        messages = [HumanMessage(content=context.get_user_input())]
        input_data = {"messages": messages}

        mcp_url = Configuration().mcp_url
        try:
            mcpclient = get_mcpclient()
            try:
                tools = await mcpclient.get_tools()
                logger.info(f"MCP tools available: {[t.name for t in tools]}")
            except Exception as e:
                logger.error(f"MCP connection failed: {e}")
                await event_emitter.emit_event(
                    f"Error: Cannot connect to finance MCP at {mcp_url}. {e}",
                    failed=True,
                )
                return

            graph = await get_graph(mcpclient)
            final_answer = None
            async for event in graph.astream(input_data, stream_mode="updates"):
                for node_name, node_output in event.items():
                    msg = f"🤔 {node_name}: "
                    if isinstance(node_output, dict) and "final_answer" in node_output:
                        final_answer = node_output["final_answer"]
                    msg += str(node_output)[:256] + "..." if len(str(node_output)) > 256 else str(node_output)
                    await event_emitter.emit_event(msg + "\n")

            if final_answer:
                await event_emitter.emit_event(str(final_answer), final=True)
            else:
                await event_emitter.emit_event(
                    "No response produced. Please try rephrasing your question.",
                    final=True,
                )
        except Exception as e:
            logger.exception(f"Graph execution error: {e}")
            await event_emitter.emit_event(
                f"Error: Failed to process request. {str(e)}", failed=True
            )
            raise

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception("cancel not supported")


def run() -> None:
    """Run the A2A Financial Agent server."""
    cfg = Configuration()
    port = cfg.port
    agent_card = get_agent_card(host="0.0.0.0", port=port)
    request_handler = DefaultRequestHandler(
        agent_executor=FinancialExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    app = server.build()
    app.routes.insert(
        0,
        Route(
            "/.well-known/agent-card.json",
            server._handle_get_agent_card,
            methods=["GET"],
            name="agent_card_new",
        ),
    )
    uvicorn.run(app, host="0.0.0.0", port=port)
