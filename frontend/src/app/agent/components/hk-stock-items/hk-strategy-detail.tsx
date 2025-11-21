import { memo, type FC } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import ScrollContainer from "@/components/shared/scroll/scroll-container";
import {
  useHKStrategyDetail,
  useHKStrategyPositions,
  useHKStrategyTrades,
  useHKStrategyAIDecisions,
  type HKStockStrategyInfo,
  type HKStrategyPosition,
  type HKStrategyTrade,
  type HKStrategyAIDecision,
  type HKStrategyAIRecommendation,
} from "@/api/hk-stock-strategy";
import { TimeUtils } from "@/lib/time";
import { formatChange, getChangeType } from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";

interface HKStrategyDetailProps {
  strategy: HKStockStrategyInfo;
}

const PositionRow: FC<{ position: HKStrategyPosition }> = memo(({ position }) => {
  const { increaseColor, decreaseColor } = useStockColors();
  const changeType = getChangeType(position.unrealized_pnl_pct);

  return (
    <tr className="border-b hover:bg-gray-50">
      <td className="px-4 py-3 font-mono text-sm">{position.symbol}</td>
      <td className="px-4 py-3 text-right text-sm">{position.lots}</td>
      <td className="px-4 py-3 text-right font-mono text-sm">
        ${position.avg_price.toFixed(2)}
      </td>
      <td className="px-4 py-3 text-right font-mono text-sm">
        ${position.current_price.toFixed(2)}
      </td>
      <td className="px-4 py-3 text-right font-mono text-sm">
        ${position.market_value.toLocaleString("en-US", { maximumFractionDigits: 0 })}
      </td>
      <td
        className="px-4 py-3 text-right font-semibold text-sm"
        style={{
          color: changeType === "increase"
            ? increaseColor
            : changeType === "decrease"
              ? decreaseColor
              : "inherit",
        }}
      >
        {formatChange(position.unrealized_pnl_pct)}
      </td>
    </tr>
  );
});

PositionRow.displayName = "PositionRow";

const TradeRow: FC<{ trade: HKStrategyTrade }> = memo(({ trade }) => {
  return (
    <tr className="border-b hover:bg-gray-50">
      <td className="px-4 py-3 text-gray-600 text-xs">
        {TimeUtils.formatDateTime(trade.timestamp)}
      </td>
      <td className="px-4 py-3 font-mono text-sm">{trade.symbol}</td>
      <td className="px-4 py-3">
        <span
          className={`inline-block rounded px-2 py-0.5 font-medium text-xs ${
            trade.side === "BUY"
              ? "bg-green-100 text-green-700"
              : "bg-red-100 text-red-700"
          }`}
        >
          {trade.side}
        </span>
      </td>
      <td className="px-4 py-3 text-right text-sm">{trade.lots}</td>
      <td className="px-4 py-3 text-right font-mono text-sm">
        ${trade.price.toFixed(2)}
      </td>
      <td className="px-4 py-3 text-right font-mono text-sm">
        ${trade.total_value.toLocaleString("en-US", { maximumFractionDigits: 0 })}
      </td>
    </tr>
  );
});

TradeRow.displayName = "TradeRow";

