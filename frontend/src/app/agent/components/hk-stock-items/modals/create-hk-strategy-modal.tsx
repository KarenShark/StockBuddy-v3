import { useForm } from "@tanstack/react-form";
import { Loader2 } from "lucide-react";
import { type FC, memo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import {
  useCreateHKStrategy,
  type CreateHKStockStrategyRequest,
} from "@/api/hk-stock-strategy";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import CloseButton from "@/components/shared/button/close-button";
import { MultiSelect } from "@/components/shared/multi-select";
import ScrollContainer from "@/components/shared/scroll/scroll-container";

interface CreateHKStrategyModalProps {
  children?: React.ReactNode;
}

// Popular HK stock symbols
const HK_STOCK_SYMBOLS = [
  { value: "00700", label: "00700 - Tencent" },
  { value: "09988", label: "09988 - Alibaba" },
  { value: "03690", label: "03690 - Meituan" },
  { value: "01810", label: "01810 - Xiaomi" },
  { value: "09618", label: "09618 - JD.com" },
  { value: "00941", label: "00941 - China Mobile" },
  { value: "02318", label: "02318 - Ping An" },
  { value: "01299", label: "01299 - AIA" },
  { value: "00388", label: "00388 - HKEX" },
  { value: "00939", label: "00939 - CCB" },
];

// Validation schema
const formSchema = z.object({
  strategy_name: z.string().min(1, "Strategy name is required"),
  symbols: z.array(z.string()).min(1, "At least one symbol is required"),
  initial_capital: z.number().min(100000, "Minimum capital is HKD 100,000"),
  max_position_size: z.number().min(0.05).max(1.0),
  max_positions: z.number().int().min(1).max(20),
  strategy_prompt: z.string().min(10, "Strategy description must be at least 10 characters"),
  rebalance_interval: z.number().int().min(60).max(3600),
});

const CreateHKStrategyModal: FC<CreateHKStrategyModalProps> = ({ children }) => {
  const [open, setOpen] = useState(false);
  const { mutateAsync: createStrategy, isPending } = useCreateHKStrategy();

  const form = useForm({
    defaultValues: {
      strategy_name: "",
      symbols: ["00700", "09988"],
      initial_capital: 1000000,
      max_position_size: 0.3,
      max_positions: 5,
      strategy_prompt: "",
      rebalance_interval: 300,
    },
    validators: {
      onSubmit: formSchema,
    },
    onSubmit: async ({ value }) => {
      try {
        const request: CreateHKStockStrategyRequest = {
          strategy_name: value.strategy_name,
          symbols: value.symbols,
          initial_capital: value.initial_capital,
          max_position_size: value.max_position_size,
          max_positions: value.max_positions,
          strategy_prompt: value.strategy_prompt,
          rebalance_interval: value.rebalance_interval,
        };

        await createStrategy(request);
        
        toast.success("Strategy Created", {
          description: `${value.strategy_name} has been created and started`,
        });
        
        setOpen(false);
        form.reset();
      } catch (error) {
        toast.error("Failed to create strategy", {
          description: error instanceof Error ? error.message : "Unknown error",
        });
      }
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>

      <DialogContent
        className="flex max-h-[90vh] min-h-96 max-w-2xl flex-col"
        showCloseButton={false}
        aria-describedby={undefined}
      >
        <DialogTitle className="flex items-center justify-between px-1">
          <h2 className="font-semibold text-lg">Create HK Stock Strategy</h2>
          <CloseButton onClick={() => setOpen(false)} />
        </DialogTitle>

        <ScrollContainer>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              e.stopPropagation();
              form.handleSubmit();
            }}
            className="space-y-6 px-1 py-4"
          >
            {/* Strategy Name */}
            <form.Field name="strategy_name">
              {(field) => (
                <FieldGroup>
                  <FieldLabel required>Strategy Name</FieldLabel>
                  <Field>
                    <Input
                      name={field.name}
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                      placeholder="e.g., HK Tech Growth"
                    />
                  </Field>
                  <FieldError>{field.state.meta.errors?.[0]?.message}</FieldError>
                </FieldGroup>
              )}
            </form.Field>

            {/* Trading Symbols */}
            <form.Field name="symbols">
              {(field) => (
                <FieldGroup>
                  <FieldLabel required>Trading Symbols</FieldLabel>
                  <Field>
                    <MultiSelect
                      options={HK_STOCK_SYMBOLS}
                      value={field.state.value}
                      onValueChange={(selected) => {
                        field.handleChange(selected);
                      }}
                      placeholder="Select HK stocks to trade"
                    />
                  </Field>
                  <FieldError>{field.state.meta.errors?.[0]?.message}</FieldError>
                </FieldGroup>
              )}
            </form.Field>

            {/* Initial Capital */}
            <form.Field name="initial_capital">
              {(field) => (
                <FieldGroup>
                  <FieldLabel required>Initial Capital (HKD)</FieldLabel>
                  <Field>
                    <Input
                      type="number"
                      name={field.name}
                      value={field.state.value}
                      onChange={(e) => field.handleChange(Number(e.target.value))}
                      onBlur={field.handleBlur}
                      min={100000}
                      step={100000}
                    />
                  </Field>
                  <FieldError>{field.state.meta.errors?.[0]?.message}</FieldError>
                </FieldGroup>
              )}
            </form.Field>

            {/* Risk Parameters */}
            <div className="grid grid-cols-2 gap-4">
              <form.Field name="max_position_size">
                {(field) => (
                  <FieldGroup>
                    <FieldLabel required>Max Position Size</FieldLabel>
                    <Field>
                      <Input
                        type="number"
                        name={field.name}
                        value={field.state.value}
                        onChange={(e) => field.handleChange(Number(e.target.value))}
                        onBlur={field.handleBlur}
                        min={0.05}
                        max={1.0}
                        step={0.05}
                      />
                    </Field>
                    <p className="text-gray-500 text-xs">
                      Max % of capital per position (0.05 - 1.0)
                    </p>
                    <FieldError>{field.state.meta.errors?.[0]?.message}</FieldError>
                  </FieldGroup>
                )}
              </form.Field>

              <form.Field name="max_positions">
                {(field) => (
                  <FieldGroup>
                    <FieldLabel required>Max Positions</FieldLabel>
                    <Field>
                      <Input
                        type="number"
                        name={field.name}
                        value={field.state.value}
                        onChange={(e) => field.handleChange(Number(e.target.value))}
                        onBlur={field.handleBlur}
                        min={1}
                        max={20}
                        step={1}
                      />
                    </Field>
                    <p className="text-gray-500 text-xs">
                      Maximum concurrent positions (1 - 20)
                    </p>
                    <FieldError>{field.state.meta.errors?.[0]?.message}</FieldError>
                  </FieldGroup>
                )}
              </form.Field>
            </div>

            {/* Rebalance Interval */}
            <form.Field name="rebalance_interval">
              {(field) => (
                <FieldGroup>
                  <FieldLabel required>Rebalance Interval (seconds)</FieldLabel>
                  <Field>
                    <Input
                      type="number"
                      name={field.name}
                      value={field.state.value}
                      onChange={(e) => field.handleChange(Number(e.target.value))}
                      onBlur={field.handleBlur}
                      min={60}
                      max={3600}
                      step={60}
                    />
                  </Field>
                  <p className="text-gray-500 text-xs">
                    How often to check and rebalance positions (60 - 3600 seconds)
                  </p>
                  <FieldError>{field.state.meta.errors?.[0]?.message}</FieldError>
                </FieldGroup>
              )}
            </form.Field>

            {/* Strategy Prompt */}
            <form.Field name="strategy_prompt">
              {(field) => (
                <FieldGroup>
                  <FieldLabel required>Strategy Description</FieldLabel>
                  <Field>
                    <Textarea
                      name={field.name}
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                      placeholder="Describe your trading strategy, e.g., 'Buy on RSI oversold, sell on RSI overbought...'"
                      rows={4}
                    />
                  </Field>
                  <p className="text-gray-500 text-xs">
                    Describe your strategy logic and trading rules
                  </p>
                  <FieldError>{field.state.meta.errors?.[0]?.message}</FieldError>
                </FieldGroup>
              )}
            </form.Field>

            {/* Submit Button */}
            <div className="flex justify-end gap-3 border-gray-200 border-t pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => setOpen(false)}
                disabled={isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="mr-2 size-4 animate-spin" />}
                Create & Start Strategy
              </Button>
            </div>
          </form>
        </ScrollContainer>
      </DialogContent>
    </Dialog>
  );
};

export default memo(CreateHKStrategyModal);

