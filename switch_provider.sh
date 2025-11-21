#!/bin/bash
# Provider 切换脚本 - 解决地区限制问题

echo "============================================"
echo "🔧 StockBuddy API Provider 切换工具"
echo "============================================"
echo ""

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ .env 文件不存在！"
    exit 1
fi

# 显示当前配置
echo "📋 当前配置:"
echo ""
grep -E "SUPER_AGENT_(PROVIDER|MODEL_ID)" .env 2>/dev/null || echo "  未找到 SUPER_AGENT 配置（使用默认配置）"
echo ""

# 选择 Provider
echo "请选择要使用的 API Provider:"
echo ""
echo "  1) OpenAI (推荐) - 无需VPN，稳定快速"
echo "  2) Moonshot (月之暗面) - 国内服务，性价比高"
echo "  3) Google Gemini - 免费额度充足"
echo "  4) OpenRouter - 需要VPN"
echo ""
read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        PROVIDER="openai"
        MODEL_ID="gpt-4o-mini"
        echo ""
        echo "✅ 选择: OpenAI (gpt-4o-mini)"
        ;;
    2)
        PROVIDER="moonshot"
        MODEL_ID="moonshot-v1-8k"
        echo ""
        echo "✅ 选择: Moonshot (moonshot-v1-8k)"
        
        # 检查是否需要创建 moonshot.yaml
        if [ ! -f "python/configs/providers/moonshot.yaml" ]; then
            echo ""
            echo "📝 创建 Moonshot 配置文件..."
            cat > python/configs/providers/moonshot.yaml << 'EOF'
name: "Moonshot"
provider_type: "openai-compatible"

enabled: true

connection:
  base_url: "https://api.moonshot.cn/v1"
  api_key_env: "MOONSHOT_API_KEY"

default_model: "moonshot-v1-8k"

defaults:
  temperature: 0.7
  max_tokens: 4096

models:
  - id: "moonshot-v1-8k"
    name: "Moonshot V1 8K"
  - id: "moonshot-v1-32k"
    name: "Moonshot V1 32K"
EOF
            echo "✅ Moonshot 配置文件已创建"
        fi
        ;;
    3)
        PROVIDER="google"
        MODEL_ID="gemini-2.5-flash"
        echo ""
        echo "✅ 选择: Google Gemini (gemini-2.5-flash)"
        ;;
    4)
        PROVIDER="openrouter"
        MODEL_ID="anthropic/claude-haiku-4.5"
        echo ""
        echo "⚠️  选择: OpenRouter (需要VPN)"
        ;;
    *)
        echo ""
        echo "❌ 无效选项"
        exit 1
        ;;
esac

# 备份 .env
echo ""
echo "📦 备份 .env 文件..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 更新 .env 配置
echo ""
echo "🔧 更新配置..."

# 删除旧的配置（如果存在）
sed -i.tmp '/^SUPER_AGENT_PROVIDER=/d' .env
sed -i.tmp '/^SUPER_AGENT_MODEL_ID=/d' .env
rm -f .env.tmp

# 添加新配置
cat >> .env << EOF

# ============================================
# Super Agent Provider 配置 (自动添加)
# 切换时间: $(date '+%Y-%m-%d %H:%M:%S')
# ============================================
SUPER_AGENT_PROVIDER=$PROVIDER
SUPER_AGENT_MODEL_ID=$MODEL_ID
EOF

echo "✅ 配置已更新"
echo ""

# 显示新配置
echo "📋 新配置:"
echo "  Provider: $PROVIDER"
echo "  Model: $MODEL_ID"
echo ""

# 询问是否重启服务
read -p "是否重启服务以应用新配置? (y/n): " restart

if [ "$restart" = "y" ] || [ "$restart" = "Y" ]; then
    echo ""
    echo "🔄 停止现有服务..."
    
    # 停止后端
    pkill -f "uvicorn" 2>/dev/null
    
    # 停止前端
    pkill -f "vite" 2>/dev/null
    pkill -f "bun.*dev" 2>/dev/null
    
    sleep 2
    
    echo "✅ 服务已停止"
    echo ""
    echo "🚀 启动服务..."
    bash start.sh &
    
    echo ""
    echo "⏳ 等待服务启动 (5秒)..."
    sleep 5
    
    echo ""
    echo "============================================"
    echo "✅ 配置切换完成！"
    echo "============================================"
    echo ""
    echo "访问: http://localhost:3000"
    echo ""
else
    echo ""
    echo "============================================"
    echo "✅ 配置已更新，请手动重启服务"
    echo "============================================"
    echo ""
    echo "运行以下命令重启服务:"
    echo "  bash start.sh"
    echo ""
fi

echo "💡 提示:"
echo "  - 备份文件: .env.backup.*"
echo "  - 配置文档: API_PROVIDER_SOLUTION.md"
echo ""

