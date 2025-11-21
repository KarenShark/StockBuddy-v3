#!/bin/bash

# StockBuddy 完整启动脚本
# 启动所有必需的服务：Backend + Agents + Frontend

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
PYTHON_DIR="$PROJECT_ROOT/python"

# 强制覆盖 Super Agent 模型配置，避免 .env 中遗留的 siliconflow 设置导致 provider 错误
# 使用 OpenRouter 访问 OpenAI 模型，格式为 openai/model-name
export SUPER_AGENT_PROVIDER="openrouter"
export SUPER_AGENT_MODEL_ID="openai/gpt-5-mini-2025-08-07"
export SUPER_AGENT_MAX_COMPLETION_TOKENS="2048"
export STOCKBUDDY_DOTENV_OVERRIDE="false"

echo "============================================"
echo "🚀 StockBuddy 完整启动脚本"
echo "============================================"

# 检查.env文件
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env文件不存在"
    echo "请创建 .env 文件并配置必要的环境变量"
    exit 1
fi

# 清理旧进程
echo ""
echo "🧹 清理旧进程..."
pkill -f "uvicorn.*stockbuddy" 2>/dev/null || true
pkill -f "stockbuddy.agents" 2>/dev/null || true
pkill -f "vite.*3000" 2>/dev/null || true
sleep 2
echo "✅ 旧进程已清理"

# 创建日志目录
LOG_DIR="/tmp/stockbuddy_logs_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"
echo "📝 日志目录: $LOG_DIR"

# 1. 启动Backend
echo ""
echo "1️⃣ 启动Backend (端口 8000)..."
cd "$PYTHON_DIR"
nohup uv run --env-file "$ENV_FILE" -m stockbuddy.server.main > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   进程ID: $BACKEND_PID"
sleep 3

# 2. 启动Research Agent
echo ""
echo "2️⃣ 启动Research Agent (端口 10004)..."
cd "$PYTHON_DIR"
nohup uv run --env-file "$ENV_FILE" -m stockbuddy.agents.research_agent > "$LOG_DIR/research_agent.log" 2>&1 &
RESEARCH_PID=$!
echo "   进程ID: $RESEARCH_PID"
sleep 5

# 3. 启动News Agent
echo ""
echo "3️⃣ 启动News Agent (端口 10005)..."
cd "$PYTHON_DIR"
nohup uv run --env-file "$ENV_FILE" -m stockbuddy.agents.news_agent > "$LOG_DIR/news_agent.log" 2>&1 &
NEWS_PID=$!
echo "   进程ID: $NEWS_PID"
sleep 4

# 4. 启动Strategy Agent
echo ""
echo "4️⃣ 启动Strategy Agent (端口 10006)..."
cd "$PYTHON_DIR"
nohup uv run --env-file "$ENV_FILE" -m stockbuddy.agents.strategy_agent > "$LOG_DIR/strategy_agent.log" 2>&1 &
STRATEGY_PID=$!
echo "   进程ID: $STRATEGY_PID"
sleep 3

# 5. 启动HK Stock Agent
echo ""
echo "5️⃣ 启动HK Stock Agent (端口 10007)..."
cd "$PYTHON_DIR"
nohup uv run --env-file "$ENV_FILE" -m stockbuddy.agents.hk_stock_agent > "$LOG_DIR/hk_stock_agent.log" 2>&1 &
HKSTOCK_PID=$!
echo "   进程ID: $HKSTOCK_PID"
sleep 3

# 6. 启动Frontend
echo ""
echo "6️⃣ 启动Frontend (端口 3000)..."
cd "$PROJECT_ROOT/frontend"
nohup bun run dev > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "   进程ID: $FRONTEND_PID"
sleep 8

echo ""
echo "⏳ 等待所有服务完全初始化..."
sleep 5

# 检查服务状态
echo ""
echo "============================================"
echo "🔍 检查服务状态..."
echo "============================================"

check_service() {
    local name=$1
    local port=$2
    local max_retries=3
    local retry=0
    
    while [ $retry -lt $max_retries ]; do
        if curl -s --connect-timeout 1 "http://localhost:$port" > /dev/null 2>&1 || \
           curl -s --connect-timeout 1 "http://localhost:$port/health" > /dev/null 2>&1; then
            echo "✅ $name (端口 $port) - 运行中"
            return 0
        fi
        retry=$((retry + 1))
        [ $retry -lt $max_retries ] && sleep 2
    done
    
    echo "⚠️  $name (端口 $port) - 启动中或未响应（请等待30秒后刷新浏览器）"
    return 1
}

check_service "Backend      " 8000
check_service "Research Agent" 10004
check_service "News Agent   " 10005
check_service "Strategy Agent" 10006
check_service "Frontend     " 3000

echo ""
echo "============================================"
echo "✅ 启动完成！"
echo "============================================"
echo ""
echo "🌐 访问地址（点击链接直接打开）:"
echo ""
echo "   🚀 前端界面: http://localhost:3000"
echo "   🔧 后端API:  http://localhost:8000"
echo ""
echo "   📡 Research Agent: http://localhost:10004"
echo "   📰 News Agent:     http://localhost:10005"
echo "   📈 Strategy Agent: http://localhost:10006"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 运行中的服务:"
ps aux | grep -E "stockbuddy|bun.*dev" | grep -v grep | awk '{print "   PID " $2 ": " $11 " " $12 " " $13}'
echo ""
echo "📝 日志文件位置:"
echo "   $LOG_DIR"
echo ""
echo "🛑 停止所有服务:"
echo "   ./stop_all.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 测试HK市场功能，尝试这些查询:"
echo "   • 最近30天的南下资金流向如何？"
echo "   • 建设银行的AH股溢价是多少？"
echo "   • 南下资金最喜欢哪些港股？"
echo ""

