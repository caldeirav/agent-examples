"""Test runner for the Financial Agent - runs use cases directly against the graph."""

import argparse
import asyncio

from financial_agent.observability import setup_mlflow_tracing

setup_mlflow_tracing()

USE_CASES = [
    "What is AAPL's PE ratio?",
    "Compare the market caps of Microsoft and Apple",
    "What's the dividend yield for NVDA?",
    "Show me TSLA price performance over the past month",
    "What's the latest news about Meta?",
    "Get the key financial metrics for GOOGL",
]


async def run_query(query: str, verbose: bool = True) -> str:
    """Run a single query through the financial agent graph."""
    from langchain_core.messages import HumanMessage

    from financial_agent.graph import get_graph, get_mcpclient

    mcpclient = get_mcpclient()
    await mcpclient.get_tools()  # Verify connection
    graph = await get_graph(mcpclient)

    input_data = {"messages": [HumanMessage(content=query)]}
    final_answer = None

    # Sync stream avoids MLflow+LangChain callback ContextVar issues with async astream
    # (https://github.com/mlflow/mlflow/issues/22088). The A2A server still uses astream.
    for event in graph.stream(input_data, stream_mode="updates"):
        for node_name, node_output in event.items():
            if verbose:
                print(f"  [{node_name}] ", end="")
            if isinstance(node_output, dict) and "final_answer" in node_output:
                final_answer = node_output["final_answer"]
            if verbose and node_output:
                preview = str(node_output)[:120] + "..." if len(str(node_output)) > 120 else str(node_output)
                print(preview)

    return final_answer or "No response"


async def run_all(queries: list[str], verbose: bool) -> None:
    """Run all queries."""
    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 60}")
        print(f"Use case {i}/{len(queries)}: {query}")
        print("=" * 60)
        try:
            answer = await run_query(query, verbose=verbose)
            print(f"\nAnswer:\n{answer}")
        except Exception as e:
            print(f"Error: {e}")
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Financial Agent")
    parser.add_argument("--query", "-q", help="Single query to run (default: run all use cases)")
    parser.add_argument("--quiet", "-Q", action="store_true", help="Only print final answers")
    args = parser.parse_args()

    queries = [args.query] if args.query else USE_CASES
    asyncio.run(run_all(queries, verbose=not args.quiet))


if __name__ == "__main__":
    main()
