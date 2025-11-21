#!/bin/bash

# StockBuddy 停止脚本
# 停止所有运行中的服务

echo "============================================"
echo "🛑 停止所有StockBuddy服务"
echo "============================================"

echo ""
echo "正在停止服务..."

# 停止Backend
pkill -f "uvicorn.*stockbuddy.server.main" 2>/dev/null && echo "✅ Backend已停止" || echo "   Backend未运行"

# 停止所有Agent
pkill -f "stockbuddy.agents.research_agent" 2>/dev/null && echo "✅ Research Agent已停止" || echo "   Research Agent未运行"
pkill -f "stockbuddy.agents.news_agent" 2>/dev/null && echo "✅ News Agent已停止" || echo "   News Agent未运行"
pkill -f "stockbuddy.agents.strategy_agent" 2>/dev/null && echo "✅ Strategy Agent已停止" || echo "   Strategy Agent未运行"

# 停止Frontend
pkill -f "bun.*dev" 2>/dev/null && echo "✅ Frontend已停止" || echo "   Frontend未运行"

sleep 1

echo ""
echo "============================================"
echo "✅ 所有服务已停止"
echo "============================================"

# 检查是否有残留进程
REMAINING=$(ps aux | grep -E "stockbuddy|bun.*dev" | grep -v grep | grep -v "stop_all.sh" | wc -l)

if [ $REMAINING -gt 0 ]; then
    echo ""
    echo "⚠️  警告: 仍有 $REMAINING 个相关进程在运行:"
    ps aux | grep -E "stockbuddy|bun.*dev" | grep -v grep | grep -v "stop_all.sh"
    echo ""
    echo "如需强制停止，运行:"
    echo "   kill -9 \$(ps aux | grep -E 'stockbuddy|bun.*dev' | grep -v grep | awk '{print \$2}')"
else
    echo "✅ 没有残留进程"
fi

echo ""

