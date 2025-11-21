import { type FC, useCallback, useState } from "react";
import { useNavigate, useLocation } from "react-router";
import { toast } from "sonner";
import {
  useExecuteTrade,
  useGetHKPortfolioSummary,
  useGetHKPortfolioValueHistory,
  useGetHKStockPositions,
  useGetHKStockTrades,
} from "@/api/hk-stock";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { AgentViewProps } from "@/types/agent";
import { AddHKTradeModal } from "../hk-stock-items/add-hk-trade-modal";
import { ConfigurePortfolioModal } from "../hk-stock-items/configure-portfolio-modal";
import { StrategyConfigModal } from "../hk-stock-items/strategy-config-modal";
import HKStockPortfolioGroup from "../hk-stock-items/hk-stock-portfolio-group";
import HKStockSummaryPanel from "../hk-stock-items/hk-stock-summary-panel";
import HKStockTradeHistoryGroup from "../hk-stock-items/hk-stock-trade-history-group";
import HKStrategyManager from "../hk-stock-items/hk-strategy-manager";

const EmptyIllustration = () => (
  <svg
    viewBox="0 0 258 185"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className="h-[185px] w-[258px]"
  >
    <rect x="40" y="30" width="178" height="125" rx="8" fill="#F3F4F6" />
    <rect x="60" y="60" width="138" height="8" rx="4" fill="#E5E7EB" />
    <rect x="60" y="80" width="100" height="8" rx="4" fill="#E5E7EB" />
    <rect x="60" y="100" width="120" height="8" rx="4" fill="#E5E7EB" />
  </svg>
);

