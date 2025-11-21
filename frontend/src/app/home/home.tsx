import { useState } from "react";
import { useNavigate } from "react-router";
import { useAllPollTaskList } from "@/api/conversation";
import ScrollContainer from "@/components/shared/scroll/scroll-container";
import { HOME_STOCK_SHOW } from "@/constants/stock";
import { agentSuggestions } from "@/mock/agent-data";
import ChatInputArea from "../agent/components/chat-conversation/chat-input-area";
import {
  AgentSuggestionsList,
  AgentTaskCards,
  SparklineStockList,
} from "./components";
import { useSparklineStocks } from "./hooks/use-sparkline-stocks";

function Home() {
  const navigate = useNavigate();
  const [inputValue, setInputValue] = useState<string>("");

  const { data: allPollTaskList } = useAllPollTaskList();
  const { sparklineStocks } = useSparklineStocks(HOME_STOCK_SHOW);

  const handleAgentClick = (agentId: string) => {
    navigate(`/agent/${agentId}`);
  };

  return (
    <div className="flex h-full min-w-[800px] flex-col gap-3">
      <SparklineStockList stocks={sparklineStocks} />

      {/* Main content area - always show welcome screen, tasks moved to Quick Links */}
      <section className="flex w-full flex-1 flex-col items-center justify-center gap-8 overflow-hidden py-8">
        <div className="space-y-4 text-center">
          <h1 className="font-semibold text-4xl tracking-tight">
            StockBuddy
          </h1>
          <p className="text-muted-foreground text-lg">
            Your AI-powered financial research assistant
            </p>
          </div>

          <ChatInputArea
            className="w-3/4 max-w-[800px]"
            value={inputValue}
            onChange={(value) => setInputValue(value)}
            onSend={() =>
              navigate("/agent/SuperAgent", {
                state: {
                  inputValue,
                },
              })
            }
          />

          <AgentSuggestionsList
            suggestions={agentSuggestions.map((suggestion) => ({
              ...suggestion,
              onClick: () => handleAgentClick(suggestion.id),
            }))}
          />
        </section>
    </div>
  );
}

export default Home;
