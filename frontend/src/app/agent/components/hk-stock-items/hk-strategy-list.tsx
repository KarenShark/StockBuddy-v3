import { Plus, TrendingUp } from "lucide-react";
import { memo, type FC } from "react";
import { Button } from "@/components/ui/button";
import ScrollContainer from "@/components/shared/scroll/scroll-container";
import type { HKStockStrategyInfo } from "@/api/hk-stock-strategy";
import HKStrategyCard from "./hk-strategy-card";
import CreateHKStrategyModal from "./modals/create-hk-strategy-modal";

interface HKStrategyListProps {
  strategies: HKStockStrategyInfo[];
  selectedStrategy?: HKStockStrategyInfo;
  onStrategySelect?: (strategy: HKStockStrategyInfo) => void;
  onStrategyStop?: (strategyId: string) => void;
}

export const HKStrategyList: FC<HKStrategyListProps> = memo(({
  strategies,
  selectedStrategy,
  onStrategySelect,
  onStrategyStop,
}) => {
  const hasStrategies = strategies.length > 0;

  return (
    <div className="flex min-w-96 flex-col gap-3">
      {hasStrategies ? (
        <ScrollContainer className="flex-1">
          <div className="flex flex-col gap-3">
            {strategies.map((strategy) => (
              <HKStrategyCard
                key={strategy.strategy_id}
                strategy={strategy}
                isSelected={
                  selectedStrategy?.strategy_id === strategy.strategy_id
                }
                onClick={() => onStrategySelect?.(strategy)}
                onStop={() => onStrategyStop?.(strategy.strategy_id)}
              />
            ))}
          </div>
        </ScrollContainer>
      ) : (
        <div className="flex flex-1 items-center justify-center rounded-xl border-2 border-gray-200 border-dashed bg-gray-50/50">
          <div className="flex flex-col items-center gap-4 px-6 py-12 text-center">
            <div className="flex size-14 items-center justify-center rounded-full bg-gray-100">
              <TrendingUp className="size-7 text-gray-400" />
            </div>
            <div className="flex flex-col gap-2">
              <p className="font-semibold text-base text-gray-700">
                No HK Stock Strategies
              </p>
              <p className="max-w-xs text-gray-500 text-sm leading-relaxed">
                Create your first strategy to start trading HK stocks
              </p>
            </div>
          </div>
        </div>
      )}
      
      <CreateHKStrategyModal>
        <Button
          variant="outline"
          className="w-full gap-3 rounded-lg py-4 text-base"
        >
          <Plus className="size-6" />
          Create HK Stock Strategy
        </Button>
      </CreateHKStrategyModal>
    </div>
  );
});

HKStrategyList.displayName = "HKStrategyList";

export default HKStrategyList;

