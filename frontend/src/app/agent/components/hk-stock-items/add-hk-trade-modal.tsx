import { useState } from "react";
import { Plus } from "lucide-react";
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

interface AddHKTradeModalProps {
  onSubmit: (trade: {
    symbol: string;
    side: "BUY" | "SELL";
    lots: number;
  }) => void;
}

// Popular HK stocks list
const POPULAR_HK_STOCKS = [
  { code: "00700", name: "Tencent" },
  { code: "09988", name: "Alibaba-SW" },
  { code: "00941", name: "China Mobile" },
  { code: "01299", name: "AIA" },
  { code: "00939", name: "CCB" },
  { code: "01398", name: "ICBC" },
  { code: "00388", name: "HKEX" },
  { code: "03690", name: "Meituan-W" },
  { code: "01810", name: "Xiaomi-W" },
  { code: "02318", name: "Ping An" },
];

export function AddHKTradeModal({ onSubmit }: AddHKTradeModalProps) {
  const [open, setOpen] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [customSymbol, setCustomSymbol] = useState("");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [lots, setLots] = useState("1");

  const handleSubmit = () => {
    const finalSymbol = symbol === "custom" ? customSymbol : symbol;
    
    if (!finalSymbol || !lots) {
      alert("Please fill in all information");
      return;
    }

    onSubmit({
      symbol: finalSymbol,
      side,
      lots: parseInt(lots),
    });

    // Reset form
    setSymbol("");
    setCustomSymbol("");
    setLots("1");
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          className="w-full gap-2 rounded-lg py-6 text-base"
        >
          <Plus className="size-5" />
          Quick Trade
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>HK Stock Trade</DialogTitle>
          <DialogDescription>
            Select stock and enter quantity (in lots)
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-6 py-4">
          {/* Trade Direction */}
          <div className="grid gap-2">
            <Label htmlFor="side">Trade Direction</Label>
            <Select
              value={side}
              onValueChange={(value) => setSide(value as "BUY" | "SELL")}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BUY">
                  <span className="text-green-600">Buy (BUY)</span>
                </SelectItem>
                <SelectItem value="SELL">
                  <span className="text-red-600">Sell (SELL)</span>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Stock Selection */}
          <div className="grid gap-2">
            <Label htmlFor="symbol">Select Stock</Label>
            <Select value={symbol} onValueChange={setSymbol}>
              <SelectTrigger>
                <SelectValue placeholder="Select popular stock or custom" />
              </SelectTrigger>
              <SelectContent>
                {POPULAR_HK_STOCKS.map((stock) => (
                  <SelectItem key={stock.code} value={stock.code}>
                    {stock.code} - {stock.name}
                  </SelectItem>
                ))}
                <SelectItem value="custom">Custom Stock Code...</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Custom Stock Code */}
          {symbol === "custom" && (
            <div className="grid gap-2">
              <Label htmlFor="customSymbol">Stock Code</Label>
              <Input
                id="customSymbol"
                placeholder="e.g. 00700"
                value={customSymbol}
                onChange={(e) => setCustomSymbol(e.target.value)}
              />
              <p className="text-gray-500 text-xs">
                Enter 5-digit code (e.g. 00700)
              </p>
            </div>
          )}

          {/* Lots */}
          <div className="grid gap-2">
            <Label htmlFor="lots">Trading Lots</Label>
            <Input
              id="lots"
              type="number"
              min="1"
              placeholder="1"
              value={lots}
              onChange={(e) => setLots(e.target.value)}
            />
            <p className="text-gray-500 text-xs">
              1 lot = 100 shares (varies by stock)
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            className={side === "BUY" ? "bg-green-600 hover:bg-green-700" : "bg-red-600 hover:bg-red-700"}
          >
            {side === "BUY" ? "Confirm Buy" : "Confirm Sell"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

