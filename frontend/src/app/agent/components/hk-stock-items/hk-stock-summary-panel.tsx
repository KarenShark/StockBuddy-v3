import type { FC } from "react";
import { TrendingDown, TrendingUp, Wallet } from "lucide-react";
import type { HKStockPortfolioSummary } from "@/api/hk-stock";

interface HKStockSummaryPanelProps {
  summary: HKStockPortfolioSummary;
}

const HKStockSummaryPanel: FC<HKStockSummaryPanelProps> = ({ summary }) => {
  const isProfitable = summary.total_pnl >= 0;
  const pnlColor = isProfitable ? "text-green-600" : "text-red-600";
  const pnlBgColor = isProfitable ? "bg-green-50" : "bg-red-50";

  return (
    <div className="flex flex-col gap-6">
      {/* Total Assets Card */}
      <div className="rounded-lg border bg-gradient-to-br from-blue-50 to-indigo-50 p-6 shadow-sm">
        <div className="mb-2 flex items-center gap-2 text-gray-600">
          <Wallet className="size-5" />
          <span className="font-medium text-sm">Total Assets</span>
        </div>
        <p className="font-bold text-3xl text-gray-900">
          ${summary.total_assets.toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </p>
        <p className="mt-1 text-gray-500 text-xs">HKD</p>
      </div>

      {/* P&L Card */}
      <div className={`rounded-lg border p-6 shadow-sm ${pnlBgColor}`}>
        <div className="mb-2 flex items-center gap-2 text-gray-600">
          {isProfitable ? (
            <TrendingUp className="size-5 text-green-600" />
          ) : (
            <TrendingDown className="size-5 text-red-600" />
          )}
          <span className="font-medium text-sm">Unrealized P&L</span>
        </div>
        <p className={`font-bold text-2xl ${pnlColor}`}>
          {isProfitable ? "+" : ""}
          ${Math.abs(summary.total_pnl).toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </p>
        <p className={`mt-1 font-medium text-sm ${pnlColor}`}>
          {isProfitable ? "+" : ""}
          {summary.total_pnl_pct.toFixed(2)}%
        </p>
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* Cash */}
        <div className="rounded-lg border bg-white p-4">
          <p className="mb-1 text-gray-500 text-xs">Available Cash</p>
          <p className="font-semibold text-gray-900 text-lg">
            ${summary.total_cash.toLocaleString("en-US", {
              minimumFractionDigits: 0,
              maximumFractionDigits: 0,
            })}
          </p>
        </div>

        {/* Positions Value */}
        <div className="rounded-lg border bg-white p-4">
          <p className="mb-1 text-gray-500 text-xs">Positions Value</p>
          <p className="font-semibold text-gray-900 text-lg">
            ${summary.total_market_value.toLocaleString("en-US", {
              minimumFractionDigits: 0,
              maximumFractionDigits: 0,
            })}
          </p>
        </div>

        {/* Position Count */}
        <div className="rounded-lg border bg-white p-4 col-span-2">
          <p className="mb-1 text-gray-500 text-xs">Open Positions</p>
          <p className="font-semibold text-gray-900 text-lg">
            {summary.position_count} stocks
          </p>
        </div>
      </div>

      {/* Paper Trading Notice */}
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
        <p className="text-amber-800 text-xs">
          ⚠️ <strong>Paper Trading Mode</strong> - All trades are simulated
          with virtual money. No real transactions.
        </p>
      </div>
    </div>
  );
};

export default HKStockSummaryPanel;

