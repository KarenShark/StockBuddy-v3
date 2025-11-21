import type { FC } from "react";
import { History } from "lucide-react";
import type { HKStockTrade } from "@/api/hk-stock";
import ScrollContainer from "@/components/shared/scroll/scroll-container";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface HKStockTradeHistoryGroupProps {
  trades: HKStockTrade[];
}

const HKStockTradeHistoryGroup: FC<HKStockTradeHistoryGroupProps> = ({
  trades,
}) => {
  const hasTrades = trades && trades.length > 0;

  return (
    <div className="flex flex-1 flex-col gap-6 border-r p-6 overflow-hidden">
      <div className="flex items-center justify-between flex-shrink-0">
        <h3 className="font-semibold text-base text-gray-950">Trade History</h3>
        {hasTrades && (
          <span className="rounded-full bg-gray-100 px-3 py-1 font-medium text-gray-600 text-sm">
            {trades.length} trades
          </span>
        )}
      </div>

      {hasTrades ? (
        <ScrollContainer className="flex-1 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">Time</p>
                </TableHead>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">Symbol</p>
                </TableHead>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">Side</p>
                </TableHead>
                <TableHead className="text-right">
                  <p className="font-normal text-gray-400 text-sm">Quantity</p>
                </TableHead>
                <TableHead className="text-right">
                  <p className="font-normal text-gray-400 text-sm">Price</p>
                </TableHead>
                <TableHead className="text-right">
                  <p className="font-normal text-gray-400 text-sm">Total</p>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {trades.map((trade) => {
                const isBuy = trade.side === "BUY";
                const sideColor = isBuy ? "text-green-600" : "text-red-600";
                const sideBg = isBuy ? "bg-green-50" : "bg-red-50";

                return (
                  <TableRow key={trade.trade_id}>
                    <TableCell>
                      <p className="text-gray-600 text-sm">
                        {new Date(trade.timestamp).toLocaleString("en-US", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </TableCell>
                    <TableCell>
                      <p className="font-medium text-gray-900 text-sm">
                        {trade.symbol.replace("HKEX:", "")}
                      </p>
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-block rounded px-2 py-1 font-medium text-xs ${sideBg} ${sideColor}`}
                      >
                        {trade.side}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <p className="text-gray-900 text-sm">{trade.quantity}</p>
                    </TableCell>
                    <TableCell className="text-right">
                      <p className="text-gray-900 text-sm">
                        ${trade.price.toFixed(2)}
                      </p>
                    </TableCell>
                    <TableCell className="text-right">
                      <p className="font-medium text-gray-900 text-sm">
                        ${trade.total_value.toLocaleString("en-US", {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </p>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </ScrollContainer>
      ) : (
        <div className="flex min-h-[400px] flex-1 items-center justify-center rounded-xl border-2 border-gray-200 bg-gray-50/50">
          <div className="flex flex-col items-center gap-4 px-6 py-12 text-center">
            <div className="flex size-14 items-center justify-center rounded-full bg-gray-100">
              <History className="size-7 text-gray-400" />
            </div>
            <div className="flex flex-col gap-2">
              <p className="font-semibold text-base text-gray-700">
                No trade history
              </p>
              <p className="max-w-xs text-gray-500 text-sm leading-relaxed">
                Your completed trades will appear here
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HKStockTradeHistoryGroup;