const AIDecisionRow: FC<{ decision: HKStrategyAIDecision; index: number }> = memo(
  ({ decision, index }) => {
    const hasRecommendations = decision.recommendation_count > 0;
    
    return (
      <div className="border-b border-gray-200 p-4 hover:bg-gray-50">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900 text-sm">
              {TimeUtils.format(decision.timestamp, "MMM DD, HH:mm:ss")}
            </span>
            <Badge variant={hasRecommendations ? "default" : "secondary"} className="text-xs">
              {decision.recommendation_count} {decision.recommendation_count === 1 ? 'recommendation' : 'recommendations'}
            </Badge>
          </div>
          <span className="text-gray-500 text-xs">
            Portfolio: ${decision.portfolio_value.toLocaleString()} HKD
          </span>
        </div>

        {/* Portfolio Status */}
        <div className="flex gap-4 mb-3 text-xs text-gray-600">
          <span>Cash: ${decision.cash.toLocaleString()} HKD</span>
          <span>Positions: {decision.position_count}</span>
        </div>

        {/* Recommendations */}
        {hasRecommendations ? (
          <div className="space-y-2">
            {decision.recommendations.map((rec, recIndex) => (
              <div
                key={recIndex}
                className="rounded-lg border border-gray-200 bg-white p-3"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        variant={
                          rec.action === "BUY"
                            ? "default"
                            : rec.action === "SELL"
                            ? "destructive"
                            : "secondary"
                        }
                        className="text-xs font-semibold"
                      >
                        {rec.action}
                      </Badge>
                      <span className="font-semibold text-gray-900">
                        {rec.symbol}
                      </span>
                      <span className="text-gray-600 text-sm">
                        {rec.lots} {rec.lots === 1 ? 'lot' : 'lots'}
                      </span>
                      {rec.executed !== null && (
                        <Badge
                          variant={rec.executed ? "default" : "destructive"}
                          className="ml-auto text-xs"
                        >
                          {rec.executed ? "✓ Executed" : "✗ Failed"}
                        </Badge>
                      )}
                    </div>
                    <p className="text-gray-700 text-sm leading-relaxed mb-2">
                      {rec.reason}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span>Confidence: {(rec.confidence * 100).toFixed(0)}%</span>
                      {rec.target_price && (
                        <span>Target: ${rec.target_price.toFixed(2)}</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-gray-500 text-sm py-2">
            No recommendations (HOLD)
          </div>
        )}
      </div>
    );
  }
);

AIDecisionRow.displayName = "AIDecisionRow";

export const HKStrategyDetail: FC<HKStrategyDetailProps> = memo(({ strategy }) => {
  const { data: detail, isLoading: detailLoading } = useHKStrategyDetail(strategy.strategy_id);
  const { data: positions = [], isLoading: positionsLoading } = useHKStrategyPositions(strategy.strategy_id);
  const { data: trades = [], isLoading: tradesLoading } = useHKStrategyTrades(strategy.strategy_id, 50);
  // Optimization: Only fetch last 20 decisions for faster loading
  const { data: aiDecisions = [], isLoading: aiDecisionsLoading } = useHKStrategyAIDecisions(strategy.strategy_id, 20);

  if (detailLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner className="size-8" />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4">
      {/* Strategy Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>{strategy.strategy_name}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="mb-1 text-gray-500 text-sm">Portfolio Value</p>
              <p className="font-semibold text-lg">
                ${strategy.current_value.toLocaleString("en-US")} HKD
              </p>
            </div>
            <div>
              <p className="mb-1 text-gray-500 text-sm">Total P&L</p>
              <p className="font-semibold text-lg">
                {formatChange(strategy.total_pnl_pct)}
              </p>
            </div>
            <div>
              <p className="mb-1 text-gray-500 text-sm">Status</p>
              <p className="font-semibold text-lg capitalize">{strategy.status}</p>
            </div>
          </div>
          
          {detail?.strategy_prompt && (
            <div className="mt-4 border-gray-200 border-t pt-4">
              <p className="mb-2 font-medium text-gray-700 text-sm">Strategy Logic:</p>
              <p className="text-gray-600 text-sm leading-relaxed">
                {detail.strategy_prompt}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Positions, Trades, and AI Decisions Tabs */}
      <Card className="flex flex-1 flex-col min-h-0">
        <Tabs defaultValue="positions" className="flex flex-1 flex-col min-h-0">
          <CardHeader className="pb-3 flex-shrink-0">
            <TabsList className="w-fit">
              <TabsTrigger value="positions">
                Positions ({positions.length})
              </TabsTrigger>
              <TabsTrigger value="trades">
                Trade History ({trades.length})
              </TabsTrigger>
              <TabsTrigger value="ai-decisions">
                🤖 AI Decisions ({aiDecisions.length})
              </TabsTrigger>
            </TabsList>
          </CardHeader>

          <CardContent className="flex-1 min-h-0 p-0">
            <TabsContent value="positions" className="h-full p-0 m-0 data-[state=active]:flex data-[state=active]:flex-col">
              <ScrollContainer className="flex-1 min-h-0">
                {positionsLoading ? (
                  <div className="flex items-center justify-center p-8">
                    <Spinner className="size-6" />
                  </div>
                ) : positions.length === 0 ? (
                  <div className="p-8 text-center text-gray-500 text-sm">
                    No open positions
                  </div>
                ) : (
                  <table className="w-full">
                    <thead className="sticky top-0 bg-gray-50 text-gray-700 text-xs uppercase">
                      <tr>
                        <th className="px-4 py-3 text-left">Symbol</th>
                        <th className="px-4 py-3 text-right">Lots</th>
                        <th className="px-4 py-3 text-right">Avg Price</th>
                        <th className="px-4 py-3 text-right">Current</th>
                        <th className="px-4 py-3 text-right">Value</th>
                        <th className="px-4 py-3 text-right">P&L %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map((position) => (
                        <PositionRow key={position.symbol} position={position} />
                      ))}
                    </tbody>
                  </table>
                )}
              </ScrollContainer>
            </TabsContent>

            <TabsContent value="trades" className="h-full p-0 m-0 data-[state=active]:flex data-[state=active]:flex-col">
              <ScrollContainer className="flex-1 min-h-0">
                {tradesLoading ? (
                  <div className="flex items-center justify-center p-8">
                    <Spinner className="size-6" />
                  </div>
                ) : trades.length === 0 ? (
                  <div className="p-8 text-center text-gray-500 text-sm">
                    No trades yet
                  </div>
                ) : (
                  <table className="w-full">
                    <thead className="sticky top-0 bg-gray-50 text-gray-700 text-xs uppercase">
                      <tr>
                        <th className="px-4 py-3 text-left">Time</th>
                        <th className="px-4 py-3 text-left">Symbol</th>
                        <th className="px-4 py-3 text-left">Side</th>
                        <th className="px-4 py-3 text-right">Lots</th>
                        <th className="px-4 py-3 text-right">Price</th>
                        <th className="px-4 py-3 text-right">Total Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trades.map((trade) => (
                        <TradeRow key={trade.trade_id} trade={trade} />
                      ))}
                    </tbody>
                  </table>
                )}
              </ScrollContainer>
            </TabsContent>

            <TabsContent value="ai-decisions" className="h-full p-0 m-0 data-[state=active]:flex data-[state=active]:flex-col">
              <ScrollContainer className="flex-1 min-h-0">
                {aiDecisionsLoading ? (
                  <div className="flex items-center justify-center p-8">
                    <Spinner className="size-6" />
                  </div>
                ) : aiDecisions.length === 0 ? (
                  <div className="p-8 text-center text-gray-500 text-sm">
                    <p className="mb-2">No AI decisions yet</p>
                    <p className="text-xs">AI will analyze the market and make recommendations every rebalance cycle</p>
                  </div>
                ) : (
                  <div className="divide-y divide-gray-200">
                    {aiDecisions.map((decision, index) => (
                      <AIDecisionRow key={decision.timestamp} decision={decision} index={index} />
                    ))}
                  </div>
                )}
              </ScrollContainer>
            </TabsContent>
          </CardContent>
        </Tabs>
      </Card>
    </div>
  );
});

HKStrategyDetail.displayName = "HKStrategyDetail";

export default HKStrategyDetail;