const HKStockAgentArea: FC<AgentViewProps> = ({ agentName }) => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const { data: positions = [], isLoading: isLoadingPositions } =
    useGetHKStockPositions();
  const { data: trades = [] } = useGetHKStockTrades();
  const { data: portfolioSummary } = useGetHKPortfolioSummary();
  const { data: portfolioHistory = [] } = useGetHKPortfolioValueHistory();
  
  const executeTradeMutation = useExecuteTrade();
  
  // Get initial tab from navigation state
  const initialTab = (location.state as any)?.activeTab || "trading";

  // Handle trade submission - execute trade via API
  const handleTradeSubmit = useCallback(
    async (trade: { symbol: string; side: "BUY" | "SELL"; lots: number }) => {
      const action = trade.side === "BUY" ? "Buy" : "Sell";
      const tradeMsg = `${action} ${trade.lots} lots of ${trade.symbol}`;
      
      const toastId = toast.loading(`Executing trade: ${tradeMsg}...`);
      
      try {
        await executeTradeMutation.mutateAsync({
          symbol: trade.symbol,
          side: trade.side,
          lots: trade.lots,
        });
        
        // Dismiss loading toast and show success
        toast.dismiss(toastId);
        toast.success("Trade Executed Successfully!", {
          description: `${tradeMsg} - Check your portfolio and trade history for updates.`,
          duration: 5000,
        });
      } catch (error) {
        console.error("Trade execution failed:", error);
        // Dismiss loading toast and show error
        toast.dismiss(toastId);
        toast.error("Trade Failed", {
          description: `Failed to execute ${tradeMsg}. Please try again.`,
          duration: 5000,
        });
      }
    },
    [executeTradeMutation]
  );

  // Handle portfolio import - send batch import command
  const handlePortfolioImport = useCallback(
    (positions: Array<{ symbol: string; name: string; lots: number; avgPrice: number }>) => {
      const message = `Imported positions:\n${positions
        .map((p) => `${p.symbol} ${p.name} ${p.lots} lots @ ${p.avgPrice}`)
        .join("\n")}`;
      
      navigate(`/agent/${agentName}`, {
        state: { inputValue: message },
      });
    },
    [agentName, navigate]
  );

  // Handle strategy config - send strategy command
  const handleStrategyConfig = useCallback(
    (config: any) => {
      const strategyMsg = `Configure Trading Strategy: ${config.strategy}, Stop Loss: ${config.stopLoss}%, Take Profit: ${config.takeProfit}%`;
      
      toast.success("Strategy Configuration Saved!", {
        description: `${strategyMsg} - ${config.enabled ? "Strategy activated" : "Strategy saved (not activated)"}`,
        duration: 5000,
      });
      
      // Optional: Navigate to chat with pre-filled strategy message
      // Uncomment if you want to send to chat as well
      // const message = `Start automated trading strategy:
      // Strategy Type: ${config.strategy}
      // Stop Loss: ${config.stopLoss}%, Take Profit: ${config.takeProfit}%
      // Max Position: ${config.maxPositionSize}%
      // Monitor Interval: ${config.monitorInterval} minutes
      // ${config.enabled ? "✅ Enable Now" : "⏸️ Save Config Only"}`;
      // navigate(`/agent/${agentName}`, {
      //   state: { inputValue: message },
      // });
    },
    [agentName, navigate]
  );

  const hasData = portfolioSummary && portfolioSummary.total_assets > 0;
  const [activeTab, setActiveTab] = useState<string>(initialTab);

  if (isLoadingPositions) return null;

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Tab Navigation */}
      <div className="border-b bg-white px-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="h-12 w-full justify-start border-0 bg-transparent p-0">
            <TabsTrigger
              value="trading"
              className="data-[state=active]:border-blue-500 data-[state=active]:border-b-2 rounded-none border-b-2 border-transparent px-6"
            >
              Manual Trading
            </TabsTrigger>
            <TabsTrigger
              value="strategies"
              className="data-[state=active]:border-blue-500 data-[state=active]:border-b-2 rounded-none border-b-2 border-transparent px-6"
            >
              Trading Strategies
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Tab Content */}
    <div className="flex flex-1 overflow-hidden">
        {activeTab === "trading" && (
          <>
      {/* Left section: Portfolio Summary */}
      <div className="flex w-96 flex-col border-r overflow-y-auto">
        <div className="px-6 py-6 border-b bg-white sticky top-0 z-10">
          <p className="font-semibold text-base">HK Stock Portfolio</p>
        </div>

        {portfolioSummary ? (
          <div className="flex flex-col gap-4 px-6 py-6">
            <HKStockSummaryPanel summary={portfolioSummary} />
            
            {/* Action Buttons */}
            <div className="space-y-2">
              <AddHKTradeModal onSubmit={handleTradeSubmit} />
              
              <div className="grid grid-cols-2 gap-2">
                <ConfigurePortfolioModal onSubmit={handlePortfolioImport} />
                <StrategyConfigModal onSubmit={handleStrategyConfig} />
              </div>
            </div>
            
            {/* Usage Hint */}
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
              <p className="text-blue-800 text-xs">
                💡 <strong>Usage Tip</strong>: After configuring portfolio and strategy, Agent will auto-monitor and execute trades
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6">
            <EmptyIllustration />
            <div className="flex flex-col gap-3 text-center text-base text-gray-400">
              <p>No portfolio data</p>
              <p>Start trading HK stocks to see your portfolio</p>
            </div>
            
            {/* Quick Start Actions */}
            <div className="w-full space-y-2">
              <ConfigurePortfolioModal onSubmit={handlePortfolioImport} />
              <AddHKTradeModal onSubmit={handleTradeSubmit} />
              <StrategyConfigModal onSubmit={handleStrategyConfig} />
            </div>
          </div>
        )}
      </div>

      {/* Right section: Trade History and Portfolio/Positions */}
      <div className="flex flex-1 overflow-hidden">
        {hasData ? (
          <>
            <HKStockTradeHistoryGroup trades={trades} />
            <HKStockPortfolioGroup
              positions={positions}
              portfolioHistory={portfolioHistory}
            />
          </>
        ) : (
          <div className="flex size-full flex-col items-center justify-center gap-8">
            <EmptyIllustration />
            <div className="flex flex-col gap-2 text-center">
              <p className="font-normal text-base text-gray-400">
                No trading activity yet
              </p>
              <p className="text-gray-300 text-sm">
                Use chat to buy/sell HK stocks or check prices
              </p>
            </div>
          </div>
        )}
            </div>
          </>
        )}
        
        {activeTab === "strategies" && <HKStrategyManager />}
      </div>
    </div>
  );
};

export default HKStockAgentArea;

