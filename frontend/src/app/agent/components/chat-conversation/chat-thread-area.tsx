import { type FC, Fragment, memo } from "react";
import ScrollContainer from "@/components/shared/scroll/scroll-container";
import { cn } from "@/lib/utils";
import type { ConversationView } from "@/types/agent";
import ChatItemArea from "./chat-item-area";
import ChatStreamingIndicator from "./chat-streaming-indicator";

interface ChatThreadAreaProps {
  className?: string;
  threads: ConversationView["threads"];
  isStreaming: boolean;
  conversationMetadata?: any;
}

const ChatThreadArea: FC<ChatThreadAreaProps> = ({
  className,
  threads,
  isStreaming,
  conversationMetadata,
}) => {
  // Extract current task status from conversation metadata
  const currentTask = conversationMetadata?.currentTaskStatus;
  let statusMessage: string | undefined;
  
  if (currentTask) {
    const { agentName, taskTitle } = currentTask;
    if (agentName && taskTitle) {
      statusMessage = `[${agentName}] ${taskTitle}`;
    } else if (agentName) {
      statusMessage = `${agentName} is working...`;
    } else if (taskTitle) {
      statusMessage = taskTitle;
    }
  }
  
  return (
    <ScrollContainer
      className={cn("w-full flex-1 space-y-6 py-6", className)}
      autoScrollToBottom
    >
      <main className="main-chat-area mx-auto space-y-6">
        {Object.entries(threads).map(([threadId, thread]) => {
          return (
            <Fragment key={threadId}>
              {/* Render all tasks within this thread */}
              {Object.entries(thread.tasks).map(([taskId, task]) => {
                if (task.items && task.items.length > 0) {
                  return <ChatItemArea key={taskId} items={task.items} />;
                }
                return null;
              })}
            </Fragment>
          );
        })}

        {/* Streaming indicator with current status */}
        {isStreaming && <ChatStreamingIndicator statusMessage={statusMessage} />}
      </main>
    </ScrollContainer>
  );
};

export default memo(ChatThreadArea);
