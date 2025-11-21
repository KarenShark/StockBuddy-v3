import { useState } from "react";
import { Brain, TrendingUp, AlertTriangle, DollarSign } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

interface StrategyConfig {
  enabled: boolean;
  strategy: string;
  stopLoss: number; // Stop loss percentage
  takeProfit: number; // Take profit percentage
  maxPositionSize: number; // Max position size per stock (%)
  monitorInterval: number; // Monitor interval (minutes)
  rsiOversold: number; // RSI oversold threshold
  rsiOverbought: number; // RSI overbought threshold
  useMACD: boolean;
  useBollinger: boolean;
}

interface StrategyConfigModalProps {
  currentConfig?: StrategyConfig;
  onSubmit: (config: StrategyConfig) => void;
}

const DEFAULT_CONFIG: StrategyConfig = {
  enabled: false,
  strategy: "technical",
  stopLoss: 5,
  takeProfit: 10,
  maxPositionSize: 20,
  monitorInterval: 15,
  rsiOversold: 30,
  rsiOverbought: 70,
  useMACD: true,
  useBollinger: true,
};

export function StrategyConfigModal({
  currentConfig,
  onSubmit,
}: StrategyConfigModalProps) {
  const [open, setOpen] = useState(false);
  const [config, setConfig] = useState<StrategyConfig>(
    currentConfig || DEFAULT_CONFIG
  );

  const updateConfig = (field: keyof StrategyConfig, value: any) => {
    setConfig({ ...config, [field]: value });
  };

  const handleSubmit = () => {
    onSubmit(config);
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2">
          <Brain className="size-4" />
          Trading Strategy
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Auto Trading Strategy Configuration</DialogTitle>
          <DialogDescription>
            Set monitoring rules and trading strategy, Agent will auto-trade based on this
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Enable Switch */}
          <div className="flex items-center justify-between rounded-lg border border-green-200 bg-green-50 p-4">
            <div className="space-y-0.5">
              <Label className="text-base">Enable Auto Trading</Label>
              <p className="text-green-700 text-xs">
                Agent will execute trades automatically based on strategy when enabled
              </p>
            </div>
            <Switch
              checked={config.enabled}
              onCheckedChange={(checked) => updateConfig("enabled", checked)}
            />
          </div>

          {/* Strategy Selection */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <TrendingUp className="size-4" />
              Trading Strategy
            </Label>
            <Select
              value={config.strategy}
              onValueChange={(value) => updateConfig("strategy", value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="technical">
                  Technical Analysis (RSI + MACD + Bollinger)
                </SelectItem>
                <SelectItem value="momentum">Momentum (Trend Following)</SelectItem>
                <SelectItem value="mean_reversion">
                  Mean Reversion (Oversold Bounce)
                </SelectItem>
                <SelectItem value="custom">Custom (AI Decision)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Risk Management */}
          <div className="space-y-4 rounded-lg border p-4">
            <Label className="flex items-center gap-2 text-base">
              <AlertTriangle className="size-4" />
              Risk Management
            </Label>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-xs">Stop Loss (%)</Label>
                <Input
                  type="number"
                  min="0"
                  max="50"
                  step="0.5"
                  value={config.stopLoss}
                  onChange={(e) =>
                    updateConfig("stopLoss", parseFloat(e.target.value))
                  }
                />
                <p className="text-gray-500 text-xs">
                  Auto stop loss when price drops beyond this %
                </p>
              </div>

              <div className="space-y-2">
                <Label className="text-xs">Take Profit (%)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  step="0.5"
                  value={config.takeProfit}
                  onChange={(e) =>
                    updateConfig("takeProfit", parseFloat(e.target.value))
                  }
                />
                <p className="text-gray-500 text-xs">
                  Auto take profit when price rises beyond this %
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-xs">Max Position Size per Stock (%)</Label>
              <Input
                type="number"
                min="5"
                max="100"
                step="5"
                value={config.maxPositionSize}
                onChange={(e) =>
                  updateConfig("maxPositionSize", parseFloat(e.target.value))
                }
              />
              <p className="text-gray-500 text-xs">
                Maximum proportion of total assets for a single stock
              </p>
            </div>
          </div>

          {/* Technical Indicators */}
          <div className="space-y-4 rounded-lg border p-4">
            <Label className="flex items-center gap-2 text-base">
              <DollarSign className="size-4" />
              Technical Indicators
            </Label>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-xs">RSI Oversold Threshold</Label>
                <Input
                  type="number"
                  min="10"
                  max="50"
                  value={config.rsiOversold}
                  onChange={(e) =>
                    updateConfig("rsiOversold", parseInt(e.target.value))
                  }
                />
              </div>

              <div className="space-y-2">
                <Label className="text-xs">RSI Overbought Threshold</Label>
                <Input
                  type="number"
                  min="50"
                  max="90"
                  value={config.rsiOverbought}
                  onChange={(e) =>
                    updateConfig("rsiOverbought", parseInt(e.target.value))
                  }
                />
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-xs">Use MACD Indicator</Label>
                <Switch
                  checked={config.useMACD}
                  onCheckedChange={(checked) => updateConfig("useMACD", checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-xs">Use Bollinger Bands</Label>
                <Switch
                  checked={config.useBollinger}
                  onCheckedChange={(checked) =>
                    updateConfig("useBollinger", checked)
                  }
                />
              </div>
            </div>
          </div>

          {/* Monitor Interval */}
          <div className="space-y-2">
            <Label className="text-xs">Monitor Interval (minutes)</Label>
            <Select
              value={config.monitorInterval.toString()}
              onValueChange={(value) =>
                updateConfig("monitorInterval", parseInt(value))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="5">5 minutes (High Frequency)</SelectItem>
                <SelectItem value="15">15 minutes (Recommended)</SelectItem>
                <SelectItem value="30">30 minutes (Standard)</SelectItem>
                <SelectItem value="60">60 minutes (Low Frequency)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-gray-500 text-xs">
              Frequency at which Agent checks market and executes strategy
            </p>
          </div>

          {/* Warning */}
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3">
            <p className="text-yellow-800 text-xs">
              ⚠️ <strong>Risk Warning</strong>: Even in paper trading, please set parameters carefully.
              Auto trading strategies may lead to frequent trades and asset volatility.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit}>
            {config.enabled ? "Enable Strategy" : "Save Config"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

