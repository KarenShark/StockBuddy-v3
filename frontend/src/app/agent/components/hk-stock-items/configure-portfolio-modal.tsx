import { useState } from "react";
import { Settings, Upload, Plus, X } from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";

interface Position {
  symbol: string;
  name: string;
  lots: number;
  avgPrice: number;
}

interface ConfigurePortfolioModalProps {
  onSubmit: (positions: Position[]) => void;
}

export function ConfigurePortfolioModal({ onSubmit }: ConfigurePortfolioModalProps) {
  const [open, setOpen] = useState(false);
  const [positions, setPositions] = useState<Position[]>([]);
  const [csvText, setCsvText] = useState("");

  // Add single position
  const addPosition = () => {
    setPositions([
      ...positions,
      { symbol: "", name: "", lots: 1, avgPrice: 0 },
    ]);
  };

  // Remove position
  const removePosition = (index: number) => {
    setPositions(positions.filter((_, i) => i !== index));
  };

  // Update position
  const updatePosition = (index: number, field: keyof Position, value: any) => {
    const updated = [...positions];
    updated[index] = { ...updated[index], [field]: value };
    setPositions(updated);
  };

  // Import from CSV
  const importFromCSV = () => {
    try {
      const lines = csvText.trim().split("\n");
      const imported: Position[] = [];

      for (let i = 1; i < lines.length; i++) {
        const parts = lines[i].split(",").map((s) => s.trim());
        if (parts.length >= 4) {
          imported.push({
            symbol: parts[0],
            name: parts[1],
            lots: parseInt(parts[2]) || 1,
            avgPrice: parseFloat(parts[3]) || 0,
          });
        }
      }

      setPositions(imported);
      setCsvText("");
      alert(`Successfully imported ${imported.length} positions`);
    } catch (error) {
      alert("CSV format error, please check format");
    }
  };

  // Submit
  const handleSubmit = () => {
    const valid = positions.every(
      (p) => p.symbol && p.lots > 0 && p.avgPrice > 0
    );

    if (!valid) {
      alert("Please fill in complete position information (stock code, lots, cost price)");
      return;
    }

    onSubmit(positions);
    setOpen(false);
  };

  // Example CSV template
  const csvTemplate = `Symbol,Name,Lots,AvgPrice
00700,Tencent,10,320.5
09988,Alibaba,5,75.2
00941,China Mobile,8,54.8`;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2">
          <Settings className="size-4" />
          Configure Portfolio
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[80vh] overflow-y-auto sm:max-w-[700px]">
        <DialogHeader>
          <DialogTitle>Import Initial Positions</DialogTitle>
          <DialogDescription>
            Configure your existing positions, Agent will monitor and trade based on this
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* CSV Import */}
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
            <div className="mb-2 flex items-center gap-2">
              <Upload className="size-4 text-blue-600" />
              <Label className="text-blue-800 font-medium">Quick Import (CSV)</Label>
            </div>
            <Textarea
              placeholder={csvTemplate}
              value={csvText}
              onChange={(e) => setCsvText(e.target.value)}
              className="mb-2 font-mono text-sm"
              rows={5}
            />
            <Button
              size="sm"
              variant="secondary"
              onClick={importFromCSV}
              disabled={!csvText.trim()}
            >
              Import CSV Data
            </Button>
          </div>

          {/* Manual Add */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="font-medium">Current Position List</Label>
              <Button size="sm" variant="outline" onClick={addPosition}>
                <Plus className="mr-1 size-4" />
                Add Position
              </Button>
            </div>

            {positions.length === 0 ? (
              <div className="py-8 text-center text-gray-400 text-sm">
                No positions, click "Add Position" or use CSV import
              </div>
            ) : (
              <div className="space-y-3">
                {positions.map((pos, index) => (
                  <div
                    key={index}
                    className="grid grid-cols-[2fr_2fr_1fr_1.5fr_auto] gap-2 rounded-lg border p-3"
                  >
                    <div>
                      <Label className="text-xs">Stock Code</Label>
                      <Input
                        placeholder="00700"
                        value={pos.symbol}
                        onChange={(e) =>
                          updatePosition(index, "symbol", e.target.value)
                        }
                      />
                    </div>
                    <div>
                      <Label className="text-xs">Stock Name</Label>
                      <Input
                        placeholder="Tencent"
                        value={pos.name}
                        onChange={(e) =>
                          updatePosition(index, "name", e.target.value)
                        }
                      />
                    </div>
                    <div>
                      <Label className="text-xs">Lots</Label>
                      <Input
                        type="number"
                        min="1"
                        value={pos.lots}
                        onChange={(e) =>
                          updatePosition(index, "lots", parseInt(e.target.value))
                        }
                      />
                    </div>
                    <div>
                      <Label className="text-xs">Cost Price (HKD)</Label>
                      <Input
                        type="number"
                        step="0.01"
                        value={pos.avgPrice}
                        onChange={(e) =>
                          updatePosition(
                            index,
                            "avgPrice",
                            parseFloat(e.target.value)
                          )
                        }
                      />
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => removePosition(index)}
                      className="mt-5"
                    >
                      <X className="size-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Statistics */}
          {positions.length > 0 && (
            <div className="rounded-lg bg-gray-50 p-3 text-sm">
              <p className="text-gray-600">
                Total <strong>{positions.length}</strong> stocks, Total lots:
                <strong>{positions.reduce((sum, p) => sum + p.lots, 0)}</strong>
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={positions.length === 0}>
            Confirm Import ({positions.length})
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

