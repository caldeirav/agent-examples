# Yahoo Finance MCP Tool

MCP server providing stock market data via the [yfinance](https://pypi.org/project/yfinance/) library. Used by the Financial Agent for real-time financial analysis.

## Tools

| Tool | Description |
|------|-------------|
| `get_stock_fundamentals` | PE ratio, market cap, dividends, sector, beta |
| `get_historical_prices` | OHLCV history, returns, moving averages |
| `get_financial_statements` | Balance sheet, income statement, cash flow |
| `get_company_news` | Recent headlines and sentiment |

## Running Locally

```bash
cd mcp/finance_tool
uv lock
uv run finance_tool.py
```

Server starts on `http://0.0.0.0:8000` with streamable-http MCP transport.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Server port |
| `MCP_TRANSPORT` | `streamable-http` | MCP transport protocol |
| `LOG_LEVEL` | `INFO` | Logging level |
