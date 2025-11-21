import { create } from "mutative";
import { AGENT_SECTION_COMPONENT_TYPE } from "@/constants/agent";
import type {
  AgentConversationsStore,
  ChatItem,
  ConversationView,
  SectionComponentType,
  SSEData,
  TaskView,
  ThreadView,
} from "@/types/agent";

// Unified helper to ensure conversation->thread->task path exists
function ensurePath(
  draft: AgentConversationsStore,
  data: {
    conversation_id: string;
    thread_id: string;
    task_id: string;
  },
): {
  conversation: ConversationView;
  thread: ThreadView;
  task: TaskView;
} {
  // Ensure conversation with sections initialized
  draft[data.conversation_id] ??= {
    threads: {},
    sections: {} as Record<SectionComponentType, ThreadView>,
  };
  const conversation = draft[data.conversation_id];

  // Ensure thread
  conversation.threads[data.thread_id] ??= { tasks: {} };
  const thread = conversation.threads[data.thread_id];

  // Ensure task
  thread.tasks[data.task_id] ??= { items: [] };
  const task = thread.tasks[data.task_id];

  return { conversation, thread, task };
}

// Helper to ensure section->task path exists
function ensureSection(
  conversation: ConversationView,
  componentType: SectionComponentType,
  taskId: string,
): TaskView {
  conversation.sections[componentType] ??= { tasks: {} };
  conversation.sections[componentType].tasks[taskId] ??= { items: [] };

  return conversation.sections[componentType].tasks[taskId];
}

// Check if item has mergeable content
function hasContent(
  item: ChatItem,
): item is ChatItem & { payload: { content: string } } {
  return "payload" in item && "content" in item.payload;
}

// Helper function: add or update item in task
function addOrUpdateItem(
  task: TaskView,
  newItem: ChatItem,
  event: "append" | "replace",
): void {
  const existingIndex = task.items.findIndex(
    (item) => item.item_id === newItem.item_id,
  );

  if (existingIndex < 0) {
    task.items.push(newItem);
    return;
  }

  const existingItem = task.items[existingIndex];
  // Merge content for streaming events, replace for others
  if (event === "append" && hasContent(existingItem) && hasContent(newItem)) {
    existingItem.payload.content += newItem.payload.content;
  } else {
    task.items[existingIndex] = newItem;
  }
}

// Generic handler for events that create chat items
function handleChatItemEvent(
  draft: AgentConversationsStore,
  data: ChatItem,
  event: "append" | "replace" = "append",
) {
  const { conversation, task } = ensurePath(draft, data);

  // Auto-maintain sections - only non-markdown types create independent sections
  const componentType = data.component_type;
  if (
    componentType &&
    AGENT_SECTION_COMPONENT_TYPE.includes(componentType as SectionComponentType)
  ) {
    const sectionTask = ensureSection(
      conversation,
      componentType as SectionComponentType,
      data.task_id,
    );
    addOrUpdateItem(sectionTask, data, event);
    return;
  }

  addOrUpdateItem(task, data, event);
}

// Core event processor - processes a single SSE event
function processSSEEvent(draft: AgentConversationsStore, sseData: SSEData) {
  const { event, data } = sseData;

  switch (event) {
    // component_generator preserves original component_type
    case "component_generator": {
      const component_type = data.payload.component_type;

      switch (component_type) {
        case "scheduled_task_result":
        case "subagent_conversation":
          handleChatItemEvent(
            draft,
            {
              ...data,
              component_type,
            },
            "replace",
          );
          break;
        default:
          handleChatItemEvent(draft, {
            ...data,
            component_type,
          });
          break;
      }
      break;
    }

    case "thread_started":
    case "message_chunk":
    case "message":
    case "task_failed":
    case "plan_failed":
    case "plan_require_user_input":
      // Other events are set as markdown type
      handleChatItemEvent(draft, { component_type: "markdown", ...data });
      break;

    case "reasoning":
      // Reasoning events get their own special renderer
      handleChatItemEvent(draft, { component_type: "reasoning", ...data });
      break;

    case "tool_call_started":
    case "tool_call_completed": {
      handleChatItemEvent(
        draft,
        {
          component_type: "tool_call",
          ...data,
          payload: {
            content: JSON.stringify(data.payload),
          },
        },
        "replace",
      );
      break;
    }

    case "reasoning_started":
    case "reasoning_completed":
      ensurePath(draft, data);
      break;
    
    case "task_started": {
      // Store current task status for streaming indicator
      ensurePath(draft, data);
      const conversation = draft.conversations[data.conversation_id];
      if (conversation) {
        const taskTitle = data.metadata?.task_title;
        const agentName = data.metadata?.agent_name || data.agent_name;
        if (taskTitle || agentName) {
          // Store in conversation metadata for easy access
          if (!conversation.metadata) {
            conversation.metadata = {};
          }
          conversation.metadata.currentTaskStatus = {
            taskTitle,
            agentName,
            taskId: data.task_id,
          };
        }
      }
      break;
    }
    
    case "task_completed":
    case "task_cancelled": {
      // Track completed tasks and clear current task status
      ensurePath(draft, data);
      const conversation = draft[data.conversation_id];
      if (conversation) {
        // Initialize metadata if needed
        if (!conversation.metadata) {
          conversation.metadata = {};
        }
        
        // Add to completed tasks set
        if (!conversation.metadata.completedTaskIds) {
          conversation.metadata.completedTaskIds = new Set();
        }
        conversation.metadata.completedTaskIds.add(data.task_id);
        
        // Clear current task if it's the one that just completed
        if (conversation.metadata.currentTaskStatus?.taskId === data.task_id) {
        delete conversation.metadata.currentTaskStatus;
        }
      }
      break;
    }

    default:
      break;
  }
}

export function updateAgentConversationsStore(
  store: AgentConversationsStore,
  sseData: SSEData,
) {
  // Use mutative to create new state with type-safe event handling
  return create(store, (draft) => {
    processSSEEvent(draft, sseData);
  });
}

/**
 * Batch update agent conversations store with multiple SSE events
 * @param store - Current agent conversations store
 * @param conversationId - The conversation ID to clear and update
 * @param sseDataList - Array of SSE events to process
 * @returns Updated store with all events processed atomically
 */
export function batchUpdateAgentConversationsStore(
  store: AgentConversationsStore,
  conversationId: string,
  sseDataList: SSEData[],
  clearHistory = false,
) {
  // Process all events in a single mutative transaction for better performance
  return create(store, (draft) => {
    // Clear existing data for this conversation
    if (clearHistory && draft[conversationId]) {
      delete draft[conversationId];
    }

    // Process all new events
    for (const sseData of sseDataList) {
      processSSEEvent(draft, sseData);
    }
  });
}
