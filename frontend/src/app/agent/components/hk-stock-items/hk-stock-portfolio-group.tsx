import type { FC } from "react";
import { LineChart as LineChartIcon, Wallet } from "lucide-react";
import type { HKPortfolioValuePoint, HKStockPosition } from "@/api/hk-stock";
import ScrollContainer from "@/components/shared/scroll/scroll-container";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface HKStockPortfolioGroupProps {
  positions: HKStockPosition[];
  portfolioHistory: HKPortfolioValuePoint[];
}

const HKStockPortfolioGroup: FC<HKStockPortfolioGroupProps> = ({
  positions,
  portfolioHistory,
}) => {
  const hasPositions = positions && positions.length > 0;
  const hasHistory = portfolioHistory && portfolioHistory.length > 0;
  
  // Keep only the last 20 data points for better visualization
  const recentHistory = portfolioHistory.slice(-20);
  
  // Generate a key based on the latest timestamp to force chart re-render
  const chartKey = recentHistory.length > 0 
    ? recentHistory[recentHistory.length - 1].timestamp 
    : 'empty';

  return (
    <div className="flex flex-1 flex-col gap-8 overflow-y-auto p-6">
      {/* Portfolio Value History Section */}
      <div className="flex flex-col gap-6 flex-shrink-0">
        <h3 className="font-semibold text-base text-gray-950">
          Portfolio Value History
        </h3>
        <div className="h-[200px]">
          {hasHistory ? (
            <div className="h-full rounded-xl border bg-white p-4" key={chartKey}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={recentHistory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="timestamp"
                    tick={{ fontSize: 11 }}
                    interval="preserveStartEnd"
                    tickFormatter={(value) => {
                      const date = new Date(value);
                      return date.toLocaleTimeString('en-US', { 
                        hour: 'numeric', 
                        minute: '2-digit',
                        hour12: true
                      });
                    }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `$${(value / 1000).toFixed(1)}K`}
                    domain={['dataMin - 1000', 'dataMax + 1000']}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      padding: '8px 12px',
                    }}
                    labelFormatter={(value) => {
                      const date = new Date(value);
                      return date.toLocaleString('en-US', { 
                        month: 'short', 
                        day: 'numeric',
                        hour: '2-digit', 
                        minute: '2-digit' 
                      });
                    }}
                    formatter={(value: number) => [`$${value.toFixed(2)}`, 'Total Value']}
                  />
                  <Line
                    type="monotone"
                    dataKey="total_value"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={{ fill: '#3b82f6', r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center rounded-xl border-2 border-gray-200 bg-gray-50/50">
              <div className="flex flex-col items-center gap-4 px-6 py-12 text-center">
                <div className="flex size-14 items-center justify-center rounded-full bg-gray-100">
                  <LineChartIcon className="size-7 text-gray-400" />
                </div>
                <div className="flex flex-col gap-2">
                  <p className="font-semibold text-base text-gray-700">
                    No portfolio value data
                  </p>
                  <p className="max-w-xs text-gray-500 text-sm leading-relaxed">
                    Portfolio value chart will appear once trading begins
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Positions Section */}
      <div className="flex flex-col gap-4 flex-shrink-0">
        <h3 className="font-semibold text-base text-gray-950">Positions</h3>
        {hasPositions ? (
          <ScrollContainer className="max-h-[500px]">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>
                    <p className="font-normal text-gray-400 text-sm">Symbol</p>
                  </TableHead>
                  <TableHead className="text-right">
                    <p className="font-normal text-gray-400 text-sm">Lots</p>
                  </TableHead>
                  <TableHead className="text-right">
                    <p className="font-normal text-gray-400 text-sm">Shares</p>
                  </TableHead>
                  <TableHead className="text-right">
                    <p className="font-normal text-gray-400 text-sm">
                      Avg Price
                    </p>
                  </TableHead>
                  <TableHead className="text-right">
                    <p className="font-normal text-gray-400 text-sm">
                      Current Price
                    </p>
                  </TableHead>
                  <TableHead className="text-right">
                    <p className="font-normal text-gray-400 text-sm">
                      Market Value
                    </p>
                  </TableHead>
                  <TableHead className="text-right">
                    <p className="font-normal text-gray-400 text-sm">P&L</p>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {positions.map((position) => {
                  const isProfitable = position.unrealized_pnl >= 0;
                  const pnlColor = isProfitable
                    ? "text-green-600"
                    : "text-red-600";

                  return (
                    <TableRow key={position.symbol}>
                      <TableCell>
                        <p className="font-medium text-gray-900 text-sm">
                          {position.symbol.replace("HKEX:", "")}
                        </p>
                      </TableCell>
                      <TableCell className="text-right">
                        <p className="text-gray-900 text-sm">
                          {position.lots}
                        </p>
                      </TableCell>
                      <TableCell className="text-right">
                        <p className="text-gray-600 text-sm">
                          {position.quantity}
                        </p>
                      </TableCell>
                      <TableCell className="text-right">
                        <p className="text-gray-900 text-sm">
                          ${position.avg_price.toFixed(2)}
                        </p>
                      </TableCell>
                      <TableCell className="text-right">
                        <p className="text-gray-900 text-sm">
                          ${position.current_price.toFixed(2)}
                        </p>
                      </TableCell>
                      <TableCell className="text-right">
                        <p className="font-medium text-gray-900 text-sm">
                          ${position.market_value.toLocaleString("en-US", {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                          })}
                        </p>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex flex-col items-end">
                          <p className={`font-medium text-sm ${pnlColor}`}>
                            {isProfitable ? "+" : ""}
                            ${Math.abs(position.unrealized_pnl).toLocaleString(
                              "en-US",
                              {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              }
                            )}
                          </p>
                          <p className={`text-xs ${pnlColor}`}>
                            {isProfitable ? "+" : ""}
                            {position.unrealized_pnl_pct.toFixed(2)}%
                          </p>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </ScrollContainer>
        ) : (
          <div className="flex min-h-[240px] items-center justify-center rounded-xl border-2 border-gray-200 bg-gray-50/50">
            <div className="flex flex-col items-center gap-4 px-6 py-12 text-center">
              <div className="flex size-14 items-center justify-center rounded-full bg-gray-100">
                <Wallet className="size-7 text-gray-400" />
              </div>
              <div className="flex flex-col gap-2">
                <p className="font-semibold text-base text-gray-700">
                  No open positions
                </p>
                <p className="max-w-xs text-gray-500 text-sm leading-relaxed">
                  Positions will appear here when trades are opened
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default HKStockPortfolioGroup;

