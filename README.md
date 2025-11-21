# StockBuddy

**StockBuddy** is an AI-powered multi-agent platform for intelligent financial analysis and automated trading. Built with modern web technologies and powered by LLMs, it brings professional-grade trading capabilities to everyone.

## 🎯 What We've Built

- **🤖 AI-Powered Trading**: Describe your strategy in natural language, let AI execute it automatically
- **📊 HK Stock Trading**: Complete paper trading system with realistic market simulation
- **🔍 Real-Time Transparency**: Monitor every AI decision with full reasoning and confidence scores
- **💼 Portfolio Management**: Comprehensive tracking of positions, P&L, and trade history
- **🎨 Modern Beautiful UI**: Intuitive interface with real-time updates and smooth interactions
- **📰 Smart News Agent**: Automated news retrieval and personalized information delivery

>**Note**: This project is for educational and research purposes. Investing involves risk. Always do your own research. ⚠️

# 📸 Product Screenshots

## 🏠 Home Dashboard
Clean, modern interface with quick access to all trading agents.

<p align="center">
  <img src="screenshots/Home.png" style="width: 100%; height: auto;">
</p>

---

## 📈 HK Stock Trading Agent

### Manual Trading Mode
Execute trades manually with real-time order execution, portfolio tracking, and comprehensive P&L monitoring.

<p align="center">
  <img src="screenshots/Auto-Trading Agent-Manual Trading.png" style="width: 100%; height: auto;">
</p>

**Features:**
- ✅ Real-time order execution (buy/sell)
- ✅ Live portfolio value tracking
- ✅ Open positions with unrealized P&L
- ✅ Complete trade history
- ✅ Realistic fee simulation (0.14% per trade)

### AI Strategy Simulation
The game-changer: **Describe your trading strategy in plain English**, and AI will execute it automatically.

<p align="center">
  <img src="screenshots/Auto-Trading Agent - Strategy Simulation - Trade History.png" style="width: 100%; height: auto;">
</p>

**How it works:**
1. Write your strategy in natural language (e.g., "Buy when price drops 5%, sell at 10% profit")
2. Set risk parameters (max position size, stop loss, take profit)
3. Choose rebalance interval (e.g., every 60 seconds)
4. AI analyzes market conditions and executes trades automatically

**Example Strategy Description:**
```
Aggressive Test Strategy - Immediate Buy

Rules:
- Buy all available stocks immediately
- Purchase 1-2 lots per stock
- Allocate 15% of capital per position
- This is a test strategy to verify trading functionality

Risk Management:
- Stop loss at 10% loss per stock
- Take profit at 15% gain per stock
```

### 🤖 AI Decision Monitoring - Full Transparency
**The breakthrough feature**: See exactly what AI is thinking, why it makes each decision, and track execution results in real-time.

<p align="center">
  <img src="screenshots/Auto-Trading Agent - Strategy Simulation - AI Interpretation.png" style="width: 100%; height: auto;">
</p>

**What you see:**
- 📅 **Timestamp**: When each decision was made
- 💰 **Portfolio State**: Total value, cash balance, open positions
- 🎯 **AI Recommendations**: BUY / SELL / HOLD with specific quantities
- 💭 **Reasoning**: Why AI made this decision
- 📊 **Confidence Score**: AI's confidence level (e.g., 85%, 92%)
- ✅ **Execution Status**: Success or failure for each recommendation
- 🎨 **Color-coded Tags**: Visual distinction between action types

**Example AI Decision:**
```
Nov 20, 22:13:01
Portfolio: $1,000,000 HKD | Cash: $1,000,000 HKD | Positions: 0

[BUY] HKEX:00700  2 lots  [✓ Executed]
Reason: Strong uptrend with high volume, entry opportunity detected
Confidence: 92% | Target: $650.00
```

**Updates every 5 seconds** - No more black box trading!

---

## 📰 News Agent - Personalized Information Feed
Schedule automated news retrieval to stay informed about your tracked stocks and market trends.

<p align="center">
  <img src="screenshots/News Agent - Scheduled Latest News Retrieval.png" style="width: 100%; height: auto;">
</p>

