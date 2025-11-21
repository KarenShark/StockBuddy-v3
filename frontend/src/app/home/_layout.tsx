import { Plus } from "lucide-react";
import { Outlet } from "react-router";
import { Button } from "@/components/ui/button";
import ScrollContainer from "@/components/shared/scroll/scroll-container";
import QuickLinks from "./components/quick-links";
import StockList from "./components/stock-list";
import StockSearchModal from "./components/stock-search-modal";

export default function HomeLayout() {
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-hidden bg-gray-100 py-4 pr-4 pl-2">
      <h1 className="font-medium text-3xl">👋 Welcome to StockBuddy !</h1>

      <div className="flex flex-1 gap-3 overflow-hidden">
        <main className="h-full flex-1 overflow-hidden rounded-lg">
          <ScrollContainer className="h-full">
            <Outlet />
          </ScrollContainer>
        </main>

        <aside className="flex min-w-62 max-w-80 flex-col overflow-hidden rounded-lg bg-white">
          <StockList />

          <StockSearchModal>
            <Button
              variant="secondary"
              className="mx-5 mt-4 mb-3 font-bold text-sm hover:bg-gray-200"
            >
              <Plus size={16} />
              Add Stocks
            </Button>
          </StockSearchModal>

          <QuickLinks />
        </aside>
      </div>
    </div>
  );
}
