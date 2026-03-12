"""LangGraph workflow for the Financial Agent."""

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_mcp_adapters.client import MultiServerMCPClient

from financial_agent.configuration import Configuration
from financial_agent.prompts import FINANCIAL_AGENT_SYSTEM_PROMPT

config = Configuration()


class ExtendedMessagesState(MessagesState):
    """State with final_answer for A2A response extraction."""

    final_answer: str = ""


def get_mcpclient():
    """Create MCP client for the finance tool server."""
    return MultiServerMCPClient(
        {
            "finance": {
                "url": config.mcp_url,
                "transport": config.mcp_transport,
            }
        }
    )


async def get_graph(client: MultiServerMCPClient) -> StateGraph:
    """Build and compile the LangGraph for the financial agent."""
    llm = ChatOpenAI(
        model=config.llm_model,
        api_key=config.llm_api_key,
        base_url=config.llm_api_base,
        temperature=0,
    )

    tools = await client.get_tools()
    llm_with_tools = llm.bind_tools(tools)
    sys_msg = SystemMessage(content=FINANCIAL_AGENT_SYSTEM_PROMPT)

    def assistant(state: ExtendedMessagesState) -> dict:
        result = llm_with_tools.invoke([sys_msg] + state["messages"])
        updated: dict = {"messages": [result]}
        if isinstance(result, AIMessage) and not result.tool_calls:
            updated["final_answer"] = result.content or ""
        return updated

    builder = StateGraph(ExtendedMessagesState)
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges("assistant", tools_condition)
    builder.add_edge("tools", "assistant")

    return builder.compile()