**View and analyze news content:**

<p align="center">
  <img src="screenshots/News Agent - Scheduled Latest News Retrieval - News Content.png" style="width: 100%; height: auto;">
</p>

**Features:**
- ✅ Scheduled news retrieval (daily, hourly, custom intervals)
- ✅ Personalized news filtering based on your interests
- ✅ AI-powered content summarization
- ✅ Real-time market information tracking

---

# ✨ Core Features

## 🎯 HK Stock Paper Trading System

### Realistic Market Simulation
We've built a **production-grade paper trading engine** that simulates real market conditions:

**Trading Fees (Hong Kong Stock Market):**
- Stamp Duty: 0.13%
- Trading Fee: 0.005%
- Settlement Fee: 0.002%
- Transaction Levy: 0.0027%
- **Total: ~0.14% per trade**

**Market Realism:**
- 🎲 **Slippage**: 0.03% - 0.10% price impact
- ⏱️ **Order Delays**: Simulated execution latency
- 📊 **Market Impact**: Larger orders have higher slippage
- 💹 **Real-time Prices**: Live market data integration
- 📦 **Lot Size Requirements**: Enforced for HK stocks

**Why this matters:**
- Test strategies without risking real money
- Understand actual trading costs before going live
- Learn the impact of fees on high-frequency strategies
- Build realistic expectations for returns

### AI Strategy Engine

**Natural Language Strategy Input:**
```
Short-term Momentum Breakout Strategy

Entry Conditions:
- Stock price above 20-day moving average
- If current price is 5%+ below historical average (oversold), buy
- If current price is 5%+ above historical average (overbought), do not buy

Position Management:
- Initial position size max 15% of capital per stock
- Maximum 3 stocks in portfolio

Exit Conditions:
- Take profit when stock gains 10%
- Stop loss when stock loses 5%
- Automatic close after holding 5 days
```

**AI Analyzer Features:**
- 🧠 Powered by LLMs (OpenAI, OpenRouter, etc.)
- 📊 Analyzes market conditions in real-time
- 🎯 Generates actionable BUY/SELL/HOLD recommendations
- 💭 Provides reasoning for each decision
- 📈 Considers your strategy rules and risk parameters
- ⏰ Automatic rebalancing at custom intervals (30s, 60s, 5min, etc.)

### AI Decision Transparency

**Every rebalance cycle records:**
```json
{
  "timestamp": "2025-11-20T22:13:01Z",
  "portfolio_value": 1000000.0,
  "cash": 850000.0,
  "positions": 3,
  "recommendations": [
    {
      "symbol": "HKEX:00700",
      "action": "BUY",
      "lots": 2,
      "reason": "Strong uptrend detected with high volume...",
      "confidence": 0.92,
      "target_price": 650.0,
      "executed": true
    }
  ]
}
```

**Access via:**
- 🖥️ Frontend UI: Real-time dashboard with visual cards
- 📡 REST API: `/api/v1/hk-stock-strategies/{id}/ai-decisions`
- 📝 Backend Logs: Detailed execution logs

### Portfolio Tracking

**Comprehensive Metrics:**
- 💰 Total Portfolio Value (real-time)
- 💵 Cash Balance
- 📊 Open Positions (quantity, lots, avg price, market value)
- 📈 Unrealized P&L (per position and total)
- 📜 Trade History (all executed orders)
- 🎯 Performance Analytics (total P&L, P&L %)

**Real-time Updates:**
- Frontend auto-refreshes every 2-3 seconds
- WebSocket support planned for instant updates
- Background polling even when tab is inactive

---

## 🤖 Super Agent & Research Agent

**Multi-modal AI Research Assistant:**
- 💬 Natural language conversation interface
- 🔧 Tool calling capabilities for data retrieval
- 📊 Access to financial databases and market data
- 🧮 Automatic calculations and analysis
- 📈 Chart generation and visualization (planned)
- 🔍 Deep dive into company fundamentals

**Use Cases:**
- "What's Apple's free cash flow trend over the past 5 years?"
- "Compare Tesla and BYD's profit margins"
- "Analyze NVIDIA's revenue breakdown by segment"
- "Is Meta's valuation reasonable compared to peers?"

