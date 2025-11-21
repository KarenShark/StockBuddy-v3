import { memo, type FC, useState } from "react";
import { toast } from "sonner";
import {
  useHKStrategies,
  useUpdateHKStrategy,
  type HKStockStrategyInfo,
} from "@/api/hk-stock-strategy";
import { Spinner } from "@/components/ui/spinner";
import HKStrategyDetail from "./hk-strategy-detail";
import HKStrategyList from "./hk-strategy-list";

export const HKStrategyManager: FC = memo(() => {
  const [selectedStrategy, setSelectedStrategy] = useState<HKStockStrategyInfo | undefined>();
  
  const { data: strategies = [], isLoading, error } = useHKStrategies();
  const { mutateAsync: updateStrategy } = useUpdateHKStrategy();

  const handleStopStrategy = async (strategyId: string) => {
    try {
      await updateStrategy({
        strategyId,
        updates: { status: "stopped" },
      });
      toast.success("Strategy Stopped", {
        description: "The strategy has been stopped successfully",
      });
      
      // Clear selection if stopped strategy was selected
      if (selectedStrategy?.strategy_id === strategyId) {
        setSelectedStrategy(undefined);
      }
    } catch (error) {
      toast.error("Failed to stop strategy", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex size-full items-center justify-center">
        <Spinner className="size-8" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex size-full items-center justify-center">
        <div className="text-center">
          <p className="mb-2 text-gray-900 text-lg font-semibold">
            Failed to load strategies
          </p>
          <p className="text-gray-600 text-sm">
            {error instanceof Error ? error.message : "Unknown error"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex size-full gap-4 p-6">
      {/* Strategy List */}
      <HKStrategyList
        strategies={strategies}
        selectedStrategy={selectedStrategy}
        onStrategySelect={setSelectedStrategy}
        onStrategyStop={handleStopStrategy}
      />

      {/* Strategy Detail */}
      {selectedStrategy ? (
        <HKStrategyDetail strategy={selectedStrategy} />
      ) : (
        <div className="flex flex-1 items-center justify-center rounded-xl border-2 border-gray-200 border-dashed">
          <div className="text-center text-gray-500">
            <p className="text-lg font-medium">No Strategy Selected</p>
            <p className="mt-2 text-sm">
              Select a strategy from the list to view details
            </p>
          </div>
        </div>
      )}
    </div>
  );
});

HKStrategyManager.displayName = "HKStrategyManager";

export default HKStrategyManager;

