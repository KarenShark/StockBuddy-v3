import { TrendingDown, TrendingUp } from "lucide-react";
import { memo, type FC } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TimeUtils } from "@/lib/time";
import { cn, formatChange, getChangeType } from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import type { HKStockStrategyInfo } from "@/api/hk-stock-strategy";

interface HKStrategyCardProps {
  strategy: HKStockStrategyInfo;
  isSelected?: boolean;
  onClick?: () => void;
  onStop?: () => void;
}

export const HKStrategyCard: FC<HKStrategyCardProps> = memo(({
  strategy,
  isSelected = false,
  onClick,
  onStop,
}) => {
  const { increaseColor, decreaseColor } = useStockColors();
  const changeType = getChangeType(strategy.total_pnl_pct);

  return (
    <div
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          onClick?.();
        }
      }}
      className={cn(
        "cursor-pointer rounded-lg border bg-white p-4 transition-all hover:shadow-md",
        isSelected ? "border-blue-500 bg-blue-50/50" : "border-gray-200"
      )}
    >
      {/* Header */}
      <div className="mb-3 flex items-start justify-between">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 text-base">
            {strategy.strategy_name}
          </h3>
          <p className="mt-1 text-gray-500 text-xs">
            {strategy.symbols.length} symbols • {TimeUtils.formatRelative(strategy.created_at)}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Badge
            variant={strategy.status === "running" ? "default" : "secondary"}
            className={cn(
              "text-xs",
              strategy.status === "running" && "bg-green-500"
            )}
          >
            {strategy.status === "running" ? "Running" : "Stopped"}
          </Badge>
          
          {strategy.status === "running" && onStop && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={(e) => e.stopPropagation()}
                >
                  Stop
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                <AlertDialogHeader>
                  <AlertDialogTitle>Stop Strategy</AlertDialogTitle>
                  <AlertDialogDescription>
                    Are you sure you want to stop "{strategy.strategy_name}"? 
                    This will pause all trading activities for this strategy.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={(e) => {
                      e.stopPropagation();
                      onStop();
                    }}
                  >
                    Stop Strategy
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </div>

      {/* Symbols */}
      <div className="mb-3 flex flex-wrap gap-1">
        {strategy.symbols.slice(0, 5).map((symbol) => (
          <span
            key={symbol}
            className="rounded bg-gray-100 px-2 py-0.5 font-mono text-gray-700 text-xs"
          >
            {symbol}
          </span>
        ))}
        {strategy.symbols.length > 5 && (
          <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-500 text-xs">
            +{strategy.symbols.length - 5} more
          </span>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 border-gray-100 border-t pt-3">
        {/* Portfolio Value */}
        <div>
          <p className="mb-1 text-gray-500 text-xs">Portfolio Value</p>
          <p className="font-semibold text-gray-900 text-sm">
            ${strategy.current_value.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })} HKD
          </p>
        </div>

        {/* P&L */}
        <div>
          <p className="mb-1 text-gray-500 text-xs">Total P&L</p>
          <div className="flex items-center gap-1.5">
            {changeType === "increase" ? (
              <TrendingUp className="size-3.5" style={{ color: increaseColor }} />
            ) : changeType === "decrease" ? (
              <TrendingDown className="size-3.5" style={{ color: decreaseColor }} />
            ) : null}
            <span
              className="font-semibold text-sm"
              style={{
                color: changeType === "increase"
                  ? increaseColor
                  : changeType === "decrease"
                    ? decreaseColor
                    : "inherit",
              }}
            >
              {formatChange(strategy.total_pnl_pct)}
            </span>
          </div>
        </div>

        {/* Positions */}
        <div>
          <p className="mb-1 text-gray-500 text-xs">Open Positions</p>
          <p className="font-medium text-gray-900 text-sm">
            {strategy.position_count}
          </p>
        </div>

        {/* Trades */}
        <div>
          <p className="mb-1 text-gray-500 text-xs">Total Trades</p>
          <p className="font-medium text-gray-900 text-sm">
            {strategy.trade_count}
          </p>
        </div>
      </div>
    </div>
  );
});

HKStrategyCard.displayName = "HKStrategyCard";

export default HKStrategyCard;