---

## 📰 News Agent

**Automated Information Delivery:**
- ⏰ Scheduled news retrieval (custom intervals)
- 🎯 Personalized filtering based on your portfolio
- 📰 Multi-source news aggregation
- 🤖 AI-powered summarization
- 📧 Push notifications (planned)
- 🔔 Custom alert rules

---

# 🏗️ System Architecture

## High-Level Architecture

StockBuddy is built on a modern, scalable multi-agent architecture that separates concerns and enables flexible integration:

<p align="center">
  <img src="screenshots/High-level StockBuddy system architecture.png" style="width: 100%; height: auto;">
</p>

**Key Components:**
- **Frontend (React + TypeScript)**: Modern web interface with real-time updates
- **Backend API (FastAPI)**: RESTful API server handling all business logic
- **Agent System**: Specialized AI agents for different trading and research tasks
- **LLM Integration**: Flexible integration with multiple AI providers
- **Data Layer**: SQLite for structured data, LanceDB for vector embeddings
- **Market Data**: Real-time feeds from multiple exchanges and data providers

## A2A Protocol Communication

Our agents communicate using the A2A (Agent-to-Agent) Protocol, enabling seamless collaboration and tool calling:

<p align="center">
  <img src="screenshots/A2A Protocol Communication.png" style="width: 100%; height: auto;">
</p>

**Protocol Features:**
- **Tool Calling**: Agents can invoke specialized tools for data retrieval and analysis
- **Message Passing**: Structured communication between agents
- **Context Sharing**: Maintain conversation history and state across agents
- **Error Handling**: Graceful degradation and retry mechanisms
- **Extensibility**: Easy to add new agents and tools to the system

**Communication Flow:**
1. User sends query to Super Agent
2. Super Agent analyzes request and determines required tools
3. Calls sub-agents (Research Agent, Trading Agent, etc.) as needed
4. Sub-agents execute tasks and return results
5. Super Agent synthesizes information and responds to user

This architecture enables complex multi-step workflows while maintaining code modularity and testability.

---

## 🔧 Technical Stack

**Frontend:**
- ⚛️ React + TypeScript
- 🎨 Tailwind CSS + shadcn/ui
- 🔄 TanStack Query (React Query) for data fetching
- 📊 Real-time updates with polling (WebSocket planned)
- 🎭 Beautiful, responsive design

**Backend:**
- 🐍 Python 3.12+
- ⚡ FastAPI for REST API
- 🤖 LangChain for agent orchestration
- 💾 SQLite + LanceDB for data storage
- 📡 Async/await for high performance

**AI Integration:**
- 🧠 Multiple LLM providers:
  - OpenAI (GPT-4, GPT-3.5)
  - OpenRouter (access to 200+ models)
  - Google Gemini
  - SiliconFlow
- 🔄 Easy model switching
- 💰 Cost-effective model selection per task

**Market Data:**
- 📊 Real-time price feeds
- 🌏 Hong Kong Stock Exchange
- 🇺🇸 US Stock Markets
- 🪙 Crypto markets (OKX, Binance)
- 📈 Historical data and analytics

---

# 🚀 Quick Start Guide

Get StockBuddy running in 5 minutes! Follow these simple steps:

## Prerequisites

