import { Activity, TrendingUp, Newspaper, ChevronRight } from "lucide-react";
import { memo } from "react";
import { useNavigate } from "react-router";
import { useAllPollTaskList } from "@/api/conversation";
import { useHKStrategies } from "@/api/hk-stock-strategy";
import { Badge } from "@/components/ui/badge";
import ScrollContainer from "@/components/shared/scroll/scroll-container";
import { cn } from "@/lib/utils";
import { TimeUtils } from "@/lib/time";

interface QuickLinkItemProps {
  icon: React.ReactNode;
  title: string;
  subtitle?: string;
  badge?: string;
  badgeVariant?: "default" | "secondary" | "destructive" | "outline";
  onClick: () => void;
}

const QuickLinkItem = memo<QuickLinkItemProps>(
  ({ icon, title, subtitle, badge, badgeVariant = "default", onClick }) => {
    return (
      <div
        onClick={onClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            onClick();
          }
        }}
        className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 transition-all hover:border-blue-300 hover:bg-blue-50/50 hover:shadow-sm"
      >
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-50 to-blue-100">
          {icon}
        </div>
        
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <div className="flex items-center gap-2">
            <p className="truncate font-medium text-gray-900 text-sm">
              {title}
            </p>
            {badge && (
              <Badge
                variant={badgeVariant}
                className="shrink-0 px-1.5 py-0 text-xs"
              >
                {badge}
              </Badge>
            )}
          </div>
          {subtitle && (
            <p className="truncate text-gray-500 text-xs">{subtitle}</p>
          )}
        </div>
        
        <ChevronRight className="size-4 shrink-0 text-gray-400" />
      </div>
    );
  }
);

QuickLinkItem.displayName = "QuickLinkItem";

export const QuickLinks = memo(() => {
  const navigate = useNavigate();
  
  // Get running strategies
  const { data: strategies = [] } = useHKStrategies("running");
  
  // Get ongoing tasks (news, research, etc.)
  const { data: allPollTaskList = [] } = useAllPollTaskList();

  // Filter to only show active/running items
  const runningStrategies = strategies.filter((s) => s.status === "running");
  // Show only tasks with results, limit to 5 recent
  const activeTasks = allPollTaskList
    .filter((task) => task.results && task.results.length > 0)
    .slice(0, 5);

  const hasItems = runningStrategies.length > 0 || activeTasks.length > 0;

  if (!hasItems) {
    return null; // Don't show section if no items
  }

  return (
    <div className="flex flex-1 flex-col gap-2 border-gray-200 border-t px-5 py-4 overflow-hidden">
      <div className="flex items-center gap-2 mb-1">
        <Activity className="size-4 text-gray-600" />
        <h3 className="font-semibold text-gray-900 text-sm">Quick Links</h3>
      </div>

      <ScrollContainer className="flex-1">
        <div className="flex flex-col gap-2">
          {/* Running Strategies */}
          {runningStrategies.map((strategy) => (
            <QuickLinkItem
              key={strategy.strategy_id}
              icon={<TrendingUp className="size-4 text-blue-600" />}
              title={strategy.strategy_name}
              subtitle={`${strategy.symbols.length} symbols • ${strategy.position_count} positions`}
              badge="Running"
              badgeVariant="default"
              onClick={() => {
                // Navigate to HK Stock Agent with strategies tab
                navigate("/agent/HKStockAgent", {
                  state: { activeTab: "strategies" },
                });
              }}
            />
          ))}

          {/* Active Tasks */}
          {activeTasks.map((task) => {
            // Determine task type and icon
            const isNewsTask = task.agent_name?.toLowerCase().includes("news");
            const icon = isNewsTask ? (
              <Newspaper className="size-4 text-purple-600" />
            ) : (
              <Activity className="size-4 text-green-600" />
            );

            // Get the first result for navigation
            const firstResult = task.results[0];
            const conversationId = firstResult?.data?.conversation_id;

            return (
              <QuickLinkItem
                key={`${task.agent_name}-${task.update_time}`}
                icon={icon}
                title={task.agent_name}
                subtitle={TimeUtils.fromUTCRelative(task.update_time)}
                badge="Active"
                badgeVariant="default"
                onClick={() => {
                  // Navigate to the conversation
                  if (conversationId) {
                    navigate(`/agent/${task.agent_name}?id=${conversationId}`);
                  } else {
                    navigate(`/agent/${task.agent_name}`);
                  }
                }}
              />
            );
          })}
        </div>
      </ScrollContainer>
    </div>
  );
});

QuickLinks.displayName = "QuickLinks";

export default QuickLinks;