**Required:**
- **Python 3.12+** - [Download here](https://www.python.org/downloads/)
- **Node.js 18+** - [Download here](https://nodejs.org/)

**Recommended (for faster setup):**
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** - Ultra-fast Python package manager
- **[bun](https://github.com/oven-sh/bun#install)** - High-performance JavaScript runtime

## Step 1: Clone the Repository

```bash
git clone https://github.com/KarenShark/StockBuddy-v3.git
cd StockBuddy-v3
```

## Step 2: Configure Your API Keys

1. **Create your environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your API keys:**
   ```bash
   # Open .env in your favorite editor
   nano .env
   # or
   code .env
   ```

3. **Required Configuration:**
   
   At minimum, you need **one LLM provider**:
   
   ```bash
   # Option 1: OpenAI (Recommended for best quality)
   OPENAI_API_KEY=sk-your-openai-api-key-here
   OPENAI_MODEL=gpt-4-turbo-preview
   
   # Option 2: OpenRouter (Access to 200+ models)
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
   
   # Option 3: Google Gemini (Free tier available)
   GOOGLE_API_KEY=your-google-api-key-here
   GOOGLE_MODEL=gemini-1.5-pro
   ```


## Step 3: Run the Application

### Linux / macOS

```bash
# Make the script executable (first time only)
chmod +x start_all.sh

# Start all services
bash start_all.sh
```

### Windows (PowerShell)

```powershell
.\start.ps1
```

**What happens:**
- ✅ Installs Python dependencies
- ✅ Installs frontend dependencies
- ✅ Starts Backend API server (FastAPI on port 8000)
- ✅ Starts Frontend dev server (React on port 1420)
- ✅ Initializes all trading agents

**First run might take 2-3 minutes to install dependencies.**

## Step 4: Access the Application

Once you see the success message, open your browser:

- **🌐 Web UI**: [http://localhost:1420](http://localhost:1420)
- **📡 API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **📊 API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

## Step 5: Test the System

### Quick Test 1: Super Agent (AI Research)
1. Click "Super Agent" from the home page
2. Ask: *"What is Apple's current market cap?"*
3. Watch AI retrieve data and provide analysis

### Quick Test 2: HK Stock Manual Trading
1. Click "HK Stock Agent" → "Manual Trading" tab
2. Select stock: `00700` (Tencent)
3. Action: `BUY`, Quantity: `1` lot
4. Click "Execute" and watch your portfolio update

### Quick Test 3: AI Strategy Simulation
1. Click "HK Stock Agent" → "Trading Strategies" tab
2. Click "Create HK Stock Strategy"
3. Fill in:
   - **Name**: `Test Strategy`
   - **Symbols**: `00700, 09988` (comma-separated)
   - **Capital**: `1000000` HKD
   - **Rebalance**: `60` seconds
   - **Strategy**: Paste this example:
   ```
   Aggressive Test Strategy
   
   Rules:
   - Buy all available stocks immediately
   - Purchase 1-2 lots per stock
   - Allocate 15% capital per position
   
   Risk Management:
   - Stop loss at 10%
   - Take profit at 15%
   ```
4. Click "Create" and watch AI trade automatically!
5. Click "🤖 AI Decisions" tab to see real-time decision-making

## 📝 Logs and Monitoring

**Check backend logs:**
```bash
tail -f logs/backend.log
```

**Check agent logs:**
```bash
# Watch all logs
tail -f logs/*.log

# Watch specific agent
tail -f logs/hk_stock_agent.log
```

## 🛑 Stopping the Application

**Press `Ctrl+C`** in the terminal where you ran `start_all.sh`

Or kill processes manually:
```bash
# Find and kill processes
pkill -f "uvicorn"
pkill -f "bun"
```

## 🔧 Troubleshooting

### Issue: "Module not found" error
**Solution**: Make sure dependencies are installed
```bash
cd python
uv pip install -e .
cd ../frontend
bun install
```

### Issue: "Port already in use"
**Solution**: Kill existing processes
```bash
# Kill backend (port 8000)
lsof -ti:8000 | xargs kill -9

# Kill frontend (port 1420)
lsof -ti:1420 | xargs kill -9
```

### Issue: "API key invalid"
**Solution**: Double-check your `.env` file
- Make sure there are no extra spaces
- Verify the API key is still valid
- Check the provider is spelled correctly

### Issue: Database errors after update
**Solution**: Reset databases (fresh start)
```bash
rm -rf lancedb/ stockbuddy.db .knowledgebase/
bash start_all.sh
```

## 🎓 Next Steps

Once everything is running:

1. ✅ **Explore the UI** - Click around and familiarize yourself with the interface
2. ✅ **Test strategies** - Experiment with different trading strategies

---

**🎉 Congratulations! You're ready to start AI-powered trading!**

---

<div align="center">
  <p>Built with ❤️ for educational and research purposes</p>
  <p><i>AI-powered trading platform for learning and experimentation</i></p>
</div>
